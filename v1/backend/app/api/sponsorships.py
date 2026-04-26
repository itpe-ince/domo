from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.notification import Notification
from app.models.post import Post
from app.models.sponsorship import Sponsorship, Subscription
from app.models.user import User
from app.schemas.sponsorship import (
    SponsorshipCreate,
    SponsorshipOut,
    SubscriptionCreate,
    SubscriptionOut,
)
from app.services.kyc import require_kyc_verified
from app.services.payments import get_payment_provider
from app.services.settings import get_setting

sponsorship_router = APIRouter(prefix="/sponsorships", tags=["sponsorships"])
subscription_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _serialize_sponsorship(s: Sponsorship, viewer_id: UUID | None = None) -> dict:
    """Apply visibility rules + anonymity."""
    is_owner = viewer_id == s.sponsor_id
    sponsor_id = None
    if not s.is_anonymous or is_owner:
        sponsor_id = s.sponsor_id
    return {
        "id": str(s.id),
        "sponsor_id": str(sponsor_id) if sponsor_id else None,
        "artist_id": str(s.artist_id),
        "post_id": str(s.post_id) if s.post_id else None,
        "bluebird_count": s.bluebird_count,
        "amount": str(s.amount),
        "currency": s.currency,
        "is_anonymous": s.is_anonymous,
        "visibility": s.visibility,
        "message": s.message,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ─── One-time sponsorship ────────────────────────────────────────────────


@sponsorship_router.post("")
async def create_sponsorship(
    body: SponsorshipCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("sponsorship_create"),
):
    if body.artist_id == user.id:
        raise ApiError(
            "VALIDATION_ERROR", "Cannot sponsor yourself", http_status=422
        )

    # KYC gate — configurable via system_settings.kyc_enforcement
    await require_kyc_verified(user, db)

    artist_result = await db.execute(select(User).where(User.id == body.artist_id))
    artist = artist_result.scalar_one_or_none()
    if not artist or artist.role != "artist":
        raise ApiError(
            "NOT_FOUND", "Artist not found or not approved", http_status=404
        )

    if body.post_id:
        post_check = await db.execute(select(Post).where(Post.id == body.post_id))
        if not post_check.scalar_one_or_none():
            raise ApiError("NOT_FOUND", "Post not found", http_status=404)

    unit = await get_setting(db, "bluebird_unit_price")
    unit_amount = Decimal(str(unit["amount"]))
    currency = unit["currency"]
    total = unit_amount * body.bluebird_count

    provider = get_payment_provider()
    intent = await provider.create_payment_intent(
        amount=total,
        currency=currency,
        metadata={
            "purpose": "sponsorship",
            "sponsor_id": str(user.id),
            "artist_id": str(body.artist_id),
            "bluebird_count": body.bluebird_count,
        },
    )

    sponsorship = Sponsorship(
        sponsor_id=user.id,
        artist_id=body.artist_id,
        post_id=body.post_id,
        bluebird_count=body.bluebird_count,
        amount=total,
        currency=currency,
        is_anonymous=body.is_anonymous,
        visibility=body.visibility,
        message=body.message,
        payment_intent_id=intent.id,
        status="pending",
    )
    db.add(sponsorship)
    await db.commit()
    await db.refresh(sponsorship)

    return {
        "data": {
            "sponsorship": _serialize_sponsorship(sponsorship, viewer_id=user.id),
            "payment_intent": {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": str(intent.amount),
                "currency": intent.currency,
                "status": intent.status,
            },
        }
    }


@sponsorship_router.post("/{sponsorship_id}/confirm")
async def confirm_sponsorship(
    sponsorship_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mock-only endpoint to simulate user finishing payment in client.

    Real Stripe flow would skip this and rely on webhook.
    """
    result = await db.execute(
        select(Sponsorship).where(Sponsorship.id == sponsorship_id)
    )
    sponsorship = result.scalar_one_or_none()
    if not sponsorship:
        raise ApiError("NOT_FOUND", "Sponsorship not found", http_status=404)
    if sponsorship.sponsor_id != user.id:
        raise ApiError("FORBIDDEN", "Not your sponsorship", http_status=403)
    if sponsorship.status == "completed":
        return {
            "data": _serialize_sponsorship(sponsorship, viewer_id=user.id)
        }

    provider = get_payment_provider()
    if sponsorship.payment_intent_id:
        await provider.confirm_payment_intent(sponsorship.payment_intent_id)

    sponsorship.status = "completed"

    # Update artist post counters & notify
    if sponsorship.post_id:
        post_result = await db.execute(
            select(Post).where(Post.id == sponsorship.post_id)
        )
        post = post_result.scalar_one_or_none()
        if post:
            post.bluebird_count = (post.bluebird_count or 0) + sponsorship.bluebird_count

    sponsor_label = (
        "익명 후원자"
        if sponsorship.is_anonymous
        else f"@{user.display_name}"
    )
    db.add(
        Notification(
            user_id=sponsorship.artist_id,
            type="sponsorship_received",
            title=f"🕊 블루버드 후원 {sponsorship.bluebird_count}개",
            body=f"{sponsor_label}님이 후원했습니다."
            + (f" — {sponsorship.message}" if sponsorship.message else ""),
            link=f"/posts/{sponsorship.post_id}" if sponsorship.post_id else None,
        )
    )
    await db.commit()
    await db.refresh(sponsorship)
    return {"data": _serialize_sponsorship(sponsorship, viewer_id=user.id)}


@sponsorship_router.get("/mine")
async def my_sponsorships(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Sponsorship)
        .where(Sponsorship.sponsor_id == user.id)
        .order_by(Sponsorship.created_at.desc())
    )
    items = result.scalars().all()
    return {"data": [_serialize_sponsorship(s, viewer_id=user.id) for s in items]}


# ─── Recurring subscription ──────────────────────────────────────────────


@subscription_router.post("")
async def create_subscription(
    body: SubscriptionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("subscription_create"),
):
    if body.artist_id == user.id:
        raise ApiError(
            "VALIDATION_ERROR", "Cannot subscribe to yourself", http_status=422
        )

    await require_kyc_verified(user, db)

    artist_result = await db.execute(select(User).where(User.id == body.artist_id))
    artist = artist_result.scalar_one_or_none()
    if not artist or artist.role != "artist":
        raise ApiError("NOT_FOUND", "Artist not found", http_status=404)

    # Block duplicate active subscription to same artist
    existing = await db.execute(
        select(Subscription).where(
            Subscription.sponsor_id == user.id,
            Subscription.artist_id == body.artist_id,
            Subscription.status == "active",
            Subscription.cancel_at_period_end.is_(False),
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "CONFLICT",
            "Already subscribed to this artist",
            http_status=409,
        )

    unit = await get_setting(db, "bluebird_unit_price")
    monthly_amount = Decimal(str(unit["amount"])) * body.monthly_bluebird

    provider = get_payment_provider()
    # Pass db so StripeProvider can cache Customer/Price (M10)
    create_sub_kwargs: dict = dict(
        sponsor_id=str(user.id),
        artist_id=str(body.artist_id),
        monthly_amount=monthly_amount,
        currency=unit["currency"],
    )
    import inspect as _inspect
    if "db" in _inspect.signature(provider.create_subscription).parameters:
        create_sub_kwargs["db"] = db
    result = await provider.create_subscription(**create_sub_kwargs)
    period_end = (
        datetime.fromtimestamp(result.current_period_end_unix, tz=timezone.utc)
        if result.current_period_end_unix
        else None
    )

    sub = Subscription(
        sponsor_id=user.id,
        artist_id=body.artist_id,
        monthly_bluebird=body.monthly_bluebird,
        monthly_amount=monthly_amount,
        currency=unit["currency"],
        provider_subscription_id=result.id,
        status="active",
        cancel_at_period_end=False,
        current_period_end=period_end,
    )
    db.add(sub)

    db.add(
        Notification(
            user_id=body.artist_id,
            type="subscription_started",
            title="🕊 정기 후원 시작",
            body=f"@{user.display_name}님이 매월 {body.monthly_bluebird} 블루버드 정기 후원을 시작했습니다.",
        )
    )
    await db.commit()
    await db.refresh(sub)
    return {"data": SubscriptionOut.model_validate(sub).model_dump(mode="json")}


@subscription_router.delete("/{subscription_id}")
async def cancel_subscription(
    subscription_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise ApiError("NOT_FOUND", "Subscription not found", http_status=404)
    if sub.sponsor_id != user.id:
        raise ApiError("FORBIDDEN", "Not your subscription", http_status=403)
    if sub.status != "active":
        raise ApiError("CONFLICT", "Already cancelled", http_status=409)

    provider = get_payment_provider()
    if sub.provider_subscription_id:
        await provider.cancel_subscription(
            sub.provider_subscription_id, at_period_end=True
        )
    # Per design.md §6.6: cancel_at_period_end=True, status stays 'active'
    sub.cancel_at_period_end = True
    sub.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sub)
    return {"data": SubscriptionOut.model_validate(sub).model_dump(mode="json")}


@subscription_router.get("/mine")
async def my_subscriptions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.sponsor_id == user.id)
        .order_by(Subscription.created_at.desc())
    )
    subs = result.scalars().all()
    return {
        "data": [
            SubscriptionOut.model_validate(s).model_dump(mode="json") for s in subs
        ]
    }
