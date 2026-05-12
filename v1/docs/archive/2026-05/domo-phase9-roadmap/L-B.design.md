---
template: design
version: 1.0
feature: domo-phase9-L-B (외부 콘텐츠 Booster 3종)
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_plan: v1/docs/01-plan/features/domo-phase9-roadmap.plan.md § L-B
status: Draft
---

# Phase 9 L-B Design — 외부 콘텐츠 Booster 3종

> **Summary**: Phase 8 H'-4/H'-5에서 시간 부족으로 defer된 외부 콘텐츠 booster 3종을 통합 구현한다.
> RSS auto-fetch(L-2), OG auto-thumbnail scraping(L-3), Newsletter open rate tracking(L-4).
> 모든 외부 호출은 Mock 모드 fallback을 가지며, alembic 0067 마이그레이션 하나로 통합한다.

---

## 1. 목표 & Acceptance Criteria

### 목표

| 워크스트림 | Phase 8 상태 | L-B 목표 |
|-----------|:----------:|---------|
| L-2 RSS auto-fetch | defer (시간 부족) | 외부 매체 기사 자동 수집 + 작가 매칭 cron |
| L-3 OG auto-thumbnail | H'-4 91% → 목표 95% | 우선순위 fallback 체계 + Redis 24h 캐시 |
| L-4 Newsletter open rate | H'-5에서 defer | 1x1 픽셀 + 클릭 트래킹 + newsletter_composer 통합 |

### Acceptance Criteria

**L-2 RSS auto-fetch**
- [ ] `external_feeds` + `external_articles` 테이블 생성 (alembic 0067 green)
- [ ] `rss_fetch_jobs.py` cron 1시간 주기로 정상 실행
- [ ] feedparser 미설치 환경에서 graceful fail (ImportError 캐치 후 로그만)
- [ ] 기사 → 작가 자동 매칭 (artist name 포함 시 `artist_id` 연결)
- [ ] 5개 이상 source 등록 후 수집 성공률 ≥ 95%

**L-3 OG auto-thumbnail**
- [ ] `POST /api/og/preview` 엔드포인트 정상 응답 (≤ 3초)
- [ ] OG 추출 우선순위: `og:image` → `twitter:image` → `first_img` → `default_thumbnail`
- [ ] Redis 연결 시 동일 URL 24시간 캐시 (두 번째 호출 ≤ 50ms)
- [ ] Redis 미연결 환경에서 캐시 없이 정상 동작 (메모리 fallback)
- [ ] httpx / beautifulsoup 미설치 시 `{"title": null, "image_url": null}` 반환

**L-4 Newsletter open rate tracking**
- [ ] `newsletter_events` 테이블 생성 (alembic 0067 포함)
- [ ] `GET /api/newsletter/track/open?issue={id}&user={id}` → 1x1 PNG + DB 이벤트 저장
- [ ] `GET /api/newsletter/track/click?issue={id}&user={id}&url={encoded}` → 302 redirect + 이벤트 저장
- [ ] `newsletter_composer.py`의 `compose_issue()` 수정 — HTML 본문에 트래킹 픽셀/링크 자동 삽입
- [ ] 중복 open 이벤트 허용 (Gmail pre-fetch 포함), click은 HMAC 서명 검증

---

## 2. Database Schema — alembic 0067

3 워크스트림을 단일 마이그레이션으로 통합한다. L-A(0066) 직후 적용.

### 2-1. L-2 RSS 관련 테이블

