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
from app.models.moderation import Report, Warning
from app.models.notification import Notification
from app.models.post import Post
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
                intro_video_url=app_obj.intro_video_url,
                portfolio_urls=app_obj.portfolio_urls,
                statement=app_obj.statement,
                badge_level="emerging",
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
