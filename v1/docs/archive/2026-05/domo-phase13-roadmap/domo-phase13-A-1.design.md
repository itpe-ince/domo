# Design — Phase 13 A-1: GitHub OAuth + 매직링크 Tests Mock Refactor

**Feature**: phase13-A-1
**Created**: 2026-05-09
**Scope**: 12 skipped tests 정상화 (respx + factory_boy 패턴 통일)
**Alembic 변경**: 없음

---

## 1. 목표 & Acceptance Criteria

### 목표

Phase 12 C-2 implement 과정에서 외부 API 의존성 및 환경 설정 부재로 인해 skip 처리된
12개 통합 테스트를 respx (httpx mock) + factory_boy 패턴으로 정상화한다.

### Acceptance Criteria

| 항목 | 기준 |
|------|------|
| skipped tests | 12 → 0 (허용 최대: 2건 이하) |
| respx 통합 | GitHub OAuth API 전체 mock 완료 |
| factory_boy 확장 | `UserFactory`, `GoogleUserFactory`, `GitHubUserFactory` 구현 |
| 회귀 | 기존 통과 tests 0건 실패 |
| alembic | 변경 없음 |
| CI | respx 미설치 시 graceful skip (env guard 적용) |

---

## 2. 대상 Tests 목록

### 카테고리 1: GitHub OAuth (7건)

| # | 파일 | 테스트 함수 | 시나리오 |
|---|------|------------|---------|
| 1 | `tests/integration/test_auth_github_oauth.py` | `test_github_new_user_signup` | 신규 사용자 — GitHub ID 미존재, 이메일 미존재 → 계정 생성 |
| 2 | `tests/integration/test_auth_github_oauth.py` | `test_github_existing_google_account_merge` | 동일 이메일 Google 계정 존재 → github_id 병합 |
| 3 | `tests/integration/test_auth_github_oauth.py` | `test_github_email_conflict_password_account` | 동일 이메일 password 계정 존재 → 409 Conflict |
| 4 | `tests/integration/test_auth_github_oauth.py` | `test_github_admin_account_forbidden` | admin 그룹 계정 GitHub 로그인 시도 → 403 Forbidden |
| 5 | `tests/integration/test_auth_github_oauth.py` | `test_github_no_verified_email` | verified 이메일 없음 → 422 Unprocessable |
| 6 | `tests/integration/test_auth_github_oauth.py` | `test_github_invalid_code` | 잘못된 authorization code → token_exchange_failed |
| 7 | `tests/integration/test_auth_github_oauth.py` | `test_github_existing_user_by_github_id` | 동일 github_id 기존 사용자 → 로그인 성공 |

### 카테고리 2: 매직링크 (5건)

| # | 파일 | 테스트 함수 | 시나리오 |
|---|------|------------|---------|
| 8 | `tests/integration/test_auth_magic_link.py` | `test_magic_link_request_cooldown` | 60초 이내 재요청 → 429 Too Many Requests |
| 9 | `tests/integration/test_auth_magic_link.py` | `test_magic_link_verify_new_user_complete` | 유효 토큰 + 신규 이메일 → 계정 생성 + JWT 발급 |
| 10 | `tests/integration/test_auth_magic_link.py` | `test_magic_link_verify_expired` | 만료된 토큰 → 401 Unauthorized |
| 11 | `tests/integration/test_auth_magic_link.py` | `test_magic_link_verify_already_used` | 이미 사용된 토큰 → 401 Unauthorized |
| 12 | `tests/integration/test_auth_magic_link.py` | `test_magic_link_verify_invalid_token` | 존재하지 않는 토큰 → 401 Unauthorized |

---

## 3. respx 통합

### 3-1. 의존성 추가

`pyproject.toml` `[tool.poetry.dev-dependencies]` 또는 `[project.optional-dependencies]`:

```toml
[tool.poetry.dev-dependencies]
respx = "^0.21"
# 기존 항목 유지
pytest = "^8.0"
pytest-asyncio = "^0.24"
httpx = "^0.27"          # respx 요구사항 — 이미 존재 시 버전 확인
factory-boy = "^3.3"
freezegun = "^1.5"
```

> **graceful 처리**: CI 환경에서 respx 미설치 시 import 실패를 방지하기 위해
> `conftest.py`에 env guard를 적용한다 (아래 3-3 참조).

### 3-2. fixture 설계 — `tests/conftest.py`

