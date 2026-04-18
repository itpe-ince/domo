"""Add sponsor_rewards + reward_claims tables

Revision ID: 0024_rewards
Revises: 0023_communities
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0024_rewards"
down_revision: Union[str, None] = "0023_communities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sponsor_rewards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("artist_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("min_bluebirds", sa.Integer, nullable=False),
        sa.Column("reward_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rewards_artist", "sponsor_rewards", ["artist_id"])

    op.create_table(
        "reward_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("reward_id", UUID(as_uuid=True), sa.ForeignKey("sponsor_rewards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sponsor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="'pending'"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reward_claims")
    op.drop_index("idx_rewards_artist", table_name="sponsor_rewards")
    op.drop_table("sponsor_rewards")
