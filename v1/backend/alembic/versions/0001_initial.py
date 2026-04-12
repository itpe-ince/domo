"""Initial Phase 0 schema: users, artist_applications, artist_profiles, notifications

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("sns_provider", sa.String(20), nullable=True),
        sa.Column("sns_id", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("language", sa.String(10), server_default="ko"),
        sa.Column("birth_date", sa.Date, nullable=True),
        sa.Column("is_minor", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "guardian_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("warning_count", sa.Integer, server_default="0"),
        sa.Column("gdpr_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_role_status", "users", ["role", "status"])
    op.create_index(
        "idx_users_sns",
        "users",
        ["sns_provider", "sns_id"],
        unique=True,
    )

    op.create_table(
        "artist_applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("portfolio_urls", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("school", sa.String(200), nullable=True),
        sa.Column("intro_video_url", sa.Text, nullable=True),
        sa.Column("sample_images", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("statement", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_artist_apps_status", "artist_applications", ["status", "created_at"]
    )

    op.create_table(
        "artist_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("artist_applications.id"),
            nullable=True,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "verified_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("school", sa.String(200), nullable=True),
        sa.Column("intro_video_url", sa.Text, nullable=True),
        sa.Column("portfolio_urls", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("statement", sa.Text, nullable=True),
        sa.Column("badge_level", sa.String(20), server_default="emerging"),
        sa.Column("payout_country", sa.String(2), nullable=True),
        sa.Column("guardian_consent", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("link", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_notifications_user",
        "notifications",
        ["user_id", "is_read", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_user", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("artist_profiles")
    op.drop_index("idx_artist_apps_status", table_name="artist_applications")
    op.drop_table("artist_applications")
    op.drop_index("idx_users_sns", table_name="users")
    op.drop_index("idx_users_role_status", table_name="users")
    op.drop_table("users")