```python
import os
import pytest

# respx graceful import guard
try:
    import respx
    import httpx as _httpx
    RESPX_AVAILABLE = True
except ImportError:
    RESPX_AVAILABLE = False


def _skip_if_no_respx():
    if not RESPX_AVAILABLE:
        pytest.skip("respx not installed — skip GitHub OAuth mock tests")


# ── GitHub OAuth mock fixture ──────────────────────────────────────────────
@pytest.fixture
def github_oauth_mock():
    """GitHub OAuth API 전체 mock.

    범위:
    - POST https://github.com/login/oauth/access_token
    - GET  https://api.github.com/user
    - GET  https://api.github.com/user/emails
    """
    _skip_if_no_respx()
    with respx.mock(assert_all_called=False) as router:
        # default 성공 응답 — 각 테스트에서 override 가능
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


# ── 매직링크 이메일 발송 mock fixture ─────────────────────────────────────
@pytest.fixture
def magic_link_email_mock(mocker):
    """magic_link service의 이메일 발송 함수를 mock.

    실제 SMTP/SendGrid 호출 없이 발송 성공 처리.
    반환값: mock 객체 (호출 여부 검증용)
    """
    mock_send = mocker.patch(
        "app.services.magic_link.send_magic_link_email",
        return_value=None,
    )
    return mock_send
```

### 3-3. 시나리오별 mock override 패턴

테스트 내에서 특정 시나리오를 재현해야 할 때 `github_oauth_mock` router를 직접 조작한다:

```python
# token_exchange 실패 시나리오 예시
def test_github_invalid_code(client, github_oauth_mock):
    github_oauth_mock.post(
        "https://github.com/login/oauth/access_token"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"error": "bad_verification_code"},  # GitHub 실제 오류 형식
        )
    )
    response = client.get("/api/v1/auth/github/callback?code=invalid_code&state=test")
    assert response.status_code == 400

# no verified email 시나리오
def test_github_no_verified_email(client, github_oauth_mock):
    github_oauth_mock.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200,
            json=[{"email": "private@users.noreply.github.com", "primary": True, "verified": False}],
        )
    )
    response = client.get("/api/v1/auth/github/callback?code=valid_code&state=test")
    assert response.status_code == 422
```

---

## 4. 12 Tests Refactor 매트릭스

### 4-1. GitHub OAuth Tests

각 테스트 공통 전제:
- `monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")`
- `monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")`
- `github_oauth_mock` fixture 주입

| # | 테스트 함수 | mock 설정 | DB 사전 조건 | 검증 포인트 |
|---|------------|-----------|------------|------------|
| 1 | `test_github_new_user_signup` | default mock (정상 응답) | users 테이블 비어있음 | status 200, JWT 발급, users에 신규 row 존재, sns_provider="github" |
| 2 | `test_github_existing_google_account_merge` | default mock, email=기존 Google 계정 email | `GoogleUserFactory` 로 기존 사용자 생성 | status 200, 기존 user row의 github_id 업데이트 확인 |
| 3 | `test_github_email_conflict_password_account` | default mock, email=기존 password 계정 email | password 계정 users row 생성 (sns_provider=None) | status 409, error code "email_conflict" |
| 4 | `test_github_admin_account_forbidden` | default mock, email=admin 계정 email | admin 그룹 users row 생성 | status 403, error code "admin_forbidden" |
| 5 | `test_github_no_verified_email` | `/user/emails` → verified=False 목록 반환 | 없음 | status 422, error code "no_verified_email" |
| 6 | `test_github_invalid_code` | `/access_token` → `{"error": "bad_verification_code"}` 반환 | 없음 | status 400, error code "token_exchange_failed" |
| 7 | `test_github_existing_user_by_github_id` | default mock, github_id=12345 | `GitHubUserFactory(github_id=12345)` 로 기존 사용자 생성 | status 200, JWT 발급, users row 신규 생성 없음 |

### 4-2. 매직링크 Tests

각 테스트 공통 전제:
- `magic_link_email_mock` fixture 주입
- `real_db_session` (또는 `db_session`) fixture로 DB 직접 조작

| # | 테스트 함수 | mock 설정 | DB 사전 조건 | 검증 포인트 |
|---|------------|-----------|------------|------------|
| 8 | `test_magic_link_request_cooldown` | `magic_link_email_mock` | magic_link_tokens에 60초 미만 요청 row 삽입 | status 429, `Retry-After` 헤더 존재 |
| 9 | `test_magic_link_verify_new_user_complete` | `magic_link_email_mock` | 유효한 token row 삽입 (expires_at=미래, used_at=None) | status 200, JWT 발급, users 신규 row 생성, token used_at 업데이트 |
| 10 | `test_magic_link_verify_expired` | — | expires_at=과거 token row 삽입 (freezegun 활용) | status 401, error code "token_expired" |
| 11 | `test_magic_link_verify_already_used` | — | used_at != None token row 삽입 | status 401, error code "token_already_used" |
| 12 | `test_magic_link_verify_invalid_token` | — | 해당 token 없음 (빈 테이블) | status 401, error code "token_not_found" |

