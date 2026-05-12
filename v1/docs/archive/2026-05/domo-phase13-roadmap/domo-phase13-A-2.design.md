---
template: design
version: 1.0
feature: domo-phase13-A-2-testcontainers-localstack-extend
date: 2026-05-09
author: itpe-ince (Claude Code, bkend-expert)
project: domo (v1)
status: Draft
wave: A
sub-pdca: A-2
carry-over: "#3"
---

# Phase 13 A-2 — testcontainers + LocalStack 확장 설계서

> **Summary**: Phase 12 A-1(17건 over-mocked tests refactor) 완료 후 잔존 12건(otel SDK · redis event loop · SES mock)을 LocalStack 도입으로 정상화한다.
> 목표: 잔존 12 skip → 0 (OTel SDK 한정 < 3 허용).
>
> **Wave**: A — 테스트 안정성 청산
> **Carry-over**: #3 (Phase 12 A-1 잔존 12 over-mocked tests)
> **alembic 변경**: 없음
> **예상 기간**: ~1주

---

## 1. 목표 & Acceptance Criteria

### 1.1 목표

| 항목 | 현재 | 목표 |
|------|:----:|:----:|
| 잔존 skip tests | 12건 | **0** (OTel SDK 한정 **< 3** 허용) |
| LocalStack 통합 | 미도입 | SES + S3 + Cognito-idp |
| 테스트 회귀 | — | **0건** |
| CI 파이프라인 | — | USE_LOCALSTACK env guard 지원 |

### 1.2 Acceptance Criteria (AC)

- **AC-1**: `pytest --tb=short -q` 실행 시 skip count ≤ 2 (OTel SDK 미설치 환경 제외 시 0)
- **AC-2**: LocalStack SES fixture 정상 실행 — `list_messages()` API로 발송 이메일 검증 가능
- **AC-3**: testcontainers Redis fixture 정상 실행 — event loop 충돌 없음
- **AC-4**: `USE_LOCALSTACK` env 미설정 시 LocalStack 의존 tests graceful skip (`pytest.mark.skipif`)
- **AC-5**: CI `ubuntu-latest` 환경에서 docker-in-docker 자동 동작
- **AC-6**: macOS docker 미설치 환경에서 graceful skip (오류 없이)
- **AC-7**: A-1 (Phase 13) 에서 도입된 testcontainers 패턴과 호환 유지
- **AC-8**: alembic 변경 없음 (`alembic heads` single head 유지)

---

## 2. 잔존 12 Skipped Tests 분류

### 2.1 카테고리별 현황

| 카테고리 | 건수 | 현재 skip 원인 | 해결 전략 |
|---------|:----:|--------------|----------|
| SES 메일 발송 | ~5건 | boto3 실제 SES 연결 필요 | LocalStack SES |
| Redis event loop | ~3건 | asyncio event loop 충돌 | testcontainers Redis + loop 처리 |
| OpenTelemetry SDK | ~2건 | otel SDK 미설치 | in-memory exporter 또는 env guard skip |
| 기타 외부 API | ~2건 | Stripe webhook 등 외부 의존 | LocalStack 또는 webhook signature mock |

### 2.2 카테고리 상세

#### 카테고리 1: SES 메일 발송 (~5건)

- 매직링크 발송 테스트 (`test_magic_link_send`)
- 이메일 인증 발송 테스트 (`test_email_verification_send`)
- 뉴스레터 발송 테스트 (`test_newsletter_broadcast`)
- 추가 SES 관련 2건 (정확한 이름은 구현 시 확인)

현재 skip 원인: `boto3.client("ses")` 호출 시 실제 AWS 자격증명 필요 → `NoCredentialsError` 또는 `EndpointResolutionError`.

해결: LocalStack SES 컨테이너를 `endpoint_url`로 주입.

#### 카테고리 2: Redis event loop 의존 (~3건)

