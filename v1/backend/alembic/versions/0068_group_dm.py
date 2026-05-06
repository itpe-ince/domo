"""Group DM 테이블 생성 — Phase 9 L-C (L-5 Group DM).

group_conversations, group_participants, group_messages 세 테이블을 신규 생성한다.
기존 1:1 dm_conversations / dm_messages 스키마는 변경하지 않는다.

Revision ID: 0068_group_dm
Revises: 0067_external_content_tracking
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0068_group_dm"
down_revision: Union[str, None] = "0067_external_content_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── group_conversations ────────────────────────────────────────────────────
    op.create_table(
        "group_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="그룹명 — 관리자(admin role)만 수정 가능",
        ),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="그룹 생성자. 탈퇴 시 NULL 허용.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="최신 메시지 시각 — 그룹 목록 정렬용",
        ),
        sa.Column(
            "max_participants",
            sa.Integer,
            nullable=False,
            server_default=sa.text("50"),
            comment="최대 참여자 수 (기본 50인)",
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="그룹 종료 시각 — 관리자 전용 소프트 클로즈",
        ),
        sa.Column(
            "closed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_group_conv_creator",
        "group_conversations",
        ["creator_id"],
        postgresql_where=sa.text("creator_id IS NOT NULL"),
    )
    op.create_index(
        "ix_group_conv_last_msg",
        "group_conversations",
        [sa.text("last_message_at DESC NULLS LAST")],
    )

    # ── group_participants ────────────────────────────────────────────────────
    op.create_table(
        "group_participants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("group_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'member'"),
            comment="'member' | 'admin'",
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "left_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="NULL = 현재 참여 중. 소프트 삭제로 메시지 히스토리 보존.",
        ),
    )

    # conversation_id + user_id 쌍은 유일 (같은 사용자가 중복 참여 불가)
    op.create_index(
        "uq_group_participants_pair",
        "group_participants",
        ["conversation_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "ix_group_part_user",
        "group_participants",
        ["user_id", "left_at"],
    )
    op.create_index(
        "ix_group_part_conv",
        "group_participants",
        ["conversation_id", "left_at"],
    )

    # ── group_messages ────────────────────────────────────────────────────────
    op.create_table(
        "group_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("group_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text,
            nullable=False,
            comment="최대 2000자 — 앱 레이어에서 검증",
        ),
        sa.Column(
            "attachment_url",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "attachment_type",
            sa.String(20),
            nullable=True,
            comment="'image' | 'file' | NULL",
        ),
        sa.Column(
            "attachment_size_bytes",
            sa.BigInteger,
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="소프트 삭제 타임스탬프",
        ),
    )

    # 그룹 메시지 목록 기본 쿼리 인덱스 (conversation_id + created_at 순)
    op.create_index(
        "ix_group_msg_conv_created",
        "group_messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(
        "ix_group_msg_sender",
        "group_messages",
        ["sender_id", "created_at"],
    )


def downgrade() -> None:
    # 종속 순서: group_messages → group_participants → group_conversations
    op.drop_index("ix_group_msg_sender", table_name="group_messages")
    op.drop_index("ix_group_msg_conv_created", table_name="group_messages")
    op.drop_table("group_messages")

    op.drop_index("ix_group_part_conv", table_name="group_participants")
    op.drop_index("ix_group_part_user", table_name="group_participants")
    op.drop_index("uq_group_participants_pair", table_name="group_participants")
    op.drop_table("group_participants")

    op.drop_index("ix_group_conv_last_msg", table_name="group_conversations")
    op.drop_index("ix_group_conv_creator", table_name="group_conversations")
    op.drop_table("group_conversations")
