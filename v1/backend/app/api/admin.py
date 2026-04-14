from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.auction import Auction, Order
from app.models.moderation import Report, Warning
from app.models.notification import Notification
from app.models.post import Follow, Post
from app.models.school import School
from app.models.user import ArtistApplication, ArtistProfile, User
from app.schemas.artist import ApplicationReviewRequest, ArtistApplicationOut
from app.schemas.moderation import (
    ReportOut,
    ReportResolveRequest,
    WarningOut,
)
from app.services.auction_jobs import process_expired_orders_once
from app.services.auth_tokens import revoke_user_tokens
from app.services.moderation import cancel_warning, issue_warning

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/artists/applications")
async def list_applications(
    status: str = Query("pending"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArtistApplication)
        .where(ArtistApplication.status == status)
        .order_by(ArtistApplication.created_at.desc())
    )
    apps = result.scalars().all()
    return {
        "data": [
            ArtistApplicationOut.model_validate(a).model_dump(mode="json") for a in apps
        ]
    }


@router.post("/artists/applications/{application_id}/approve")
async def approve_application(
    application_id: str,
    body: ApplicationReviewRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArtistApplication).where(ArtistApplication.id == application_id)
    )
    app_obj = result.scalar_one_or_none()
    if not app_obj:
        raise ApiError("NOT_FOUND", "Application not found", http_status=404)
    if app_obj.status != "pending":
        raise ApiError("CONFLICT", "Application already reviewed", http_status=409)

    # 1. 신청 승인
    app_obj.status = "approved"
    app_obj.reviewed_by = admin.id
    app_obj.review_note = body.note
    app_obj.reviewed_at = datetime.now(timezone.utc)

    # 2. 유저 role 변경 + 기존 refresh 토큰 무효화 (M2)
    user_result = await db.execute(select(User).where(User.id == app_obj.user_id))
    user = user_result.scalar_one()
    user.role = "artist"
    await revoke_user_tokens(db, user.id, reason="admin_role_change")

    # 3. ArtistProfile 생성
    existing_profile = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == user.id)
    )
    if not existing_profile.scalar_one_or_none():
        db.add(
            ArtistProfile(
                user_id=user.id,
                application_id=app_obj.id,
                verified_by=admin.id,
                school=app_obj.school,
                department=app_obj.department,
                graduation_year=app_obj.graduation_year,
                is_enrolled=getattr(app_obj, "is_enrolled", True),
                genre_tags=app_obj.genre_tags,
                intro_video_url=app_obj.intro_video_url,
                portfolio_urls=app_obj.portfolio_urls,
                representative_works=app_obj.representative_works,
                exhibitions=app_obj.exhibitions,
                awards=app_obj.awards,
                statement=app_obj.statement,
                badge_level="student" if getattr(app_obj, "is_enrolled", True) else "emerging",
            )
        )

    # 4. 신청자에게 알림
    db.add(
        Notification(
            user_id=user.id,
            type="artist_approved",
            title="작가 승인 완료",
            body="축하합니다! 작가 심사가 승인되었습니다.",
            link="/profile",
        )
    )

    await db.commit()
    await db.refresh(app_obj)
    return {"data": ArtistApplicationOut.model_validate(app_obj).model_dump(mode="json")}


@router.post("/artists/applications/{application_id}/reject")
async def reject_application(
    application_id: str,
    body: ApplicationReviewRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArtistApplication).where(ArtistApplication.id == application_id)
    )
    app_obj = result.scalar_one_or_none()
    if not app_obj:
        raise ApiError("NOT_FOUND", "Application not found", http_status=404)
    if app_obj.status != "pending":
        raise ApiError("CONFLICT", "Application already reviewed", http_status=409)

    app_obj.status = "rejected"
    app_obj.reviewed_by = admin.id
    app_obj.review_note = body.note
    app_obj.reviewed_at = datetime.now(timezone.utc)

    db.add(
        Notification(
            user_id=app_obj.user_id,
            type="artist_rejected",
            title="작가 심사 결과",
            body=body.note or "심사가 거절되었습니다. 자세한 내용은 관리자에게 문의해주세요.",
            link="/artists/apply",
        )
    )

    await db.commit()
    await db.refresh(app_obj)
    return {"data": ArtistApplicationOut.model_validate(app_obj).model_dump(mode="json")}


# ─── Digital Art Verdict (G1 P0 fix) ────────────────────────────────────
# Reference: design.md §5.7 digital art verdict flow

class DigitalArtVerdictRequest(BaseModel):
    verdict: str  # 'approved' | 'rejected'
    note: str | None = None