- exchange rate 캐시 테스트 (`test_exchange_rate_cache`)
- ml_feed_inference Redis 캐시 테스트 (`test_ml_feed_cache`)
- 기타 Redis 비동기 테스트 1건

현재 skip 원인: pytest-asyncio event loop scope 충돌 — 기존 `@pytest.mark.asyncio` 데코레이터가 module scope Redis fixture와 충돌.

해결: testcontainers Redis fixture를 Phase 12 A-1 패턴과 동일하게 적용 + `asyncio_mode = "auto"` 설정 확인.

#### 카테고리 3: OpenTelemetry SDK (~2건)

- otel span 검증 테스트 (`test_otel_span_created`, `test_otel_trace_propagation`)

현재 skip 원인: `opentelemetry-sdk` 패키지 미설치 시 `ImportError`.

해결: in-memory exporter (`opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter`) 활용 또는 `OTEL_ENABLED` env guard로 graceful skip 유지. OTel SDK 설치 여부에 따라 < 3 허용.

#### 카테고리 4: 기타 외부 API (~2건)

- Stripe webhook signature 검증 테스트 등

현재 skip 원인: 외부 API 실제 호출 또는 서명 검증 키 필요.

해결: webhook signature mock (stripe-mock 또는 HMAC 직접 계산 fixture) 적용. LocalStack Stripe 지원 없으므로 mock 방식 유지.

---

## 3. LocalStack 통합 설계

### 3.1 의존성 추가

`v1/backend/pyproject.toml` 에 dev 의존성 추가:

```toml
[tool.poetry.group.dev.dependencies]
# 기존 Phase 12 A-1 의존성 유지
testcontainers = {version = "^4.0", extras = ["redis"]}
respx = "^0.21"
moto = {version = "^5.0", extras = ["ses", "s3"]}

# Phase 13 A-2 신규 추가
testcontainers-localstack = "^0.0.1"   # 또는 testcontainers[localstack]
localstack-client = "^2.5"             # boto3 endpoint override 유틸
boto3 = "^1.34"                        # SES/S3/Cognito 클라이언트
```

> **대안**: `testcontainers[localstack]` extras 방식이 패키지 안정성이 더 높으면 우선 채택.
> 실제 설치 시 `testcontainers` 버전과의 호환성 확인 후 결정.

### 3.2 환경 변수 Guard

```bash
# 로컬 개발 (LocalStack 활성화)
USE_LOCALSTACK=true pytest tests/

# CI GitHub Actions (자동 활성화)
# docker-in-docker 사용 가능하므로 USE_LOCALSTACK=true 기본값 설정
USE_LOCALSTACK=true

# macOS 또는 docker 미설치 환경
# USE_LOCALSTACK 미설정 → LocalStack 의존 tests graceful skip
```

### 3.3 conftest.py LocalStack Fixture

`v1/backend/tests/conftest.py` 확장 (기존 Phase 12 A-1 패턴 하단에 추가):

```python
import os
import boto3
import pytest
from testcontainers.localstack import LocalStackContainer

# ──────────────────────────────────────────────
# LocalStack 통합 Fixtures (Phase 13 A-2)
# ──────────────────────────────────────────────

USE_LOCALSTACK = os.getenv("USE_LOCALSTACK", "false").lower() == "true"

_localstack_skip = pytest.mark.skipif(
    not USE_LOCALSTACK,
    reason="LocalStack not enabled. Set USE_LOCALSTACK=true to run.",
)


@pytest.fixture(scope="session")
def localstack_container():
    """LocalStack 컨테이너 — session scope로 단일 기동 (시작 시간 ~30초 완화).

    활성화 조건: USE_LOCALSTACK=true
    제공 서비스: ses, s3, cognito-idp
    """
    if not USE_LOCALSTACK:
        pytest.skip("LocalStack disabled. Set USE_LOCALSTACK=true.")

    with LocalStackContainer(image="localstack/localstack:3") as ls:
        ls.with_services("ses", "s3", "cognito-idp")
        yield ls


@pytest.fixture
def aws_ses_client(localstack_container):
    """SES boto3 client → LocalStack endpoint 주입."""
    return boto3.client(
        "ses",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def aws_s3_client(localstack_container):
    """S3 boto3 client → LocalStack endpoint 주입."""
    return boto3.client(
        "s3",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture
def aws_cognito_client(localstack_container):
    """Cognito-idp boto3 client → LocalStack endpoint 주입."""
    return boto3.client(
        "cognito-idp",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@pytest.fixture(autouse=False)
def ses_verified_identity(aws_ses_client):
    """SES LocalStack: 발신자 이메일 도메인 사전 인증 (LocalStack은 verification 항상 통과)."""
    aws_ses_client.verify_email_identity(EmailAddress="noreply@domo.test")
    yield
    # cleanup 불필요 — session scope LocalStack 컨테이너 종료 시 자동 정리
```