```sql
-- external_feeds: 수집 대상 RSS 소스 등록
CREATE TABLE external_feeds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url  TEXT NOT NULL UNIQUE,          -- RSS endpoint URL
    source_name TEXT NOT NULL,                 -- 표시 이름 (예: "Hypebeast Korea")
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    fetch_interval_hours INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- external_articles: 수집된 기사
CREATE TABLE external_articles (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feed_id      UUID NOT NULL REFERENCES external_feeds(id) ON DELETE CASCADE,
    url          TEXT NOT NULL UNIQUE,          -- 기사 원문 URL
    title        TEXT NOT NULL,
    summary      TEXT,                          -- RSS description 또는 OG description
    published_at TIMESTAMPTZ,
    artist_id    UUID REFERENCES users(id),     -- 자동 매칭 결과 (nullable)
    match_confidence FLOAT,                     -- 매칭 신뢰도 0.0~1.0
    is_approved  BOOLEAN NOT NULL DEFAULT FALSE, -- admin 승인 큐
    og_image_url TEXT,                          -- OG thumbnail (L-3 연동)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_external_articles_feed_id ON external_articles(feed_id);
CREATE INDEX ix_external_articles_artist_id ON external_articles(artist_id)
    WHERE artist_id IS NOT NULL;
CREATE INDEX ix_external_articles_published_at ON external_articles(published_at DESC);
```

### 2-2. L-4 Newsletter Events 테이블

```sql
-- newsletter_events: open / click 이벤트 로그
CREATE TABLE newsletter_events (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id   UUID NOT NULL REFERENCES newsletter_issues(id) ON DELETE CASCADE,
    user_id    UUID REFERENCES users(id) ON DELETE SET NULL,  -- 탈퇴 시 NULL 유지
    event_type TEXT NOT NULL CHECK (event_type IN ('open', 'click')),
    url        TEXT,                            -- click 이벤트 시 원본 URL
    user_agent TEXT,
    ip_hash    TEXT,                            -- IP SHA-256 (GDPR 준수)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_newsletter_events_issue_id ON newsletter_events(issue_id);
CREATE INDEX ix_newsletter_events_user_id ON newsletter_events(user_id)
    WHERE user_id IS NOT NULL;
CREATE INDEX ix_newsletter_events_event_type ON newsletter_events(event_type, created_at DESC);
```

### 2-3. OG Cache (L-3)

별도 테이블 없음. Redis key 구조: `og:cache:{sha256(url)}` (TTL 86400s).
Redis 미연결 시 in-process LRU 캐시(512 entries)로 fallback.

---

## 3. Service Layer

### 3-1. L-2 RSS — `app/services/rss_fetch_jobs.py`

기존 cron 패턴(`draft_cleanup_jobs.py` 참조)을 따른다. R-5 격리 원칙에 따라 단독 cron worker로 분리.

```
rss_fetch_jobs.py
  └─ fetch_all_feeds(db) — 활성 feed 전체 순회
       └─ fetch_single_feed(db, feed) — feedparser로 항목 파싱
            └─ upsert_article(db, feed_id, entry) — 중복 URL skip
                 └─ match_artist(db, article) — 작가 자동 매칭
```

**주요 로직**

```python
# feedparser Mock fallback
try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False
    log.warning("feedparser not installed — RSS fetch disabled (Mock mode)")

async def fetch_all_feeds(db: AsyncSession) -> dict:
    if not _FEEDPARSER_AVAILABLE:
        return {"skipped": True, "reason": "feedparser_not_installed"}
    feeds = await _get_active_feeds(db)
    results = []
    for feed in feeds:
        result = await fetch_single_feed(db, feed)
        results.append(result)
    return {"processed": len(results), "results": results}
```

**작가 자동 매칭 전략**

1. `display_name` 키워드 검색 (대소문자 무시, 공백 정규화)
2. 매칭 후보 여러 명이면 `match_confidence`가 가장 높은 1명만 연결
3. LLM 매칭은 선택 옵션 (환경변수 `LLM_ARTIST_MATCH_ENABLED=true`일 때만 활성화)
4. `match_confidence` 0.7 미만이면 `artist_id = NULL` (admin 수동 확인)

**cron 등록 (`app/main.py` 또는 scheduler 모듈)**

```python
# 1시간 주기
scheduler.add_job(run_rss_fetch, "interval", hours=1, id="rss_fetch")
```

---

### 3-2. L-3 OG Scraping — `app/services/og_scraper.py`

**의존성 Mock fallback**

```python
try:
    import httpx
    from bs4 import BeautifulSoup
    _OG_AVAILABLE = True
except ImportError:
    _OG_AVAILABLE = False
    log.warning("httpx/beautifulsoup not installed — OG scraping in mock mode")
```

