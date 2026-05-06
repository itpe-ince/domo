"""alembic 0082 — featured_artist_candidates (K-4 AI Featured Artist 자동 선정)

Phase 10 K-4: admin 검수 큐 도입. autopublish OFF 정책.
publish 시 Phase 8 G'-7 featured_artists 테이블에 INSERT.

Depends: 0081_diversity_config (K-2)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0082"
down_revision = "0081_diversity_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENUM 타입 생성
    op.execute("""
        CREATE TYPE featured_candidate_status AS ENUM
        ('pending', 'approved', 'rejected', 'published', 'expired')
    """)

    op.execute("""
        CREATE TABLE featured_artist_candidates (
            id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            artist_id       UUID        NOT NULL
                                REFERENCES users(id) ON DELETE CASCADE,
            week_start      DATE        NOT NULL,
            composite_score FLOAT       NOT NULL,
            reasoning       JSONB       NOT NULL DEFAULT '{}',
            status          featured_candidate_status NOT NULL DEFAULT 'pending',
            admin_id        UUID        REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at     TIMESTAMPTZ,
            published_at    TIMESTAMPTZ,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # 같은 작가 같은 주 중복 방지
    op.create_index(
        "uq_featured_artist_candidates_artist_week",
        "featured_artist_candidates",
        ["artist_id", "week_start"],
        unique=True,
    )

    # admin 검수 큐 조회 최적화
    op.create_index(
        "ix_featured_artist_candidates_status_week",
        "featured_artist_candidates",
        ["status", "week_start"],
    )

    # 특정 주 전체 후보 조회
    op.create_index(
        "ix_featured_artist_candidates_week_start",
        "featured_artist_candidates",
        ["week_start"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_featured_artist_candidates_week_start",
        table_name="featured_artist_candidates",
    )
    op.drop_index(
        "ix_featured_artist_candidates_status_week",
        table_name="featured_artist_candidates",
    )
    op.drop_index(
        "uq_featured_artist_candidates_artist_week",
        table_name="featured_artist_candidates",
    )
    op.execute("DROP TABLE IF EXISTS featured_artist_candidates")
    op.execute("DROP TYPE IF EXISTS featured_candidate_status")
