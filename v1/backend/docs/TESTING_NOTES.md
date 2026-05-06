# Testing Notes — Domo Backend

> 잔존 skipped 테스트 사유 명시 및 후속 진입 조건 정의.
> Phase 10 CO-1 PR-1 작성. 갱신일: 2026-05-05.

---

## 정책 원칙

- **과도한 mocking 금지**: 실제 DB 동작을 mock으로 대체하면 프로덕션 회귀를 발견하지 못한다. 통합 테스트는 실제 인프라(PostgreSQL, Redis, S3 등)가 CI에 구성되는 시점에 작성한다.
- **skip 허용 조건**: 외부 인프라 의존이 명확하고, 단위 테스트로 커버할 수 없는 경우에만 `@pytest.mark.skip`을 사용한다. skip 시 `reason` 인자에 사유와 해제 조건을 반드시 명시한다.
- **이월 원칙**: skip된 테스트는 해당 인프라가 CI에 구성되는 Phase에 일괄 활성화한다. 무기한 이월은 금지.

---

## 잔존 Skipped 테스트 목록

### 1. `tests/integration/test_personalized_feed.py:87`

**함수명**: `test_personalized_feed_v1_returns_scored_data`

**skip 사유**:
`_personalized_feed_v1` 내부에서 `Follow.followee_id == viewer_id` SQLAlchemy 조건을 사용한다.
Mock 세션으로는 ORM 표현식 비교가 실제 DB와 다르게 동작하여 follow 관계 필터링이 동작하지 않는다.
over-mocked 통합 테스트로, 현재 CI(SQLite in-memory) 환경에서 실행하면 항상 False를 반환하는 비신뢰 결과를 낸다.

**출처**: Phase 6 carry-over (post_engagement_cache PDCA)

**해제 조건**:
CI 파이프라인에 실제 PostgreSQL + pgvector 환경이 구성된 시점.
`DATABASE_URL=postgresql+asyncpg://...` 환경변수가 CI에 주입되고,
alembic 마이그레이션이 완전히 적용된 후 skip을 제거하고 실행 가능.

**이월 시점**: Phase 11 (CI PostgreSQL 환경 구성 예정)

---

### 2. FCM/APNs 실제 토큰 의존 테스트

**대상 파일**: `tests/unit/test_push_services.py`

**현황**:
현재 `test_push_services.py`의 5개 테스트는 모두 mock 모드(자격증명 미설정)에서의 동작을 검증하며,
실제 FCM/APNs 자격증명을 사용하는 end-to-end 전송 테스트는 아직 작성되지 않았다.

**skip 사유**:
- FCM: `FIREBASE_CREDENTIALS_JSON` 환경변수 미설정 시 `FCMService.is_mock = True`로 동작하므로 실제 Push 전송 불가
- APNs: `APNS_KEY_FILE` 환경변수 미설정 시 `APNsService.is_mock = True`로 동작
- 실 토큰(디바이스 등록 토큰) 없이는 전송 성공/실패를 검증할 수 없음

**해제 조건**:
staging 환경에서 실제 FCM 서비스 계정 자격증명(`FIREBASE_CREDENTIALS_JSON`)과
APNs 키 파일(`APNS_KEY_FILE`)이 CI secret으로 주입된 시점.
테스트 디바이스 등록 토큰도 별도 secret으로 관리 필요.

**이월 시점**: Phase 12 (staging CI 환경 구성, Push 서비스 실 테스트 대상)

---

### 3. S3 미디어 업로드 boto3 stub 테스트

**대상 파일**: `tests/unit/test_image_transform.py` 및 미디어 업로드 관련 통합 테스트

**현황**:
`test_image_transform.py`는 PIL in-memory 이미지를 사용하여 변환 로직만 검증하며,
실제 S3 업로드(boto3 `put_object` 호출) 경로는 단위 테스트에서 커버되지 않는다.
현재 미디어 업로드 API 통합 테스트는 S3 stub 없이 파일 경로 반환만 검증한다.

**skip 사유**:
- 실 S3 bucket access key(`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET`)가 CI에 미설정
- LocalStack 컨테이너가 CI에 미구성 (docker-compose 기반 CI 서비스 없음)
- boto3 stub(moto 라이브러리) 도입 전 실제 업로드 경로 검증 불가

**해제 조건**:
아래 중 하나가 CI에 구성된 시점:
1. LocalStack S3를 CI `services`로 추가 (`docker.io/localstack/localstack`)
2. `moto` 라이브러리 도입 후 `@mock_s3` 데코레이터로 boto3 stub 적용
3. 실제 AWS S3 테스트 bucket + CI secret 주입

**이월 시점**: Phase 11 (인프라 CI 구성 대상, LocalStack 또는 moto 도입)

---

---

## ml_experiments 보존 정책 (CO-1 PR-6 연계)

- 실험 종료 후 90일간 `ml_experiment_assignments` 원본 레코드 보존
- 90일 후: 집계 통계 요약(`ml_experiments.result_summary`) 후 원본 삭제
- 상세 정책: `v1/docs/operations/ml-experiments-policy.md` 참조
- Phase 11에서 scheduled cleanup cron 구현 예정

---

## 신규 테스트 추가 시 가이드

1. skip 없이 unit test로 작성 가능한 경우: mock/stub을 충분히 활용하여 단위 테스트 작성
2. 실 인프라가 필요한 경우: 위 목록에 항목을 추가하고 해제 조건을 명시한 후 Phase 이월
3. `@pytest.mark.skip(reason="...")` 사용 시 reason에 반드시 해제 조건과 이월 Phase 명시
4. 회귀 0 원칙: 기존 passed 테스트는 skip/xfail로 변경 금지