**추출 우선순위 체계**

| 순위 | 소스 | 속성 |
|:---:|------|-----|
| 1 | Open Graph | `og:image` |
| 2 | Twitter Card | `twitter:image` |
| 3 | 첫 번째 이미지 | `<img src>` ≥ 100×100px 추정 |
| 4 | 기본 썸네일 | `/static/og-default.png` |

**캐시 레이어**

```python
async def scrape_og(url: str, redis=None) -> OGData:
    cache_key = f"og:cache:{hashlib.sha256(url.encode()).hexdigest()}"

    # Redis 캐시 확인
    if redis:
        cached = await redis.get(cache_key)
        if cached:
            return OGData.model_validate_json(cached)

    # Mock 모드 fallback
    if not _OG_AVAILABLE:
        return OGData(title=None, description=None, image_url=None, site_name=None)

    # 실제 스크래핑
    result = await _scrape_with_httpx(url)

    # 캐시 저장 (24시간)
    if redis:
        await redis.setex(cache_key, 86400, result.model_dump_json())
    else:
        _LOCAL_CACHE[cache_key] = result  # in-process LRU fallback

    return result
```

**응답 스키마**

```python
class OGData(BaseModel):
    title: str | None
    description: str | None
    image_url: str | None
    site_name: str | None
```

---

### 3-3. L-4 Newsletter Tracking — `newsletter_composer.py` 수정

기존 `compose_issue()` → `_build_markdown()` → `md_to_html()` 흐름에서
HTML 변환 이후 트래킹 요소를 삽입한다. Markdown 단계에서는 건드리지 않는다.

**수정 위치**: `_compose_issue_inner()` 내 `html = md_to_html(md)` 라인 이후

```python
# 트래킹 픽셀 + 링크 주입
html = _inject_tracking(html, issue_id=str(issue.id_placeholder))
```

**`_inject_tracking()` 구현**

```python
BASE_URL = settings.APP_BASE_URL  # 예: https://domo.art

def _inject_tracking(html: str, issue_id: str, user_id: str = "") -> str:
    """HTML 본문에 open tracking 픽셀과 click tracking wrapper를 삽입."""
    # 1x1 open pixel: </body> 직전 삽입
    pixel_url = f"{BASE_URL}/api/newsletter/track/open?issue={issue_id}&user={{user_id}}"
    pixel_tag = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none"/>'

    # click tracking: <a href="..."> → <a href="/api/newsletter/track/click?...">
    def _wrap_link(match):
        original_url = match.group(2)
        # Domo 내부 링크는 skip (이중 redirect 방지)
        if original_url.startswith(BASE_URL) or original_url.startswith("/api/"):
            return match.group(0)
        encoded = urllib.parse.quote(original_url, safe="")
        track_url = (
            f"{BASE_URL}/api/newsletter/track/click"
            f"?issue={issue_id}&user={{user_id}}&url={encoded}"
        )
        return f'<a href="{track_url}">{match.group(1)}</a>'

    html = re.sub(r'<a href="([^"]+)">([^<]+)</a>', _wrap_link, html)

    # pixel 삽입
    if "</body>" in html:
        html = html.replace("</body>", f"{pixel_tag}</body>")
    else:
        html += pixel_tag

    return html
```

**참고**: `user_id`는 실제 발송 시점(C-5 newsletter_dispatcher)에서 per-subscriber로 치환한다.
`compose_issue()` 단계에서는 `{user_id}` 플레이스홀더를 그대로 두고, 발송 직전에 문자열 치환.

---

## 4. API Endpoints

### 4-1. L-3 OG Preview

```
POST /api/og/preview
Content-Type: application/json
Authorization: Bearer {token}  (인증 선택 — guest도 허용 가능)

Request:
{ "url": "https://example.com/article" }

Response 200:
{
  "title": "작품 제목",
  "description": "기사 요약...",
  "image_url": "https://example.com/thumbnail.jpg",
  "site_name": "Hypebeast Korea",
  "cached": false
}

Response 422: URL 형식 오류
Response 504: 외부 사이트 타임아웃 (httpx timeout 5s)
```

