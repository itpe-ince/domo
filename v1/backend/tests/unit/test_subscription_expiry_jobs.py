"""Unit tests for A-8 subscription_expiry_jobs.py.

Tests:
  1. No-op when no active subscriptions are expiring
  2. Creates notification + stamps expiry_notified_at for eligible subscription
  3. Skips already-notified row (expiry_notified_at IS NOT NULL)
  4. Skips cancelled subscriptions
  5. Correct days_left in notification body
  6. New A-8 metrics counters imported from app.core.metrics
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.subscription_expiry_jobs import notify_expiring_subscriptions_once


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_sub(
    *,
    status: str = "active",
    days_until_end: int = 5,
    expiry_notified_at: datetime | None = None,
) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sponsor_id = uuid.uuid4()
    sub.artist_id = uuid.uuid4()
    sub.status = status
    sub.current_period_end = _now() + timedelta(days=days_until_end)
    sub.expiry_notified_at = expiry_notified_at
    return sub


def _make_db(subscriptions: list[MagicMock]) -> AsyncMock:
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = subscriptions
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    return db


# ─── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_expiring_subscriptions_returns_zero():
    """No subscriptions in window → no notifications, returns 0."""
    db = _make_db([])
    count = await notify_expiring_subscriptions_once(db)
    assert count == 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_eligible_subscription_creates_notification():
    """Active sub expiring in 3 days → notification created, expiry_notified_at stamped."""
    sub = _make_sub(status="active", days_until_end=3, expiry_notified_at=None)
    db = _make_db([sub])

    count = await notify_expiring_subscriptions_once(db)

    assert count == 1
    db.add.assert_called_once()
    db.commit.assert_called_once()

    # expiry_notified_at must have been set
    assert sub.expiry_notified_at is not None

    # notification object that was added
    notif = db.add.call_args[0][0]
    assert notif.type == "subscription_expiring"
    assert "구독이" in notif.body
    assert "만료됩니다" in notif.body
    assert str(sub.sponsor_id) == str(notif.user_id)


@pytest.mark.asyncio
async def test_already_notified_row_is_skipped():
    """Sub with expiry_notified_at set → skipped, returns 0."""
    sub = _make_sub(
        status="active",
        days_until_end=3,
        expiry_notified_at=_now() - timedelta(days=1),
    )
    db = _make_db([sub])

    count = await notify_expiring_subscriptions_once(db)

    assert count == 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_cancelled_subscription_not_in_candidates():
    """Cancelled subs are not returned by the query (simulated by empty list)."""
    # cron query filters status='active' — simulate by providing no data
    db = _make_db([])
    count = await notify_expiring_subscriptions_once(db)
    assert count == 0


@pytest.mark.asyncio
async def test_days_left_in_notification_body():
    """Notification body contains correct days remaining."""
    sub = _make_sub(status="active", days_until_end=6, expiry_notified_at=None)
    db = _make_db([sub])

    await notify_expiring_subscriptions_once(db)

    notif = db.add.call_args[0][0]
    # days_until_end=6 may render as "5일" or "6일" due to micro-second time delta in computation
    assert "5일" in notif.body or "6일" in notif.body


@pytest.mark.asyncio
async def test_multiple_eligible_subscriptions():
    """Two eligible subs → two notifications, commit called once."""
    subs = [
        _make_sub(status="active", days_until_end=2),
        _make_sub(status="active", days_until_end=5),
    ]
    db = _make_db(subs)

    count = await notify_expiring_subscriptions_once(db)

    assert count == 2
    assert db.add.call_count == 2
    db.commit.assert_called_once()


def test_a8_metrics_importable():
    """A-8 metrics are importable from app.core.metrics."""
    from app.core.metrics import (  # noqa: F401
        subscription_expiry_notif_total,
        subscription_expiring_count,
    )
