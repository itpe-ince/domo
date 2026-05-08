"""pytest conftest.py — Phase 12 A-1.

testcontainers PostgreSQL fixture (session scope) + transaction rollback 격리.
USE_TESTCONTAINERS=true 환경변수 설정 시에만 컨테이너 기동.
미설정 환경(CI macOS 등)에서 graceful skip.
"""
from __future__ import annotations

import os
import subprocess

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ── testcontainers graceful import (미설치 시 skip) ─────────────────────────
try:
    from testcontainers.postgres import PostgresContainer  # type: ignore[import]
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False

# USE_TESTCONTAINERS 환경변수로 옵트인 — 기본값 false (CI 미지원 환경 대응)
USE_TESTCONTAINERS = os.getenv("USE_TESTCONTAINERS", "false").lower() == "true"

# backend 루트 경로 (alembic 실행 위치)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── session scope: 컨테이너 1회만 시작 ─────────────────────────────────────

@pytest.fixture(scope="session")
def pg_container():
    """PostgreSQL testcontainer (pgvector 포함) — session scope, 1회 시작.

    USE_TESTCONTAINERS=true 미설정 시 graceful skip.
    """
    if not USE_TESTCONTAINERS:
        pytest.skip(
            "testcontainers 비활성. 사용하려면 USE_TESTCONTAINERS=true 설정."
        )
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip(
            "testcontainers 미설치. pip install 'testcontainers[postgresql]' 필요."
        )
    # pgvector/pgvector:pg15 이미지: pgvector extension 내장 (alembic migration 호환)
    with PostgresContainer("pgvector/pgvector:pg15") as pg:
        yield pg


@pytest.fixture(scope="session")
def real_db_engine(pg_container):
    """실제 PostgreSQL async 엔진 + alembic upgrade head (1회).

    alembic 변경 없음 — 기존 migration만 적용.
    """
    # sync URL로 alembic 실행
    sync_url = pg_container.get_connection_url()
    # asyncpg driver로 async 엔진 생성
    async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # alembic upgrade head 실행 (schema freeze — 변경 없음)
    result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL": sync_url},
        cwd=_BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head 실패:\n{result.stdout}\n{result.stderr}"
        )

    engine = create_async_engine(async_url, echo=False)
    yield engine
    # 컨테이너 종료 시 자동 정리


@pytest_asyncio.fixture
async def real_db_session(real_db_engine):
    """function scope: 각 테스트마다 transaction rollback으로 격리.

    BEGIN → 테스트 실행 → ROLLBACK (데이터 잔류 없음).
    """
    async_session_factory = sessionmaker(
        real_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        # 중첩 트랜잭션 시작 (테스트 격리용)
        async with session.begin():
            yield session
            # 테스트 완료 후 항상 rollback — 격리 보장
            await session.rollback()
