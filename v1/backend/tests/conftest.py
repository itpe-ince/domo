"""pytest conftest.py — Phase 12 A-1 / Phase 13 A-1 / Phase 13 A-2.

testcontainers PostgreSQL fixture (session scope) + transaction rollback 격리.
USE_TESTCONTAINERS=true 환경변수 설정 시에만 컨테이너 기동.
미설정 환경(CI macOS 등)에서 graceful skip.

Phase 13 A-1 추가:
- github_oauth_mock: respx 기반 GitHub API HTTP mock fixture
- magic_link_email_mock: 이메일 발송 함수 patch mock fixture
- respx 미설치 시 graceful skip (RESPX_AVAILABLE guard)

Phase 13 A-2 추가:
- localstack_container: LocalStack SES/S3/Cognito-idp (session scope)
- aws_ses_client / aws_s3_client / aws_cognito_client: boto3 → LocalStack
- in_memory_tracer: OTel in-memory span exporter (SDK 설치 시)
- USE_LOCALSTACK=true 환경변수로 옵트인
"""
from __future__ import annotations

import os
import subprocess
from unittest.mock import AsyncMock

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

# ── LocalStack graceful import (미설치 시 비활성) ────────────────────────────
try:
    from testcontainers.localstack import LocalStackContainer  # type: ignore[import]
    LOCALSTACK_AVAILABLE = True
except ImportError:
    LOCALSTACK_AVAILABLE = False

# ── boto3 graceful import (LocalStack 클라이언트 생성용) ─────────────────────
try:
    import boto3 as _boto3  # type: ignore[import]
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

# ── OTel graceful import (in-memory exporter fixture용) ──────────────────────
try:
    from opentelemetry.sdk.trace import TracerProvider as _TracerProvider  # type: ignore[import]
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter as _InMemorySpanExporter  # type: ignore[import]
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor as _SimpleSpanProcessor  # type: ignore[import]
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# ── respx graceful import (미설치 시 fixture 내에서 skip) ───────────────────
try:
    import respx as _respx_module
    import httpx as _httpx
    RESPX_AVAILABLE = True
except ImportError:
    RESPX_AVAILABLE = False


def _skip_if_no_respx() -> None:
    """respx 미설치 환경에서 테스트를 graceful skip."""
    if not RESPX_AVAILABLE:
        pytest.skip("respx 미설치 — GitHub OAuth mock 테스트 skip. pip install respx 후 재실행.")

# USE_TESTCONTAINERS 환경변수로 옵트인 — 기본값 false (CI 미지원 환경 대응)
USE_TESTCONTAINERS = os.getenv("USE_TESTCONTAINERS", "false").lower() == "true"

# USE_LOCALSTACK 환경변수로 옵트인 — 기본값 false (docker 미설치 환경 대응)
USE_LOCALSTACK = os.getenv("USE_LOCALSTACK", "false").lower() == "true"

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


# ── Phase 13 A-1: GitHub OAuth mock fixture ────────────────────────────────


@pytest.fixture
def github_oauth_mock():
    """GitHub OAuth API 전체 HTTP mock (respx 기반).

    mock 범위:
    - POST https://github.com/login/oauth/access_token
    - GET  https://api.github.com/user
    - GET  https://api.github.com/user/emails

    각 테스트에서 router를 직접 조작해 시나리오별 응답 override 가능.
    respx 미설치 시 graceful skip.
    """
    _skip_if_no_respx()

    with _respx_module.mock(assert_all_called=False) as router:
        # 기본 성공 응답 — 각 테스트에서 시나리오별 override
        router.post("https://github.com/login/oauth/access_token").mock(
            return_value=_httpx.Response(
                200,
                json={"access_token": "github_token_test", "token_type": "bearer"},
            )
        )
        router.get("https://api.github.com/user").mock(
            return_value=_httpx.Response(
                200,
                json={
                    "id": 12345,
                    "login": "testuser",
                    "name": "Test User",
                    "email": "test@github.local",
                    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                },
            )
        )
        router.get("https://api.github.com/user/emails").mock(
            return_value=_httpx.Response(
                200,
                json=[
                    {
                        "email": "test@github.local",
                        "primary": True,
                        "verified": True,
                        "visibility": "public",
                    }
                ],
            )
        )
        yield router


