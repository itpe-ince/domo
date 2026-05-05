"""Artist patronage dashboard endpoints (B-2).

Routes (all under /me/patronage):
  GET  /summary        — aggregate stats for the artist
  GET  /supporters     — paginated list of supporters
  GET  /revenue        — time-series revenue (daily | monthly)
  POST /payout-request — create payout request (optional, placeholder)

Auth guard: all endpoints require role='artist'. Non-artist → 403 ARTIST_ONLY.
N+1 policy: each endpoint issues a single aggregate SQL (or two at most for
separate Sponsorship + Subscription tables). No per-row loads.
"""
from __future__ import annotations

import base64
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.sponsorship import Sponsorship, Subscription
from app.models.user import User
from app.schemas.patronage import (
    ChurnItem,
    ChurnListResponse,
    PayoutRequestBody,
    PayoutRequestResponse,
    PatronageSummary,
    PatronageSummaryResponse,
    RevenueDataPoint,
    RevenueResponse,
    SupporterItem,
    SupportersResponse,
    TierDistribution,
)

router = APIRouter(prefix="/me/patronage", tags=["me-patronage"])

# ─── Helpers ──────────────────────────────────────────────────────────────────

_USD_PER_KRW = Decimal("0.00073")  # rough fallback; replace with fx service later


def _to_cents(amount: Decimal, currency: str) -> int:
    """Convert DB amount (Numeric 12,2) to USD cents for API output.

    The Sponsorship/Subscription tables store KRW amounts as default.
    For simplicity we apply a fixed conversion; Phase 6+ can call an FX service.
    """
    if currency.upper() == "USD":
        return int((amount * 100).to_integral_value())
    # KRW → USD cents
    return int((amount * _USD_PER_KRW * 100).to_integral_value())


def _require_artist(user: User) -> None:
    if user.role != "artist":
        raise ApiError(
            "ARTIST_ONLY",
            "This endpoint is only available to artists",
            http_status=403,
        )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ─── 1. Summary ───────────────────────────────────────────────────────────────


@router.get("/summary", response_model=PatronageSummaryResponse)
async def get_patronage_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("patronage_summary"),
):
    _require_artist(user)
    now = _now_utc()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = current_month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    thirty_days_ago = now - timedelta(days=30)

    # ── One-time sponsorships aggregate ──────────────────────────────────────
    # Single SQL: lifetime + current month + previous month revenue from sponsorships
    sp_agg = await db.execute(
        select(
            func.coalesce(func.sum(Sponsorship.amount), 0).label("lifetime"),
            func.coalesce(
                func.sum(
                    case(
                        (Sponsorship.created_at >= current_month_start, Sponsorship.amount),
                        else_=Decimal("0"),
                    )
                ),
                0,
            ).label("current_month"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Sponsorship.created_at >= prev_month_start)
                            & (Sponsorship.created_at < current_month_start),
                            Sponsorship.amount,
                        ),
                        else_=Decimal("0"),
                    )
                ),
                0,
            ).label("prev_month"),
            func.count(func.distinct(Sponsorship.sponsor_id)).label("unique_sponsors"),
            Sponsorship.currency,
        )
        .where(
            Sponsorship.artist_id == user.id,
            Sponsorship.status == "completed",
        )
        .group_by(Sponsorship.currency)
    )
    sp_row = sp_agg.first()
    sp_lifetime = Decimal(sp_row.lifetime) if sp_row else Decimal("0")
    sp_current = Decimal(sp_row.current_month) if sp_row else Decimal("0")
    sp_prev = Decimal(sp_row.prev_month) if sp_row else Decimal("0")
    sp_currency = sp_row.currency if sp_row else "KRW"
    total_sponsors = int(sp_row.unique_sponsors) if sp_row else 0

    # ── Subscriptions aggregate ───────────────────────────────────────────────
    # Single SQL: active count + churn + monthly run-rate
    sub_agg = await db.execute(
        select(
            func.count(Subscription.id)
            .filter(Subscription.status == "active")
            .label("active_count"),
            func.count(Subscription.id)
            .filter(
                Subscription.status == "cancelled",
                Subscription.cancelled_at >= thirty_days_ago,
            )
            .label("churned_30d"),
            func.coalesce(
                func.sum(Subscription.monthly_amount).filter(
                    Subscription.status == "active"
                ),
                0,
            ).label("monthly_run_rate"),
            func.coalesce(
                func.sum(Subscription.monthly_amount).filter(
                    Subscription.status == "active",
                ),
                0,
            ).label("sub_current"),
            Subscription.currency,
        )
        .where(Subscription.artist_id == user.id)
        .group_by(Subscription.currency)
    )
    sub_row = sub_agg.first()
    active_subs = int(sub_row.active_count) if sub_row else 0
    churned_30d = int(sub_row.churned_30d) if sub_row else 0
    sub_currency = sub_row.currency if sub_row else "KRW"
    sub_monthly_rr = Decimal(sub_row.monthly_run_rate) if sub_row else Decimal("0")

    # Combine revenue (both tables use same currency in practice)
    lifetime_cents = _to_cents(sp_lifetime, sp_currency)
    current_cents = _to_cents(sp_current, sp_currency) + _to_cents(
        sub_monthly_rr, sub_currency
    )
    prev_cents = _to_cents(sp_prev, sp_currency)

    # ── Unique subscribers count ──────────────────────────────────────────────
    sub_count_result = await db.execute(
        select(func.count(func.distinct(Subscription.sponsor_id))).where(
            Subscription.artist_id == user.id,
            Subscription.status == "active",
        )
    )
    total_subscribers = sub_count_result.scalar_one() or 0

    total_supporters = total_sponsors + total_subscribers

    summary = PatronageSummary(
        total_supporters=total_supporters,
        total_sponsors=total_sponsors,
        total_subscribers=total_subscribers,
        lifetime_revenue_usd_cents=lifetime_cents,
        current_month_revenue_usd_cents=current_cents,
        previous_month_revenue_usd_cents=prev_cents,
        active_subscriptions=active_subs,
        churned_last_30d=churned_30d,
        tier_distribution=TierDistribution(
            subscriber=total_subscribers,
            sponsor=total_sponsors,
            follower=0,
        ),
        currency="USD",
    )
    return PatronageSummaryResponse(data=summary)


