"""Admin: user management endpoints."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.security import hash_password
from app.db.session import get_db
from app.models.notification import Notification
from app.models.user import ArtistApplication, ArtistProfile, User
from app.schemas.artist import ApplicationReviewRequest, ArtistApplicationOut
from app.services.auth_tokens import revoke_user_tokens

log = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# ──────────────────────────────────────────────────────────────────────────────
# 스키마
# ──────────────────────────────────────────────────────────────────────────────

class AdminCreateUserRequest(BaseModel):
    """POST /admin/users 요청 본문."""
    email: EmailStr
    display_name: str = Field(min_length=3, max_length=50)
    role: Literal["user", "artist", "admin"] = "user"
    send_magic_link: bool = True  # 기본값 True — 평문 비밀번호를 admin이 보지 않도록
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class UserUpdateRequest(BaseModel):
    status: str | None = None
    role: str | None = None
    badge_level: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_display_name(raw: str) -> str:
    """소문자 변환 → 앞뒤 공백 제거 → 내부 공백을 underscore로.

    기존 회원가입 패턴과 동일하게 처리한다.
    """
    return raw.strip().lower().replace(" ", "_")


# ──────────────────────────────────────────────────────────────────────────────
# Artist application 관리 endpoints
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# User 관리 endpoints
# ──────────────────────────────────────────────────────────────────────────────

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


@router.post("/users", status_code=201)
async def create_user_by_admin(
    body: AdminCreateUserRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """admin이 사용자를 직접 생성한다.

    보안 원칙:
    - 임시 비밀번호는 bcrypt hash만 DB에 저장, 평문은 즉시 폐기.
    - 응답/로그에 평문 비밀번호 절대 노출 금지.
    - send_magic_link=True 시 사용자가 직접 비밀번호를 설정하도록 유도.
    """
    # 1. email 중복 검증
    existing = await db.scalar(select(User).where(User.email == str(body.email)))
    if existing is not None:
        raise ApiError("ALREADY_EXISTS", "이미 등록된 이메일입니다.", http_status=409)

    # 2. display_name 정규화
    display_name = _normalize_display_name(body.display_name)

    # 3. 임시 비밀번호 생성 — 평문은 즉시 hash 후 폐기
    _tmp_plain = secrets.token_urlsafe(32)
    password_hash = hash_password(_tmp_plain)
    del _tmp_plain  # 평문 즉시 폐기

    # 4. User 생성
    new_user = User(
        email=str(body.email),
        display_name=display_name,
        role=body.role,
        status="active",
        password_hash=password_hash,
        country_code=body.country_code,
    )
    db.add(new_user)
    await db.flush()  # id 확보
    await db.refresh(new_user)

    # 5. 매직 링크 발송
    magic_link_sent = False
    if body.send_magic_link:
        from app.services.magic_link import send_admin_invite_magic_link
        result = await send_admin_invite_magic_link(
            email=str(body.email),
            display_name=display_name,
            role=body.role,
        )
        magic_link_sent = result.get("sent", False)
        if not magic_link_sent:
            log.warning(
                "magic_link_skipped | user_id=%s reason=%s",
                new_user.id,
                result.get("reason", "unknown"),
            )

    await db.commit()
    await db.refresh(new_user)

    # 6. Audit log
    log.info(
        "AUDIT action=admin_create_user admin=%s target=%s role=%s",
        admin.id,
        new_user.id,
        body.role,
    )

    return {
        "data": {
            "id": str(new_user.id),
            "email": new_user.email,
            "display_name": new_user.display_name,
            "role": new_user.role,
            "status": new_user.status,
            "magic_link_sent": magic_link_sent,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        }
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    # ── Self-modify 차단 (line 237~244) ─────────────────────────────────────
    # admin이 자신의 role을 변경하는 것은 허용하지 않는다.
    # (다른 admin이 해야 함 — 4-eyes 원칙)
    if body.role is not None and user.id == admin.id:
        raise ApiError(
            "SELF_MODIFY_FORBIDDEN",
            "자신의 권한은 변경할 수 없습니다.",
            http_status=400,
        )
    # admin이 자신을 정지시키는 것도 차단
    if body.status == "suspended" and user.id == admin.id:
        raise ApiError(
            "SELF_MODIFY_FORBIDDEN",
            "자신의 계정을 정지할 수 없습니다.",
            http_status=400,
        )
    # ────────────────────────────────────────────────────────────────────────

    old_role = user.role

    if body.status and body.status in ("active", "suspended"):
        user.status = body.status
        db.add(Notification(
            user_id=user.id, type="account_status_changed", title="계정 상태 변경",
            body=f"계정이 {'활성화' if body.status == 'active' else '정지'}되었습니다.",
        ))
    if body.role and body.role in ("user", "artist", "admin"):
        user.role = body.role
        await revoke_user_tokens(db, user.id, reason="admin_role_change")
        log.info(
            "AUDIT action=admin_role_change admin=%s target=%s old=%s new=%s",
            admin.id,
            user.id,
            old_role,
            body.role,
        )
    if body.badge_level:
        prof_result = await db.execute(select(ArtistProfile).where(ArtistProfile.user_id == user_id))
        prof = prof_result.scalar_one_or_none()
        if prof:
            prof.badge_level = body.badge_level

    await db.commit()
    return {"data": {"id": str(user.id), "status": user.status, "role": user.role}}
