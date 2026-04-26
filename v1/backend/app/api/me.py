"""/me endpoints — GDPR data export, soft delete, consent (Phase 4 M3).

Reference: phase4.design.md §6
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db

log = logging.getLogger(__name__)
from app.models.auction import Auction, Bid, Order
from app.models.auth_token import RefreshToken
from app.models.moderation import Report, Warning
from app.models.notification import Notification
from app.models.post import Comment, Follow, Like, Post
from app.models.sponsorship import Sponsorship, Subscription
from app.models.user import ArtistApplication, ArtistProfile, User
from app.services.auth_tokens import revoke_user_tokens
from app.services.email import get_email_provider
from app.services.email.templates import account_deleted as account_deleted_tpl
from app.services.guardian import (
    is_minor as calc_is_minor,
    request_guardian_consent,
)

router = APIRouter(prefix="/me", tags=["me"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Export ─────────────────────────────────────────────────────────────


def _user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "display_name": u.display_name,
        "role": u.role,
        "status": u.status,
        "avatar_url": u.avatar_url,
        "bio": u.bio,
        "country_code": u.country_code,
        "language": u.language,
        "is_minor": u.is_minor,
        "warning_count": u.warning_count,
        "gdpr_consent_at": u.gdpr_consent_at.isoformat() if u.gdpr_consent_at else None,
        "privacy_policy_version": u.privacy_policy_version,
        "terms_version": u.terms_version,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("/export")
async def export_my_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("gdpr_export"),
):
    """GDPR Right to Data Portability — returns full user data as JSON.

    Rate limit: 1 per 24h (enforced via Redis rate_limit decorator, scope gdpr_export).
    gdpr_export_count is incremented for audit/total tracking only.
    """
    # Artist application + profile
    app_result = await db.execute(
        select(ArtistApplication).where(ArtistApplication.user_id == user.id)
    )
    applications = [
        {
            "id": str(a.id),
            "status": a.status,
            "school": a.school,
            "statement": a.statement,
            "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
            "review_note": a.review_note,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in app_result.scalars()
    ]

    profile_result = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    profile_dict = (
        {
            "school": profile.school,
            "statement": profile.statement,
            "badge_level": profile.badge_level,
            "verified_at": profile.verified_at.isoformat()
            if profile.verified_at
            else None,
        }
        if profile
        else None
    )

    # Posts by this user
    posts_result = await db.execute(
        select(Post).where(Post.author_id == user.id)
    )
    posts = [
        {
            "id": str(p.id),
            "type": p.type,
            "title": p.title,
            "content": p.content,
            "genre": p.genre,
            "tags": p.tags,
            "status": p.status,
            "like_count": p.like_count,
            "bluebird_count": p.bluebird_count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in posts_result.scalars()
    ]

    # Comments
    comments_result = await db.execute(
        select(Comment).where(Comment.author_id == user.id)
    )
    comments = [
        {
            "id": str(c.id),
            "post_id": str(c.post_id),
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments_result.scalars()
    ]

    # Follows
    following_result = await db.execute(
        select(Follow.followee_id).where(Follow.follower_id == user.id)
    )
    following = [str(row[0]) for row in following_result.all()]
    followers_result = await db.execute(
        select(Follow.follower_id).where(Follow.followee_id == user.id)
    )
    followers = [str(row[0]) for row in followers_result.all()]

    # Likes
    likes_result = await db.execute(
        select(Like.post_id).where(Like.user_id == user.id)
    )
    liked_posts = [str(row[0]) for row in likes_result.all()]

    # Sponsorships made
    spo_result = await db.execute(
        select(Sponsorship).where(Sponsorship.sponsor_id == user.id)
    )
    sponsorships_made = [
        {
            "id": str(s.id),
            "artist_id": str(s.artist_id),
            "bluebird_count": s.bluebird_count,
            "amount": str(s.amount),
            "currency": s.currency,
            "is_anonymous": s.is_anonymous,
            "visibility": s.visibility,
            "message": s.message,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in spo_result.scalars()
    ]

    # Sponsorships received (if artist)
    spo_recv_result = await db.execute(
        select(Sponsorship).where(Sponsorship.artist_id == user.id)
    )
    sponsorships_received = [
        {
            "id": str(s.id),
            "bluebird_count": s.bluebird_count,
            "amount": str(s.amount),
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in spo_recv_result.scalars()
    ]

    # Subscriptions
    sub_result = await db.execute(
        select(Subscription).where(Subscription.sponsor_id == user.id)
    )
    subscriptions = [
        {
            "id": str(s.id),
            "artist_id": str(s.artist_id),
            "monthly_bluebird": s.monthly_bluebird,
            "monthly_amount": str(s.monthly_amount),
            "status": s.status,
            "cancel_at_period_end": s.cancel_at_period_end,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sub_result.scalars()
    ]

    # Orders
    orders_result = await db.execute(
        select(Order).where(Order.buyer_id == user.id)
    )
    orders = [
        {
            "id": str(o.id),
            "product_post_id": str(o.product_post_id),
            "source": o.source,
            "amount": str(o.amount),
            "status": o.status,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders_result.scalars()
    ]

    # Auctions (as seller)
    auctions_result = await db.execute(
        select(Auction).where(Auction.seller_id == user.id)
    )
    auctions = [
        {
            "id": str(a.id),
            "product_post_id": str(a.product_post_id),
            "start_price": str(a.start_price),
            "current_price": str(a.current_price),
            "status": a.status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in auctions_result.scalars()
    ]

    # Bids placed
    bids_result = await db.execute(
        select(Bid).where(Bid.bidder_id == user.id)
    )
    bids = [
        {
            "id": str(b.id),
            "auction_id": str(b.auction_id),
            "amount": str(b.amount),
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bids_result.scalars()
    ]

    # Warnings
    warnings_result = await db.execute(
        select(Warning).where(Warning.user_id == user.id)
    )
    warnings = [
        {
            "id": str(w.id),
            "reason": w.reason,
            "is_active": w.is_active,
            "appealed": w.appealed,
            "cancelled_at": w.cancelled_at.isoformat() if w.cancelled_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in warnings_result.scalars()
    ]

    # Reports made
    reports_result = await db.execute(
        select(Report).where(Report.reporter_id == user.id)
    )
    reports_made = [
        {
            "id": str(r.id),
            "target_type": r.target_type,
            "target_id": str(r.target_id),
            "reason": r.reason,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports_result.scalars()
    ]

    # Notifications
    notif_result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(200)
    )
    notifications = [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notif_result.scalars()
    ]

    data = {
        "export_version": "v1",
        "exported_at": _now().isoformat(),
        "user": _user_dict(user),
        "artist_applications": applications,
        "artist_profile": profile_dict,
        "posts": posts,
        "comments": comments,
        "follows": {"following": following, "followers": followers},
        "liked_posts": liked_posts,
        "sponsorships_made": sponsorships_made,
        "sponsorships_received": sponsorships_received,
        "subscriptions": subscriptions,
        "orders": orders,
        "auctions_as_seller": auctions,
        "bids_placed": bids,
        "warnings": warnings,
        "reports_made": reports_made,
        "notifications": notifications,
    }

    user.gdpr_export_count += 1
    await db.commit()

    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="domo_export_{user.id}.json"',
        },
    )


# ─── Soft Delete ────────────────────────────────────────────────────────


class DeleteRequest(BaseModel):
    confirm: str  # must equal "DELETE MY ACCOUNT"


@router.post("/delete")
async def request_deletion(
    body: DeleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Schedule account deletion with 30-day grace period."""
    if body.confirm != "DELETE MY ACCOUNT":
        raise ApiError(
            "VALIDATION_ERROR",
            'Confirm phrase must be exactly "DELETE MY ACCOUNT"',
            http_status=422,
        )
    if user.deleted_at is not None:
        raise ApiError(
            "CONFLICT", "Deletion already requested", http_status=409
        )
    if user.role == "admin":
        raise ApiError(
            "FORBIDDEN",
            "Admin accounts cannot be self-deleted. Contact another admin.",
            http_status=403,
        )

    now = _now()
    user.deleted_at = now
    user.deletion_scheduled_for = now + timedelta(days=30)

    # Revoke all sessions
    await revoke_user_tokens(db, user.id, reason="account_deletion")

    # Notify the user
    db.add(
        Notification(
            user_id=user.id,
            type="account_deletion_scheduled",
            title="계정 삭제 요청 접수",
            body=f"계정이 30일 후 ({user.deletion_scheduled_for.date()}) 영구 삭제됩니다. 그 전까지는 복구 가능합니다.",
            link="/me/account",
        )
    )

    await db.commit()

    # Send account deletion confirmation email
    try:
        msg = account_deleted_tpl.render(
            user_email=user.email,
            user_name=user.display_name,
            deletion_scheduled_for=user.deletion_scheduled_for.date().isoformat(),
        )
        await get_email_provider().send(msg)
    except Exception as exc:  # noqa: BLE001
        log.warning("account_deleted email failed: %s", exc)

    return {
        "data": {
            "deleted_at": now.isoformat(),
            "deletion_scheduled_for": user.deletion_scheduled_for.isoformat(),
            "grace_period_days": 30,
        }
    }