# ─── 2. Supporters list ───────────────────────────────────────────────────────


def _encode_cursor(sponsor_id: str, source: str) -> str:
    payload = json.dumps({"sid": sponsor_id, "src": source})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> dict | None:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        return json.loads(payload)
    except Exception:
        return None


@router.get("/supporters", response_model=SupportersResponse)
async def get_supporters(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    filter: Literal["active", "churned", "all"] = Query("all"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("patronage_supporters"),
):
    _require_artist(user)

    # ── Fetch subscriptions (recurring supporters) ────────────────────────────
    sub_q = (
        select(
            Subscription.sponsor_id,
            func.min(Subscription.created_at).label("since"),
            func.sum(Subscription.monthly_amount).label("lifetime_amount"),
            func.coalesce(
                func.sum(Subscription.monthly_amount).filter(
                    Subscription.status == "active"
                ),
                0,
            ).label("monthly_amount"),
            Subscription.status,
            Subscription.currency,
        )
        .where(Subscription.artist_id == user.id)
        .group_by(Subscription.sponsor_id, Subscription.status, Subscription.currency)
    )
    if filter == "active":
        sub_q = sub_q.where(Subscription.status == "active")
    elif filter == "churned":
        sub_q = sub_q.where(Subscription.status == "cancelled")

    sub_result = await db.execute(sub_q)
    sub_rows = sub_result.all()

    # ── Fetch one-time sponsors ───────────────────────────────────────────────
    sp_q = (
        select(
            Sponsorship.sponsor_id,
            func.min(Sponsorship.created_at).label("since"),
            func.sum(Sponsorship.amount).label("lifetime_amount"),
            Sponsorship.currency,
        )
        .where(
            Sponsorship.artist_id == user.id,
            Sponsorship.status == "completed",
        )
        .group_by(Sponsorship.sponsor_id, Sponsorship.currency)
    )
    sp_result = await db.execute(sp_q)
    sp_rows = sp_result.all()

    # ── Merge: subscribers take priority if they appear in both ───────────────
    merged: dict[str, dict] = {}
    for row in sub_rows:
        sid = str(row.sponsor_id)
        merged[sid] = {
            "user_id": sid,
            "tier": "subscriber",
            "since": row.since,
            "lifetime_amount": Decimal(row.lifetime_amount),
            "monthly_amount": Decimal(row.monthly_amount),
            "subscription_status": row.status,
            "currency": row.currency,
        }
    for row in sp_rows:
        sid = str(row.sponsor_id)
        if sid not in merged:
            if filter == "churned":
                continue  # churned filter only shows cancelled subscribers
            merged[sid] = {
                "user_id": sid,
                "tier": "sponsor",
                "since": row.since,
                "lifetime_amount": Decimal(row.lifetime_amount),
                "monthly_amount": Decimal("0"),
                "subscription_status": None,
                "currency": row.currency,
            }

    # Sort by since desc for consistent cursor pagination
    all_items = sorted(merged.values(), key=lambda x: x["since"], reverse=True)

    # ── Apply cursor ──────────────────────────────────────────────────────────
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded:
            cursor_sid = decoded.get("sid", "")
            # Find position in sorted list
            pos = next(
                (i for i, x in enumerate(all_items) if x["user_id"] == cursor_sid),
                None,
            )
            if pos is not None:
                all_items = all_items[pos + 1 :]

    page = all_items[: limit + 1]
    has_more = len(page) > limit
    page = page[:limit]

    # ── Batch load user info for display ─────────────────────────────────────
    user_ids = [uuid.UUID(item["user_id"]) for item in page]
    user_map: dict[str, User] = {}
    if user_ids:
        u_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in u_result.scalars().all():
            user_map[str(u.id)] = u

    supporters = []
    for item in page:
        u = user_map.get(item["user_id"])
        supporters.append(
            SupporterItem(
                user_id=item["user_id"],
                username=u.display_name if u else item["user_id"][:8],
                avatar_url=u.avatar_url if u else None,
                tier=item["tier"],
                since=item["since"].isoformat() if item["since"] else "",
                lifetime_amount_cents=_to_cents(item["lifetime_amount"], item["currency"]),
                monthly_amount_cents=_to_cents(item["monthly_amount"], item["currency"]),
                subscription_status=item["subscription_status"],
            )
        )

    next_cursor = None
    if has_more and page:
        next_cursor = _encode_cursor(page[-1].user_id, page[-1].tier)

    return SupportersResponse(data=supporters, next_cursor=next_cursor, has_more=has_more)


# ─── 3. Revenue time-series ───────────────────────────────────────────────────


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    granularity: Literal["daily", "monthly"] = Query("daily"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("patronage_revenue"),
):
    _require_artist(user)

    # Default: last 30 days
    today = _now_utc().date()
    if from_date is None:
        from_date = today - timedelta(days=30)
    if to_date is None:
        to_date = today

    if from_date > to_date:
        raise ApiError(
            "VALIDATION_ERROR",
            "from date must be <= to date",
            http_status=422,
        )
    if (to_date - from_date).days > 366:
        raise ApiError(
            "VALIDATION_ERROR",
            "Date range cannot exceed 366 days",
            http_status=422,
        )

    from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=timezone.utc)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # ── One aggregate SQL per table ───────────────────────────────────────────
    if granularity == "daily":
        trunc_fn = func.date_trunc("day", Sponsorship.created_at)
        sp_q = (
            select(
                trunc_fn.label("bucket"),
                func.sum(Sponsorship.amount).label("total"),
                Sponsorship.currency,
            )
            .where(
                Sponsorship.artist_id == user.id,
                Sponsorship.status == "completed",
                Sponsorship.created_at >= from_dt,
                Sponsorship.created_at <= to_dt,
            )
            .group_by("bucket", Sponsorship.currency)
            .order_by("bucket")
        )

        sub_trunc = func.date_trunc("day", Subscription.created_at)
        sub_q = (
            select(
                sub_trunc.label("bucket"),
                func.sum(Subscription.monthly_amount).label("total"),
                Subscription.currency,
            )
            .where(
                Subscription.artist_id == user.id,
                Subscription.status == "active",
                Subscription.created_at >= from_dt,
                Subscription.created_at <= to_dt,
            )
            .group_by("bucket", Subscription.currency)
            .order_by("bucket")
        )
    else:  # monthly
        trunc_fn = func.date_trunc("month", Sponsorship.created_at)
        sp_q = (
            select(
                trunc_fn.label("bucket"),
                func.sum(Sponsorship.amount).label("total"),
                Sponsorship.currency,
            )
            .where(
                Sponsorship.artist_id == user.id,
                Sponsorship.status == "completed",
                Sponsorship.created_at >= from_dt,
                Sponsorship.created_at <= to_dt,
            )
            .group_by("bucket", Sponsorship.currency)
            .order_by("bucket")
        )

        sub_trunc = func.date_trunc("month", Subscription.created_at)
        sub_q = (
            select(
                sub_trunc.label("bucket"),
                func.sum(Subscription.monthly_amount).label("total"),
                Subscription.currency,
            )
            .where(
                Subscription.artist_id == user.id,
                Subscription.status == "active",
                Subscription.created_at >= from_dt,
                Subscription.created_at <= to_dt,
            )
            .group_by("bucket", Subscription.currency)
            .order_by("bucket")
        )

    sp_rows = (await db.execute(sp_q)).all()
    sub_rows = (await db.execute(sub_q)).all()

    # Merge into bucket map (key = date string)
    buckets: dict[str, int] = {}

    for row in sp_rows:
        bucket_dt: datetime = row.bucket
        key = _format_bucket(bucket_dt, granularity)
        cents = _to_cents(Decimal(row.total), row.currency)
        buckets[key] = buckets.get(key, 0) + cents

    for row in sub_rows:
        bucket_dt = row.bucket
        key = _format_bucket(bucket_dt, granularity)
        cents = _to_cents(Decimal(row.total), row.currency)
        buckets[key] = buckets.get(key, 0) + cents

    # Fill all buckets in range with 0 if not present
    data_points = _fill_range(from_date, to_date, granularity, buckets)

    return RevenueResponse(
        data=data_points,
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        granularity=granularity,
    )