### 3.4 docker-compose.test.yml (선택 — Compose 방식 대안)

testcontainers Python 라이브러리 방식이 충분하면 docker-compose.test.yml은 생략 가능.
필요 시 `v1/backend/tests/docker-compose.test.yml`:

```yaml
version: "3.9"
services:
  localstack:
    image: localstack/localstack:3
    environment:
      SERVICES: ses,s3,cognito-idp
      AWS_DEFAULT_REGION: us-east-1
      AWS_ACCESS_KEY_ID: test
      AWS_SECRET_ACCESS_KEY: test
      DEBUG: 0
    ports:
      - "4566:4566"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 5s
      timeout: 10s
      retries: 10
```

---

## 4. 12 Tests Refactor 매트릭스

### 4.1 전체 매트릭스

| 카테고리 | 건수 | Before | After | Fixture |
|---------|:----:|--------|-------|---------|
| SES 메일 발송 | ~5 | `@pytest.mark.skip` (boto3 no credentials) | LocalStack SES 직접 검증 | `aws_ses_client`, `ses_verified_identity` |
| Redis event loop | ~3 | `@pytest.mark.skip` (event loop 충돌) | testcontainers Redis (Phase 12 패턴) | `redis_container` (기존 재활용) |
| OTel SDK | ~2 | `@pytest.mark.skip` (ImportError) | in-memory exporter 또는 env guard | `InMemorySpanExporter` |
| 기타 (Stripe 등) | ~2 | `@pytest.mark.skip` (외부 API) | webhook signature mock | HMAC fixture |

### 4.2 카테고리 1: SES tests refactor

**Before** (현재 skip 상태):

```python
@pytest.mark.skip(reason="SES requires real AWS credentials")
async def test_magic_link_send(client, db_session):
    response = await client.post("/auth/magic-link", json={"email": "user@test.com"})
    assert response.status_code == 200
    # SES 발송 검증 불가
```

**After** (LocalStack SES 통합):

```python
@_localstack_skip
async def test_magic_link_send(client, db_session, aws_ses_client, ses_verified_identity):
    """매직링크 발송 테스트 — LocalStack SES 실제 수신 검증."""
    response = await client.post("/auth/magic-link", json={"email": "user@test.com"})
    assert response.status_code == 200

    # LocalStack SES에서 발송된 이메일 확인
    messages = aws_ses_client.list_messages()  # LocalStack 확장 API
    assert len(messages["Messages"]) == 1
    assert "magic" in messages["Messages"][0]["Subject"].lower()
```

> **주의**: `list_messages()` API는 LocalStack Pro 또는 Community 버전 확인 필요.
> Community 버전에서 미지원 시 `send_email` mock capture 방식으로 대체.

**Service 레이어 수정** — SES 클라이언트 endpoint 주입 지원:

