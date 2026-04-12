"""Phase 1: posts, media_assets, product_posts, follows, likes, comments

Revision ID: 0002_phase1_content
Revises: 0001_initial
Create Date: 2026-04-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_phase1_content"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("genre", sa.String(50), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("language", sa.String(10), server_default="ko"),
        sa.Column("like_count", sa.Integer, server_default="0"),
        sa.Column("comment_count", sa.Integer, server_default="0"),
        sa.Column("view_count", sa.Integer, server_default="0"),
        sa.Column("bluebird_count", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(20), server_default="pending_review"),
        sa.Column("digital_art_check", sa.String(20), server_default="pending"),
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
    )
    op.create_index("idx_posts_author", "posts", ["author_id", "created_at"])
    op.create_index("idx_posts_feed", "posts", ["status", "type", "created_at"])
    op.create_index("idx_posts_genre", "posts", ["genre", "status", "created_at"])

    op.create_table(
        "media_assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("thumbnail_url", sa.Text, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("duration_sec", sa.Integer, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("external_source", sa.String(20), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("order_index", sa.Integer, server_default="0"),
        sa.Column("is_making_video", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_media_post", "media_assets", ["post_id", "order_index"])

    op.create_table(
        "product_posts",
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("is_auction", sa.Boolean, server_default=sa.text("false")),
        sa.Column("is_buy_now", sa.Boolean, server_default=sa.text("false")),
        sa.Column("buy_now_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), server_default="KRW"),
        sa.Column("dimensions", sa.String(100), nullable=True),
        sa.Column("medium", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("is_sold", sa.Boolean, server_default=sa.text("false")),
    )

    op.create_table(
        "follows",
        sa.Column(
            "follower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column(
            "followee_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_follows_followee", "follows", ["followee_id"])

    op.create_table(
        "likes",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comments.id"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), server_default="visible"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_comments_post", "comments", ["post_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_comments_post", table_name="comments")
    op.drop_table("comments")
    op.drop_table("likes")
    op.drop_index("idx_follows_followee", table_name="follows")
    op.drop_table("follows")
    op.drop_table("product_posts")
    op.drop_index("idx_media_post", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index("idx_posts_genre", table_name="posts")
    op.drop_index("idx_posts_feed", table_name="posts")
    op.drop_index("idx_posts_author", table_name="posts")
    op.drop_table("posts")