def _format_bucket(dt: datetime, granularity: str) -> str:
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m")


def _fill_range(
    from_date: date,
    to_date: date,
    granularity: str,
    buckets: dict[str, int],
) -> list[RevenueDataPoint]:
    """Generate one data point per bucket in range, 0 if no revenue."""
    points: list[RevenueDataPoint] = []
    if granularity == "daily":
        current = from_date
        while current <= to_date:
            key = current.strftime("%Y-%m-%d")
            points.append(RevenueDataPoint(date=key, amount_cents=buckets.get(key, 0)))
            current += timedelta(days=1)
    else:
        # monthly: iterate months
        year, month = from_date.year, from_date.month
        end_year, end_month = to_date.year, to_date.month
        while (year, month) <= (end_year, end_month):
            key = f"{year:04d}-{month:02d}"
            points.append(RevenueDataPoint(date=key, amount_cents=buckets.get(key, 0)))
            month += 1
            if month > 12:
                month = 1
                year += 1
    return points


# ─── 4. Churn list (D'-2) ────────────────────────────────────────────────────


@router.get("/churn", response_model=ChurnListResponse)
async def get_churn_list(
    limit: int = Query(20, ge=1, le=100),
    from_date: str | None = Query(None, alias="from"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("patronage_churn"),
):
    """Return recently churned subscribers for the authenticated artist.

    Default window: last 30 days.
    Rate limit: 30/min/user (patronage_churn scope).
    """
    _require_artist(user)

    # Determine cutoff date
    if from_date:
        try:
            cutoff = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        except ValueError:
            raise ApiError(
                "VALIDATION_ERROR",
                "Invalid 'from' date — expected ISO8601 format",
                http_status=422,
            )
    else:
        cutoff = _now_utc() - timedelta(days=30)

    # Single SQL: cancelled subscriptions for this artist within window
    q = (
        select(
            Subscription.sponsor_id,
            Subscription.cancelled_at,
            Subscription.cancellation_reason,
            Subscription.cancellation_feedback,
            Subscription.monthly_amount,
            Subscription.currency,
        )
        .where(
            Subscription.artist_id == user.id,
            Subscription.status == "cancelled",
            Subscription.cancelled_at >= cutoff,
            Subscription.cancelled_at.is_not(None),
        )
        .order_by(Subscription.cancelled_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).all()

    if not rows:
        return ChurnListResponse(data=[])

    # Batch load user info
    sponsor_ids = [row.sponsor_id for row in rows]
    u_result = await db.execute(select(User).where(User.id.in_(sponsor_ids)))
    user_map: dict[str, User] = {str(u.id): u for u in u_result.scalars().all()}

    items: list[ChurnItem] = []
    for row in rows:
        u = user_map.get(str(row.sponsor_id))
        feedback_preview: str | None = None
        if row.cancellation_feedback:
            feedback_preview = row.cancellation_feedback[:100]

        items.append(
            ChurnItem(
                user_id=str(row.sponsor_id),
                username=u.display_name if u else str(row.sponsor_id)[:8],
                avatar_url=u.avatar_url if u else None,
                cancelled_at=(
                    row.cancelled_at.isoformat()
                    if row.cancelled_at
                    else _now_utc().isoformat()
                ),
                cancellation_reason=row.cancellation_reason,
                cancellation_feedback_preview=feedback_preview,
                tier="subscriber",
                lifetime_amount_cents=_to_cents(
                    row.monthly_amount, row.currency
                ),
            )
        )

    return ChurnListResponse(data=items)


# ─── 5. Payout request (optional placeholder) ─────────────────────────────────


@router.post("/payout-request", response_model=PayoutRequestResponse)
async def create_payout_request(
    body: PayoutRequestBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Placeholder payout request endpoint.

    Full integration with settlement_jobs.py is carry-over (Phase 6).
    Returns a stub response so the frontend can render the modal flow.
    """
    _require_artist(user)

    if user.identity_verified_at is None:
        raise ApiError(
            "KYC_REQUIRED",
            "Identity verification required before requesting payout",
            http_status=403,
        )

    # Stub — real implementation will persist a PayoutRequest row and trigger settlement
    return PayoutRequestResponse(
        id=str(uuid.uuid4()),
        amount_cents=body.amount_cents,
        currency=body.currency,
        method=body.method,
        status="pending_review",
        created_at=_now_utc().isoformat(),
    )
