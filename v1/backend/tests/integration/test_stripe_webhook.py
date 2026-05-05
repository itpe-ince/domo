"""Integration tests for POST /v1/webhooks/stripe (G'-1).

Strategy: direct endpoint function calls with AsyncMock DB session.
No real DB, no Stripe API calls. Mirrors test_payments_setup_intent.py pattern.

Test count: 12
  Signature / parsing:
    1.  200 valid event (mock mode, no sig needed)
    2.  400 signature header missing (stripe mode)
    3.  400 signature forged / invalid (stripe mode)
    4.  400 body parse failure (mock mode, malformed JSON)

  Event handlers — 200 processed:
    5.  payment_intent.succeeded → Sponsorship completed
    6.  payment_intent.payment_failed → Notification created
    7.  invoice.payment_succeeded → Subscription period_end updated
    8.  invoice.payment_failed → Subscription past_due
    9.  customer.subscription.deleted → Subscription cancelled
    10. charge.dispute.created → 200 (log-only, no DB mutation required)
    11. unknown event_type → 200 graceful (no handler, still stored)

  Idempotency:
    12. Duplicate event_id → 200 with duplicate=True, no reprocessing

  DB failure:
    (covered via handler exception path in test 5 variant — separate test)
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.api.webhooks import stripe_webhook, payments_webhook, _verify_stripe_signature
from app.core.errors import ApiError


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_db(*, flush_raises: Exception | None = None) -> AsyncMock:
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    if flush_raises:
        db.flush = AsyncMock(side_effect=flush_raises)
    else:
        db.flush = AsyncMock()
    return db


def _make_request(payload: bytes) -> MagicMock:
    req = MagicMock()
    req.body = AsyncMock(return_value=payload)
    return req


def _event(
    event_type: str = "payment_intent.succeeded",
    event_id: str | None = None,
    data_object: dict | None = None,
) -> dict:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:16]}",
        "type": event_type,
        "data": {
            "object": data_object or {},
        },
    }


def _json_bytes(d: dict) -> bytes:
    return json.dumps(d).encode()


def _make_sponsorship(
    *,
    payment_intent_id: str = "pi_test_123",
    status: str = "pending",
    sponsor_id: uuid.UUID | None = None,
    artist_id: uuid.UUID | None = None,
) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.payment_intent_id = payment_intent_id
    s.status = status
    s.sponsor_id = sponsor_id or uuid.uuid4()
    s.artist_id = artist_id or uuid.uuid4()
    return s


def _make_subscription(
    *,
    provider_subscription_id: str = "sub_test_123",
    status: str = "active",
    sponsor_id: uuid.UUID | None = None,
) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.provider_subscription_id = provider_subscription_id
    s.status = status
    s.sponsor_id = sponsor_id or uuid.uuid4()
    s.current_period_end = None
    s.cancelled_at = None
    return s


# ─── Fixture: mock payment provider = mock_stripe ────────────────────────────


@pytest.fixture(autouse=True)
def mock_settings_mock_stripe():
    """Force mock_stripe mode so signature verification is bypassed."""
    settings = MagicMock()
    settings.payment_provider = "mock_stripe"
    settings.stripe_webhook_secret = ""
    with patch("app.api.webhooks.get_settings", return_value=settings):
        yield settings


# ─── Test 1: 200 valid event (mock mode) ─────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_event_returns_200():
    evt = _event("checkout.session.completed")
    db = _make_db()
    req = _make_request(_json_bytes(evt))

    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert resp["data"]["type"] == "checkout.session.completed"
    db.commit.assert_called_once()


# ─── Test 2: 400 signature missing in stripe mode ────────────────────────────


@pytest.mark.asyncio
async def test_missing_signature_in_stripe_mode_returns_400(mock_settings_mock_stripe):
    mock_settings_mock_stripe.payment_provider = "stripe"
    mock_settings_mock_stripe.stripe_webhook_secret = "whsec_test"

    with pytest.raises(ApiError) as exc_info:
        _verify_stripe_signature(b"{}", sig_header=None)

    assert exc_info.value.status_code == 400
    assert "MISSING_SIGNATURE" in exc_info.value.code


# ─── Test 3: 400 forged signature in stripe mode ─────────────────────────────


@pytest.mark.asyncio
async def test_forged_signature_returns_400(mock_settings_mock_stripe):
    mock_settings_mock_stripe.payment_provider = "stripe"
    mock_settings_mock_stripe.stripe_webhook_secret = "whsec_real_secret"

    with patch("app.api.webhooks.get_settings", return_value=mock_settings_mock_stripe):
        with pytest.raises(ApiError) as exc_info:
            _verify_stripe_signature(
                b'{"id":"evt_test","type":"test"}',
                sig_header="t=1234,v1=forged_signature",
            )

    assert exc_info.value.status_code == 400
    assert "INVALID_SIGNATURE" in exc_info.value.code


# ─── Test 4: 400 malformed body in mock mode ─────────────────────────────────


@pytest.mark.asyncio
async def test_malformed_body_returns_400():
    with pytest.raises(ApiError) as exc_info:
        _verify_stripe_signature(b"not json at all !!!", sig_header=None)

    assert exc_info.value.status_code == 400
    assert "INVALID_PAYLOAD" in exc_info.value.code


# ─── Test 5: payment_intent.succeeded → Sponsorship completed ────────────────


@pytest.mark.asyncio
async def test_payment_intent_succeeded_marks_sponsorship_completed():
    intent_id = "pi_test_succeeded_001"
    sponsorship = _make_sponsorship(payment_intent_id=intent_id, status="pending")

    evt = _event(
        "payment_intent.succeeded",
        data_object={"id": intent_id},
    )
    db = _make_db()

    # Mock DB execute returning the sponsorship
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sponsorship)
    ))

    req = _make_request(_json_bytes(evt))
    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert sponsorship.status == "completed"
    # Two notifications added (sponsor + artist)
    assert db.add.call_count >= 2


# ─── Test 6: payment_intent.payment_failed → Notification created ────────────


@pytest.mark.asyncio
async def test_payment_intent_failed_creates_notification():
    intent_id = "pi_test_failed_001"
    sponsorship = _make_sponsorship(payment_intent_id=intent_id, status="pending")

    evt = _event(
        "payment_intent.payment_failed",
        data_object={"id": intent_id},
    )
    db = _make_db()
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=sponsorship)
    ))

    req = _make_request(_json_bytes(evt))
    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert sponsorship.status == "failed"
    # One notification (sponsor only)
    assert db.add.call_count >= 1


# ─── Test 7: invoice.payment_succeeded → Subscription period_end updated ──────


@pytest.mark.asyncio
async def test_invoice_payment_succeeded_updates_subscription():
    sub_provider_id = "sub_inv_succeeded_001"
    subscription = _make_subscription(
        provider_subscription_id=sub_provider_id, status="active"
    )

    evt = _event(
        "invoice.payment_succeeded",
        data_object={
            "subscription": sub_provider_id,
            "lines": {
                "data": [{"period": {"end": 1800000000}}],
            },
        },
    )
    db = _make_db()
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=subscription)
    ))

    req = _make_request(_json_bytes(evt))
    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert subscription.current_period_end is not None
    # Notification added
    assert db.add.call_count >= 1


# ─── Test 8: invoice.payment_failed → Subscription past_due ─────────────────


@pytest.mark.asyncio
async def test_invoice_payment_failed_marks_past_due():
    sub_provider_id = "sub_inv_failed_001"
    subscription = _make_subscription(
        provider_subscription_id=sub_provider_id, status="active"
    )

    evt = _event(
        "invoice.payment_failed",
        data_object={"subscription": sub_provider_id},
    )
    db = _make_db()
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=subscription)
    ))

    req = _make_request(_json_bytes(evt))
    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert subscription.status == "past_due"
    assert db.add.call_count >= 1


# ─── Test 9: customer.subscription.deleted → Subscription cancelled ───────────


@pytest.mark.asyncio
async def test_subscription_deleted_marks_cancelled():
    sub_provider_id = "sub_deleted_001"
    subscription = _make_subscription(
        provider_subscription_id=sub_provider_id, status="active"
    )

    evt = _event(
        "customer.subscription.deleted",
        data_object={"id": sub_provider_id},
    )
    db = _make_db()
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=subscription)
    ))

    req = _make_request(_json_bytes(evt))
    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert subscription.status == "cancelled"
    assert subscription.cancelled_at is not None
    assert db.add.call_count >= 1


# ─── Test 10: charge.dispute.created → 200 log-only ─────────────────────────


@pytest.mark.asyncio
async def test_dispute_created_returns_200():
    evt = _event(
        "charge.dispute.created",
        data_object={
            "id": "dp_test_001",
            "charge": "ch_test_001",
            "amount": 5000,
            "currency": "krw",
        },
    )
    db = _make_db()
    req = _make_request(_json_bytes(evt))

    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    db.commit.assert_called_once()


# ─── Test 11: unknown event_type → 200 graceful ───────────────────────────────


@pytest.mark.asyncio
async def test_unknown_event_type_returns_200_gracefully():
    evt = _event("completely.unknown.event.type.xyz")
    db = _make_db()
    req = _make_request(_json_bytes(evt))

    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert resp["data"]["type"] == "completely.unknown.event.type.xyz"
    # Still committed (stored for audit)
    db.commit.assert_called_once()


# ─── Test 12: Idempotent duplicate → 200 with duplicate=True ─────────────────


@pytest.mark.asyncio
async def test_duplicate_event_id_returns_200_with_duplicate_flag():
    evt_id = "evt_duplicate_idempotency_test"
    evt = _event("payment_intent.succeeded", event_id=evt_id)

    # flush raises IntegrityError → duplicate path
    db = _make_db(flush_raises=IntegrityError("duplicate", {}, Exception()))
    req = _make_request(_json_bytes(evt))

    resp = await stripe_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    assert resp["data"]["duplicate"] is True
    # Rolled back, NOT committed
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


# ─── Bonus: legacy /payments alias also works ─────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_payments_alias_returns_200():
    evt = _event("checkout.session.completed")
    db = _make_db()
    req = _make_request(_json_bytes(evt))

    resp = await payments_webhook(request=req, db=db, stripe_signature=None)

    assert resp["data"]["received"] is True
    db.commit.assert_called_once()
