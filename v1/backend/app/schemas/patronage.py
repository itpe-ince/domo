"""Pydantic schemas for artist patronage dashboard (B-2 + D'-2).

Endpoints:
  GET /v1/me/patronage/summary
  GET /v1/me/patronage/supporters
  GET /v1/me/patronage/revenue
  GET /v1/me/patronage/churn   (D'-2)
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ─── Summary ─────────────────────────────────────────────────────────────────


class TierDistribution(BaseModel):
    subscriber: int = 0
    sponsor: int = 0
    follower: int = 0


class PatronageSummary(BaseModel):
    total_supporters: int
    total_sponsors: int
    total_subscribers: int
    lifetime_revenue_usd_cents: int
    current_month_revenue_usd_cents: int
    previous_month_revenue_usd_cents: int
    active_subscriptions: int
    churned_last_30d: int
    tier_distribution: TierDistribution
    currency: str = "USD"


class PatronageSummaryResponse(BaseModel):
    data: PatronageSummary


# ─── Supporters list ──────────────────────────────────────────────────────────


class SupporterItem(BaseModel):
    user_id: str
    username: str
    avatar_url: str | None
    tier: Literal["sponsor", "subscriber", "follower"]
    since: str  # ISO8601
    lifetime_amount_cents: int
    monthly_amount_cents: int
    subscription_status: Literal["active", "cancelled", "past_due"] | None


class SupportersResponse(BaseModel):
    data: list[SupporterItem]
    next_cursor: str | None = None
    has_more: bool = False


# ─── Revenue time-series ──────────────────────────────────────────────────────


class RevenueDataPoint(BaseModel):
    date: str  # YYYY-MM-DD or YYYY-MM for monthly
    amount_cents: int
    currency: str = "USD"


class RevenueResponse(BaseModel):
    data: list[RevenueDataPoint]
    from_date: str
    to_date: str
    granularity: Literal["daily", "monthly"]


# ─── Payout request (optional B-2 scope) ─────────────────────────────────────


class PayoutRequestBody(BaseModel):
    amount_cents: int = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    method: Literal["bank_transfer", "stripe"] = "stripe"


class PayoutRequestResponse(BaseModel):
    id: str
    amount_cents: int
    currency: str
    method: str
    status: str
    created_at: str


# ─── Churn list (D'-2) ───────────────────────────────────────────────────────


class ChurnItem(BaseModel):
    """One recently-churned subscriber as seen by the artist."""

    user_id: str
    username: str
    avatar_url: str | None = None
    cancelled_at: str  # ISO8601
    cancellation_reason: (
        Literal["too_expensive", "changed_mind", "not_satisfied", "other"] | None
    ) = None
    cancellation_feedback_preview: str | None = None  # max 100 chars
    tier: Literal["subscriber", "sponsor"] = "subscriber"
    lifetime_amount_cents: int = 0


class ChurnListResponse(BaseModel):
    data: list[ChurnItem]
