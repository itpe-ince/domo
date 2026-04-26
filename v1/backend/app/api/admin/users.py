"""Admin: user management endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import ArtistApplication, ArtistProfile, User
from app.schemas.artist import ApplicationReviewRequest, ArtistApplicationOut
from app.services.auth_tokens import revoke_user_tokens

from datetime import datetime, timezone

router = APIRouter(tags=["admin"])


class UserUpdateRequest(BaseModel):
    status: str | None = None
    role: str | None = None
    badge_level: str | None = None


@router.get("/artists/applications")
async def list_applications(
    status: str = Query("pending"),
    admin: User = Depends(require_admin_with_2fa),
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
    admin: User = Depends(require_admin_with_2fa),
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

    app_obj.status = "approved"
    app_obj.reviewed_by = admin.id
    app_obj.review_note = body.note
    app_obj.reviewed_at = datetime.now(timezone.utc)

    user_result = await db.execute(select(User).where(User.id == app_obj.user_id))
    user = user_result.scalar_one()
    user.role = "artist"
    await revoke_user_tokens(db, user.id, reason="admin_role_change")

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
    admin: User = Depends(require_admin_with_2fa),
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


@router.get("/users")
async def list_users(
    q: str | None = Query(None),
    role: str | None = Query(None),
    status: str | None = Query(None),
    country: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_admin_with_2fa),
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
    _admin: User = Depends(require_admin_with_2fa),
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
