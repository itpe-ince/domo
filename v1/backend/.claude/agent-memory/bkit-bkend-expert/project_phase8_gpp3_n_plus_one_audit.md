---
name: Phase 8 G''-3 N+1 Audit
description: G''-3 완료: check_query_plans.sh 18쿼리 보강, db-perf.yml CI, 0059 3 indexes, 4 unit tests, db-performance.md
type: project
---

G''-3 n-plus-one-audit 완료 (2026-05-04).

**Why:** Phase 8 G'' 단계 DB 최적화 — D-6 EXPLAIN ANALYZE CI 통합 + N+1 audit.

**How to apply:** G'' 5개 sub-PDCA 병렬 중 하나. alembic 0059 → 0060(B'-1), 0061(B'-2) 충돌 없음.

## 산출물

- `.github/workflows/db-perf.yml` — PR마다 postgres:16 spin up + alembic + 18쿼리 EXPLAIN gate
- `v1/backend/scripts/check_query_plans.sh` — D-6 8쿼리 → 18쿼리 (Phase 6/7 +10)
- `v1/backend/scripts/perf_baseline.sh` — hey 부하테스트 p50/p95/p99 측정 (10 endpoints)
- `v1/backend/alembic/versions/0059_perf_indexes.py` — 3 신규 인덱스
- `v1/backend/tests/unit/test_query_optimization.py` — 4 unit tests
- `v1/docs/operations/db-performance.md` — N+1 audit 결과 + 인덱스 목록 + baseline 측정법

## N+1 Audit 결과

**발견된 N+1: 0건** — 코드베이스 전체가 이미 배치 fetch 패턴으로 구현됨.

핵심 패턴 (이미 적용됨):
- `selectinload(Post.media)` + `selectinload(Post.product)` — 모든 list 엔드포인트
- Batch author fetch: `{p.author_id for p in posts}` → 단일 User IN 쿼리
- `_attach_active_auction_end_at` — 단일 Auction IN 쿼리 (post당 1쿼리 X)
- `me_patronage` 전체 aggregate SQL only (per-row 0)

## alembic 0059 인덱스

신규 3개:
1. `ix_notifications_user_unread` — partial (is_read=false) → 뱃지 카운트 hot path
2. `ix_sponsorships_artist_status_created` — 아티스트 측 tier 자격 + winback cron
3. `ix_artist_interviews_status_created` — C-1 어드민 목록 sort

중복 발견 → 추가 안 함 (pre-existing):
- `idx_search_history_user_active` (0049)
- `ix_media_coverage_locale_published_at` (0057)
- `ix_newsletter_issues_status_locale` (0058)

## CI workflow 구조

```
PR → db-perf.yml → postgres:16 service → alembic upgrade head → 18쿼리 EXPLAIN → Seq Scan 발견시 PR 차단
```
