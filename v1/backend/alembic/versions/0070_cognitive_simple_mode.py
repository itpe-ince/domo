"""alembic 0070 — users.cognitive_simple_mode + accessibility_preferences 컬럼 추가

Phase 9 L-E: 인지 장애 사용자를 위한 단순 모드 플래그 및 접근성 설정 JSON.
기본값 false / '{}' — 기존 사용자 영향 없음.

Depends: 0066_pgvector_embeddings (0067~0069 미완료 시 안전 하한)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0070_cognitive_simple_mode"
down_revision: Union[str, None] = "0069_dm_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cognitive_simple_mode: 인지 단순 모드 플래그 (기본 false)
    op.add_column(
        "users",
        sa.Column(
            "cognitive_simple_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Partial index — true 사용자만 인덱싱하여 오버헤드 최소화
    op.create_index(
        "ix_users_cognitive_simple_mode",
        "users",
        ["cognitive_simple_mode"],
        postgresql_where=sa.text("cognitive_simple_mode = true"),
    )

    # accessibility_preferences: 장래 확장용 JSONB (고대비 모드, 폰트 크기 오버라이드 등)
    op.add_column(
        "users",
        sa.Column(
            "accessibility_preferences",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_users_cognitive_simple_mode", table_name="users")
    op.drop_column("users", "cognitive_simple_mode")
    op.drop_column("users", "accessibility_preferences")
