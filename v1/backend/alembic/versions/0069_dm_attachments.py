"""1:1 DM 첨부파일 컬럼 추가 — Phase 9 L-C (L-7 File Attachment).

dm_messages 테이블에 attachment_url, attachment_type, attachment_size_bytes 컬럼을 추가한다.
기존 데이터는 변경하지 않으며 새 컬럼은 모두 nullable이다.

Revision ID: 0069_dm_attachments
Revises: 0068_group_dm
Create Date: 2026-05-05
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0069_dm_attachments"
down_revision: Union[str, None] = "0068_group_dm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 첨부파일 URL (S3 CDN 또는 로컬 미디어 경로)
    op.add_column(
        "dm_messages",
        sa.Column(
            "attachment_url",
            sa.Text,
            nullable=True,
            comment="S3 CDN URL 또는 로컬 미디어 경로",
        ),
    )
    # 첨부파일 유형: 'image' | 'file' | NULL
    op.add_column(
        "dm_messages",
        sa.Column(
            "attachment_type",
            sa.String(20),
            nullable=True,
            comment="'image' | 'file' | NULL",
        ),
    )
    # 첨부파일 크기 (바이트)
    op.add_column(
        "dm_messages",
        sa.Column(
            "attachment_size_bytes",
            sa.BigInteger,
            nullable=True,
            comment="파일 크기 — presign 요청 시 검증 후 저장",
        ),
    )

    # 첨부파일 있는 메시지 조회용 인덱스 (관리자 모더레이션 큐)
    op.create_index(
        "ix_dm_msg_attachment",
        "dm_messages",
        ["attachment_type"],
        postgresql_where=sa.text("attachment_type IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_dm_msg_attachment", table_name="dm_messages")
    op.drop_column("dm_messages", "attachment_size_bytes")
    op.drop_column("dm_messages", "attachment_type")
    op.drop_column("dm_messages", "attachment_url")
