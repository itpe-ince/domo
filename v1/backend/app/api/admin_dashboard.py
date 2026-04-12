"""Admin dashboard + system settings API.

Reference: design.md §3.2 admin endpoints, §2.2 system_settings.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.auction import Auction, Order
from app.models.moderation import Report
from app.models.post import Post
from app.models.sponsorship import Sponsorship, Subscription, SystemSetting
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Stats: counts + recent activity ─────────────────────────────────────


@router.get("/dashboard/stats")
async def dashboard_stats(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    since = _now() - timedelta(days=days)

    total_users = await db.scalar(select(func.count()).select_from(User))
    total_artists = await db.scalar(
        select(func.count()).select_from(User).where(User.role == "artist")
    )
    suspended = await db.scalar(
        select(func.count()).select_from(User).where(User.status == "suspended")
    )
    new_users = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= since)
    )

    total_posts = await db.scalar(select(func.count()).select_from(Post))
    published_posts = await db.scalar(
        select(func.count()).select_from(Post).where(Post.status == "published")
    )
    pending_review = await db.scalar(
        select(func.count())
        .select_from(Post)
        .where(Post.status == "pending_review")
    )
    new_posts = await db.scalar(
        select(func.count()).select_from(Post).where(Post.created_at >= since)
    )

    active_auctions = await db.scalar(
        select(func.count()).select_from(Auction).where(Auction.status == "active")
    )
    ended_auctions = await db.scalar(
        select(func.count())
        .select_from(Auction)
        .where(Auction.status.in_(["ended", "settled"]))
    )

    pending_reports = await db.scalar(
        select(func.count()).select_from(Report).where(Report.status == "pending")
    )

    sponsorships_count = await db.scalar(
        select(func.count())
        .select_from(Sponsorship)
        .where(Sponsorship.status == "completed")
    )
    active_subscriptions = await db.scalar(
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.status == "active")
    )

    return {
        "data": {
            "window_days": days,
            "users": {
                "total": int(total_users or 0),
                "artists": int(total_artists or 0),
                "suspended": int(suspended or 0),
                "new_in_window": int(new_users or 0),
            },
            "content": {
                "total_posts": int(total_posts or 0),
                "published": int(published_posts or 0),
                "pending_review": int(pending_review or 0),
                "new_in_window": int(new_posts or 0),
            },
            "auctions": {
                "active": int(active_auctions or 0),
                "ended": int(ended_auctions or 0),
            },
            "moderation": {
                "pending_reports": int(pending_reports or 0),
            },
            "sponsorship": {
                "completed_total": int(sponsorships_count or 0),
                "active_subscriptions": int(active_subscriptions or 0),
            },
        }
    }


# ─── Revenue: aggregate by source ────────────────────────────────────────


@router.get("/dashboard/revenue")
async def dashboard_revenue(
    days: int = Query(30, ge=1, le=365),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    since = _now() - timedelta(days=days)

    # Sponsorship revenue (completed)
    spo_total = await db.scalar(
        select(func.coalesce(func.sum(Sponsorship.amount), 0)).where(
            Sponsorship.status == "completed",
            Sponsorship.created_at >= since,
        )
    )
    spo_count = await db.scalar(
        select(func.count()).select_from(Sponsorship).where(
            Sponsorship.status == "completed",
            Sponsorship.created_at >= since,
        )
    )

    # Subscription revenue projection (current monthly)
    sub_monthly = await db.scalar(
        select(func.coalesce(func.sum(Subscription.monthly_amount), 0)).where(
            Subscription.status == "active",
        )
    )
    sub_count = await db.scalar(
        select(func.count()).select_from(Subscription).where(
            Subscription.status == "active",
        )
    )

    # Order revenue (paid only)
    auction_total = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == "paid",
            Order.source == "auction",
            Order.paid_at.is_not(None),
            Order.paid_at >= since,
        )
    )
    auction_fee = await db.scalar(
        select(func.coalesce(func.sum(Order.platform_fee), 0)).where(
            Order.status == "paid",
            Order.source == "auction",
            Order.paid_at.is_not(None),
            Order.paid_at >= since,
        )
    )
    buy_now_total = await db.scalar(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == "paid",
            Order.source == "buy_now",
            Order.paid_at.is_not(None),
            Order.paid_at >= since,
        )
    )
    buy_now_fee = await db.scalar(
        select(func.coalesce(func.sum(Order.platform_fee), 0)).where(
            Order.status == "paid",
            Order.source == "buy_now",
            Order.paid_at.is_not(None),
            Order.paid_at >= since,
        )
    )

    gmv = (
        Decimal(str(spo_total or 0))
        + Decimal(str(auction_total or 0))
        + Decimal(str(buy_now_total or 0))
    )
    platform_fee_total = Decimal(str(auction_fee or 0)) + Decimal(str(buy_now_fee or 0))

    return {
        "data": {
            "window_days": days,
            "currency": "KRW",
            "gmv_total": str(gmv),
            "platform_fee_total": str(platform_fee_total),
            "by_source": {
                "sponsorship": {
                    "amount": str(spo_total or 0),
                    "count": int(spo_count or 0),
                },
                "subscription_monthly_run_rate": {
                    "amount": str(sub_monthly or 0),
                    "active_count": int(sub_count or 0),
                },
                "auction": {
                    "amount": str(auction_total or 0),
                    "platform_fee": str(auction_fee or 0),
                },
                "buy_now": {
                    "amount": str(buy_now_total or 0),
                    "platform_fee": str(buy_now_fee or 0),
                },
            },
        }
    }


# ─── System Settings ─────────────────────────────────────────────────────


@router.get("/settings")
async def list_settings(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    items = result.scalars().all()
    return {
        "data": [
            {
                "key": s.key,
                "value": s.value,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in items
        ]
    }


@router.patch("/settings/{key}")
async def update_setting(
    key: str,
    payload: dict[str, Any] = Body(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if "value" not in payload:
        raise ApiError(
            "VALIDATION_ERROR",
            "Body must contain 'value' field",
            http_status=422,
        )
    value = payload["value"]
    if not isinstance(value, dict):
        raise ApiError(
            "VALIDATION_ERROR",
            "value must be a JSON object",
            http_status=422,
        )

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = SystemSetting(key=key, value=value)
        db.add(setting)
    await db.commit()
    await db.refresh(setting)
    return {
        "data": {
            "key": setting.key,
            "value": setting.value,
            "updated_at": setting.updated_at.isoformat()
            if setting.updated_at
            else None,
        }
    }
