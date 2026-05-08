"""password_reset_tokens table — Phase 12 C-1.

별도 테이블로 분리한 이유:
- users 테이블에 인증 관련 컬럼이 이미 5개 — 추가 시 테이블 오염
- 재설정 요청 내역 (IP, 발송 시각, 사용 여부) 독립 감사 추적
- 재발급 시 기존 토큰 일괄 무효화 패턴 구현 용이

Revision ID: 0086_password_reset_tokens
Revises: 0085_email_password_auth
Create Date: 2026-05-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import INET, UUID

revision = "0086_password_reset_tokens"
down_revision = "0087_github_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(64), unique=True, nullable=False),
        sa.Column("ip_address", INET(), nullable=True),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # 토큰 조회 (1회용 검증)
    op.create_index(
        "ix_password_reset_tokens_token",
        "password_reset_tokens",
        ["token"],
        unique=True,
    )
    # cooldown 확인 + 만료 토큰 스캔
    op.create_index(
        "ix_password_reset_tokens_user_id_expires",
        "password_reset_tokens",
        ["user_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id_expires", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
