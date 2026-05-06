"""Device token + notification preferences API — B'-3 push-email-digest-foundation.

Endpoints:
  POST   /me/devices                              — Register push token
  DELETE /me/devices/{device_id}                  — Revoke token (soft-delete)
  GET    /me/notifications/preferences            — Get user preferences
  PATCH  /me/notifications/preferences            — Update user preferences
  POST   /me/test-push                            — Send test push (debug)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.device_token import DeviceToken
from app.models.notification_preferences import NotificationPreferences
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["me-devices"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class DeviceRegisterRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=500, description="FCM or APNs token")
    platform: str = Field(..., pattern="^(fcm|apns)$", description="fcm or apns")
    device_id: str | None = Field(
        None,
        max_length=255,
        description="Caller-provided unique device ID for deduplication",
    )


class NotificationPrefsUpdate(BaseModel):
    push_enabled: bool | None = None
    email_enabled: bool | None = None
    push_per_type: dict | None = Field(
        None,
        description=(
            "Per-type push overrides: "
            "{auction: bool, sponsorship: bool, engagement: bool, system: bool, digest: bool}"
        ),
    )
    email_per_type: dict | None = Field(
        None,
        description=(
            "Per-type email overrides: "
            "{auction: bool, sponsorship: bool, engagement: bool, system: bool, digest: bool}"
        ),
    )
    digest_frequency: str | None = Field(
        None,
        pattern="^(weekly|biweekly|monthly|never)$",
        description="Email digest frequency",
    )


# ─── Device endpoints ─────────────────────────────────────────────────────────


@router.post("/devices")
async def register_device(
    body: DeviceRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register (or upsert) a push token for the current user.

    If a token with the same (user_id, device_id) already exists and is active,
    the token string is updated in place (token rotation). If it was soft-deleted,
    a new row is created.
    """
    now = datetime.now(timezone.utc)

    # Attempt upsert: find existing active row for this device_id
    if body.device_id:
        result = await db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user.id,
                    DeviceToken.device_id == body.device_id,
                    DeviceToken.deleted_at.is_(None),
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.token = body.token
            existing.platform = body.platform
            existing.last_active_at = now
            await db.commit()
            await db.refresh(existing)
            return {"data": _serialize_token(existing)}

    # Also check if this exact token already registered (any device_id)
    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == user.id,
                DeviceToken.token == body.token,
                DeviceToken.deleted_at.is_(None),
            )
        )
    )
    existing_by_token = result.scalar_one_or_none()
    if existing_by_token:
        existing_by_token.last_active_at = now
        if body.device_id:
            existing_by_token.device_id = body.device_id
        await db.commit()
        await db.refresh(existing_by_token)
        return {"data": _serialize_token(existing_by_token)}

    # Create new row
    device = DeviceToken(
        user_id=user.id,
        token=body.token,
        platform=body.platform,
        device_id=body.device_id,
        last_active_at=now,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    log.info(
        "device registered: user=%s platform=%s device_id=%s",
        user.id,
        body.platform,
        body.device_id,
    )
    return {"data": _serialize_token(device)}


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a registered device token (revoke push)."""
    result = await db.execute(
        select(DeviceToken).where(
            DeviceToken.id == device_id,
            DeviceToken.deleted_at.is_(None),
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise ApiError("NOT_FOUND", "Device token not found", http_status=404)
    if device.user_id != user.id:
        raise ApiError("FORBIDDEN", "Not your device", http_status=403)

    device.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"data": {"deleted": True, "id": str(device_id)}}


# ─── Notification preference endpoints ───────────────────────────────────────


def _get_or_create_prefs_query(user_id: uuid.UUID):
    return select(NotificationPreferences).where(
        NotificationPreferences.user_id == user_id
    )


@router.get("/notifications/preferences")
async def get_notification_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's notification preferences.

    If no preferences row exists, returns GDPR defaults (all False).
    """
    result = await db.execute(_get_or_create_prefs_query(user.id))
    prefs = result.scalar_one_or_none()
    if prefs is None:
        # Return defaults without persisting (lazy creation on first PATCH)
        return {
            "data": {
                "user_id": str(user.id),
                "push_enabled": False,
                "email_enabled": False,
                "push_per_type": {},
                "email_per_type": {},
                "digest_frequency": "weekly",
            }
        }
    return {"data": _serialize_prefs(prefs)}


@router.patch("/notifications/preferences")
async def update_notification_preferences(
    body: NotificationPrefsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update (upsert) notification preferences for the current user.

    Only supplied fields are updated. GDPR: toggles must be explicitly set to True
    by the user — never auto-enabled.
    """
    result = await db.execute(_get_or_create_prefs_query(user.id))
    prefs = result.scalar_one_or_none()

    if prefs is None:
        # First time: create with provided values + GDPR defaults
        prefs = NotificationPreferences(
            user_id=user.id,
            push_enabled=body.push_enabled if body.push_enabled is not None else False,
            email_enabled=body.email_enabled if body.email_enabled is not None else False,
            push_per_type=body.push_per_type or {},
            email_per_type=body.email_per_type or {},
            digest_frequency=body.digest_frequency or "weekly",
        )
        db.add(prefs)
    else:
        if body.push_enabled is not None:
            prefs.push_enabled = body.push_enabled
        if body.email_enabled is not None:
            prefs.email_enabled = body.email_enabled
        if body.push_per_type is not None:
            # Merge with existing per-type map
            merged = {**prefs.push_per_type, **body.push_per_type}
            prefs.push_per_type = merged
        if body.email_per_type is not None:
            merged_email = {**prefs.email_per_type, **body.email_per_type}
            prefs.email_per_type = merged_email
        if body.digest_frequency is not None:
            prefs.digest_frequency = body.digest_frequency

    await db.commit()
    await db.refresh(prefs)
    return {"data": _serialize_prefs(prefs)}


# ─── Debug: test push ─────────────────────────────────────────────────────────


@router.post("/test-push")
async def test_push(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test push notification to all active devices of the current user.

    For development and debugging. Works in Mock mode without real credentials.
    """
    from app.services.push_notifier import push_notifier

    # Temporarily override preference check for test — always dispatch
    from app.models.device_token import DeviceToken
    from app.services.push.firebase import fcm_service
    from app.services.push.apns import apns_service

    result = await db.execute(
        select(DeviceToken).where(
            and_(
                DeviceToken.user_id == user.id,
                DeviceToken.deleted_at.is_(None),
            )
        )
    )
    tokens = list(result.scalars().all())

    if not tokens:
        return {
            "data": {
                "sent": 0,
                "results": [],
                "note": "No active device tokens registered. POST /me/devices first.",
            }
        }

    results = []
    for device in tokens:
        if device.platform == "fcm":
            r = await fcm_service.send(
                device.token,
                title="Domo 테스트 알림",
                body="푸시 알림이 정상적으로 작동합니다!",
                data={"type": "test"},
            )
        else:
            r = await apns_service.send(
                device.token,
                title="Domo 테스트 알림",
                body="푸시 알림이 정상적으로 작동합니다!",
            )
        results.append({"device_id": str(device.id), "platform": device.platform, **r})

    return {"data": {"sent": len(results), "results": results}}


# ─── Serializers ──────────────────────────────────────────────────────────────


def _serialize_token(dt: DeviceToken) -> dict:
    return {
        "id": str(dt.id),
        "user_id": str(dt.user_id),
        "platform": dt.platform,
        "device_id": dt.device_id,
        "last_active_at": dt.last_active_at.isoformat() if dt.last_active_at else None,
        "created_at": dt.created_at.isoformat() if dt.created_at else None,
    }


def _serialize_prefs(p: NotificationPreferences) -> dict:
    return {
        "user_id": str(p.user_id),
        "push_enabled": p.push_enabled,
        "email_enabled": p.email_enabled,
        "push_per_type": p.push_per_type or {},
        "email_per_type": p.email_per_type or {},
        "digest_frequency": p.digest_frequency,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
