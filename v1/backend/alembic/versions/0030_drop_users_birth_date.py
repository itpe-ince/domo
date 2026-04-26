"""Drop unused users.birth_date column (design §7.1 uses birth_year only).

Revision ID: 0030_drop_users_birth_date
Revises: 0029_user_stripe_customer
Create Date: 2026-04-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_drop_users_birth_date"
down_revision: Union[str, None] = "0029_user_stripe_customer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "birth_date")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("birth_date", sa.Date, nullable=True),
    )