### 4-3. 매직링크 freezegun 활용 패턴

```python
from freezegun import freeze_time
from datetime import datetime, timedelta, timezone

def test_magic_link_verify_expired(client, db_session):
    token_value = "expired_token_abc123"
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=30)

    # DB에 만료된 토큰 삽입
    db_session.execute(
        "INSERT INTO magic_link_tokens (token, email, expires_at) VALUES (:t, :e, :ex)",
        {"t": token_value, "e": "user@example.com", "ex": expired_at},
    )
    db_session.commit()

    response = client.post("/api/v1/auth/magic-link/verify", json={"token": token_value})
    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"
```

---

## 5. UserFactory 확장

### 5-1. `tests/factories.py` 전체 구조

```python
import factory
from factory import Faker, Sequence, LazyAttribute
from app.models.user import User  # 실제 모델 import 경로에 맞게 조정


class UserFactory(factory.Factory):
    """기본 사용자 Factory — email/password 계정."""

    class Meta:
        model = User

    email = Faker("email")
    display_name = Sequence(lambda n: f"user_{n}")
    avatar_url = ""
    bio = ""
    country_code = "KR"
    sns_provider = None          # password 계정
    password_hash = None
    email_verified = False
    github_id = None
    is_admin = False


class GoogleUserFactory(UserFactory):
    """Google OAuth 사용자 Factory."""

    sns_provider = "google"
    email_verified = True        # Google은 verified 보장
    github_id = None


class GitHubUserFactory(UserFactory):
    """GitHub OAuth 사용자 Factory."""

    sns_provider = "github"
    email_verified = True        # GitHub verified email 보장
    github_id = Sequence(lambda n: 10000 + n)
```

### 5-2. Factory 사용 예시

```python
# tests/integration/test_auth_github_oauth.py

from tests.factories import GitHubUserFactory, GoogleUserFactory, UserFactory


def test_github_existing_user_by_github_id(client, db_session, github_oauth_mock):
    # github_id=12345로 기존 사용자 생성
    existing_user = GitHubUserFactory(github_id=12345, email="test@github.local")
    db_session.add(existing_user)
    db_session.commit()

    response = client.get("/api/v1/auth/github/callback?code=valid_code&state=test")
    assert response.status_code == 200
    assert "access_token" in response.json()

    # 신규 row 생성 없음 확인
    user_count = db_session.query(User).count()
    assert user_count == 1


def test_github_existing_google_account_merge(client, db_session, github_oauth_mock):
    # 동일 이메일 Google 계정
    existing_user = GoogleUserFactory(email="test@github.local")
    db_session.add(existing_user)
    db_session.commit()

    response = client.get("/api/v1/auth/github/callback?code=valid_code&state=test")
    assert response.status_code == 200

    # github_id 병합 확인
    db_session.refresh(existing_user)
    assert existing_user.github_id == 12345  # mock 기본 github_id
```

---

## 6. CI 영향

### 6-1. respx 미설치 graceful skip

```python
# tests/conftest.py — env guard (위 3-2 참조)
try:
    import respx
    RESPX_AVAILABLE = True
except ImportError:
    RESPX_AVAILABLE = False

# GitHub OAuth 관련 fixture 내부에서 호출
def _skip_if_no_respx():
    if not RESPX_AVAILABLE:
        pytest.skip("respx not installed")
```

CI `pyproject.toml`에 respx 추가 후에는 skip 발생하지 않음. 로컬 환경 호환성 유지 목적.

### 6-2. testcontainers 불필요

respx는 httpx 레이어를 mock하므로 외부 서버 컨테이너 불필요.
기존 `pytest-asyncio` + `real_db_session` 조합과 충돌 없음.

### 6-3. 환경 변수 격리

`monkeypatch.setenv` 활용으로 테스트 간 환경 변수 오염 방지:

```python
@pytest.fixture(autouse=False)
def github_env(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")
```

### 6-4. CI 파이프라인 명령

