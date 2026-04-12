"""User-facing moderation endpoints: report content, view own warnings, appeal."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.moderation import Report, Warning
from app.models.notification import Notification
from app.models.post import Comment, Post
from app.models.user import User
from app.schemas.moderation import (
    AppealRequest,
    ReportCreate,
    ReportOut,
    WarningOut,
)

reports_router = APIRouter(prefix="/reports", tags=["reports"])
warnings_router = APIRouter(prefix="/warnings", tags=["warnings"])


@reports_router.post("")
async def create_report(
    body: ReportCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("report_create"),
):
    # Verify target exists
    if body.target_type == "post":
        result = await db.execute(select(Post).where(Post.id == body.target_id))
        target = result.scalar_one_or_none()
        if not target:
            raise ApiError("NOT_FOUND", "Post not found", http_status=404)
        if target.author_id == user.id:
            raise ApiError(
                "VALIDATION_ERROR",
                "Cannot report your own content",
                http_status=422,
            )
    elif body.target_type == "comment":
        result = await db.execute(
            select(Comment).where(Comment.id == body.target_id)
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ApiError("NOT_FOUND", "Comment not found", http_status=404)
        if target.author_id == user.id:
            raise ApiError(
                "VALIDATION_ERROR",
                "Cannot report your own content",
                http_status=422,
            )
    elif body.target_type == "user":
        result = await db.execute(select(User).where(User.id == body.target_id))
        target = result.scalar_one_or_none()
        if not target:
            raise ApiError("NOT_FOUND", "User not found", http_status=404)
        if target.id == user.id:
            raise ApiError(
                "VALIDATION_ERROR",
                "Cannot report yourself",
                http_status=422,
            )

    report = Report(
        reporter_id=user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        description=body.description,
        status="pending",
    )
    db.add(report)

    # Notify all admins
    admin_result = await db.execute(select(User).where(User.role == "admin"))
    for admin in admin_result.scalars().all():
        db.add(
            Notification(
                user_id=admin.id,
                type="report_received",
                title="새 신고",
                body=f"{body.target_type} 신고: {body.reason}",
                link="/admin/moderation",
            )
        )

    await db.commit()
    await db.refresh(report)
    return {"data": ReportOut.model_validate(report).model_dump(mode="json")}


@warnings_router.get("/mine")
async def my_warnings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Warning)
        .where(Warning.user_id == user.id)
        .order_by(Warning.created_at.desc())
    )
    warnings = list(result.scalars().all())
    return {
        "data": [
            WarningOut.model_validate(w).model_dump(mode="json") for w in warnings
        ]
    }


@warnings_router.post("/{warning_id}/appeal")
async def appeal_warning(
    warning_id: UUID,
    body: AppealRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        raise ApiError("NOT_FOUND", "Warning not found", http_status=404)
    if warning.user_id != user.id:
        raise ApiError("FORBIDDEN", "Not your warning", http_status=403)
    if not warning.is_active:
        raise ApiError(
            "CONFLICT", "Warning already cancelled", http_status=409
        )
    if warning.appealed:
        raise ApiError("CONFLICT", "Already appealed", http_status=409)

    warning.appealed = True
    warning.appeal_note = body.note

    # Notify admins
    admin_result = await db.execute(select(User).where(User.role == "admin"))
    for admin in admin_result.scalars().all():
        db.add(
            Notification(
                user_id=admin.id,
                type="appeal_received",
                title="이의 제기 접수",
                body=f"{user.display_name}님이 경고에 이의를 제기했습니다.",
                link="/admin/moderation",
            )
        )

    await db.commit()
    await db.refresh(warning)
    return {"data": WarningOut.model_validate(warning).model_dump(mode="json")}
