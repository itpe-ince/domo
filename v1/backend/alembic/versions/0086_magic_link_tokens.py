"""alembic 0086 — magic_link_tokens 테이블 생성 (Phase 12 C-2).

매직링크 비밀번호 없는 가입/로그인을 위한 토큰 저장 테이블.
- users 테이블에 컬럼 추가 시 null 컬럼 난립 방지를 위해 별도 테이블 사용.
- 토큰 수명(24h) 및 1회용 관리 명확화.

down_revision = "0085_email_password_auth"
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0086_magic_link_tokens"
down_revision = "0085_email_password_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv4/IPv6 최대 45자
        sa.Column("is_used", sa.Boolean, default=False, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_magic_link_tokens_token", "magic_link_tokens", ["token"])
    op.create_index("ix_magic_link_tokens_email", "magic_link_tokens", ["email"])


def downgrade() -> None:
    op.drop_index("ix_magic_link_tokens_token", table_name="magic_link_tokens")
    op.drop_index("ix_magic_link_tokens_email", table_name="magic_link_tokens")
    op.drop_table("magic_link_tokens")