```python
# v1/backend/app/services/email_service.py

import os
import boto3
from typing import Optional

class EmailService:
    def __init__(self, endpoint_url: Optional[str] = None):
        self._client = boto3.client(
            "ses",
            endpoint_url=endpoint_url or os.getenv("AWS_SES_ENDPOINT_URL"),
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )

    async def send_magic_link(self, email: str, token: str) -> None:
        self._client.send_email(
            Source="noreply@domo.test",
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": "Domo 매직링크"},
                "Body": {"Text": {"Data": f"링크: https://domo.app/auth/verify?token={token}"}},
            },
        )
```

`conftest.py` fixture에서 `EmailService(endpoint_url=localstack_url)` 주입.

### 4.3 카테고리 2: Redis event loop tests refactor

Phase 12 A-1에서 도입된 `redis_container` fixture를 재활용한다.

**Before** (event loop 충돌로 skip):

```python
@pytest.mark.skip(reason="redis event loop conflict in test env")
async def test_exchange_rate_cache(redis_client):
    await redis_client.set("exchange:USD:KRW", "1350")
    rate = await redis_client.get("exchange:USD:KRW")
    assert rate == b"1350"
```

**After** (testcontainers Redis, Phase 12 패턴 재활용):

```python
async def test_exchange_rate_cache(redis_container):
    """exchange rate Redis 캐시 — testcontainers Redis 재활용."""
    import redis.asyncio as aioredis

    redis_url = redis_container.get_connection_url()
    client = aioredis.from_url(redis_url)

    await client.set("exchange:USD:KRW", "1350", ex=3600)
    rate = await client.get("exchange:USD:KRW")
    assert rate == b"1350"

    await client.aclose()
```

**event loop 충돌 처리** — `pytest.ini` 또는 `pyproject.toml` 에 다음 설정 확인:

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

module scope fixture와 function scope test 간 event loop 불일치 발생 시:

```python
# conftest.py
import asyncio
import pytest

@pytest.fixture(scope="session")
def event_loop_policy():
    """session scope event loop policy — loop 재사용 충돌 방지."""
    policy = asyncio.DefaultEventLoopPolicy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
```

### 4.4 카테고리 3: OTel SDK tests refactor

**접근 A — in-memory exporter 활용** (권장, SDK 설치 시):

```python
# conftest.py
try:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

_otel_skip = pytest.mark.skipif(
    not OTEL_AVAILABLE,
    reason="opentelemetry-sdk not installed. Install to run OTel tests.",
)


@pytest.fixture
def in_memory_tracer():
    """in-memory span exporter — 실제 collector 없이 span 검증."""
    if not OTEL_AVAILABLE:
        pytest.skip("opentelemetry-sdk not available.")

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    yield provider, exporter

    exporter.clear()
```

**After** (in-memory exporter 사용):

```python
@_otel_skip
def test_otel_span_created(in_memory_tracer):
    """otel span 생성 검증 — in-memory exporter."""
    provider, exporter = in_memory_tracer
    tracer = provider.get_tracer("domo.test")

    with tracer.start_as_current_span("test_operation") as span:
        span.set_attribute("user.id", "user_123")

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_operation"
    assert spans[0].attributes["user.id"] == "user_123"
```

**접근 B — env guard graceful skip 유지** (SDK 미설치 시 허용):

OTel SDK 설치 여부가 환경마다 다를 수 있으므로 < 3 skip 허용 범위 내로 처리.
`@_otel_skip` 데코레이터로 명시적 skip → 원인 불명확한 오류 skip과 구분.

### 4.5 카테고리 4: 기타 외부 API tests refactor

**Stripe webhook signature mock**:

```python
# tests/fixtures/stripe_fixtures.py
import hashlib
import hmac
import time
import pytest

def generate_stripe_signature(payload: str, secret: str) -> str:
    """Stripe webhook signature 직접 계산 (실제 SDK 로직 재현)."""
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.fixture
def stripe_webhook_secret():
    return "whsec_test_secret_for_testing_only"


@pytest.fixture
def stripe_event_payload():
    return '{"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_test"}}}'
```

