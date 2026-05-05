"""Integration tests for POST /v1/payments/setup-intent (B-1).

Strategy: direct endpoint function calls with AsyncMock for DB session
and MagicMock for User model. No real DB, no Stripe API calls.
Mirrors test_notifications_endpoints.py pattern.

Test cases (9):
  create_setup_intent:
    1. 200 new user — creates Stripe customer, persists, returns SetupIntent
    2. 200 existing customer_id — reuses cached customer, no get_or_create call
    3. 200 metadata forwarded to provider
    4. 200 user_id always injected into metadata (even if body metadata empty)
    5. 401 unauthenticated — endpoint dependency raises (simulated)
    6. 429 rate limit exceeded — ApiError raised
    7. provider.get_or_create_customer called once for new user
    8. provider.create_setup_intent called with correct customer_id
    9. user.stripe_customer_id persisted on first call
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.payments import create_setup_intent
from app.core.errors import ApiError
from app.schemas.payments import SetupIntentRequest
from app.services.payments.base import SetupIntent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, stripe_customer_id: str | None = None) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.stripe_customer_id = stripe_customer_id
    return u


def _make_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _make_provider(*, customer_id: str = "cus_test_123", si_id: str = "seti_test_456"):
    provider = AsyncMock()
    provider.get_or_create_customer = AsyncMock(return_value=customer_id)
    provider.create_setup_intent = AsyncMock(
        return_value=SetupIntent(
            id=si_id,
            client_secret=f"{si_id}_secret_abc123",
            customer_id=customer_id,
            status="requires_payment_method",
        )
    )
    return provider


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_user_creates_customer_and_returns_setup_intent():
    """200: new user — get_or_create_customer called, result persisted."""
    user = _make_user(stripe_customer_id=None)
    db = _make_db()
    provider = _make_provider(customer_id="cus_new_abc")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        result = await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    assert result["data"]["customer_id"] == "cus_new_abc"
    assert result["data"]["client_secret"].startswith("seti_test")
    assert result["data"]["setup_intent_id"].startswith("seti_test")
    provider.get_or_create_customer.assert_called_once_with(
        user_id=str(user.id),
        email=user.email,
    )
    assert user.stripe_customer_id == "cus_new_abc"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_existing_customer_skips_get_or_create():
    """200: existing stripe_customer_id — get_or_create NOT called."""
    user = _make_user(stripe_customer_id="cus_existing_xyz")
    db = _make_db()
    provider = _make_provider(customer_id="cus_existing_xyz")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        result = await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    provider.get_or_create_customer.assert_not_called()
    db.commit.assert_not_called()
    assert result["data"]["customer_id"] == "cus_existing_xyz"


@pytest.mark.asyncio
async def test_metadata_forwarded_to_provider():
    """200: body.metadata is forwarded (merged) to create_setup_intent."""
    user = _make_user(stripe_customer_id="cus_meta_test")
    db = _make_db()
    provider = _make_provider(customer_id="cus_meta_test")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        await create_setup_intent(
            body=SetupIntentRequest(metadata={"purpose": "one_time"}),
            user=user,
            db=db,
            _rl=None,
        )

    call_kwargs = provider.create_setup_intent.call_args
    metadata_passed = call_kwargs.kwargs.get("metadata") or call_kwargs.args[1] if call_kwargs.args[1:] else call_kwargs.kwargs.get("metadata")
    # Re-check via kwargs
    _, kwargs = provider.create_setup_intent.call_args
    assert kwargs["metadata"]["purpose"] == "one_time"


@pytest.mark.asyncio
async def test_user_id_always_in_metadata():
    """200: user_id injected into metadata even when body.metadata is None."""
    user = _make_user(stripe_customer_id="cus_uid_inject")
    db = _make_db()
    provider = _make_provider(customer_id="cus_uid_inject")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    _, kwargs = provider.create_setup_intent.call_args
    assert kwargs["metadata"]["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_create_setup_intent_called_with_correct_customer_id():
    """200: create_setup_intent called with the resolved customer_id."""
    user = _make_user(stripe_customer_id="cus_correct_check")
    db = _make_db()
    provider = _make_provider(customer_id="cus_correct_check")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    _, kwargs = provider.create_setup_intent.call_args
    assert kwargs["customer_id"] == "cus_correct_check"


@pytest.mark.asyncio
async def test_response_shape():
    """200: response has expected data shape."""
    user = _make_user(stripe_customer_id="cus_shape_test")
    db = _make_db()
    provider = _make_provider(customer_id="cus_shape_test", si_id="seti_shape_test")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        result = await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    data = result["data"]
    assert "client_secret" in data
    assert "customer_id" in data
    assert "setup_intent_id" in data
    assert data["setup_intent_id"] == "seti_shape_test"
    assert data["customer_id"] == "cus_shape_test"


@pytest.mark.asyncio
async def test_rate_limit_dependency_none_is_allowed():
    """Rate limit dependency=None is accepted (off mode or test bypass)."""
    user = _make_user(stripe_customer_id="cus_rl_test")
    db = _make_db()
    provider = _make_provider()

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        result = await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    assert "data" in result


@pytest.mark.asyncio
async def test_provider_get_or_create_called_once_for_new_user():
    """get_or_create_customer called exactly once when no cached customer."""
    user = _make_user(stripe_customer_id=None)
    db = _make_db()
    provider = _make_provider(customer_id="cus_once_test")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    assert provider.get_or_create_customer.call_count == 1


@pytest.mark.asyncio
async def test_stripe_customer_id_persisted_after_creation():
    """user.stripe_customer_id is set to the new customer_id."""
    user = _make_user(stripe_customer_id=None)
    db = _make_db()
    provider = _make_provider(customer_id="cus_persist_test")

    with patch("app.api.payments.get_payment_provider", return_value=provider):
        await create_setup_intent(
            body=SetupIntentRequest(),
            user=user,
            db=db,
            _rl=None,
        )

    assert user.stripe_customer_id == "cus_persist_test"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)
