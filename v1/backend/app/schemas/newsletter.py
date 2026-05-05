"""Pydantic schemas for C-5 newsletter-digest."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


VALID_LOCALES = frozenset({"ko", "en", "ja", "zh", "es"})
VALID_FREQUENCIES = frozenset({"weekly", "biweekly", "monthly", "never"})
VALID_ISSUE_STATUSES = frozenset({"draft", "sending", "sent", "failed"})


# ─── Admin issue schemas ───────────────────────────────────────────────────────


class AdminPatchIssueRequest(BaseModel):
    """PATCH /admin/newsletter/issues/{id}"""

    subject: str | None = Field(default=None, max_length=200)
    body_markdown: str | None = None
    status: str | None = Field(
        default=None,
        pattern="^(draft|sending|sent|failed)$",
    )


class NewsletterIssueOut(BaseModel):
    """Serialised NewsletterIssue row."""

    id: UUID
    issue_date: date
    subject: str
    body_markdown: str
    body_html: str
    locale: str
    featured_artist_id: UUID | None
    new_top_artists: list
    new_posts_highlight: list
    media_coverage_ids: list
    status: str
    sent_count: int
    failed_count: int
    sent_at: datetime | None
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime


# ─── User preference schemas ──────────────────────────────────────────────────


class NewsletterPreferencesOut(BaseModel):
    """Serialised NewsletterPreferences row."""

    user_id: UUID
    is_subscribed: bool
    frequency: str
    preferred_locale: str
    last_sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PatchNewsletterPreferencesRequest(BaseModel):
    """PATCH /me/newsletter/preferences"""

    is_subscribed: bool | None = None
    frequency: str | None = Field(
        default=None,
        pattern="^(weekly|biweekly|monthly|never)$",
    )
    preferred_locale: str | None = Field(
        default=None,
        pattern="^(ko|en|ja|zh|es)$",
    )