**After** (signature mock 활용):

```python
async def test_stripe_webhook_handler(
    client, stripe_webhook_secret, stripe_event_payload
):
    """Stripe webhook signature 검증 테스트 — HMAC mock."""
    sig = generate_stripe_signature(stripe_event_payload, stripe_webhook_secret)

    response = await client.post(
        "/webhooks/stripe",
        content=stripe_event_payload,
        headers={
            "stripe-signature": sig,
            "content-type": "application/json",
        },
    )
    assert response.status_code == 200
```

---

## 5. CI 영향 분석

### 5.1 GitHub Actions 설정

`.github/workflows/test.yml` 수정:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      # docker-in-docker는 ubuntu-latest에서 기본 지원
      # LocalStack은 testcontainers Python이 자동 기동
    env:
      USE_LOCALSTACK: "true"          # CI에서 자동 활성화
      USE_TESTCONTAINERS: "1"         # Phase 12 A-1 호환
      AWS_DEFAULT_REGION: "us-east-1"
      AWS_ACCESS_KEY_ID: "test"
      AWS_SECRET_ACCESS_KEY: "test"

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          cd v1/backend
          pip install poetry
          poetry install --with dev

      - name: Run tests (with LocalStack)
        run: |
          cd v1/backend
          poetry run pytest tests/ --tb=short -q
        timeout-minutes: 15   # LocalStack 시작 시간 고려 (+30초)
```

### 5.2 실행 시간 영향

| 시나리오 | 예상 추가 시간 | 완화 방법 |
|---------|:------------:|----------|
| LocalStack 컨테이너 초기화 | +25~35초 | session scope fixture (1회만 기동) |
| SES 이메일 발송 검증 | +2~5초/건 | 5건 기준 +10~25초 |
| testcontainers Redis (기존 A-1) | 기존 유지 | — |
| 전체 추가 시간 | **+1~2분** | session scope로 최소화 |

### 5.3 macOS 로컬 환경 (docker 미설치)

```bash
# docker 미설치 환경
USE_LOCALSTACK=false pytest tests/
# → LocalStack 의존 tests: graceful skip (오류 아님)
# → 나머지 tests: 정상 실행

# docker 설치 환경
USE_LOCALSTACK=true pytest tests/
# → 전체 실행
```

### 5.4 로컬 개발 단축 명령

`v1/backend/Makefile` 또는 `pyproject.toml` scripts 추가:

```makefile
# Makefile
test-full:
	USE_LOCALSTACK=true pytest tests/ --tb=short -q

test-fast:
	pytest tests/ --tb=short -q --ignore=tests/integration/
```

---

## 6. Test Plan

### 6.1 목표

| 지표 | 현재 | 목표 |
|------|:----:|:----:|
| skip count | 12건 | **0** (OTel 미설치 < 3 허용) |
| passed count | 750 | **+12 이상 (목표 762)** |
| 회귀 건수 | — | **0건** |

### 6.2 실행 순서

```
1단계: 의존성 설치 확인
  poetry install --with dev
  poetry run pip show testcontainers localstack-client boto3

2단계: LocalStack 단독 동작 확인 (conftest.py 단위)
  USE_LOCALSTACK=true pytest tests/conftest.py --co -q
  → localstack_container fixture 수집 확인

3단계: SES tests 실행
  USE_LOCALSTACK=true pytest tests/ -k "ses or email or magic_link" -v

4단계: Redis tests 실행
  USE_TESTCONTAINERS=1 pytest tests/ -k "cache or redis" -v

5단계: OTel tests 실행
  pytest tests/ -k "otel or span or trace" -v

6단계: 전체 실행 (회귀 확인)
  USE_LOCALSTACK=true USE_TESTCONTAINERS=1 pytest tests/ --tb=short -q

7단계: skip count 최종 확인
  USE_LOCALSTACK=true pytest tests/ --tb=short -q | grep -E "passed|skipped|failed"
