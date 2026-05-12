---
name: Phase 8 G''-1 OpenTelemetry Tracing
description: G''-1 완료: OTel SDK 통합, 8 cron worker manual span, 5 critical op span, G'-4 trace_id booster, 4 tests, opentelemetry.md ops guide
type: project
---

G''-1 opentelemetry-tracing 완료 (Phase 8 Wave 1, 2026-05-04).

**Baseline**: 311 tests passing, alembic 0058 head.

## 신규/수정 파일

### Backend
- `pyproject.toml` (수정) — 6 OTel 패키지 추가
- `app/core/config.py` (수정) — 4 OTEL settings (otel_enabled, otel_service_name, otel_otlp_endpoint, otel_sampling_rate)
- `app/services/otel_setup.py` (신규 ~160 LOC) — init_otel/shutdown_otel/get_tracer helpers
- `app/main.py` (수정) — lifespan에 init_otel(app, engine) + shutdown_otel() 추가
- `app/services/analytics.py` (수정) — _inject_trace_id() G'-4 booster, capture_event에 trace_id 자동 주입
- 8 cron worker (수정) — manual span + tracer import:
  - auction_jobs.py: `cron.auction` span (rows_processed, expired_orders, second_chance_offered)
  - auction_promotion_jobs.py: `cron.auction_promotion` span + `pillow.generate_share_card` span
  - tier_release_jobs.py: `cron.tier_release` span
  - schedule_jobs.py: `cron.schedule` span
  - artist_index_jobs.py: `cron.artist_index` span (artists_ranked)
  - subscription_expiry_jobs.py: `cron.subscription_expiry` span (notifications_created)
  - post_engagement_jobs.py: `cron.post_engagement` (tracer import)
  - newsletter_jobs.py: `cron.newsletter` span (issues_processed)
- Critical operation spans:
  - app/api/posts.py: `feed.personalized_v1` span (user_id, has_cursor, limit)
  - app/services/press_kit_generator.py: `press_kit.generate` span
  - app/services/newsletter_composer.py: `newsletter.compose_issue` span
  - app/services/llm_gateway.py: `llm.generate_interview` span (model, max_tokens, usage_tokens)
- `tests/unit/test_otel_setup.py` (신규 ~200 LOC) — 6 tests (init mock/real, shutdown graceful/noop, trace_id inject/no-inject)

### Docs
- `v1/docs/operations/opentelemetry.md` (신규) — AWS X-Ray production deployment guide (ECS task def, ADOT config, IAM, sampling policy, PII policy, manual span table)

## 주요 설계 결정

**Mock mode 패턴**: OTEL_ENABLED=False 시 opentelemetry.sdk import 자체를 건너뜀 → cold-start 빠름. get_tracer()는 opentelemetry-api의 NoOpTracer를 반환 → start_as_current_span() calls zero overhead.

**Inner function 패턴**: generate_press_kit, compose_issue, _generate_share_card, generate_interview — span wrapper + _inner 함수로 분리. public API 시그니처 불변.

**G'-4 booster**: _inject_trace_id()가 opentelemetry.trace.get_current_span() 호출 → trace_id != 0 이면 PostHog props에 "trace_id" 32자 hex 주입. X-Ray ↔ PostHog 상관관계 활성화.

**R-5 격리 유지**: 각 cron worker는 여전히 별도 AsyncSessionLocal + 별도 Prometheus label. OTel span만 추가.

**PII**: span attributes에 email/phone 절대 금지. user_id (UUID string), auction_id, artist_id만 허용.

## AWS X-Ray 배포 (carry-over → Phase 9 ops)
- ECS Fargate task definition에 ADOT Collector sidecar 추가
- IAM: xray:PutTraceSegments + xray:PutTelemetryRecords
- OTEL_OTLP_ENDPOINT=localhost:4317
- Sampling: staging 100%, production 10%

**Why:** OQ-4=B (AWS X-Ray) Phase 8 plan에 포함. 실제 AWS 인프라 배포는 Phase 9 ops PDCA에서 처리.
**How to apply:** G''-1 코드 통합 완료. Phase 9에서 ECS task def + IAM role만 추가하면 즉시 활성화.
