import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.coupon import AppliedCoupon
from app.models.notification import Notification
from app.models.post import Post
from app.models.sponsorship import Sponsorship, Subscription
from app.models.user import User
from app.schemas.coupon import AppliedCouponOut, WinbackCouponRequest, WinbackCouponResponse
from app.schemas.sponsorship import (
    AutoRenewToggleRequest,
    SponsorshipCreate,
    SponsorshipOut,
    SubscriptionCancelRequest,
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionRenewResponse,
)
from app.services.kyc import require_kyc_verified
from app.services.payments import get_coupon_provider, get_payment_provider
from app.services.payments.coupon import create_winback_coupon, winback_dm_link
from app.services.settings import get_setting
from app.services.analytics import capture_event

log = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags to prevent stored XSS."""
    return _HTML_TAG_RE.sub("", text).strip()


def _log_action(action: str, **kwargs: object) -> None:
    """Structured audit log line."""
    parts = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
    log.info("AUDIT action=%s %s", action, parts)

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

    # G'-4: server-side sponsorship completion event
    capture_event(
        str(user.id),
        "sponsor_completed_server",
        {
            "amount_cents": int(sponsorship.amount * 100),
            "bluebird_count": sponsorship.bluebird_count,
            "artist_id": str(sponsorship.artist_id),
            "post_id": str(sponsorship.post_id) if sponsorship.post_id else None,
        },
    )

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
    body: SubscriptionCancelRequest | None = None,
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

    # Extract optional cancel metadata
    reason = body.reason if body else None
    raw_feedback = body.feedback if body else None
    immediate = body.immediate if body else False

    # XSS defence: strip HTML from free-text feedback
    clean_feedback: str | None = None
    if raw_feedback:
        clean_feedback = _strip_html(raw_feedback)
        if not clean_feedback:
            clean_feedback = None

    provider = get_payment_provider()
    if sub.provider_subscription_id:
        await provider.cancel_subscription(
            sub.provider_subscription_id, at_period_end=not immediate
        )

    # Per design.md §6.6: cancel_at_period_end=True, status stays 'active'
    sub.cancel_at_period_end = not immediate
    sub.cancelled_at = datetime.now(timezone.utc)
    sub.cancellation_reason = reason
    sub.cancellation_feedback = clean_feedback

    # Audit log (feedback truncated to 50 chars for log safety)
    _log_action(
        "SUBSCRIPTION_CANCELLED",
        subscription_id=str(subscription_id),
        sponsor_id=str(user.id),
        artist_id=str(sub.artist_id),
        reason=reason,
        immediate=immediate,
        feedback_preview=(clean_feedback[:50] if clean_feedback else None),
    )

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


@subscription_router.post("/{subscription_id}/renew")
async def renew_subscription(
    subscription_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("subscription_renew"),
):
    """POST /v1/subscriptions/{id}/renew — B'-4 stripe-billing-auto-renewal.

    Manually triggers renewal of a subscription:
    - If active with cancel_at_period_end=True → reverts cancel flag (keeps subscription alive)
    - If 'cancelled' status → creates a new Stripe subscription (re-start)
    - If 'past_due' → triggers retry via Stripe billing (status becomes active on webhook)
    - If already active & auto-renewing → 200 (idempotent)

    Auth: subscription owner only.
    Rate limit: subscription_renew (5/min).
    """
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise ApiError("NOT_FOUND", "Subscription not found", http_status=404)
    if sub.sponsor_id != user.id:
        raise ApiError("FORBIDDEN", "Not your subscription", http_status=403)

    provider = get_payment_provider()
    now = datetime.now(timezone.utc)

    if sub.status == "active" and sub.cancel_at_period_end:
        # Revert pending cancellation → subscription renews automatically
        if sub.provider_subscription_id:
            if hasattr(provider, "revert_cancel_at_period_end"):
                try:
                    await provider.revert_cancel_at_period_end(
                        sub.provider_subscription_id
                    )
                except Exception as exc:
                    log.warning("revert_cancel_at_period_end failed (non-fatal): %s", exc)
            else:
                # Generic: cancel_subscription with at_period_end=True is the cancel path;
                # to revert we modify cancel_at_period_end=False
                try:
                    import asyncio as _asyncio
                    if hasattr(provider, "_stripe"):
                        await _asyncio.to_thread(
                            provider._stripe.Subscription.modify,
                            sub.provider_subscription_id,
                            cancel_at_period_end=False,
                        )
                except Exception as exc:
                    log.warning("Stripe revert cancel_at_period_end failed: %s", exc)

        sub.cancel_at_period_end = False
        sub.cancelled_at = None
        sub.cancellation_reason = None
        # Reset expiry notification so cron can fire again next cycle if needed
        sub.expiry_notified_at = None
        message = "구독 취소가 철회되었습니다. 자동 갱신이 계속됩니다."

    elif sub.status == "cancelled":
        # Re-start: create new Stripe subscription
        unit = await get_setting(db, "bluebird_unit_price")
        monthly_amount = sub.monthly_amount
        currency = sub.currency

        import inspect as _inspect
        create_sub_kwargs: dict = dict(
            sponsor_id=str(user.id),
            artist_id=str(sub.artist_id),
            monthly_amount=monthly_amount,
            currency=currency,
        )
        if "db" in _inspect.signature(provider.create_subscription).parameters:
            create_sub_kwargs["db"] = db

        try:
            new_result = await provider.create_subscription(**create_sub_kwargs)
        except Exception as exc:
            log.error("re-start subscription failed: %s", exc)
            raise ApiError(
                "PAYMENT_ERROR",
                "구독 재시작에 실패했습니다. 결제 수단을 확인해주세요.",
                http_status=502,
            ) from exc

        period_end = (
            datetime.fromtimestamp(new_result.current_period_end_unix, tz=timezone.utc)
            if new_result.current_period_end_unix
            else None
        )
        sub.provider_subscription_id = new_result.id
        sub.status = "active"
        sub.cancel_at_period_end = False
        sub.cancelled_at = None
        sub.cancellation_reason = None
        sub.cancellation_feedback = None
        sub.current_period_end = period_end
        sub.expiry_notified_at = None

        # Notify artist
        db.add(
            Notification(
                user_id=sub.artist_id,
                type="subscription_renewed",
                title="구독이 재시작되었습니다",
                body=f"@{user.display_name}님이 정기 후원을 다시 시작했습니다.",
            )
        )
        message = "구독이 재시작되었습니다."

    elif sub.status == "past_due":
        # Stripe handles billing retry automatically; we just log and return current state.
        # In production Stripe will retry and fire invoice.payment_succeeded/failed webhook.
        _log_action(
            "SUBSCRIPTION_RENEW_PAST_DUE",
            subscription_id=str(subscription_id),
            sponsor_id=str(user.id),
            provider_subscription_id=sub.provider_subscription_id,
        )
        message = "결제 재시도가 예정되어 있습니다. Stripe가 자동으로 처리합니다."

    else:
        # Already active and auto-renewing — idempotent
        message = "구독이 이미 활성 상태입니다."

    _log_action(
        "SUBSCRIPTION_RENEWED",
        subscription_id=str(subscription_id),
        sponsor_id=str(user.id),
        previous_status=sub.status if sub.status != "active" else "active",
    )

    await db.commit()
    await db.refresh(sub)

    capture_event(
        str(user.id),
        "subscription_renewed_manual",
        {
            "subscription_id": str(subscription_id),
            "artist_id": str(sub.artist_id),
            "status": sub.status,
        },
    )

    return {
        "data": {
            **SubscriptionOut.model_validate(sub).model_dump(mode="json"),
            "renewed_at": now.isoformat(),
            "message": message,
        }
    }


@subscription_router.patch("/{subscription_id}/auto-renew")
async def toggle_auto_renew(
    subscription_id: UUID,
    body: AutoRenewToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """PATCH /v1/subscriptions/{id}/auto-renew — B'-4 auto_renew toggle.

    Enables or disables automatic renewal for the subscription.
    When auto_renew_enabled=False the user must manually renew via POST /renew.
    Stripe continues billing on its schedule; this flag controls backend monitoring
    and UI guidance only (does NOT cancel Stripe subscription).
    """
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise ApiError("NOT_FOUND", "Subscription not found", http_status=404)
    if sub.sponsor_id != user.id:
        raise ApiError("FORBIDDEN", "Not your subscription", http_status=403)
    if sub.status not in ("active", "past_due"):
        raise ApiError(
            "CONFLICT",
            "자동 갱신 설정은 활성 구독에서만 변경 가능합니다.",
            http_status=409,
        )

    sub.auto_renew_enabled = body.auto_renew_enabled

    _log_action(
        "AUTO_RENEW_TOGGLED",
        subscription_id=str(subscription_id),
        sponsor_id=str(user.id),
        auto_renew_enabled=body.auto_renew_enabled,
    )

    await db.commit()
    await db.refresh(sub)

    capture_event(
        str(user.id),
        "auto_renew_toggled",
        {
            "subscription_id": str(subscription_id),
            "auto_renew_enabled": body.auto_renew_enabled,
        },
    )

    return {"data": SubscriptionOut.model_validate(sub).model_dump(mode="json")}


@subscription_router.post("/{subscription_id}/winback-coupon")
async def apply_winback_coupon(
    subscription_id: UUID,
    body: WinbackCouponRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("winback_coupon"),
):
    """POST /v1/subscriptions/{id}/winback-coupon — G'-2.

    Applies a reason-based winback coupon to the subscription:
      too_expensive    → percent_off=50, duration=repeating, 1 month
      changed_mind     → percent_off=30, duration=repeating, 1 month
      not_satisfied    → percent_off=20, duration=repeating, 1 month + DM link placeholder
      other            → percent_off=10, duration=once

    Also reverts cancel_at_period_end=True → False (retains subscriber).
    Rate limit: 1/day/subscription (idempotency guard via DB check).
    """
    # ── 1. Fetch + owner check ────────────────────────────────────────────────
    result = await db.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise ApiError("NOT_FOUND", "Subscription not found", http_status=404)
    if sub.sponsor_id != user.id:
        raise ApiError("FORBIDDEN", "Not your subscription", http_status=403)

    # ── 2. Idempotency guard: 1 winback coupon per subscription per 24h ───────
    window_start = datetime.now(timezone.utc) - timedelta(hours=24)
    existing = await db.execute(
        select(AppliedCoupon).where(
            AppliedCoupon.subscription_id == sub.id,
            AppliedCoupon.applied_at > window_start,
        )
    )
    if existing.scalar_one_or_none():
        raise ApiError(
            "WINBACK_ALREADY_USED",
            "A winback coupon has already been applied to this subscription today.",
            http_status=409,
        )

    # ── 3. Sanitize optional feedback ────────────────────────────────────────
    clean_feedback: str | None = None
    if body.feedback:
        clean_feedback = _strip_html(body.feedback)
        if not clean_feedback:
            clean_feedback = None

    # ── 4. Create coupon via provider ─────────────────────────────────────────
    coupon_provider = get_coupon_provider()
    idempotency_key = f"winback_{sub.id}_{body.reason}_{secrets.token_hex(4)}"
    try:
        coupon = await create_winback_coupon(
            provider=coupon_provider,
            reason=body.reason,
            subscription_id=str(sub.id),
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        log.error("create_winback_coupon failed: %s", exc)
        raise ApiError(
            "COUPON_CREATE_FAILED",
            "Failed to create winback coupon.",
            http_status=502,
        ) from exc

    # ── 5. Attach coupon to Stripe subscription + revert cancel ───────────────
    if sub.provider_subscription_id:
        attach_key = f"winback_attach_{sub.id}_{coupon.id}"
        try:
            await coupon_provider.attach_coupon_to_subscription(
                subscription_id=sub.provider_subscription_id,
                coupon_id=coupon.id,
                idempotency_key=attach_key,
            )
        except Exception as exc:
            log.error("attach_coupon_to_subscription failed: %s", exc)
            raise ApiError(
                "COUPON_ATTACH_FAILED",
                "Failed to attach winback coupon to subscription.",
                http_status=502,
            ) from exc

        # Revert cancel_at_period_end via payment provider (Stripe.Subscription.modify)
        try:
            payment_provider = get_payment_provider()
            if hasattr(payment_provider, "revert_cancel_at_period_end"):
                await payment_provider.revert_cancel_at_period_end(
                    sub.provider_subscription_id
                )
        except Exception as exc:
            # Non-fatal: coupon was already attached; log warning
            log.warning("revert_cancel_at_period_end failed (non-fatal): %s", exc)

    # ── 6. Update subscription: cancel_at_period_end=False ────────────────────
    sub.cancel_at_period_end = False

    # Store feedback in cancellation_feedback if provided
    if clean_feedback:
        sub.cancellation_feedback = clean_feedback

    # ── 7. Persist AppliedCoupon row ──────────────────────────────────────────
    applied = AppliedCoupon(
        user_id=user.id,
        subscription_id=sub.id,
        stripe_coupon_id=coupon.id,
        coupon_code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        duration=coupon.duration,
        duration_in_months=coupon.duration_in_months,
        valid_until=coupon.valid_until,
    )
    db.add(applied)
    await db.commit()
    await db.refresh(applied)

    # ── 8. Audit log ─────────────────────────────────────────────────────────
    _log_action(
        "WINBACK_COUPON_APPLIED",
        reason=body.reason,
        subscription_id=str(subscription_id),
        coupon_id=coupon.id,
        sponsor_id=str(user.id),
        cancel_reverted=True,
    )

    # ── 9. G'-4 server-side event ─────────────────────────────────────────────
    capture_event(
        str(user.id),
        "winback_coupon_accepted_server",
        {
            "reason": body.reason,
            "coupon_id": coupon.id,
            "subscription_id": str(subscription_id),
            "discount_value": coupon.discount_value,
        },
    )

    dm_link = winback_dm_link(body.reason)

    return {
        "data": WinbackCouponResponse(
            coupon_applied=True,
            cancel_reverted=True,
            dm_link=dm_link,
            applied_coupon=AppliedCouponOut.model_validate(applied),
        ).model_dump(mode="json")
    }
