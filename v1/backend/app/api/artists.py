from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import ArtistApplication, User
from app.schemas.artist import ArtistApplicationCreate, ArtistApplicationOut

router = APIRouter(prefix="/artists", tags=["artists"])


@router.post("/apply")
async def apply_artist(
    body: ArtistApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role == "artist":
        raise ApiError(
            "CONFLICT", "You are already an artist", http_status=409
        )

    # 진행 중 신청 있는지 확인
    existing = await db.execute(
        select(ArtistApplication).where(
            ArtistApplication.user_id == user.id,
            ArtistApplication.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "CONFLICT", "You already have a pending application", http_status=409
        )

    application = ArtistApplication(
        user_id=user.id,
        portfolio_urls=body.portfolio_urls,
        school=body.school,
        intro_video_url=body.intro_video_url,
        sample_images=body.sample_images,
        statement=body.statement,
        status="pending",
    )
    db.add(application)

    # 관리자에게 알림 (모든 admin 대상)
    admin_result = await db.execute(select(User).where(User.role == "admin"))
    admins = admin_result.scalars().all()
    for admin in admins:
        db.add(
            Notification(
                user_id=admin.id,
                type="artist_application_received",
                title="새 작가 심사 신청",
                body=f"{user.display_name}님이 작가 심사를 신청했습니다.",
                link=f"/admin/applications/{application.id}",
            )
        )

    await db.commit()
    await db.refresh(application)
    return {"data": ArtistApplicationOut.model_validate(application).model_dump(mode="json")}


@router.get("/apply/me")
async def my_application(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ArtistApplication)
        .where(ArtistApplication.user_id == user.id)
        .order_by(ArtistApplication.created_at.desc())
    )
    apps = result.scalars().all()
    return {
        "data": [
            ArtistApplicationOut.model_validate(a).model_dump(mode="json") for a in apps
        ]
    }
