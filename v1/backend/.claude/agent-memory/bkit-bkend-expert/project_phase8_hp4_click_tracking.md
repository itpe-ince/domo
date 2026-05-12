---
name: Phase 8 H'-4 Click Tracking RSS Thumbnail
description: H'-4 완료: MediaCoverage click tracking frontend+backend, 3 new tests (11 total). RSS+auto-thumbnail carry-over Phase 9+.
type: project
---

H'-4 click-tracking-rss-thumbnail 완료 (click tracking only; RSS+thumbnail carry-over).

**Why:** MediaCoverage C-4 프로덕션 후 click-through analytics 수집 필요. PostHog event에 url+source 추가해 funnel 분석 가능.

**How to apply:** 다음 단계에서 RSS auto-fetch(feedparser) 및 OG image scraping 구현 시 참고.

## 변경 파일

### Frontend
- `src/lib/analytics/events.ts` — `MediaCoverageClickEvent` 확장: `url`, `source` 필드 추가; `coverage_type` union에 `"podcast" | "tv"` 추가
- `src/components/stories/MediaCoverageGrid.tsx` — `handleClick` 에 `url`, `source` 전달; 불필요한 타입 캐스트 제거
- `src/components/users/UserMediaCoverage.tsx` — `captureEvent` import 추가; `handleClick` 구현; `<a>` onClick 연결

### Backend
- `app/api/media_coverage.py` — `POST /media-coverage/{id}/click` 추가 (60/min/IP rate limit, 200/404/422)
- `app/core/rate_limit.py` — `"media_coverage_click"` scope 추가 (60/min/IP)
- `tests/integration/test_media_coverage.py` — 3 tests 추가 (Test 9~11): 200, 404, 422 케이스. 8→11 tests.

## Carry-over
- RSS auto-fetch (`media_rss_jobs.py`, feedparser) → Phase 9+
- Auto-thumbnail OG scraping (httpx+BeautifulSoup) → Phase 9+
