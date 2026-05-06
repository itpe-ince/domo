"""Create dm_conversations and dm_messages tables — B'-2 dm-messaging.

Conversation normalizes user_a_id < user_b_id to prevent duplicate pairs.
Message supports soft-delete, edit tracking, and read receipts.

Revision ID: 0063_dm_messaging
Revises: 0062_exchange_rates
Create Date: 2026-05-04
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0063_dm_messaging"
down_revision: Union[str, None] = "0062_exchange_rates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Conversations ──────────────────────────────────────────────────────
    op.create_table(
        "dm_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="Always the participant with the lexicographically smaller UUID.",
        ),
        sa.Column(
            "user_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="Always the participant with the lexicographically larger UUID.",
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
            comment="Updated on each new message for conversation list ordering.",
        ),
        # Soft-hide flags — conversation is hidden for a participant but not deleted.
        # The counterpart still sees it; messages are preserved.
        sa.Column(
            "deleted_a",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="User A has hidden this conversation.",
        ),
        sa.Column(
            "deleted_b",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="User B has hidden this conversation.",
        ),
        # Admin moderation: hard-close a conversation (no new messages allowed).
        sa.Column(
            "closed_by_admin_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "closed_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Prevent duplicate conversations between the same two users.
    # user_a_id < user_b_id is enforced at the application level before insert.
    op.create_index(
        "uq_dm_conversations_pair",
        "dm_conversations",
        ["user_a_id", "user_b_id"],
        unique=True,
    )

    # Conversation list ordered by most recent message.
    op.create_index(
        "ix_dm_conversations_a_last_msg",
        "dm_conversations",
        ["user_a_id", "last_message_at"],
    )
    op.create_index(
        "ix_dm_conversations_b_last_msg",
        "dm_conversations",
        ["user_b_id", "last_message_at"],
    )

    # ── Messages ───────────────────────────────────────────────────────────
    op.create_table(
        "dm_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dm_conversations.id", ondelete="CASCADE"),
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
            comment="Plain text body — max 2000 chars enforced at app layer.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set when the recipient calls POST /conversations/{id}/read.",
        ),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Set when sender edits body within 5-minute window.",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft-delete timestamp — body replaced with [deleted] sentinel.",
        ),
    )

    # Primary message list query: conversation messages ordered by time.
    op.create_index(
        "ix_dm_messages_conv_created",
        "dm_messages",
        ["conversation_id", "created_at"],
    )

    # Used to verify sender ownership before edit/delete.
    op.create_index(
        "ix_dm_messages_sender_created",
        "dm_messages",
        ["sender_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_dm_messages_sender_created", table_name="dm_messages")
    op.drop_index("ix_dm_messages_conv_created", table_name="dm_messages")
    op.drop_table("dm_messages")

    op.drop_index("ix_dm_conversations_b_last_msg", table_name="dm_conversations")
    op.drop_index("ix_dm_conversations_a_last_msg", table_name="dm_conversations")
    op.drop_index("uq_dm_conversations_pair", table_name="dm_conversations")
    op.drop_table("dm_conversations")
