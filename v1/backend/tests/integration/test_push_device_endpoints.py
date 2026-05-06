"""Integration-style endpoint tests for push device + notification preferences — B'-3.

Strategy: direct endpoint function calls with MagicMock for SQLAlchemy model
instances, AsyncMock for DB session. No real DB, no FCM/APNs calls.

10 integration test cases:

POST /me/devices (3):
  1. New token registered — creates DeviceToken row
  2. Upsert by device_id — updates existing row
  3. Duplicate token string — updates last_active_at

DELETE /me/devices/{id} (2):
  4. Successful revoke — sets deleted_at
  5. Cross-user attempt raises FORBIDDEN

GET /me/notifications/preferences (2):
  6. No prefs row — returns GDPR defaults (all False)
  7. Existing row — returns serialized values

PATCH /me/notifications/preferences (2):
  8. Create on first PATCH
  9. Merge push_per_type with existing

POST /me/test-push (1):
  10. No active tokens — returns sent=0 with note
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import ApiError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_user(*, user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.display_name = "Test Artist"
    u.email = "artist@test.com"
    return u


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


# ── POST /me/devices ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_device_new_token():
    """New token — creates a DeviceToken row and returns it.

    ORM 클래스 패치 없이 db.execute side_effect + db.refresh side_effect 활용.
    select(DeviceToken)와 충돌하지 않도록 ORM 클래스를 직접 건드리지 않는다.
    """
    from app.api.me_devices import register_device, DeviceRegisterRequest

    user = _make_user()
    db = _make_db()

    # device_id 조회: None 반환 (기존 없음)
    mock_result_device_id = AsyncMock()
    mock_result_device_id.scalar_one_or_none = MagicMock(return_value=None)
    # token 조회: None 반환 (중복 없음)
    mock_result_token = AsyncMock()
    mock_result_token.scalar_one_or_none = MagicMock(return_value=None)
    db.execute.side_effect = [mock_result_device_id, mock_result_token]

    # db.refresh가 새로 생성된 DeviceToken 인스턴스에 id/created_at 등을 주입
    token_id = uuid.uuid4()
    now = _now()

    async def _refresh(obj):
        obj.id = token_id
        obj.user_id = user.id
        obj.platform = "fcm"
        obj.device_id = "device-abc"
        obj.last_active_at = now
        obj.created_at = now

    db.refresh = AsyncMock(side_effect=_refresh)

    body = DeviceRegisterRequest(
        token="fcm-token-xyz123",
        platform="fcm",
        device_id="device-abc",
    )

    response = await register_device(body=body, user=user, db=db)

    assert "data" in response
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_register_device_upsert_by_device_id():
    """Existing token with same device_id — updates token string in place."""
    from app.api.me_devices import register_device, DeviceRegisterRequest

    user = _make_user()
    db = _make_db()

    existing = MagicMock()
    existing.id = uuid.uuid4()
    existing.user_id = user.id
    existing.platform = "fcm"
    existing.device_id = "device-abc"
    existing.last_active_at = _now()
    existing.created_at = _now()
    existing.token = "old-token"

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=existing)
    db.execute.return_value = mock_result

    async def _refresh(obj):
        pass

    db.refresh = AsyncMock(side_effect=_refresh)

    body = DeviceRegisterRequest(
        token="new-token-xyz",
        platform="fcm",
        device_id="device-abc",
    )

    response = await register_device(body=body, user=user, db=db)

    assert "data" in response
    assert existing.token == "new-token-xyz"
    db.commit.assert_called_once()
    db.add.assert_not_called()  # upsert, not insert


@pytest.mark.asyncio
async def test_register_device_duplicate_token():
    """Duplicate token string (no device_id match) — updates last_active_at only.

    device_id=None이므로 첫 번째 select(by device_id) 블록은 건너뛰고,
    두 번째 select(by token)만 실행된다.
    ORM 클래스 패치 없이 db.execute side_effect 활용.
    """
    from app.api.me_devices import register_device, DeviceRegisterRequest

    user = _make_user()
    db = _make_db()

    existing = MagicMock()
    existing.id = uuid.uuid4()
    existing.user_id = user.id
    existing.platform = "fcm"
    existing.device_id = None
    existing.last_active_at = None
    existing.created_at = _now()
    existing.token = "same-token"

    # device_id=None이므로 if body.device_id 블록 자체가 실행되지 않음
    # → execute 호출은 token 중복 확인 1번만 발생
    token_result = AsyncMock()
    token_result.scalar_one_or_none = MagicMock(return_value=existing)
    db.execute.return_value = token_result
    db.refresh = AsyncMock()

    body = DeviceRegisterRequest(
        token="same-token",
        platform="fcm",
        device_id=None,
    )

    response = await register_device(body=body, user=user, db=db)

    assert "data" in response
    assert existing.last_active_at is not None
    db.add.assert_not_called()


# ── DELETE /me/devices/{id} ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_device_success():
    """Revoke own device — sets deleted_at."""
    from app.api.me_devices import revoke_device

    user = _make_user()
    db = _make_db()
    device_id = uuid.uuid4()

    device = MagicMock()
    device.id = device_id
    device.user_id = user.id
    device.deleted_at = None

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=device)
    db.execute.return_value = mock_result

    response = await revoke_device(device_id=device_id, user=user, db=db)

    assert response["data"]["deleted"] is True
    assert device.deleted_at is not None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_revoke_device_cross_user_forbidden():
    """Cross-user revoke — raises FORBIDDEN."""
    from app.api.me_devices import revoke_device

    user = _make_user()
    other_user_id = uuid.uuid4()
    db = _make_db()
    device_id = uuid.uuid4()

    device = MagicMock()
    device.id = device_id
    device.user_id = other_user_id  # different user
    device.deleted_at = None

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=device)
    db.execute.return_value = mock_result

    with pytest.raises(ApiError) as exc_info:
        await revoke_device(device_id=device_id, user=user, db=db)

    assert exc_info.value.code == "FORBIDDEN"


# ── GET /me/notifications/preferences ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_prefs_no_row_returns_gdpr_defaults():
    """No preferences row — returns defaults (all False)."""
    from app.api.me_devices import get_notification_preferences

    user = _make_user()
    db = _make_db()

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute.return_value = mock_result

    response = await get_notification_preferences(user=user, db=db)

    data = response["data"]
    assert data["push_enabled"] is False
    assert data["email_enabled"] is False
    assert data["push_per_type"] == {}
    assert data["email_per_type"] == {}
    assert data["digest_frequency"] == "weekly"


@pytest.mark.asyncio
async def test_get_prefs_existing_row():
    """Existing preferences row — returns serialized values."""
    from app.api.me_devices import get_notification_preferences

    user = _make_user()
    db = _make_db()

    prefs = MagicMock()
    prefs.user_id = user.id
    prefs.push_enabled = True
    prefs.email_enabled = False
    prefs.push_per_type = {"auction": True}
    prefs.email_per_type = {}
    prefs.digest_frequency = "biweekly"
    prefs.updated_at = _now()

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=prefs)
    db.execute.return_value = mock_result

    response = await get_notification_preferences(user=user, db=db)

    data = response["data"]
    assert data["push_enabled"] is True
    assert data["digest_frequency"] == "biweekly"
    assert data["push_per_type"] == {"auction": True}


# ── PATCH /me/notifications/preferences ──────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_prefs_creates_row_on_first_call():
    """First PATCH — creates a new NotificationPreferences row.

    ORM 클래스 패치 없이 db.execute.return_value + db.refresh side_effect 활용.
    NotificationPreferences 생성자가 실제로 호출되고, db.refresh가 속성을 주입한다.
    """
    from app.api.me_devices import update_notification_preferences, NotificationPrefsUpdate

    user = _make_user()
    db = _make_db()

    # 기존 행 없음 → 새로 생성 분기
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute.return_value = mock_result

    now = _now()

    async def _refresh(obj):
        # db.refresh가 실제 DB 처럼 updated_at을 채워준다
        obj.updated_at = now

    db.refresh = AsyncMock(side_effect=_refresh)

    body = NotificationPrefsUpdate(push_enabled=True)

    response = await update_notification_preferences(body=body, user=user, db=db)

    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_patch_prefs_merges_per_type():
    """PATCH with push_per_type — merges into existing dict."""
    from app.api.me_devices import update_notification_preferences, NotificationPrefsUpdate

    user = _make_user()
    db = _make_db()

    prefs = MagicMock()
    prefs.user_id = user.id
    prefs.push_enabled = True
    prefs.email_enabled = False
    prefs.push_per_type = {"auction": True}
    prefs.email_per_type = {}
    prefs.digest_frequency = "weekly"
    prefs.updated_at = _now()

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=prefs)
    db.execute.return_value = mock_result
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    body = NotificationPrefsUpdate(push_per_type={"system": False})

    response = await update_notification_preferences(body=body, user=user, db=db)

    # Merged result should contain both keys
    assert prefs.push_per_type == {"auction": True, "system": False}
    db.add.assert_not_called()  # existing row updated, not inserted
    db.commit.assert_called_once()


# ── POST /me/test-push ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_test_push_no_tokens():
    """test-push with no active tokens — returns sent=0 with note."""
    from app.api.me_devices import test_push

    user = _make_user()
    db = _make_db()

    mock_result = AsyncMock()
    mock_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    db.execute.return_value = mock_result

    response = await test_push(user=user, db=db)

    assert response["data"]["sent"] == 0
    assert "note" in response["data"]
