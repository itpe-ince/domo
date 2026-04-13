"""Post editor: scheduled_at, location fields

Revision ID: 0011_post_editor_fields
Revises: 0010_search_logs
Create Date: 2026-04-13

Adds:
- posts.scheduled_at (TIMESTAMPTZ) — 예약 게시
- posts.location_name (VARCHAR 200) — 장소명
- posts.location_lat (DOUBLE PRECISION) — 위도
- posts.location_lng (DOUBLE PRECISION) — 경도
- idx_posts_scheduled 인덱스
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0011_post_editor_fields"
down_revision: Union[str, None] = "0010_search_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("posts", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("location_name", sa.String(200), nullable=True))
    op.add_column("posts", sa.Column("location_lat", sa.Float, nullable=True))
    op.add_column("posts", sa.Column("location_lng", sa.Float, nullable=True))
    op.create_index(
        "idx_posts_scheduled",
        "posts",
        ["scheduled_at"],
        postgresql_where=sa.text("scheduled_at IS NOT NULL AND status = 'scheduled'"),
    )


def downgrade() -> None:
    op.drop_index("idx_posts_scheduled", table_name="posts")
    op.drop_column("posts", "location_lng")
    op.drop_column("posts", "location_lat")
    op.drop_column("posts", "location_name")
    op.drop_column("posts", "scheduled_at")
