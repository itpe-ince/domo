"""Add schools table with initial seed data

Revision ID: 0013_schools
Revises: 0012_collections
Create Date: 2026-04-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0013_schools"
down_revision: Union[str, None] = "0012_collections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INITIAL_SCHOOLS = [
    ("서울대학교", "Seoul National University", "KR", "snu.ac.kr", "university"),
    ("홍익대학교", "Hongik University", "KR", "hongik.ac.kr", "university"),
    ("국민대학교", "Kookmin University", "KR", "kookmin.ac.kr", "university"),
    ("이화여자대학교", "Ewha Womans University", "KR", "ewha.ac.kr", "university"),
    ("중앙대학교", "Chung-Ang University", "KR", "cau.ac.kr", "university"),
    ("한국예술종합학교", "Korea National University of Arts", "KR", "karts.ac.kr", "art_school"),
    ("계원예술대학교", "Kaywon University of Art & Design", "KR", "kaywon.ac.kr", "art_school"),
    ("도쿄예술대학", "Tokyo University of the Arts", "JP", "geidai.ac.jp", "art_school"),
    ("무사시노미술대학", "Musashino Art University", "JP", "musabi.ac.jp", "art_school"),
    ("로열 칼리지 오브 아트", "Royal College of Art", "GB", "rca.ac.uk", "art_school"),
    ("파슨스 디자인 스쿨", "Parsons School of Design", "US", "newschool.edu", "art_school"),
    ("로드아일랜드 디자인 스쿨", "Rhode Island School of Design", "US", "risd.edu", "art_school"),
]


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name_ko", sa.String(200), nullable=False),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=False),
        sa.Column("email_domain", sa.String(100), nullable=False, unique=True),
        sa.Column("school_type", sa.String(20), server_default="university"),
        sa.Column("logo_url", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_schools_country", "schools", ["country_code"])
    op.create_index("idx_schools_domain", "schools", ["email_domain"])

    # Seed data
    schools_table = sa.table(
        "schools",
        sa.column("name_ko", sa.String),
        sa.column("name_en", sa.String),
        sa.column("country_code", sa.String),
        sa.column("email_domain", sa.String),
        sa.column("school_type", sa.String),
    )
    op.bulk_insert(
        schools_table,
        [
            {"name_ko": s[0], "name_en": s[1], "country_code": s[2], "email_domain": s[3], "school_type": s[4]}
            for s in INITIAL_SCHOOLS
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_schools_domain", table_name="schools")
    op.drop_index("idx_schools_country", table_name="schools")
    op.drop_table("schools")