# ── Phase 13 A-1: 매직링크 이메일 발송 mock fixture ───────────────────────


@pytest.fixture
def magic_link_email_mock(mocker):
    """매직링크 이메일 발송 함수를 AsyncMock으로 patch.

    실제 SMTP/SES 호출 없이 발송 성공으로 처리.
    반환값: AsyncMock 객체 (호출 여부/인자 검증 가능).
    """
    mock_send = mocker.patch(
        "app.services.magic_link_auth.send_magic_link_email",
        new_callable=AsyncMock,
        return_value=None,
    )
    # auth.py에서도 직접 import하므로 양쪽 patch
    mocker.patch(
        "app.api.auth.send_magic_link_email",
        new_callable=AsyncMock,
        return_value=None,
    )
    return mock_send


# ─── Phase 13 A-2: LocalStack SES/S3/Cognito fixtures ───────────────────────
#
# USE_LOCALSTACK=true 설정 시에만 컨테이너를 기동.
# 미설정 환경(macOS docker 미설치, 단순 단위 테스트)에서 graceful skip.
# LocalStack Community 이미지 기준 (localstack/localstack:3) — Pro 기능 사용 안 함.

# skipif 마커 — LocalStack 의존 테스트에 공통 적용
localstack_skip = pytest.mark.skipif(
    not USE_LOCALSTACK,
    reason="LocalStack 미활성. USE_LOCALSTACK=true 설정 시 실행.",
)


@pytest.fixture(scope="session")
def localstack_container():
    """LocalStack 컨테이너 — session scope, 단 1회 기동.

    제공 서비스: ses, s3, cognito-idp
    활성화 조건: USE_LOCALSTACK=true + LOCALSTACK_AVAILABLE

    시작 시간: ~25-35초 (session scope로 1회만 기동).
    """
    if not USE_LOCALSTACK:
        pytest.skip("LocalStack 미활성. USE_LOCALSTACK=true 설정 시 실행.")
    if not LOCALSTACK_AVAILABLE:
        pytest.skip(
            "testcontainers LocalStack 미설치. "
            "pip install 'testcontainers[localstack]' 필요."
        )

    with LocalStackContainer(image="localstack/localstack:3") as ls:
        ls.with_services("ses", "s3", "cognito-idp")
        yield ls


@pytest.fixture
def aws_ses_client(localstack_container):
    """SES boto3 client — LocalStack endpoint 주입 (function scope).

    LocalStack SES는 항상 발송 성공 처리.
    발송 이메일 검증: aws_ses_client.list_messages()로 확인 가능 (Community 기준).
    """
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 미설치. pip install boto3 필요.")
    return _boto3.client(
        "ses",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def aws_s3_client(localstack_container):
    """S3 boto3 client — LocalStack endpoint 주입 (function scope)."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 미설치. pip install boto3 필요.")
    return _boto3.client(
        "s3",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def aws_cognito_client(localstack_container):
    """Cognito-idp boto3 client — LocalStack endpoint 주입 (function scope)."""
    if not BOTO3_AVAILABLE:
        pytest.skip("boto3 미설치. pip install boto3 필요.")
    return _boto3.client(
        "cognito-idp",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def ses_verified_identity(aws_ses_client):
    """SES 발신자 이메일 사전 인증 — LocalStack은 항상 통과.

    실제 AWS SES는 도메인/이메일 인증이 필요하지만,
    LocalStack은 verify 요청을 즉시 통과 처리함.
    """
    aws_ses_client.verify_email_identity(EmailAddress="noreply@domo.test")
    yield


# ─── Phase 13 A-2: OTel in-memory exporter fixture ──────────────────────────


@pytest.fixture
def in_memory_tracer():
    """OTel in-memory span exporter — 실제 Collector 없이 span 검증 가능.

    SDK 미설치 시 graceful skip (OTel SDK는 선택적 의존성).
    """
    if not OTEL_AVAILABLE:
        pytest.skip(
            "opentelemetry-sdk 미설치. pip install opentelemetry-sdk 필요."
        )

    exporter = _InMemorySpanExporter()
    provider = _TracerProvider()
    provider.add_span_processor(_SimpleSpanProcessor(exporter))

    yield provider, exporter

    exporter.clear()
