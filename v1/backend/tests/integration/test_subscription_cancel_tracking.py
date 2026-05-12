"""Integration tests for D'-2 subscription cancellation tracking.

Endpoints under test:
  DELETE /v1/subscriptions/{id}  — with optional cancel body
  GET    /v1/me/patronage/churn  — artist-only churn list

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock objects.
No real DB or Stripe required. Mirrors test_patronage_dashboard.py pattern.

Test count: 6
  cancel_subscription:
    1. 200 cancel with reason + feedback (cancellation_reason stored, HTML sanitized)
    2. 200 cancel without body (backward compat — reason stays None)
    3. 422 invalid reason value (pydantic validation)
    4. 422 feedback > 500 chars (pydantic validation)
  get_churn_list:
    5. 200 returns churn items for artist with sample data
    6. 403 non-artist returns ARTIST_ONLY error
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pydantic
import pytest

from app.api.me_patronage import get_churn_list
from app.api.sponsorships import cancel_subscription
from app.core.errors import ApiError
from app.schemas.sponsorship import SubscriptionCancelRequest, SubscriptionOut


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_artist() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "artist"
    u.display_name = "test_artist"
    u.avatar_url = "https://cdn.example.com/avatar.jpg"
    u.identity_verified_at = datetime.now(timezone.utc)
    return u


def _make_non_artist() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    u.display_name = "regular_user"
    u.avatar_url = None
    u.identity_verified_at = None
    return u


def _make_active_subscription(sponsor_id: uuid.UUID, artist_id: uuid.UUID) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.sponsor_id = sponsor_id
    sub.artist_id = artist_id
    sub.status = "active"
    sub.monthly_bluebird = 10
    sub.monthly_amount = Decimal("10000.00")
    sub.currency = "KRW"
    sub.provider_subscription_id = "stripe_sub_test"
    sub.cancel_at_period_end = False
    sub.current_period_end = None
    sub.cancelled_at = None
    sub.cancellation_reason = None
    sub.cancellation_feedback = None
    sub.created_at = datetime.now(timezone.utc)
    return sub


def _make_cancel_db(sub: MagicMock):
    """DB that returns the subscription on first execute."""
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = sub

    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_provider_mock():
    provider = AsyncMock()
    provider.cancel_subscription = AsyncMock()
    return provider


# ─── Tests: cancel_subscription ───────────────────────────────────────────────


def _stub_subscription_out(sub: MagicMock) -> SubscriptionOut:
    """Build a real SubscriptionOut from a MagicMock subscription for validation."""
    return SubscriptionOut(
        id=sub.id,
        sponsor_id=sub.sponsor_id,
        artist_id=sub.artist_id,
        monthly_bluebird=sub.monthly_bluebird,
        monthly_amount=sub.monthly_amount,
        currency=sub.currency,
        status=sub.status,
        cancel_at_period_end=sub.cancel_at_period_end,
        current_period_end=sub.current_period_end,
        cancelled_at=sub.cancelled_at,
        cancellation_reason=sub.cancellation_reason,
        cancellation_feedback=sub.cancellation_feedback,
        created_at=sub.created_at,
    )


@pytest.mark.asyncio
async def test_cancel_with_reason_and_feedback():
    """200 — cancellation_reason and sanitized feedback are stored."""
    artist = _make_artist()
    sub = _make_active_subscription(artist.id, uuid.uuid4())
    db = _make_cancel_db(sub)
    provider = _make_provider_mock()

    body = SubscriptionCancelRequest(
        reason="too_expensive",
        feedback="It costs <b>too much</b>",
        immediate=False,
    )

    with patch("app.api.sponsorships.get_payment_provider", return_value=provider):
        with patch(
            "app.api.sponsorships.SubscriptionOut.model_validate",
            side_effect=lambda s: _stub_subscription_out(s),
        ):
            result = await cancel_subscription(
                subscription_id=sub.id,
                body=body,
                user=artist,
                db=db,
            )

    # Verify model was mutated before commit
    assert sub.cancellation_reason == "too_expensive"
    # HTML tags stripped
    assert sub.cancellation_feedback == "It costs too much"
    assert sub.cancel_at_period_end is True
    assert sub.cancelled_at is not None
    db.commit.assert_called_once()
    assert "data" in result


@pytest.mark.asyncio
async def test_cancel_without_body_backward_compat():
    """200 — body=None is accepted; reason and feedback remain None."""
    artist = _make_artist()
    sub = _make_active_subscription(artist.id, uuid.uuid4())
    db = _make_cancel_db(sub)
    provider = _make_provider_mock()

    with patch("app.api.sponsorships.get_payment_provider", return_value=provider):
        with patch(
            "app.api.sponsorships.SubscriptionOut.model_validate",
            side_effect=lambda s: _stub_subscription_out(s),
        ):
            result = await cancel_subscription(
                subscription_id=sub.id,
                body=None,
                user=artist,
                db=db,
            )

    assert "data" in result
    assert sub.cancellation_reason is None
    assert sub.cancellation_feedback is None
    db.commit.assert_called_once()


def test_cancel_request_invalid_reason():
    """422 — pydantic rejects unknown reason value."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        SubscriptionCancelRequest(reason="invalid_reason")


def test_cancel_request_feedback_too_long():
    """422 — pydantic rejects feedback > 500 chars."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        SubscriptionCancelRequest(feedback="x" * 501)


# ─── Tests: get_churn_list ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_churn_list_returns_data_for_artist():
    """200 — artist receives list of churned subscribers."""
    artist = _make_artist()

    sponsor_id = uuid.uuid4()
    sponsor_user = MagicMock()
    sponsor_user.id = sponsor_id
    sponsor_user.display_name = "churn_user"
    sponsor_user.avatar_url = None

    cancelled_at = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Row representing a cancelled subscription
    churn_row = MagicMock()
    churn_row.sponsor_id = sponsor_id
    churn_row.cancelled_at = cancelled_at
    churn_row.cancellation_reason = "too_expensive"
    churn_row.cancellation_feedback = "Way too pricey for my budget"
    churn_row.monthly_amount = Decimal("10000.00")
    churn_row.currency = "KRW"

    call_count = [0]

    db = AsyncMock()

    async def execute(query):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # Churn query
            result.all.return_value = [churn_row]
        else:
            # User batch load
            result.scalars.return_value.all.return_value = [sponsor_user]
        return result

    db.execute = execute

    with patch("app.api.me_patronage.rate_limit", return_value=lambda *a, **kw: None):
        response = await get_churn_list(
            limit=20,
            from_date=None,
            user=artist,
            db=db,
            _rl=None,
        )

    assert len(response.data) == 1
    item = response.data[0]
    assert item.user_id == str(sponsor_id)
    assert item.username == "churn_user"
    assert item.cancellation_reason == "too_expensive"
    assert item.cancellation_feedback_preview is not None
    assert len(item.cancellation_feedback_preview) <= 100
    assert item.tier == "subscriber"


@pytest.mark.asyncio
async def test_churn_list_403_non_artist():
    """403 — non-artist gets ARTIST_ONLY error."""
    non_artist = _make_non_artist()
    db = AsyncMock()

    with pytest.raises(ApiError) as exc_info:
        await get_churn_list(
            limit=20,
            from_date=None,
            user=non_artist,
            db=db,
            _rl=None,
        )

    assert exc_info.value.code == "ARTIST_ONLY"
    assert exc_info.value.status_code == 403
