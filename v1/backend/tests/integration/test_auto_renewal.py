"""Integration tests for B'-4 stripe-billing-auto-renewal.

Endpoints/jobs under test:
  POST  /v1/subscriptions/{id}/renew        — manual renewal
  PATCH /v1/subscriptions/{id}/auto-renew   — auto_renew toggle
  auto_renewal_cron_loop                    — 11th cron worker sweep
  webhook: invoice.payment_succeeded booster — B'-4 enhanced audit + period reset
  webhook: invoice.payment_failed booster   — B'-4 retry strategy + user notify

Strategy: direct function calls with AsyncMock DB + MagicMock objects.
No real DB or Stripe required. Mirrors test_subscription_cancel_tracking.py pattern.

Test count: 8
  renew_subscription:
    1. 200 active + cancel_at_period_end=True → reverts cancel flag
    2. 200 cancelled → re-starts subscription via provider
    3. 200 past_due → returns monitoring message (Stripe handles retry)
    4. 200 already active → idempotent
    5. 403 non-owner rejected
  toggle_auto_renew:
    6. 200 disables auto_renew on active subscription
    7. 409 cannot toggle on cancelled subscription
  auto_renewal_cron:
    8. cron sweep: upcoming subs counted, past_due escalation creates notification
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.sponsorships import renew_subscription, toggle_auto_renew
from app.core.errors import ApiError
from app.schemas.sponsorship import AutoRenewToggleRequest
from app.services.auto_renewal_jobs import check_auto_renewals_once
from app.services.payments.webhook_handlers import (
    handle_invoice_payment_failed,
    handle_invoice_payment_succeeded,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    u = MagicMock()
    u.id = user_id or uuid.uuid4()
    u.display_name = "test_sponsor"
    u.identity_verified_at = datetime.now(timezone.utc)
    u.role = "user"
    return u


def _make_subscription(
    sponsor_id: uuid.UUID,
    artist_id: uuid.UUID | None = None,
    status: str = "active",
    cancel_at_period_end: bool = False,
    auto_renew_enabled: bool = True,
    current_period_end: datetime | None = None,
) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sponsor_id = sponsor_id
    sub.artist_id = artist_id or uuid.uuid4()
    sub.monthly_bluebird = 5
    sub.monthly_amount = Decimal("9900.00")
    sub.currency = "KRW"
    sub.status = status
    sub.cancel_at_period_end = cancel_at_period_end
    sub.auto_renew_enabled = auto_renew_enabled
    sub.current_period_end = current_period_end or (
        datetime.now(timezone.utc) + timedelta(days=30)
    )
    sub.cancelled_at = None
    sub.cancellation_reason = None
    sub.cancellation_feedback = None
    sub.expiry_notified_at = None
    sub.provider_subscription_id = f"sub_mock_{uuid.uuid4().hex[:12]}"
    sub.created_at = datetime.now(timezone.utc)
    return sub


def _make_db(sub: MagicMock | None = None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sub
    db.execute.return_value = result
    return db


# ─── Test 1: renew active + cancel_at_period_end=True reverts cancel ─────────


@pytest.mark.asyncio
async def test_renew_reverts_pending_cancellation():
    """POST /renew on active+cancel_at_period_end=True should revert flag."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="active",
        cancel_at_period_end=True,
    )
    db = _make_db(sub)

    mock_provider = AsyncMock()
    mock_provider.revert_cancel_at_period_end = AsyncMock()

    with (
        patch("app.api.sponsorships.get_payment_provider", return_value=mock_provider),
        patch("app.api.sponsorships.get_setting", new_callable=AsyncMock) as mock_setting,
        patch("app.api.sponsorships.capture_event"),
    ):
        mock_setting.return_value = {"amount": "9900", "currency": "KRW"}
        result = await renew_subscription(
            subscription_id=sub.id,
            user=user,
            db=db,
        )

    assert result["data"]["cancel_at_period_end"] is False
    assert result["data"]["cancelled_at"] is None
    assert "message" in result["data"]


# ─── Test 2: renew cancelled sub → re-starts subscription ───────────────────


