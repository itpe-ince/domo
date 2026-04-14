"""Artist onboarding Phase 1: profile field expansion + badge rename

Revision ID: 0014_artist_onboarding
Revises: 0013_schools
Create Date: 2026-04-14

Adds to artist_applications:
  department, graduation_year, is_enrolled, genre_tags,
  enrollment_proof_url, representative_works, exhibitions, awards

Adds to artist_profiles:
  department, graduation_year, is_enrolled, genre_tags,
  representative_works, exhibitions, awards

Badge level rename:
  emerging → student, featured → emerging, popular → recommended, master → popular
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from alembic import op

revision: str = "0014_artist_onboarding"
down_revision: Union[str, None] = "0013_schools"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # artist_applications
    op.add_column("artist_applications", sa.Column("department", sa.String(100), nullable=True))
    op.add_column("artist_applications", sa.Column("graduation_year", sa.Integer, nullable=True))
    op.add_column("artist_applications", sa.Column("is_enrolled", sa.Boolean, server_default="true"))
    op.add_column("artist_applications", sa.Column("genre_tags", ARRAY(sa.Text), nullable=True))
    op.add_column("artist_applications", sa.Column("enrollment_proof_url", sa.Text, nullable=True))
    op.add_column("artist_applications", sa.Column("representative_works", JSONB, nullable=True))
    op.add_column("artist_applications", sa.Column("exhibitions", JSONB, nullable=True))
    op.add_column("artist_applications", sa.Column("awards", JSONB, nullable=True))

    # artist_profiles
    op.add_column("artist_profiles", sa.Column("department", sa.String(100), nullable=True))
    op.add_column("artist_profiles", sa.Column("graduation_year", sa.Integer, nullable=True))
    op.add_column("artist_profiles", sa.Column("is_enrolled", sa.Boolean, server_default="true"))
    op.add_column("artist_profiles", sa.Column("genre_tags", ARRAY(sa.Text), nullable=True))
    op.add_column("artist_profiles", sa.Column("representative_works", JSONB, nullable=True))
    op.add_column("artist_profiles", sa.Column("exhibitions", JSONB, nullable=True))
    op.add_column("artist_profiles", sa.Column("awards", JSONB, nullable=True))

    # Badge level rename
    op.execute("UPDATE artist_profiles SET badge_level = 'popular' WHERE badge_level = 'master'")
    op.execute("UPDATE artist_profiles SET badge_level = 'recommended' WHERE badge_level = 'popular' AND badge_level != 'popular'")
    op.execute("UPDATE artist_profiles SET badge_level = 'student' WHERE badge_level = 'emerging'")
    # Note: 'featured' → 'emerging' (featured가 있으면)
    op.execute("UPDATE artist_profiles SET badge_level = 'emerging' WHERE badge_level = 'featured'")


def downgrade() -> None:
    # Reverse badge rename
    op.execute("UPDATE artist_profiles SET badge_level = 'featured' WHERE badge_level = 'emerging'")
    op.execute("UPDATE artist_profiles SET badge_level = 'emerging' WHERE badge_level = 'student'")
    op.execute("UPDATE artist_profiles SET badge_level = 'master' WHERE badge_level = 'popular'")

    # artist_profiles
    for col in ("awards", "exhibitions", "representative_works", "genre_tags", "is_enrolled", "graduation_year", "department"):
        op.drop_column("artist_profiles", col)

    # artist_applications
    for col in ("awards", "exhibitions", "representative_works", "enrollment_proof_url", "genre_tags", "is_enrolled", "graduation_year", "department"):
        op.drop_column("artist_applications", col)
