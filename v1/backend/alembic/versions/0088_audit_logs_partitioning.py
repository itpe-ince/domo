"""alembic 0088 — audit_logs 테이블 월별 파티셔닝 (Phase 13 B-2).

기존 단일 audit_logs 테이블을 PostgreSQL 16 declarative partitioning
(PARTITION BY RANGE on created_at)으로 전환.

전략:
  - 신규 파티션 테이블 audit_logs_new 생성
  - 기본 파티션 6개 (2026-04 ~ 2026-09) + DEFAULT 파티션
  - 기존 데이터 INSERT INTO ... SELECT (100건 미만 가정)
  - audit_logs DROP → audit_logs_new RENAME → audit_logs
  - 인덱스 4개 부모 테이블에 생성 (각 파티션 자동 상속)

100건 이상 대규모 환경:
  - ATTACH PARTITION 방식 사용 권장 (설계 문서 섹션 3.3 참고)
  - 단계별 마이그레이션 후 downtime 없이 파티션 전환 가능

Revision ID: 0088_audit_logs_partitioning
Revises: 0086_password_reset_tokens
Create Date: 2026-05-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0088_audit_logs_partitioning"
down_revision = "0086_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # 1단계: 파티션 부모 테이블 생성 (PARTITION BY RANGE)
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE audit_logs_new (
            id              UUID        NOT NULL DEFAULT uuid_generate_v4(),
            actor_id        UUID        REFERENCES users(id) ON DELETE SET NULL,
            actor_role      VARCHAR(20),
            action          VARCHAR(100) NOT NULL,
            target_type     VARCHAR(50),
            target_id       UUID,
            audit_metadata  JSONB,
            ip_address      INET,
            user_agent      TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'success',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # ──────────────────────────────────────────────────────────────────────────
    # 2단계: 기본 파티션 6개 생성 (2026-04 ~ 2026-09)
    # ──────────────────────────────────────────────────────────────────────────
    partitions = [
        ("audit_logs_2026_04", "2026-04-01", "2026-05-01"),
        ("audit_logs_2026_05", "2026-05-01", "2026-06-01"),
        ("audit_logs_2026_06", "2026-06-01", "2026-07-01"),
        ("audit_logs_2026_07", "2026-07-01", "2026-08-01"),
        ("audit_logs_2026_08", "2026-08-01", "2026-09-01"),
        ("audit_logs_2026_09", "2026-09-01", "2026-10-01"),
    ]

    for name, from_date, to_date in partitions:
        op.execute(f"""
            CREATE TABLE {name}
            PARTITION OF audit_logs_new
            FOR VALUES FROM ('{from_date}') TO ('{to_date}')
        """)

    # ──────────────────────────────────────────────────────────────────────────
    # 3단계: DEFAULT 파티션 — 경계 밖 행 안전망 (미래 파티션 미생성 시 fallback)
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE audit_logs_default
        PARTITION OF audit_logs_new
        DEFAULT
    """)

    # ──────────────────────────────────────────────────────────────────────────
    # 4단계: 인덱스 생성 (부모 테이블 → 각 파티션 자동 상속)
    # ──────────────────────────────────────────────────────────────────────────

    # 인덱스 1: actor_id + created_at DESC (actor별 최신 감사 조회)
    op.execute("""
        CREATE INDEX ix_audit_logs_actor
        ON audit_logs_new (actor_id, created_at DESC NULLS LAST)
    """)

    # 인덱스 2: action + created_at DESC (action별 최신 감사 조회)
    op.execute("""
        CREATE INDEX ix_audit_logs_action
        ON audit_logs_new (action, created_at DESC NULLS LAST)
    """)

    # 인덱스 3: target_type + target_id (대상 객체별 감사 조회)
    op.execute("""
        CREATE INDEX ix_audit_logs_target
        ON audit_logs_new (target_type, target_id)
    """)

    # 인덱스 4: created_at DESC (기간별 조회 + cleanup worker)
    op.execute("""
        CREATE INDEX ix_audit_logs_created
        ON audit_logs_new (created_at DESC NULLS LAST)
    """)

    # ──────────────────────────────────────────────────────────────────────────
    # 5단계: 기존 데이터 이전 (100건 미만 가정 → INSERT SELECT)
    #
    # 100건 이상 대규모 환경에서는 ATTACH PARTITION 방식을 권장한다:
    #   1) 개별 월 테이블을 CREATE TABLE ... (LIKE audit_logs INCLUDING ALL)
    #   2) 데이터 복사 후 CHECK 제약 추가
    #   3) ALTER TABLE audit_logs_new ATTACH PARTITION ... FOR VALUES FROM ... TO ...
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO audit_logs_new
            (id, actor_id, actor_role, action, target_type, target_id,
             audit_metadata, ip_address, user_agent, status, created_at)
        SELECT
            id, actor_id, actor_role, action, target_type, target_id,
            audit_metadata, ip_address, user_agent, status, created_at
        FROM audit_logs
    """)

    # ──────────────────────────────────────────────────────────────────────────
    # 6단계: 기존 단일 테이블 DROP + 파티션 테이블 rename
    # audit_logs는 다른 테이블에서 FK 참조하지 않으므로 바로 DROP 가능
    # ──────────────────────────────────────────────────────────────────────────
    op.execute("DROP TABLE audit_logs")
    op.execute("ALTER TABLE audit_logs_new RENAME TO audit_logs")

    # 파티션 테이블은 rename 후에도 각 파티션 이름은 그대로 유지됨
    # (audit_logs_2026_04 등은 이미 올바른 이름)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────────
    # 파티션 테이블 → 단일 테이블로 복원
    # ──────────────────────────────────────────────────────────────────────────

    # 1단계: 단일 테이블 생성 (backup 역할)
    op.execute("""
        CREATE TABLE audit_logs_backup (
            id              UUID        NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
            actor_id        UUID        REFERENCES users(id) ON DELETE SET NULL,
            actor_role      VARCHAR(20),
            action          VARCHAR(100) NOT NULL,
            target_type     VARCHAR(50),
            target_id       UUID,
            audit_metadata  JSONB,
            ip_address      INET,
            user_agent      TEXT,
            status          VARCHAR(20) NOT NULL DEFAULT 'success',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # 2단계: 파티션 테이블에서 데이터 이전 (audit_logs = 파티션 테이블)
    op.execute("""
        INSERT INTO audit_logs_backup
            (id, actor_id, actor_role, action, target_type, target_id,
             audit_metadata, ip_address, user_agent, status, created_at)
        SELECT
            id, actor_id, actor_role, action, target_type, target_id,
            audit_metadata, ip_address, user_agent, status, created_at
        FROM audit_logs
    """)

    # 3단계: 파티션 테이블 DROP (파티션 포함 CASCADE)
    op.execute("DROP TABLE audit_logs")

    # 4단계: backup → audit_logs 복원
    op.execute("ALTER TABLE audit_logs_backup RENAME TO audit_logs")

    # 5단계: 인덱스 재생성 (0084_audit_logs.py 원본 인덱스 복원)
    op.execute("""
        CREATE INDEX ix_audit_logs_actor
        ON audit_logs (actor_id, created_at DESC NULLS LAST)
    """)
    op.execute("""
        CREATE INDEX ix_audit_logs_action
        ON audit_logs (action, created_at DESC NULLS LAST)
    """)
    op.execute("""
        CREATE INDEX ix_audit_logs_target
        ON audit_logs (target_type, target_id)
    """)
    op.execute("""
        CREATE INDEX ix_audit_logs_created
        ON audit_logs (created_at DESC NULLS LAST)
    """)
