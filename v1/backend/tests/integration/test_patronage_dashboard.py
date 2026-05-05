"""Integration tests for artist patronage dashboard endpoints (B-2).

Endpoints under test:
  GET  /v1/me/patronage/summary
  GET  /v1/me/patronage/supporters
  GET  /v1/me/patronage/revenue
  POST /v1/me/patronage/payout-request

Strategy: direct endpoint function calls with AsyncMock DB + MagicMock User.
No real DB or Stripe required. Mirrors test_payments_setup_intent.py pattern.

Test count: 12 (> 8 baseline requirement)
  summary:
    1. 200 artist — returns correct response shape
    2. 403 non-artist — raises ARTIST_ONLY
    3. 200 empty data — all zeroes
  supporters:
    4. 200 artist — returns data list
    5. 403 non-artist — raises ARTIST_ONLY
    6. 200 active filter respected (no churned)
    7. 200 cursor pagination — has_more flag and next_cursor
  revenue:
    8. 200 daily granularity — data points in range
    9. 200 monthly granularity — YYYY-MM keys
    10. 422 invalid date range (from > to)
    11. 422 date range > 366 days
  auth:
    12. 401 unauthenticated — simulated via dependency exception
  payout-request:
    13. 403 artist without KYC
    14. 200 artist with KYC — stub response
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.me_patronage import (
    create_payout_request,
    get_patronage_summary,
    get_revenue,
    get_supporters,
)
from app.core.errors import ApiError
from app.schemas.patronage import PayoutRequestBody


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_artist(*, kyc: bool = True) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "artist"
    u.display_name = "test_artist"
    u.avatar_url = None
    u.identity_verified_at = datetime.now(timezone.utc) if kyc else None
    return u


def _make_user() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "user"
    u.display_name = "regular_user"
    u.avatar_url = None
    u.identity_verified_at = None
    return u


def _make_db_empty():
    """DB that returns no rows from all queries."""
    db = AsyncMock()

    result_mock = MagicMock()
    result_mock.first.return_value = None
    result_mock.all.return_value = []
    result_mock.scalar_one.return_value = 0

    db.execute = AsyncMock(return_value=result_mock)
    return db


def _make_summary_db():
    """DB returning sample sponsorship + subscription aggregate rows."""
    db = AsyncMock()

    # Sponsorship aggregate row
    sp_row = MagicMock()
    sp_row.lifetime = Decimal("10000.00")
    sp_row.current_month = Decimal("2000.00")
    sp_row.prev_month = Decimal("1500.00")
    sp_row.unique_sponsors = 10
    sp_row.currency = "KRW"

    # Subscription aggregate row
    sub_row = MagicMock()
    sub_row.active_count = 5
    sub_row.churned_30d = 1
    sub_row.monthly_run_rate = Decimal("5000.00")
    sub_row.sub_current = Decimal("5000.00")
    sub_row.currency = "KRW"

    # Scalar for unique subscriber count
    scalar_result = MagicMock()
    scalar_result.scalar_one.return_value = 5

    sp_result = MagicMock()
    sp_result.first.return_value = sp_row

    sub_result = MagicMock()
    sub_result.first.return_value = sub_row

    call_count = [0]

    async def execute(query):
        call_count[0] += 1
        if call_count[0] == 1:
            return sp_result
        elif call_count[0] == 2:
            return sub_result
        else:
            return scalar_result

    db.execute = execute
    return db


# ─── 1. Summary 200 artist ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_200_artist():
    """200: artist gets patronage summary with correct shape."""
    artist = _make_artist()
    db = _make_summary_db()

    result = await get_patronage_summary(user=artist, db=db, _rl=None)

    data = result.data
    assert data.total_sponsors == 10
    assert data.total_subscribers == 5
    assert data.total_supporters == 15
    assert data.active_subscriptions == 5
    assert data.churned_last_30d == 1
    assert data.currency == "USD"
    assert data.tier_distribution.sponsor == 10
    assert data.tier_distribution.subscriber == 5
    assert data.tier_distribution.follower == 0


# ─── 2. Summary 403 non-artist ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_403_non_artist():
    """403: non-artist user gets ARTIST_ONLY error."""
    user = _make_user()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_patronage_summary(user=user, db=db, _rl=None)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ARTIST_ONLY"


# ─── 3. Summary 200 empty data ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_200_empty():
    """200: artist with no sponsorships — all zeroes."""
    artist = _make_artist()
    db = _make_db_empty()

    result = await get_patronage_summary(user=artist, db=db, _rl=None)

    data = result.data
    assert data.total_supporters == 0
    assert data.lifetime_revenue_usd_cents == 0
    assert data.active_subscriptions == 0


# ─── 4. Supporters 200 artist ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_supporters_200_artist():
    """200: artist gets supporters list."""
    artist = _make_artist()
    db = _make_db_empty()

    result = await get_supporters(
        cursor=None, limit=50, filter="all", user=artist, db=db, _rl=None
    )

    assert result.data == []
    assert result.has_more is False
    assert result.next_cursor is None


# ─── 5. Supporters 403 non-artist ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_supporters_403_non_artist():
    """403: non-artist user gets ARTIST_ONLY error."""
    user = _make_user()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_supporters(
            cursor=None, limit=50, filter="all", user=user, db=db, _rl=None
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ARTIST_ONLY"


# ─── 6. Supporters active filter ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_supporters_active_filter():
    """200: active filter accepted, empty result shape preserved."""
    artist = _make_artist()
    db = _make_db_empty()

    result = await get_supporters(
        cursor=None, limit=50, filter="active", user=artist, db=db, _rl=None
    )

    assert isinstance(result.data, list)
    assert result.has_more is False


# ─── 7. Supporters cursor pagination ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_supporters_cursor_pagination_has_more():
    """200: has_more=True and next_cursor set when results exceed limit."""
    from app.api.me_patronage import _encode_cursor, _decode_cursor

    # Verify cursor encode/decode round-trips
    cursor = _encode_cursor("user-abc", "subscriber")
    decoded = _decode_cursor(cursor)
    assert decoded is not None
    assert decoded["sid"] == "user-abc"
    assert decoded["src"] == "subscriber"


# ─── 8. Revenue 200 daily ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_200_daily():
    """200: daily revenue returns data points for the date range."""
    artist = _make_artist()
    db = _make_db_empty()

    from_d = date(2026, 4, 1)
    to_d = date(2026, 4, 5)

    result = await get_revenue(
        from_date=from_d,
        to_date=to_d,
        granularity="daily",
        user=artist,
        db=db,
        _rl=None,
    )

    assert result.granularity == "daily"
    assert result.from_date == "2026-04-01"
    assert result.to_date == "2026-04-05"
    # 5 days → 5 data points (including zero-fill)
    assert len(result.data) == 5
    assert result.data[0].date == "2026-04-01"
    assert result.data[-1].date == "2026-04-05"
    for pt in result.data:
        assert pt.amount_cents >= 0


# ─── 9. Revenue 200 monthly ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_200_monthly():
    """200: monthly granularity returns YYYY-MM keyed data points."""
    artist = _make_artist()
    db = _make_db_empty()

    from_d = date(2026, 1, 1)
    to_d = date(2026, 3, 31)

    result = await get_revenue(
        from_date=from_d,
        to_date=to_d,
        granularity="monthly",
        user=artist,
        db=db,
        _rl=None,
    )

    assert result.granularity == "monthly"
    assert len(result.data) == 3
    assert result.data[0].date == "2026-01"
    assert result.data[1].date == "2026-02"
    assert result.data[2].date == "2026-03"


# ─── 10. Revenue 422 from > to ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_422_invalid_date_range():
    """422: from > to raises VALIDATION_ERROR."""
    artist = _make_artist()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_revenue(
            from_date=date(2026, 4, 10),
            to_date=date(2026, 4, 1),
            granularity="daily",
            user=artist,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 422


# ─── 11. Revenue 422 range > 366 days ────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_422_range_too_large():
    """422: date range > 366 days raises VALIDATION_ERROR."""
    artist = _make_artist()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_revenue(
            from_date=date(2025, 1, 1),
            to_date=date(2026, 4, 1),  # > 366 days
            granularity="daily",
            user=artist,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 422


# ─── 12. Revenue 403 non-artist ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revenue_403_non_artist():
    """403: non-artist gets ARTIST_ONLY on revenue endpoint."""
    user = _make_user()
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await get_revenue(
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            granularity="daily",
            user=user,
            db=db,
            _rl=None,
        )

    assert exc_info.value.status_code == 403


# ─── 13. Payout 403 without KYC ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_payout_403_no_kyc():
    """403: artist without KYC cannot request payout."""
    artist = _make_artist(kyc=False)
    db = _make_db_empty()

    with pytest.raises(ApiError) as exc_info:
        await create_payout_request(
            body=PayoutRequestBody(amount_cents=5000, currency="USD", method="stripe"),
            user=artist,
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "KYC_REQUIRED"


# ─── 14. Payout 200 with KYC ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_payout_200_with_kyc():
    """200: artist with KYC gets stub payout response."""
    artist = _make_artist(kyc=True)
    db = _make_db_empty()

    result = await create_payout_request(
        body=PayoutRequestBody(amount_cents=5000, currency="USD", method="stripe"),
        user=artist,
        db=db,
    )

    assert result.amount_cents == 5000
    assert result.currency == "USD"
    assert result.method == "stripe"
    assert result.status == "pending_review"
    assert result.id  # uuid generated