```

### 6.3 성공 기준 체크리스트

```
[ ] AC-1: skip ≤ 2 (USE_LOCALSTACK=true, otel 미설치 환경 기준)
[ ] AC-2: SES list_messages() 또는 send_email mock 검증 동작
[ ] AC-3: Redis event loop 충돌 0건
[ ] AC-4: USE_LOCALSTACK 미설정 시 LocalStack tests graceful skip
[ ] AC-5: CI ubuntu-latest 자동 통과 (GitHub Actions)
[ ] AC-6: macOS docker 미설치 시 오류 없이 skip
[ ] AC-7: Phase 12 A-1 tests 회귀 0건 (기존 redis_container 호환)
[ ] AC-8: alembic heads single head 유지
```

---

## 7. 위임 Agent

### 7.1 bkend-expert 역할

이 sub-PDCA는 **bkend-expert** agent가 단독 위임 실행한다.

| 작업 | 파일 | 우선순위 |
|------|------|:-------:|
| pyproject.toml 의존성 추가 | `v1/backend/pyproject.toml` | 1 |
| conftest.py LocalStack fixture | `v1/backend/tests/conftest.py` | 1 |
| SES tests refactor (5건) | `tests/test_email_*.py` 등 | 2 |
| EmailService endpoint 주입 지원 | `app/services/email_service.py` | 2 |
| Redis tests refactor (3건) | `tests/test_cache_*.py` 등 | 2 |
| OTel in-memory exporter fixture | `tests/conftest.py` | 3 |
| Stripe webhook mock fixture | `tests/fixtures/stripe_fixtures.py` | 3 |
| CI workflow 수정 | `.github/workflows/test.yml` | 4 |
| Makefile 단축 명령 | `v1/backend/Makefile` | 5 |

### 7.2 위임 제약

- alembic 변경 없음 (데이터 모델 변경 0)
- A-1 (Phase 13) testcontainers 패턴 **호환 필수** — `redis_container` fixture 이름 및 인터페이스 유지
- OTel tests: SDK 미설치 시 < 3 skip 허용 (강제 설치 X)
- LocalStack Community 버전 기준 (`localstack/localstack:3`) — Pro 기능 의존 금지

---

## 8. 리스크 & Mitigation

| 리스크 | 영향 | 가능성 | Mitigation |
|--------|:----:|:------:|------------|
| LocalStack `list_messages()` Community 미지원 | 중 | 중간 | `send_email` call count mock으로 대체 |
| testcontainers LocalStack 이미지 pull 실패 (CI) | 높음 | 낮음 | retry 설정, 이미지 캐싱 (`actions/cache`) |
| event loop scope 불일치 (asyncio_mode 충돌) | 중 | 중간 | `asyncio_mode = "auto"` + session loop policy |
| OTel SDK 버전 불일치 | 낮음 | 낮음 | `OTEL_AVAILABLE` guard, < 3 skip 허용 범위 내 처리 |
| LocalStack 시작 시간 CI 타임아웃 | 중 | 중간 | `timeout-minutes: 15` + session scope 단일 기동 |
| A-1 기존 tests 회귀 | 높음 | 낮음 | A-2 시작 전 A-1 CI 통과 확인 후 진행 |

---

## 9. 관련 문서

- Phase 13 Roadmap: `/Users/sangincha/dev/domo/v1/docs/01-plan/features/domo-phase13-roadmap.plan.md`
- Phase 12 Archive: `/Users/sangincha/dev/domo/v1/docs/archive/2026-05/domo-phase12-roadmap/`
- A-1 Design (Phase 13): 별도 design 문서 참조 (tests-env-mock-refactor)

---

## 10. 버전 이력

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 0.1 | 2026-05-09 | 초기 작성. 잔존 12 tests 4개 카테고리 분류, LocalStack fixture 설계, CI 영향 분석. | itpe-ince (Claude Code, bkend-expert) |
