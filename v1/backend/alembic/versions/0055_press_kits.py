"""Add press_kits table — C-2 press-kit-auto-export.

Cache + history for artist press kit PDFs.
30-day cache via expires_at partial index on active records.

Revision ID: 0055_press_kits
Revises: 0054_artist_interviews
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

revision: str = "0055_press_kits"
down_revision: Union[str, None] = "0054_artist_interviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "press_kits",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artist_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("page_count", sa.Integer, nullable=False),
        sa.Column(
            "interview_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("artist_interviews.id"),
            nullable=True,
        ),
        sa.Column("generation_metadata", JSONB, nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Composite index: (artist_id, locale) — cache lookup
    op.create_index(
        "ix_press_kits_artist_locale",
        "press_kits",
        ["artist_id", "locale"],
    )

    # Index for admin history list (artist + created_at DESC)
    op.create_index(
        "ix_press_kits_artist_created",
        "press_kits",
        ["artist_id", "created_at"],
    )

    # Index on (artist_id, locale, expires_at) for cache lookup.
    # NOTE: PostgreSQL requires IMMUTABLE functions in partial index predicates,
    # so `WHERE expires_at > now()` is not allowed. Use plain index instead;
    # the cache logic filters on expires_at at query time.
    op.execute(
        "CREATE INDEX ix_press_kits_active "
        "ON press_kits (artist_id, locale, expires_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_press_kits_active")
    op.drop_index("ix_press_kits_artist_created", table_name="press_kits")
    op.drop_index("ix_press_kits_artist_locale", table_name="press_kits")
    op.drop_table("press_kits")
