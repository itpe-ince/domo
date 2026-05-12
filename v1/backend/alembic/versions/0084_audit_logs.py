"""alembic 0084 — audit_logs 테이블 신설 (Phase 11 D-2).

admin endpoint 전체 + user sensitive action 감사 로그를 PostgreSQL에 영구 저장.
인덱스 4개 (actor_id+created_at / action+created_at / target_type+target_id / created_at).
보존 기간: AUDIT_LOG_RETENTION_DAYS (default 365일), 24번째 cleanup worker 담당.

down_revision = "0083_ai_collections"
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0084_audit_logs"
down_revision = "0083_ai_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("audit_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 인덱스 1: actor_id + created_at DESC (actor별 최신 감사 조회)
    op.create_index(
        "ix_audit_logs_actor",
        "audit_logs",
        ["actor_id", "created_at"],
        postgresql_ops={"created_at": "DESC NULLS LAST"},
    )

    # 인덱스 2: action + created_at DESC (action별 최신 감사 조회)
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action", "created_at"],
        postgresql_ops={"created_at": "DESC NULLS LAST"},
    )

    # 인덱스 3: target_type + target_id (대상 객체별 감사 조회)
    op.create_index(
        "ix_audit_logs_target",
        "audit_logs",
        ["target_type", "target_id"],
    )

    # 인덱스 4: created_at DESC (기간별 감사 조회 + cleanup worker)
    op.create_index(
        "ix_audit_logs_created",
        "audit_logs",
        ["created_at"],
        postgresql_ops={"created_at": "DESC NULLS LAST"},
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor", table_name="audit_logs")
    op.drop_table("audit_logs")