def _post_summary(post: Post) -> dict:
    return {
        "id": str(post.id),
        "author_id": str(post.author_id),
        "type": post.type,
        "title": post.title,
        "status": post.status,
        "digital_art_check": post.digital_art_check,
        "created_at": post.created_at.isoformat(),
        "media": [
            {
                "id": str(m.id),
                "type": m.type,
                "url": m.url,
                "thumbnail_url": m.thumbnail_url,
            }
            for m in (post.media or [])
        ],
    }


@router.get("/posts/digital-art-queue")
async def digital_art_queue(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Posts waiting for digital-art verdict (status=pending_review, check=pending)."""
    result = await db.execute(
        select(Post)
        .where(
            Post.status == "pending_review",
            Post.digital_art_check == "pending",
        )
        .options(selectinload(Post.media))
        .order_by(Post.created_at.asc())
        .limit(limit)
    )
    posts = list(result.scalars().all())
    return {"data": [_post_summary(p) for p in posts]}


@router.post("/posts/{post_id}/digital-art-verdict")
async def digital_art_verdict(
    post_id: UUID,
    body: DigitalArtVerdictRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.verdict not in ("approved", "rejected"):
        raise ApiError(
            "VALIDATION_ERROR",
            "verdict must be 'approved' or 'rejected'",
            http_status=422,
        )

    result = await db.execute(
        select(Post)
        .where(Post.id == post_id)
        .options(selectinload(Post.media))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    if post.digital_art_check not in ("pending", "rejected"):
        raise ApiError(
            "CONFLICT",
            f"Post is not awaiting verdict (current: {post.digital_art_check})",
            http_status=409,
        )

    if body.verdict == "approved":
        post.digital_art_check = "approved"
        post.status = "published"
        notification_title = "포스트 게시 완료"
        notification_body = "디지털 아트 판독을 통과했습니다. 포스트가 공개되었습니다."
    else:
        post.digital_art_check = "rejected"
        post.status = "hidden"
        notification_title = "포스트 게시 거절"
        notification_body = body.note or "디지털 아트로 판독되어 게시가 거절되었습니다."

    db.add(
        Notification(
            user_id=post.author_id,
            type="digital_art_verdict",
            title=notification_title,
            body=notification_body,
            link=f"/posts/{post.id}",
        )
    )

    await db.commit()
    return {"data": _post_summary(post)}


# ─── Auction settlement (Phase 2 Week 10) ──────────────────────────────


@router.post("/auctions/process-expired")
async def trigger_process_expired(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the auction expiry sweep (also runs every 5 min in background)."""
    summary = await process_expired_orders_once(db)
    return {"data": summary}


# ─── Moderation: Reports & Appeals (Phase 3 Week 11) ────────────────────


def _target_owner_id_query(target_type: str, target_id):
    """Helper: build SELECT statement to find owner of report target."""
    if target_type == "post":
        from app.models.post import Post

        return select(Post.author_id).where(Post.id == target_id)
    if target_type == "comment":
        from app.models.post import Comment

        return select(Comment.author_id).where(Comment.id == target_id)
    if target_type == "user":
        return select(User.id).where(User.id == target_id)
    return None


@router.get("/reports")
async def list_reports(
    status: str = Query("pending"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Report)
        .where(Report.status == status)
        .order_by(Report.created_at.desc())
    )
    reports = list(result.scalars().all())
    return {
        "data": [
            ReportOut.model_validate(r).model_dump(mode="json") for r in reports
        ]
    }


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: UUID,
    body: ReportResolveRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise ApiError("NOT_FOUND", "Report not found", http_status=404)
    if report.status != "pending":
        raise ApiError("CONFLICT", "Report already handled", http_status=409)

    if body.action == "issue_warning":
        # Find the offender
        owner_query = _target_owner_id_query(report.target_type, report.target_id)
        if owner_query is None:
            raise ApiError(
                "VALIDATION_ERROR",
                f"Unsupported target_type: {report.target_type}",
                http_status=422,
            )
        owner_result = await db.execute(owner_query)
        owner_id = owner_result.scalar_one_or_none()
        if not owner_id:
            raise ApiError(
                "NOT_FOUND",
                "Reported target no longer exists",
                http_status=404,
            )
        await issue_warning(
            db,
            owner_id,
            body.note or f"신고 처리: {report.reason}",
            issued_by=admin.id,
            report_id=report.id,
        )
        report.status = "resolved"
    elif body.action == "dismiss":
        report.status = "rejected"

    report.handled_by = admin.id
    report.handled_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(report)
    return {"data": ReportOut.model_validate(report).model_dump(mode="json")}


@router.get("/appeals")
async def list_appeals(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Active warnings with pending appeals."""
    result = await db.execute(
        select(Warning)
        .where(Warning.appealed.is_(True), Warning.is_active.is_(True))
        .order_by(Warning.created_at.desc())
    )
    warnings = list(result.scalars().all())
    return {
        "data": [
            WarningOut.model_validate(w).model_dump(mode="json") for w in warnings
        ]
    }


@router.post("/warnings/{warning_id}/cancel")
async def cancel_warning_endpoint(
    warning_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        raise ApiError("NOT_FOUND", "Warning not found", http_status=404)
    if not warning.is_active:
        raise ApiError("CONFLICT", "Already cancelled", http_status=409)

    await cancel_warning(db, warning, cancelled_by=admin.id)
    await db.commit()
    await db.refresh(warning)
    return {"data": WarningOut.model_validate(warning).model_dump(mode="json")}


@router.post("/warnings/{warning_id}/reject-appeal")
async def reject_appeal(
    warning_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        raise ApiError("NOT_FOUND", "Warning not found", http_status=404)
    if not warning.appealed:
        raise ApiError("CONFLICT", "No appeal to reject", http_status=409)
    if not warning.is_active:
        raise ApiError("CONFLICT", "Warning already cancelled", http_status=409)

    # Mark appealed=False but keep warning active
    warning.appealed = False
    warning.appeal_note = (warning.appeal_note or "") + " [관리자 거절]"

    db.add(
        Notification(
            user_id=warning.user_id,
            type="appeal_rejected",
            title="이의 제기 거절",
            body="제출하신 이의 제기가 거절되었습니다.",
            link="/warnings",
        )
    )

    await db.commit()
    await db.refresh(warning)
    return {"data": WarningOut.model_validate(warning).model_dump(mode="json")}


# ═══════════════════════════════════════════════════════════════════════
# P1 Admin Panel — User / School / Content / Transaction Management
# ═══════════════════════════════════════════════════════════════════════


class UserUpdateRequest(BaseModel):
    status: str | None = None
    role: str | None = None
    badge_level: str | None = None


@router.get("/users")
async def list_users(
    q: str | None = Query(None),
    role: str | None = Query(None),
    status: str | None = Query(None),
    country: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(User)
    if q:
        query = query.where(User.display_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if country:
        query = query.where(User.country_code == country)

    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(limit))
    users = result.scalars().all()

    return {
        "data": [
            {
                "id": str(u.id), "email": u.email, "display_name": u.display_name,
                "avatar_url": u.avatar_url, "role": u.role, "status": u.status,
                "country_code": u.country_code, "warning_count": u.warning_count,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    if body.status and body.status in ("active", "suspended"):
        user.status = body.status
        db.add(Notification(
            user_id=user.id, type="account_status_changed", title="계정 상태 변경",
            body=f"계정이 {'활성화' if body.status == 'active' else '정지'}되었습니다.",
        ))
    if body.role and body.role in ("user", "artist", "admin"):
        user.role = body.role
        await revoke_user_tokens(db, user.id, reason="admin_role_change")
    if body.badge_level:
        prof_result = await db.execute(select(ArtistProfile).where(ArtistProfile.user_id == user_id))
        prof = prof_result.scalar_one_or_none()
        if prof:
            prof.badge_level = body.badge_level

    await db.commit()
    return {"data": {"id": str(user.id), "status": user.status, "role": user.role}}


# ─── School Management ──────────────────────────────────────────────────


class SchoolCreateRequest(BaseModel):
    name_ko: str
    name_en: str
    country_code: str
    email_domain: str
    school_type: str = "university"
    logo_url: str | None = None


class SchoolUpdateRequest(BaseModel):
    name_ko: str | None = None
    name_en: str | None = None
    email_domain: str | None = None
    status: str | None = None


@router.get("/schools")
async def list_schools(
    q: str | None = Query(None),
    country: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(School)
    if q:
        query = query.where(School.name_ko.ilike(f"%{q}%") | School.name_en.ilike(f"%{q}%"))
    if country:
        query = query.where(School.country_code == country)
    if status:
        query = query.where(School.status == status)

    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(School.name_en.asc()).offset(offset).limit(limit))
    schools = result.scalars().all()

    return {
        "data": [
            {
                "id": str(s.id), "name_ko": s.name_ko, "name_en": s.name_en,
                "country_code": s.country_code, "email_domain": s.email_domain,
                "school_type": s.school_type, "status": s.status,
            }
            for s in schools
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.post("/schools")
async def create_school(
    body: SchoolCreateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(School).where(School.email_domain == body.email_domain))
    if existing.scalar_one_or_none():
        raise ApiError("CONFLICT", "Email domain already registered", http_status=409)
    school = School(**body.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return {"data": {"id": str(school.id), "name_en": school.name_en, "email_domain": school.email_domain}}


@router.patch("/schools/{school_id}")
async def update_school(
    school_id: UUID,
    body: SchoolUpdateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise ApiError("NOT_FOUND", "School not found", http_status=404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(school, k, v)
    await db.commit()
    return {"data": {"id": str(school.id), "status": school.status}}


# ─── Content Management ─────────────────────────────────────────────────


class PostStatusUpdate(BaseModel):
    status: str
    reason: str | None = None


@router.get("/posts/list")
async def list_posts_admin(
    q: str | None = Query(None),
    type: str | None = Query(None),
    status: str | None = Query(None),
    genre: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(Post).options(selectinload(Post.media))
    if q:
        query = query.where(Post.title.ilike(f"%{q}%") | Post.content.ilike(f"%{q}%"))
    if type:
        query = query.where(Post.type == type)
    if status:
        query = query.where(Post.status == status)
    if genre:
        query = query.where(Post.genre == genre)

    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Post.created_at.desc()).offset(offset).limit(limit))
    posts = result.scalars().all()

    author_ids = list({p.author_id for p in posts})
    author_map = {}
    if author_ids:
        authors = await db.execute(select(User).where(User.id.in_(author_ids)))
        author_map = {u.id: u for u in authors.scalars()}

    return {
        "data": [
            {
                "id": str(p.id), "title": p.title, "type": p.type,
                "genre": p.genre, "status": p.status,
                "like_count": p.like_count, "view_count": p.view_count,
                "author_name": author_map[p.author_id].display_name if p.author_id in author_map else "unknown",
                "thumbnail_url": (p.media[0].thumbnail_url or p.media[0].url) if p.media else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.patch("/posts/{post_id}/status")
async def update_post_status(
    post_id: UUID,
    body: PostStatusUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise ApiError("NOT_FOUND", "Post not found", http_status=404)
    post.status = body.status
    db.add(Notification(
        user_id=post.author_id, type="post_status_changed", title="게시물 상태 변경",
        body=f"'{post.title or '무제'}'이(가) {body.status}로 변경되었습니다." + (f" 사유: {body.reason}" if body.reason else ""),
        link=f"/posts/{post.id}",
    ))
    await db.commit()
    return {"data": {"id": str(post.id), "status": post.status}}


# ─── Transaction Management ─────────────────────────────────────────────


@router.get("/auctions/list")
async def list_auctions_admin(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(Auction)
    if status:
        query = query.where(Auction.status == status)
    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Auction.created_at.desc()).offset(offset).limit(limit))
    auctions = result.scalars().all()

    seller_ids = list({a.seller_id for a in auctions})
    seller_map = {}
    if seller_ids:
        sellers = await db.execute(select(User).where(User.id.in_(seller_ids)))
        seller_map = {u.id: u for u in sellers.scalars()}

    return {
        "data": [
            {
                "id": str(a.id),
                "seller_name": seller_map[a.seller_id].display_name if a.seller_id in seller_map else "unknown",
                "start_price": float(a.start_price), "current_price": float(a.current_price),
                "currency": a.currency, "bid_count": a.bid_count, "status": a.status,
                "end_at": a.end_at.isoformat(),
            }
            for a in auctions
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }


@router.get("/orders/list")
async def list_orders_admin(
    status: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func as sqlfunc

    query = select(Order)
    if status:
        query = query.where(Order.status == status)
    if source:
        query = query.where(Order.source == source)
    total = await db.scalar(select(sqlfunc.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Order.created_at.desc()).offset(offset).limit(limit))
    orders = result.scalars().all()

    user_ids = list({o.buyer_id for o in orders} | {o.seller_id for o in orders})
    user_map = {}
    if user_ids:
        users = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map = {u.id: u for u in users.scalars()}

    return {
        "data": [
            {
                "id": str(o.id),
                "buyer_name": user_map[o.buyer_id].display_name if o.buyer_id in user_map else "unknown",
                "seller_name": user_map[o.seller_id].display_name if o.seller_id in user_map else "unknown",
                "amount": float(o.amount), "currency": o.currency,
                "platform_fee": float(o.platform_fee),
                "source": o.source, "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
        "pagination": {"total": total or 0, "offset": offset, "limit": limit},
    }
