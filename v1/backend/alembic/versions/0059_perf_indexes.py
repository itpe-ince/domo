"""G''-3 n-plus-one-audit: performance indexes for core queries.

Adds 3 new indexes identified by EXPLAIN ANALYZE audit (3 others pre-exist):
  1. notifications partial WHERE is_read = false  — unread count badge hot path
  2. sponsorships (artist_id, status, created_at) — tier eligibility artist side
  3. artist_interviews (status, created_at)       — C-1 admin list sort efficiency

Pre-existing indexes that already cover the G''-3 audit queries:
  - idx_search_history_user_active (0049)           — A-5 search history
  - ix_newsletter_issues_status_locale (0058)       — C-5 newsletter cron
  - ix_media_coverage_locale_published_at (0057)    — C-4 media coverage list

Revision ID: 0059_perf_indexes
Revises: 0058_newsletter
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0059_perf_indexes"
down_revision: Union[str, None] = "0058_newsletter"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. notifications: unread count fast path ────────────────────────────
    # Covers: SELECT COUNT(*) WHERE user_id = ? AND is_read = false
    # Partial index (WHERE is_read = false) minimises index size — only unread
    # rows are indexed, which is the hottest read path (badge count).
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "created_at"],
        postgresql_where=sa.text("is_read = false"),
    )

    # ── 2. sponsorships: tier eligibility cron + A-8 winback ───────────────
    # Covers: WHERE artist_id = ? AND status = 'completed' AND created_at >=
    # Used by _viewer_meets_tier sponsor check and subscription_expiry_jobs.
    op.create_index(
        "ix_sponsorships_artist_status_created",
        "sponsorships",
        ["artist_id", "status", "created_at"],
    )

    # ── 3. search_history: A-5 history list + purge ─────────────────────────
    # Already covered by idx_search_history_user_active (0049_search_history).
    # Skip to avoid duplicate.

    # ── 4. newsletter_issues: cron worker status + locale lookup ────────────
    # Covers: WHERE status = 'sending' AND locale = ?
    # Already covered by ix_newsletter_issues_status_locale (0058_newsletter);
    # skip to avoid duplicate — verified below in comment.
    # (0058 already creates: status, locale composite index)

    # ── 5. media_coverage: C-4 list page ────────────────────────────────────
    # Already covered by ix_media_coverage_locale_published_at (0057_media_coverage).
    # Skip to avoid duplicate.

    # ── 6. artist_interviews: C-1 admin list ────────────────────────────────
    # Covers: WHERE status = ? ORDER BY created_at DESC
    # Already covered by ix_artist_interviews_status (0054_artist_interviews);
    # add compound with created_at for sort efficiency.
    op.create_index(
        "ix_artist_interviews_status_created",
        "artist_interviews",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_artist_interviews_status_created", table_name="artist_interviews")
    op.drop_index("ix_sponsorships_artist_status_created", table_name="sponsorships")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
