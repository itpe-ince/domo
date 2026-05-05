"""User newsletter preference endpoints — C-5 newsletter-digest.

GET   /me/newsletter/preferences          — fetch own preferences (create default if none)
PATCH /me/newsletter/preferences          — opt-in/out + frequency + locale
GET   /newsletter/unsubscribe?token=...   — 1-click unsubscribe (no auth required)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.newsletter_preferences import NewsletterPreferences
from app.models.user import User
from app.schemas.newsletter import (
    NewsletterPreferencesOut,
    PatchNewsletterPreferencesRequest,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["newsletter"])

# ─── Helper ───────────────────────────────────────────────────────────────────


def _prefs_to_out(prefs: NewsletterPreferences) -> dict:
    return NewsletterPreferencesOut(
        user_id=prefs.user_id,
        is_subscribed=prefs.is_subscribed,
        frequency=prefs.frequency,
        preferred_locale=prefs.preferred_locale,
        last_sent_at=prefs.last_sent_at,
        created_at=prefs.created_at,
        updated_at=prefs.updated_at,
    ).model_dump(mode="json")


async def _get_or_create_prefs(
    db: AsyncSession, user: User
) -> NewsletterPreferences:
    """Return existing preferences or create a default (opt-out) row."""
    result = await db.execute(
        select(NewsletterPreferences).where(
            NewsletterPreferences.user_id == user.id
        )
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        prefs = NewsletterPreferences(user_id=user.id)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


# ─── GET /me/newsletter/preferences ──────────────────────────────────────────


@router.get("/me/newsletter/preferences")
async def get_my_newsletter_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_me_read"),
):
    """Return current user's newsletter preferences.

    Creates a default opt-out row if none exists (GDPR: opt-in required).
    """
    prefs = await _get_or_create_prefs(db, current_user)
    return {"data": _prefs_to_out(prefs)}


# ─── PATCH /me/newsletter/preferences ────────────────────────────────────────


@router.patch("/me/newsletter/preferences")
async def patch_my_newsletter_preferences(
    body: PatchNewsletterPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("newsletter_me_write"),
):
    """Update newsletter preferences: opt-in/out, frequency, locale."""
    # Ensure row exists
    await _get_or_create_prefs(db, current_user)

    updates: dict = {}
    if body.is_subscribed is not None:
        updates["is_subscribed"] = body.is_subscribed
    if body.frequency is not None:
        updates["frequency"] = body.frequency
    if body.preferred_locale is not None:
        updates["preferred_locale"] = body.preferred_locale

    if updates:
        await db.execute(
            update(NewsletterPreferences)
            .where(NewsletterPreferences.user_id == current_user.id)
            .values(**updates)
            .execution_options(synchronize_session=False)
        )
        await db.commit()

    # Re-fetch to return fresh state
    result = await db.execute(
        select(NewsletterPreferences).where(
            NewsletterPreferences.user_id == current_user.id
        )
    )
    prefs = result.scalar_one()
    return {"data": _prefs_to_out(prefs)}


# ─── GET /newsletter/unsubscribe ─────────────────────────────────────────────


@router.get("/newsletter/unsubscribe")
async def newsletter_unsubscribe(
    token: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """1-click unsubscribe via token embedded in email footer links.

    No authentication required — token acts as proof of recipient.
    Returns 200 with success message on valid token.
    Returns 404 on unknown/expired token.
    """
    result = await db.execute(
        select(NewsletterPreferences).where(
            NewsletterPreferences.unsubscribe_token == token
        )
    )
    prefs = result.scalar_one_or_none()
    if prefs is None:
        raise ApiError(
            "INVALID_TOKEN",
            "Unsubscribe token not found or already used.",
            http_status=404,
        )

    if prefs.is_subscribed:
        await db.execute(
            update(NewsletterPreferences)
            .where(NewsletterPreferences.unsubscribe_token == token)
            .values(is_subscribed=False)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        log.info("newsletter: unsubscribed user_id=%s via token", prefs.user_id)

    return {"data": {"unsubscribed": True, "user_id": str(prefs.user_id)}}
