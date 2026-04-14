"""Add edu_email verification fields to artist_applications

Revision ID: 0015_edu_email
Revises: 0014_artist_onboarding
Create Date: 2026-04-14
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0015_edu_email"
down_revision: Union[str, None] = "0014_artist_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("artist_applications", sa.Column("edu_email", sa.String(255), nullable=True))
    op.add_column("artist_applications", sa.Column("edu_email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("artist_profiles", sa.Column("edu_email", sa.String(255), nullable=True))
    op.add_column("artist_profiles", sa.Column("edu_email_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("artist_profiles", "edu_email_verified_at")
    op.drop_column("artist_profiles", "edu_email")
    op.drop_column("artist_applications", "edu_email_verified_at")
    op.drop_column("artist_applications", "edu_email")
