"""alembic 0085 — 이메일+비밀번호 인증 컬럼 추가 (Phase 11 D-3).

users 테이블에 이메일 인증 및 일반 사용자 로그인 잠금 컬럼을 추가한다.
- password_hash / failed_login_count 는 이미 존재하므로 추가하지 않음.
- admin의 locked_until 과 분리하여 일반 사용자 잠금 상태를 별도 컬럼으로 관리.

추가 컬럼:
  email_verified                BOOLEAN NOT NULL DEFAULT FALSE
  email_verification_token      VARCHAR(64) NULL
  email_verification_sent_at    TIMESTAMPTZ NULL
  email_verification_expires_at TIMESTAMPTZ NULL
  failed_login_locked_until     TIMESTAMPTZ NULL  (일반 사용자용 별도 잠금)

down_revision = "0084_audit_logs"
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0085_email_password_auth"
down_revision = "0084_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # email_verified — 기본값 False, 기존 Google 계정은 True로 일괄 설정
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 이메일 인증 토큰 (secrets.token_urlsafe(32) = 43자)
    op.add_column(
        "users",
        sa.Column("email_verification_token", sa.String(64), nullable=True),
    )

    # 인증 메일 발송 시각 (5분 cooldown 계산용)
    op.add_column(
        "users",
        sa.Column(
            "email_verification_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 토큰 만료 시각 (24시간)
    op.add_column(
        "users",
        sa.Column(
            "email_verification_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 일반 사용자 로그인 잠금 해제 시각 (admin의 locked_until 과 분리)
    op.add_column(
        "users",
        sa.Column(
            "failed_login_locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 기존 Google OAuth 사용자는 이메일이 이미 Google에서 검증됨 → email_verified=True
    # sns_provider = 'google' 인 경우 일괄 업데이트
    op.execute(
        sa.text(
            "UPDATE users SET email_verified = true WHERE sns_provider = 'google'"
        )
    )

    # 인증 토큰 조회 인덱스 (verify 엔드포인트 성능)
    op.create_index(
        "ix_users_email_verification_token",
        "users",
        ["email_verification_token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_email_verification_token", table_name="users")
    op.drop_column("users", "failed_login_locked_until")
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_sent_at")
    op.drop_column("users", "email_verification_token")
    op.drop_column("users", "email_verified")
