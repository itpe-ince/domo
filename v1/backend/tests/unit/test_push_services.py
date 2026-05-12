"""Unit tests for FCM, APNs, push_notifier, and email_digest — B'-3.

5 unit test cases:

1. FCMService.is_mock — True when credentials not set
2. FCMService._mock_send — returns mock message_id with status=mock
3. APNsService.is_mock — True when credentials not set
4. APNsService._mock_send — returns mock message_id with status=mock
5. PushNotifier.notify_user — returns [] when push_enabled=False (GDPR gate)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── FCM ────────────────────────────────────────────────────────────────────────


def test_fcm_is_mock_when_no_credentials():
    """FCMService.is_mock returns True when firebase_credentials_json not set."""
    from app.services.push.firebase import FCMService

    svc = FCMService()
    # Force settings load with empty credential
    with pytest.MonkeyPatch.context() as mp:
        class FakeSettings:
            firebase_credentials_json = ""

        import app.core.config as cfg_mod
        mp.setattr(cfg_mod, "get_settings", lambda: FakeSettings())
        assert svc.is_mock is True


def test_fcm_mock_send_returns_mock_status():
    """FCMService._mock_send returns dict with status=mock and message_id prefix."""
    from app.services.push.firebase import FCMService

    svc = FCMService()
    result = svc._mock_send("token-xyz", "Test Title", "Test Body")

    assert result["status"] == "mock"
    assert result["platform"] == "fcm"
    assert result["message_id"].startswith("fcm-mock-")


# ── APNs ───────────────────────────────────────────────────────────────────────


def test_apns_is_mock_when_no_credentials():
    """APNsService.is_mock returns True when key_id/team_id not set."""
    from app.services.push.apns import APNsService

    svc = APNsService()
    # With empty defaults from Settings, should be mock
    with pytest.MonkeyPatch.context() as mp:
        class FakeSettings:
            apns_key_id = ""
            apns_team_id = ""
            apns_auth_key_p8 = ""
            apns_bundle_id = "art.domo.app"
            apns_sandbox = True

        import app.core.config as cfg_mod
        mp.setattr(cfg_mod, "get_settings", lambda: FakeSettings())
        assert svc.is_mock is True


def test_apns_mock_send_returns_mock_status():
    """APNsService._mock_send returns dict with status=mock."""
    from app.services.push.apns import APNsService

    svc = APNsService()
    result = svc._mock_send("apns-device-token", "Hello", "World")

    assert result["status"] == "mock"
    assert result["platform"] == "apns"
    assert result["message_id"].startswith("apns-mock-")


# ── PushNotifier ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_push_notifier_returns_empty_when_push_disabled():
    """PushNotifier.notify_user returns [] when push_enabled=False (GDPR gate)."""
    from app.services.push_notifier import PushNotifier

    notifier = PushNotifier()
    user_id = uuid.uuid4()

    db = AsyncMock()

    prefs = MagicMock()
    prefs.push_enabled = False
    prefs.push_per_type = {}

    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=prefs)
    db.execute = AsyncMock(return_value=mock_result)

    results = await notifier.notify_user(
        db, user_id, "auction_ending_1h", "Test", "Body"
    )

    assert results == []
    # Should only have called execute once (prefs check), not device token query
    assert db.execute.call_count == 1