@pytest.mark.asyncio
async def test_renew_cancelled_subscription_restarts():
    """POST /renew on cancelled sub should create new Stripe subscription."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="cancelled",
        cancel_at_period_end=False,
    )
    sub.cancelled_at = datetime.now(timezone.utc) - timedelta(days=5)
    db = _make_db(sub)

    new_sub_result = MagicMock()
    new_sub_result.id = f"sub_mock_new_{uuid.uuid4().hex[:12]}"
    new_sub_result.status = "active"
    new_sub_result.current_period_end_unix = int(
        (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()
    )
    new_sub_result.cancel_at_period_end = False

    mock_provider = AsyncMock()
    mock_provider.create_subscription = AsyncMock(return_value=new_sub_result)

    with (
        patch("app.api.sponsorships.get_payment_provider", return_value=mock_provider),
        patch("app.api.sponsorships.get_setting", new_callable=AsyncMock) as mock_setting,
        patch("app.api.sponsorships.capture_event"),
    ):
        mock_setting.return_value = {"amount": "9900", "currency": "KRW"}
        result = await renew_subscription(
            subscription_id=sub.id,
            user=user,
            db=db,
        )

    assert result["data"]["status"] == "active"
    assert result["data"]["cancel_at_period_end"] is False
    mock_provider.create_subscription.assert_awaited_once()


# ─── Test 3: renew past_due → monitoring response ────────────────────────────


@pytest.mark.asyncio
async def test_renew_past_due_returns_monitoring_message():
    """POST /renew on past_due returns 200 with monitoring message (Stripe handles retry)."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="past_due",
    )
    db = _make_db(sub)

    mock_provider = AsyncMock()

    with (
        patch("app.api.sponsorships.get_payment_provider", return_value=mock_provider),
        patch("app.api.sponsorships.get_setting", new_callable=AsyncMock) as mock_setting,
        patch("app.api.sponsorships.capture_event"),
    ):
        mock_setting.return_value = {"amount": "9900", "currency": "KRW"}
        result = await renew_subscription(
            subscription_id=sub.id,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "message" in result["data"]
    assert "Stripe" in result["data"]["message"] or "결제" in result["data"]["message"]


# ─── Test 4: renew already active → idempotent ───────────────────────────────


@pytest.mark.asyncio
async def test_renew_already_active_idempotent():
    """POST /renew on already active sub (no cancel_at_period_end) returns 200 idempotently."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="active",
        cancel_at_period_end=False,
    )
    db = _make_db(sub)

    mock_provider = AsyncMock()

    with (
        patch("app.api.sponsorships.get_payment_provider", return_value=mock_provider),
        patch("app.api.sponsorships.get_setting", new_callable=AsyncMock) as mock_setting,
        patch("app.api.sponsorships.capture_event"),
    ):
        mock_setting.return_value = {"amount": "9900", "currency": "KRW"}
        result = await renew_subscription(
            subscription_id=sub.id,
            user=user,
            db=db,
        )

    assert "data" in result
    assert "message" in result["data"]


# ─── Test 5: renew non-owner → 403 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_renew_non_owner_rejected():
    """POST /renew by non-owner raises 403 FORBIDDEN."""
    owner = _make_user()
    other_user = _make_user()
    sub = _make_subscription(sponsor_id=owner.id, status="active")
    db = _make_db(sub)

    mock_provider = AsyncMock()

    with (
        patch("app.api.sponsorships.get_payment_provider", return_value=mock_provider),
        patch("app.api.sponsorships.get_setting", new_callable=AsyncMock),
        patch("app.api.sponsorships.capture_event"),
    ):
        with pytest.raises(ApiError) as exc_info:
            await renew_subscription(
                subscription_id=sub.id,
                user=other_user,
                db=db,
            )

    assert exc_info.value.status_code == 403


# ─── Test 6: toggle_auto_renew disables on active subscription ───────────────


@pytest.mark.asyncio
async def test_toggle_auto_renew_disable():
    """PATCH /auto-renew with auto_renew_enabled=False disables on active sub."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="active",
        auto_renew_enabled=True,
    )
    db = _make_db(sub)

    with patch("app.api.sponsorships.capture_event"):
        result = await toggle_auto_renew(
            subscription_id=sub.id,
            body=AutoRenewToggleRequest(auto_renew_enabled=False),
            user=user,
            db=db,
        )

    assert sub.auto_renew_enabled is False
    assert "data" in result


# ─── Test 7: toggle_auto_renew on cancelled → 409 ────────────────────────────


@pytest.mark.asyncio
async def test_toggle_auto_renew_cancelled_rejected():
    """PATCH /auto-renew on cancelled subscription raises 409 CONFLICT."""
    user = _make_user()
    sub = _make_subscription(
        sponsor_id=user.id,
        status="cancelled",
        auto_renew_enabled=False,
    )
    db = _make_db(sub)

    with patch("app.api.sponsorships.capture_event"):
        with pytest.raises(ApiError) as exc_info:
            await toggle_auto_renew(
                subscription_id=sub.id,
                body=AutoRenewToggleRequest(auto_renew_enabled=True),
                user=user,
                db=db,
            )

    assert exc_info.value.status_code == 409


# ─── Test 8: cron sweep — upcoming + past_due escalation ─────────────────────


@pytest.mark.asyncio
async def test_auto_renewal_cron_sweep():
    """check_auto_renewals_once detects upcoming subs and escalates past_due."""
    now = datetime.now(timezone.utc)
    sponsor_id = uuid.uuid4()

    # Active sub expiring in 3 days (upcoming, not yet notified)
    upcoming_sub = _make_subscription(
        sponsor_id=sponsor_id,
        status="active",
        auto_renew_enabled=True,
        current_period_end=now + timedelta(days=3),
    )
    upcoming_sub.expiry_notified_at = None
    upcoming_sub.cancel_at_period_end = False

    # Past_due sub past the 72h escalation threshold
    past_period_end = now - timedelta(hours=80)
    past_due_sub = _make_subscription(
        sponsor_id=sponsor_id,
        status="past_due",
        auto_renew_enabled=True,
        current_period_end=past_period_end,
    )

    db = AsyncMock()
    call_count = 0

    def _execute_side_effect(query):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # First execute: upcoming subs
            result.scalars.return_value.all.return_value = [upcoming_sub]
        elif call_count == 2:
            # Second execute: past_due subs
            result.scalars.return_value.all.return_value = [past_due_sub]
        elif call_count == 3:
            # Third execute: existing notification check (none)
            result.scalar_one_or_none.return_value = None
        else:
            result.scalars.return_value.all.return_value = []
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.auto_renewal_jobs.capture_event"):
        summary = await check_auto_renewals_once(db)

    assert summary["upcoming_checked"] == 1
    assert summary["past_due_escalated"] == 1
    # Notification was added for past_due escalation
    db.add.assert_called()
