"""Add early_access columns to posts + sponsorships composite index — artist-tier-release PDCA #10 PR1.

Adds:
- posts.early_access_until TIMESTAMP WITH TIME ZONE NULL
- posts.early_access_tier VARCHAR(20) NULL
- CHECK ck_posts_early_access_tier_enum (subscriber|sponsor|follower)
- CHECK ck_posts_early_access_pair (NULL pair consistency)
- Partial index ix_posts_early_access_until WHERE NOT NULL
- Composite index ix_sponsorships_sponsor_artist_status (OQ-D-5=A, R-5 mitigation)

Option β: Post.visibility enum NOT extended; tier_only is computed effective state.

Revision ID: 0041_post_tier_release
Revises: 0040_series_tables
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0041_post_tier_release"
down_revision: Union[str, None] = "0040_series_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add early_access columns (additive, nullable — backward compatible)
    op.add_column("posts", sa.Column("early_access_until",
        sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("early_access_tier",
        sa.String(20), nullable=True))

    # 2. tier enum CHECK
    op.create_check_constraint("ck_posts_early_access_tier_enum", "posts",
        "early_access_tier IS NULL OR "
        "early_access_tier IN ('subscriber', 'sponsor', 'follower')")

    # 3. NULL pair consistency CHECK — both columns must be NULL together or both set
    op.create_check_constraint("ck_posts_early_access_pair", "posts",
        "(early_access_until IS NULL) = (early_access_tier IS NULL)")

    # 4. Partial index — cron worker sweep + tier qualification lookup
    # NOTE: PostgreSQL NOW() is not IMMUTABLE so cannot appear in WHERE clause;
    # "IS NOT NULL" partial index covers active rows efficiently.
    op.create_index("ix_posts_early_access_until", "posts",
        ["early_access_until"],
        postgresql_where=sa.text("early_access_until IS NOT NULL"))

    # 5. OQ-D-5=A: sponsorships composite index for _viewer_meets_tier EXISTS queries
    op.create_index("ix_sponsorships_sponsor_artist_status", "sponsorships",
        ["sponsor_id", "artist_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_sponsorships_sponsor_artist_status",
        table_name="sponsorships")
    op.drop_index("ix_posts_early_access_until", table_name="posts",
        postgresql_where=sa.text("early_access_until IS NOT NULL"))
    op.drop_constraint("ck_posts_early_access_pair", "posts", type_="check")
    op.drop_constraint("ck_posts_early_access_tier_enum", "posts", type_="check")
    op.drop_column("posts", "early_access_tier")
    op.drop_column("posts", "early_access_until")
