"""Add communities, community_members, community_posts tables

Revision ID: 0023_communities
Revises: 0022_settlements
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0023_communities"
down_revision: Union[str, None] = "0022_settlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GENRE_COMMUNITIES = [
    ("Painting", "painting"), ("Drawing", "drawing"), ("Photography", "photography"),
    ("Sculpture", "sculpture"), ("Mixed Media", "mixed_media"),
]

COUNTRY_COMMUNITIES = [
    ("Korea", "KR"), ("Japan", "JP"), ("United States", "US"),
    ("United Kingdom", "GB"), ("Taiwan", "TW"),
]


def upgrade() -> None:
    op.create_table(
        "communities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cover_image_url", sa.Text, nullable=True),
        sa.Column("member_count", sa.Integer, server_default="0"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_communities_type", "communities", ["type"])

    op.create_table(
        "community_members",
        sa.Column("community_id", UUID(as_uuid=True), sa.ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(20), server_default="'member'"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "community_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("community_id", UUID(as_uuid=True), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_community_posts", "community_posts", ["community_id", "created_at"])

    # Seed genre communities
    communities = sa.table("communities", sa.column("name"), sa.column("type"), sa.column("description"))
    op.bulk_insert(communities, [
        {"name": name, "type": "genre", "description": f"{name} artists community"}
        for name, _ in GENRE_COMMUNITIES
    ] + [
        {"name": name, "type": "country", "description": f"{name} artists community"}
        for name, _ in COUNTRY_COMMUNITIES
    ])


def downgrade() -> None:
    op.drop_index("idx_community_posts", table_name="community_posts")
    op.drop_table("community_posts")
    op.drop_table("community_members")
    op.drop_index("idx_communities_type", table_name="communities")
    op.drop_table("communities")
