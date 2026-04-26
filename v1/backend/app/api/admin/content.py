"""Admin: content moderation endpoints (posts, reports, appeals, warnings)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.moderation import Report, Warning
from app.models.notification import Notification
from app.models.post import Post
from app.models.user import User
from app.schemas.moderation import (
    ReportOut,
    ReportResolveRequest,
    WarningOut,
)
from app.services.moderation import cancel_warning, issue_warning

router = APIRouter(tags=["admin"])


class DigitalArtVerdictRequest(BaseModel):
    verdict: str  # 'approved' | 'rejected'
    note: str | None = None


class PostStatusUpdate(BaseModel):
    status: str
    reason: str | None = None


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


def _target_owner_id_query(target_type: str, target_id):
    if target_type == "post":
        from app.models.post import Post
        return select(Post.author_id).where(Post.id == target_id)
    if target_type == "comment":
        from app.models.post import Comment
        return select(Comment.author_id).where(Comment.id == target_id)
    if target_type == "user":
        return select(User.id).where(User.id == target_id)
    return None


@router.get("/posts/digital-art-queue")
async def digital_art_queue(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin_with_2fa),
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
    admin: User = Depends(require_admin_with_2fa),
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


@router.get("/posts/list")
async def list_posts_admin(
    q: str | None = Query(None),
    type: str | None = Query(None),
    status: str | None = Query(None),
    genre: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin_with_2fa),
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
    _admin: User = Depends(require_admin_with_2fa),
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


@router.get("/reports")
async def list_reports(
    status: str = Query("pending"),
    admin: User = Depends(require_admin_with_2fa),
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
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise ApiError("NOT_FOUND", "Report not found", http_status=404)
    if report.status != "pending":
        raise ApiError("CONFLICT", "Report already handled", http_status=409)

    if body.action == "issue_warning":
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
    admin: User = Depends(require_admin_with_2fa),
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
    admin: User = Depends(require_admin_with_2fa),
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
    admin: User = Depends(require_admin_with_2fa),
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