```bash
# 설치
poetry install --with dev

# 실행 (skipped 0 목표 확인)
pytest tests/integration/test_auth_github_oauth.py \
       tests/integration/test_auth_magic_link.py \
       -v --tb=short

# 전체 회귀 검증
pytest tests/ -v --tb=short -q
```

---

## 7. Test Plan

### 7-1. 목표 지표

| 지표 | Before | After |
|------|--------|-------|
| skipped | 12 | 0 (허용 최대 2) |
| passed | N (기존) | N + 12 |
| failed | 0 | 0 |
| 회귀 | — | 0 |

### 7-2. 검증 순서

1. `pyproject.toml` respx 추가 후 `poetry install --with dev`
2. `tests/conftest.py` — `github_oauth_mock`, `magic_link_email_mock` fixture 추가
3. `tests/factories.py` — `GitHubUserFactory`, `GoogleUserFactory` 추가/확장
4. GitHub OAuth 7건 skip 제거 + mock 적용 후 개별 실행 확인
5. 매직링크 5건 skip 제거 + fixture 적용 후 개별 실행 확인
6. `pytest tests/` 전체 실행 — 회귀 0건 확인

### 7-3. 시나리오별 검증 포인트

#### GitHub OAuth

```
test_github_new_user_signup
  ✓ HTTP 200
  ✓ access_token, refresh_token 포함
  ✓ DB users에 sns_provider="github" row 생성
  ✓ github_id=12345 저장

test_github_existing_google_account_merge
  ✓ HTTP 200
  ✓ users row 추가 생성 없음 (count 동일)
  ✓ 기존 row.github_id = 12345 업데이트

test_github_email_conflict_password_account
  ✓ HTTP 409
  ✓ body.code = "email_conflict"

test_github_admin_account_forbidden
  ✓ HTTP 403
  ✓ body.code = "admin_forbidden"

test_github_no_verified_email
  ✓ HTTP 422
  ✓ body.code = "no_verified_email"

test_github_invalid_code
  ✓ HTTP 400
  ✓ body.code = "token_exchange_failed"

test_github_existing_user_by_github_id
  ✓ HTTP 200
  ✓ JWT 발급
  ✓ users count 변화 없음
```

#### 매직링크

```
test_magic_link_request_cooldown
  ✓ HTTP 429
  ✓ Retry-After 헤더 존재

test_magic_link_verify_new_user_complete
  ✓ HTTP 200
  ✓ access_token 포함
  ✓ users 신규 row 생성
  ✓ magic_link_tokens.used_at != None

test_magic_link_verify_expired
  ✓ HTTP 401
  ✓ body.code = "token_expired"

test_magic_link_verify_already_used
  ✓ HTTP 401
  ✓ body.code = "token_already_used"

test_magic_link_verify_invalid_token
  ✓ HTTP 401
  ✓ body.code = "token_not_found"
```

---

## 8. 위임 Agent

### bkend-expert 작업 범위

| 파일 | 작업 내용 |
|------|---------|
| `pyproject.toml` | `respx = "^0.21"` dev dependency 추가 |
| `tests/conftest.py` | `github_oauth_mock`, `magic_link_email_mock` fixture 추가, graceful import guard |
| `tests/factories.py` | `UserFactory`, `GoogleUserFactory`, `GitHubUserFactory` 추가/확장 |
| `tests/integration/test_auth_github_oauth.py` | 7개 tests skip 제거, mock fixture 주입, 시나리오별 응답 차별화 |
| `tests/integration/test_auth_magic_link.py` | 5개 tests skip 제거, DB fixture 조작, freezegun 적용 |

### 작업 순서

```
1. pyproject.toml respx 추가
2. tests/factories.py UserFactory 확장
3. tests/conftest.py fixture 추가
4. test_auth_github_oauth.py 7건 refactor
5. test_auth_magic_link.py 5건 refactor
6. pytest 전체 실행 — 0 skipped 확인
```

---

## 9. 비고

- **alembic 변경 없음**: DB 스키마 변경 불필요. 기존 `magic_link_tokens`, `users` 테이블 그대로 사용.
- **respx 버전**: `^0.21` — httpx `^0.27`과 호환 확인 필요. 충돌 시 `^0.20`으로 fallback.
- **freezegun**: 매직링크 만료 시나리오에서 `datetime.now()` 조작 용도로만 사용. 기존 설치 여부 확인 후 신규 추가.
- **factory_boy SQLAlchemy 연동**: `factory.alchemy.SQLAlchemyModelFactory` 사용 시 `Meta.sqlalchemy_session` 설정 필요. 현재 구조에 맞게 조정.