@router.post("/delete/cancel")
async def cancel_deletion(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel pending deletion during the 30-day grace period."""
    if user.deleted_at is None:
        raise ApiError("CONFLICT", "No pending deletion", http_status=409)
    if user.deletion_scheduled_for and user.deletion_scheduled_for < _now():
        raise ApiError(
            "CONFLICT",
            "Grace period has expired — account already purged",
            http_status=409,
        )

    user.deleted_at = None
    user.deletion_scheduled_for = None

    db.add(
        Notification(
            user_id=user.id,
            type="account_deletion_cancelled",
            title="계정 삭제 취소",
            body="계정 삭제 요청이 취소되었습니다.",
        )
    )
    await db.commit()
    return {"data": {"ok": True}}


# ─── Consent versions ────────────────────────────────────────────────────


class AcceptPoliciesRequest(BaseModel):
    privacy_policy_version: str
    terms_version: str


@router.post("/accept-policies")
async def accept_policies(
    body: AcceptPoliciesRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the user has accepted the current privacy policy + terms."""
    user.privacy_policy_version = body.privacy_policy_version
    user.terms_version = body.terms_version
    user.gdpr_consent_at = _now()
    await db.commit()
    return {
        "data": {
            "privacy_policy_version": user.privacy_policy_version,
            "terms_version": user.terms_version,
            "accepted_at": user.gdpr_consent_at.isoformat(),
        }
    }


# ─── Onboarding + Guardian (Phase 4 M5) ─────────────────────────────────


class OnboardingRequest(BaseModel):
    birth_year: int
    country_code: str


@router.post("/onboarding")
async def complete_onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_year = _now().year
    if body.birth_year < 1900 or body.birth_year > current_year:
        raise ApiError(
            "VALIDATION_ERROR", "Invalid birth year", http_status=422
        )
    if len(body.country_code) != 2:
        raise ApiError(
            "VALIDATION_ERROR",
            "country_code must be a 2-letter ISO code",
            http_status=422,
        )

    user.birth_year = body.birth_year
    user.country_code = body.country_code.upper()
    user.onboarded_at = _now()

    minor = await calc_is_minor(db, user.birth_year, user.country_code)
    user.is_minor = minor

    status_result: dict = {
        "is_minor": minor,
        "guardian_required": minor,
        "onboarded": True,
    }

    if minor and user.status != "pending_guardian":
        # Suspend until guardian approves
        user.status = "pending_guardian"

    await db.commit()
    return {"data": status_result}


class GuardianRequestInput(BaseModel):
    guardian_email: str
    guardian_name: str | None = None


@router.post("/guardian/request")
async def request_guardian(
    body: GuardianRequestInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.is_minor:
        raise ApiError(
            "VALIDATION_ERROR",
            "Guardian consent is only required for minors",
            http_status=422,
        )
    if "@" not in body.guardian_email:
        raise ApiError(
            "VALIDATION_ERROR", "Invalid guardian email", http_status=422
        )

    consent = await request_guardian_consent(
        db, user, body.guardian_email, body.guardian_name
    )
    await db.commit()
    return {
        "data": {
            "id": str(consent.id),
            "guardian_email": consent.guardian_email,
            "expires_at": consent.expires_at.isoformat(),
            "status": "pending",
        }
    }
