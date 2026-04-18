"""Add user_preferences + bookmarks tables

Revision ID: 0019_user_preferences
Revises: 0018_bookmarks
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from alembic import op

revision: str = "0019_user_preferences"
down_revision: Union[str, None] = "0018_bookmarks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_genres", ARRAY(sa.Text), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_genres")