**라우터 등록**: `app/api/og.py` → `app/main.py`에 include

### 4-2. L-4 Newsletter Open Tracking

```
GET /api/newsletter/track/open?issue={issue_id}&user={user_id}

Response 200:
Content-Type: image/png
[1x1 투명 PNG 바이너리]

사이드이펙트: newsletter_events INSERT (event_type='open')
인증 불필요 (email client에서 직접 호출)
```

### 4-3. L-4 Newsletter Click Tracking

```
GET /api/newsletter/track/click?issue={issue_id}&user={user_id}&url={encoded_url}

Response 302:
Location: {decoded original url}

사이드이펙트: newsletter_events INSERT (event_type='click', url=decoded_url)
인증 불필요
```

**1x1 PNG 상수** (17 bytes — 최소 투명 PNG):

```python
_TRANSPARENT_1X1_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    # ... (표준 1x1 투명 PNG 바이트열)
])
```

실제 구현 시 파이썬 표준 `struct` 로 생성하거나 리터럴 바이트열 사용.

---

## 5. Frontend Changes

### 5-1. OG 미리보기 UI (포스트 에디터)

**대상 파일**: `v1/frontend/src/app/posts/new/page.tsx` (또는 PostEditor 컴포넌트)

**동작 흐름**:

1. 사용자가 에디터 본문에 URL 입력 (정규식: `https?://[^\s]+`)
2. Debounce 800ms 후 `POST /api/og/preview` 호출
3. 응답 수신 시 에디터 하단에 OG 카드 미리보기 렌더링
4. 사용자가 "첨부" 버튼 클릭 시 `og_preview` 필드에 데이터 저장

**OG 카드 UI 스펙** (Tailwind):

```tsx
// OGPreviewCard.tsx (신규 컴포넌트)
interface OGPreviewCardProps {
  title: string | null
  description: string | null
  imageUrl: string | null
  siteName: string | null
  url: string
  onDismiss: () => void
}
```

- 썸네일 이미지: 좌측 80×80px, 없을 경우 도메인 아이콘 fallback
- 제목: 1줄 말줄임 (truncate)
- 설명: 2줄 말줄임 (line-clamp-2)
- 사이트명 + URL 도메인 표시
- 닫기 버튼 (X)

**로딩 상태**: Skeleton 컴포넌트 (pulse animation)
**에러 상태**: "미리보기를 불러올 수 없습니다" 토스트

### 5-2. i18n 키 추가

`v1/frontend/src/i18n/*.json` 5개 파일에 추가:

```json
{
  "og": {
    "previewTitle": "링크 미리보기",
    "loadFail": "미리보기를 불러올 수 없습니다",
    "attach": "링크 첨부",
    "dismiss": "닫기"
  },
  "newsletter": {
    "trackingNote": "오픈율 측정을 위한 추적 픽셀이 포함됩니다"
  }
}
```

---

## 6. Mock 모드 Fallback

모든 외부 의존성은 설치 여부와 무관하게 서버가 정상 시작·동작해야 한다.

| 의존성 | 감지 방법 | Fallback 동작 |
|-------|---------|-------------|
| `feedparser` | `ImportError` 캐치 | RSS fetch skip, 로그 경고, 빈 결과 반환 |
| `httpx` | `ImportError` 캐치 | OG scrape skip, `OGData(all None)` 반환 |
| `beautifulsoup4` | `ImportError` 캐치 | OG scrape skip, `OGData(all None)` 반환 |
| Redis | `ConnectionError` 또는 미연결 | in-process LRU(512 entries) 사용 |
| LLM Gateway (artist match) | 환경변수 미설정 | keyword-only 매칭으로 fallback |

**Mock 모드 확인 로그 형식**:

```
[RSS] feedparser not installed — rss_fetch_jobs running in mock mode (no-op)
[OG]  httpx not installed — og_scraper running in mock mode (returns null data)
[OG]  Redis unavailable — falling back to in-process LRU cache (512 entries)
```

