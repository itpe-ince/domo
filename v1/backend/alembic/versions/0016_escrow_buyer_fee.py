"""Add buyer_fee and escrow fields to orders

Revision ID: 0016_escrow_buyer_fee
Revises: 0015_edu_email
Create Date: 2026-04-18

Adds:
- orders.buyer_fee (NUMERIC 12,2) — 구매자 수수료 (판매금액의 10%)
- orders.shipping_status — 배송 상태
- orders.inspection_status — 콜렉터 검수 상태
- orders.settled_at — 작가 정산 완료 시각
- orders.inspection_completed_at — 검수 완료 시각
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0016_escrow_buyer_fee"
down_revision: Union[str, None] = "0015_edu_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("buyer_fee", sa.Numeric(12, 2), server_default="0"))
    op.add_column("orders", sa.Column("shipping_status", sa.String(20), server_default="'pending'"))
    op.add_column("orders", sa.Column("inspection_status", sa.String(20), server_default="'pending'"))
    op.add_column("orders", sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("inspection_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "inspection_completed_at")
    op.drop_column("orders", "settled_at")
    op.drop_column("orders", "inspection_status")
    op.drop_column("orders", "shipping_status")
    op.drop_column("orders", "buyer_fee")
