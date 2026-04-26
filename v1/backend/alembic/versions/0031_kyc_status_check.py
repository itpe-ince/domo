"""Add CHECK constraint on kyc_sessions.status.

Valid values: pending | processing | verified | failed | expired

Revision ID: 0031_kyc_status_check
Revises: 0030_drop_users_birth_date
Create Date: 2026-04-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0031_kyc_status_check"
down_revision: Union[str, None] = "0030_drop_users_birth_date"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "ck_kyc_sessions_status"
_VALID = ("pending", "processing", "verified", "failed", "expired")


def upgrade() -> None:
    op.create_check_constraint(
        _CONSTRAINT,
        "kyc_sessions",
        f"status IN ({', '.join(repr(v) for v in _VALID)})",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "kyc_sessions", type_="check")