---

## 7. i18n Keys

5개 로케일(`ko`, `en`, `ja`, `zh`, `es`) 모두 추가:

| Key | ko | en |
|-----|----|----|
| `og.previewTitle` | 링크 미리보기 | Link Preview |
| `og.loadFail` | 미리보기를 불러올 수 없습니다 | Could not load preview |
| `og.attach` | 링크 첨부 | Attach Link |
| `og.dismiss` | 닫기 | Dismiss |
| `newsletter.trackingNote` | 오픈율 측정을 위한 추적 픽셀이 포함됩니다 | Includes a tracking pixel for open rate measurement |

---

## 8. Test Plan

### 단위 테스트

| 테스트 대상 | 파일 위치 | 핵심 케이스 |
|-----------|---------|-----------|
| `rss_fetch_jobs.py` | `tests/services/test_rss_fetch.py` | 정상 수집, feedparser 미설치 mock, 중복 URL skip, 작가 매칭 |
| `og_scraper.py` | `tests/services/test_og_scraper.py` | OG 추출 성공, 우선순위 fallback, Redis 캐시 hit/miss, mock 모드 |
| `newsletter_composer.py` | `tests/services/test_newsletter_composer.py` | `_inject_tracking()` pixel 삽입, 링크 wrapping, Domo 내부 URL skip |
| newsletter tracking API | `tests/api/test_newsletter_track.py` | open → 1x1 PNG + DB, click → 302 redirect + DB |
| OG preview API | `tests/api/test_og_preview.py` | 정상 응답, 타임아웃 504, 잘못된 URL 422 |

### 통합 테스트

```
smoke_test_L_B.sh:
  1. DB 마이그레이션 확인 (alembic 0067 green)
  2. RSS feed 1개 등록 → 수동 fetch 트리거 → external_articles 확인
  3. OG preview API: 실제 URL 호출 → image_url 반환 확인
  4. Newsletter track open: GET → PNG Content-Type 확인 + newsletter_events row 확인
  5. Newsletter track click: GET → 302 Location 확인 + click row 확인
```

### 테스트 수 목표

기존 412 tests → **440+ tests** (L-B: ~28 신규)

---

## 9. 위임 Agent

| 워크스트림 | 담당 agent | 범위 |
|-----------|----------|------|
| L-2 RSS cron + DB | **bkend-expert** | alembic 0067 (RSS 테이블), rss_fetch_jobs.py, 작가 매칭 로직 |
| L-3 OG scraper + API | **bkend-expert** | og_scraper.py, POST /api/og/preview, Redis 캐시 |
| L-4 Newsletter tracking DB + API | **bkend-expert** | alembic 0067 (newsletter_events), track API 2종, newsletter_composer 수정 |
| L-3 OG 미리보기 UI | **frontend-architect** | OGPreviewCard.tsx, 에디터 연동, i18n |

**구현 순서 권장**:

```
1. alembic 0067 작성 & 적용 (bkend-expert)
2. rss_fetch_jobs.py + og_scraper.py (bkend-expert, 병렬 가능)
3. newsletter_composer.py 수정 + track API (bkend-expert)
4. OG Preview UI (frontend-architect, 3과 병렬 가능)
5. 통합 smoke test
```

---

## 10. 비고 — 알려진 한계

- **Gmail/Apple Mail image blocking**: 1x1 픽셀 open rate는 실제보다 과소 측정될 수 있음.
  B'-5 analytics dashboard에 "측정 정확도 ~70% (이미지 차단 클라이언트 제외)" 안내 문구 추가.
- **RSS HTML-only 피드**: feedparser가 HTML 페이지를 RSS로 오인하면 파싱 실패.
  `_is_valid_feed()` 헬퍼로 `<rss>` 또는 `<feed>` 루트 태그 사전 확인.
- **OG 스크래핑 법적 주의**: `robots.txt` 준수 의무 없음 (메타 태그 읽기는 브라우저 동일 동작).
  단, 응답 Content-Type이 `text/html`이 아닌 경우(PDF 등) 즉시 skip.
