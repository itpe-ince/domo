---
name: Phase 9 L-B External Content Booster
description: L-B 완료: alembic 0067, rss_fetch_jobs cron(13번째), og_scraper+LRU, newsletter tracking API 2종, inject_tracking, 11 tests
type: project
---

Phase 9 L-B 외부 콘텐츠 Booster 3종 완료. (2026-05-05)

**Why:** Phase 8 H'-4/H'-5에서 시간 부족으로 defer된 RSS auto-fetch(L-2), OG auto-thumbnail(L-3), Newsletter open rate tracking(L-4) 통합 구현.

**How to apply:** 이후 L-C(0068+0069), L-E(0070), L-F(0071+0072)는 0067 이후 chain. newsletter_events 테이블 및 inject_tracking 함수 재활용 가능.

## 생성/수정 파일

| 파일 | 역할 |
|------|------|
| `alembic/versions/0067_external_content_tracking.py` | external_feeds, external_articles, newsletter_events 3테이블 + 인덱스 |
| `app/services/rss_fetch_jobs.py` | RSS 수집 cron (13번째 worker), feedparser graceful fallback |
| `app/services/og_scraper.py` | OG 메타태그 스크래퍼, Redis 24h 캐시, in-process LRU 512 fallback |
| `app/services/newsletter_composer.py` | inject_tracking() 추가, urllib.parse import, get_settings import |
| `app/api/og.py` | POST /og/preview (로그인 필수, 캐시 조회, 504 타임아웃) |
| `app/api/newsletter_tracking.py` | GET /newsletter/track/open (1x1 PNG), GET /newsletter/track/click (302) |
| `app/main.py` | og_router + newsletter_tracking_router 등록, 13번째 rss_fetch_task, RSS_FETCH_WORKER_ENABLED guard |
| `tests/unit/test_rss_fetch_jobs.py` | 6 tests (mock모드, 정상수집, 중복skip, 작가매칭, 잘못된피드) |
| `tests/unit/test_og_scraper.py` | 4 tests (mock모드, OG추출, Redis hit, LRU fallback) |
| `tests/unit/test_newsletter_tracking.py` | 6 tests (pixel삽입, 링크변환, 내부URL skip, track_open, track_click, DB기록) |

## 주요 설계 결정

- alembic 0067 down_revision="0066_pgvector_embeddings"
- feedparser.parse()는 동기 → run_in_executor 처리
- newsletter tracking 엔드포인트는 인증 없음 (email client 직접 호출)
- inject_tracking의 user_id는 플레이스홀더 "{user_id}" — 발송 직전 치환
- 13번째 cron worker: RSS_FETCH_WORKER_ENABLED env guard (embedding 패턴 동일)
