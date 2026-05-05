"""Unit tests for G'-4 backend-posthog-integration — app/services/analytics.py.

Tests:
  1. init_posthog Mock mode (POSTHOG_API_KEY unset) → _posthog_enabled=False, no SDK call
  2. capture_event Mock mode → console log (logger.info), no posthog.capture call
  3. capture_event with valid api_key → posthog.capture called with correct args (mocked SDK)
  4. _redact_pii strips email, phone, card_number, iban, ssn
  5. shutdown_posthog graceful — calls posthog.shutdown only when enabled
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _reset_analytics_module():
    """Reset _posthog_enabled flag between tests by re-importing the module."""
    import importlib
    import app.services.analytics as analytics_mod
    analytics_mod._posthog_enabled = False
    return analytics_mod


# ─── Test 1: init_posthog Mock mode ───────────────────────────────────────────


def test_init_posthog_mock_mode_no_api_key():
    """When POSTHOG_API_KEY is empty, init_posthog sets _posthog_enabled=False and logs."""
    analytics = _reset_analytics_module()

    mock_settings = MagicMock()
    mock_settings.posthog_api_key = ""
    mock_settings.posthog_host = "https://us.i.posthog.com"

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch("app.services.analytics.log") as mock_log:
            analytics.init_posthog()

    assert analytics._posthog_enabled is False
    mock_log.info.assert_called_once()
    assert "Mock mode" in mock_log.info.call_args[0][0]


# ─── Test 2: capture_event Mock mode ─────────────────────────────────────────


def test_capture_event_mock_mode_logs_to_console():
    """capture_event in Mock mode logs the event and does NOT call posthog.capture."""
    analytics = _reset_analytics_module()
    analytics._posthog_enabled = False  # explicitly Mock mode

    with patch("app.services.analytics.log") as mock_log:
        analytics.capture_event("user-123", "test_event", {"foo": "bar"})

    mock_log.info.assert_called_once()
    call_args = mock_log.info.call_args[0]
    assert "test_event" in call_args[1] or "test_event" in str(call_args)


# ─── Test 3: capture_event with mocked SDK ───────────────────────────────────


def test_capture_event_calls_posthog_sdk_when_enabled():
    """capture_event with _posthog_enabled=True calls posthog.capture with correct args."""
    analytics = _reset_analytics_module()
    analytics._posthog_enabled = True

    mock_posthog = MagicMock()

    with patch.dict("sys.modules", {"posthog": mock_posthog}):
        analytics.capture_event(
            "user-abc",
            "sponsor_completed_server",
            {"amount_cents": 5000, "artist_id": "artist-xyz"},
        )

    mock_posthog.capture.assert_called_once_with(
        distinct_id="user-abc",
        event="sponsor_completed_server",
        properties={"amount_cents": 5000, "artist_id": "artist-xyz"},
    )

    # Reset for other tests
    analytics._posthog_enabled = False


# ─── Test 4: _redact_pii strips PII keys ─────────────────────────────────────


def test_redact_pii_strips_sensitive_keys():
    """_redact_pii removes email, phone, card_number, iban, ssn from properties."""
    analytics = _reset_analytics_module()

    dirty = {
        "email": "user@example.com",
        "phone": "+1-555-0100",
        "card_number": "4111111111111111",
        "iban": "DE89370400440532013000",
        "ssn": "123-45-6789",
        "amount_cents": 5000,
        "artist_id": "abc-123",
        "phone_number": "0101234567",
    }
    clean = analytics._redact_pii(dirty)

    assert "email" not in clean
    assert "phone" not in clean
    assert "card_number" not in clean
    assert "iban" not in clean
    assert "ssn" not in clean
    assert "phone_number" not in clean
    # Safe keys preserved
    assert clean["amount_cents"] == 5000
    assert clean["artist_id"] == "abc-123"


def test_redact_pii_empty_props():
    """_redact_pii handles empty dict without error."""
    analytics = _reset_analytics_module()
    assert analytics._redact_pii({}) == {}


def test_redact_pii_no_pii_keys_unchanged():
    """_redact_pii returns props unchanged when no PII keys present."""
    analytics = _reset_analytics_module()
    props = {"worker": "tier_release", "rows_processed": 42}
    assert analytics._redact_pii(props) == props


# ─── Test 5: shutdown_posthog graceful ───────────────────────────────────────


def test_shutdown_posthog_noop_in_mock_mode():
    """shutdown_posthog does nothing when _posthog_enabled=False."""
    analytics = _reset_analytics_module()
    analytics._posthog_enabled = False

    mock_posthog = MagicMock()
    with patch.dict("sys.modules", {"posthog": mock_posthog}):
        analytics.shutdown_posthog()

    mock_posthog.shutdown.assert_not_called()


def test_shutdown_posthog_calls_sdk_shutdown_when_enabled():
    """shutdown_posthog calls posthog.shutdown() when _posthog_enabled=True."""
    analytics = _reset_analytics_module()
    analytics._posthog_enabled = True

    mock_posthog = MagicMock()
    with patch.dict("sys.modules", {"posthog": mock_posthog}):
        analytics.shutdown_posthog()

    mock_posthog.shutdown.assert_called_once()

    # Reset for other tests
    analytics._posthog_enabled = False
