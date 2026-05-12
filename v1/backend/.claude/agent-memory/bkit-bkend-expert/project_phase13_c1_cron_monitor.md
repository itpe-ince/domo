---
name: Phase 13 C-1 Cron Monitor
description: C-1 완료: Redis hash 기반 26개 cron worker 상태 추적, Slack overdue alert, admin API, frontend 모니터 페이지, 25개 cron worker 통합
type: project
---

Phase 13 C-1 admin-system-cron-monitor 완료.

**Why:** 운영 안정성 확보 — 26개 cron worker의 실행 상태를 Redis hash에 기록하고 /admin/system에서 실시간 모니터링.

**How to apply:** 새 cron worker 추가 시 WORKER_REGISTRY + WORKER_INTERVAL_LABELS에 등록하고 loop에 `_push_cron_status` 호출 추가.

## 주요 결정사항
- alembic 0089: 생략 (Redis hash TTL 1h 충분)
- overdue 기준: 5분(300초) 이상 미실행
- Slack alert: SLACK_WEBHOOK_URL env 미설정 시 graceful skip
- 26번째 worker: slack_alert (자기참조 OK)

## 파일 목록

### 신규 생성
- `/v1/backend/app/services/cron_monitor.py` — Redis hash 기록 + status 조회 (record_cron_run, get_all_cron_status, check_overdue_workers, track_cron)
- `/v1/backend/app/services/slack_alert_cron.py` — 26번째 worker, 1분 interval, Slack Block Kit webhook
- `/v1/backend/app/api/admin_system.py` — GET /admin/system/crons, GET /admin/system/crons/{name}
- `/v1/frontend/src/app/admin/system/page.tsx` — 26개 worker 상태 테이블, 30초 auto-refresh
- `/v1/backend/tests/unit/test_cron_monitor.py` — 10 tests
- `/v1/docs/02-design/features/domo-phase13-C-1.design.md`

### 수정 (25개 cron worker)
모든 cron_loop 함수에 `from app.services.cron_monitor import record_cron_run as _push_cron_status` 추가 + try/except 블록에 await 삽입:
- auction_jobs, gdpr_jobs, schedule_jobs, badge_jobs, settlement_jobs
- webhook_cleanup_jobs, draft_cleanup_jobs, tier_release_jobs, auction_promotion_jobs
- artist_index_jobs, post_engagement_jobs, subscription_expiry_jobs, newsletter_jobs
- exchange_rate_jobs, email_digest_jobs, auto_renewal_jobs, embedding_jobs
- rss_fetch_jobs, cohort_alert_jobs, ml_feed_training, artwork_caption_jobs
- featured_artist_jobs, ai_curation_jobs, audit_log_cleanup_jobs, audit_partition_cron

### main.py 변경
- `from app.services.slack_alert_cron import slack_alert_cron_loop` 추가
- `from app.api import admin_system as admin_system_router` 추가
- 26번째 task (slack_alert_task) 등록
- `api_v1.include_router(admin_system_router.router)` 추가

## Redis 스키마
```
key: cron:status:{worker_name}
fields: last_run_at, status, error_message, run_count
TTL: 3600초
```

## API
```
GET /admin/system/crons              → {workers: [...], summary: {...}}
GET /admin/system/crons/{worker_name} → single worker dict
```

## 테스트
- `tests/unit/test_cron_monitor.py` — 10 tests
- record_cron_run 정상/실패/Redis오류 케이스
- get_all_cron_status Redis mock/disabled
- check_overdue_workers 5분 임계값
- Slack alert 포맷 + graceful skip
- track_cron 데코레이터 success 경로
