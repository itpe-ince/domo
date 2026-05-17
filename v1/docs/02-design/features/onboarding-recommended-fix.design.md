---
template: design
version: 1.0
feature: onboarding-recommended-fix
date: 2026-05-17
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
status: retroactive
---

# onboarding-recommended-fix Design Document

> **Summary**: 백엔드 `/v1/onboarding/recommended-artists` 엔드포인트 신규 + 프론트 `OnboardingStep2Sponsor` null-artist 핫픽스 설계.
>
> **Project**: domo / v1
> **Date**: 2026-05-17
> **Status**: Retroactive
> **Planning Doc**: [onboarding-recommended-fix.plan.md](../../01-plan/features/onboarding-recommended-fix.plan.md)

---

## 1. Overview

### 1.1 Design Goals

1. Phase 6 A-2 carry-over로 남았던 백엔드 엔드포인트를 **최소 변경**으로 구현 — 신규 모델/마이그레이션/스키마 추가 없음
2. 프론트엔드 `OnboardingStep2Sponsor`의 무반응 버튼 버그를 **표면 패치가 아닌 상태 머신 분리**로 근본 해결
3. 기존 컨벤션(envelope `{"data": ...}`, FastAPI router prefix, anonymous endpoint pattern) 정확히 추종

### 1.2 Design Principles

- **YAGNI**: 추천 알고리즘 단순화(rank ASC + follower fallback + shuffle). ML 기반 추천이나 사용자별 personalization은 별도 PDCA
- **Graceful degradation**: artist load 실패도 사용자가 다음 단계로 진행 가능해야 함(skip flow 유지)
- **Single Source of Truth**: 응답 shape은 frontend `RecommendedArtist` 타입과 1:1 매칭 — backend가 그것에 맞춤

---

## 2. Architecture

### 2.1 Component Diagram

```
┌──────────────────────────────────┐     ┌─────────────────────────────────┐
│ OnboardingStep2Sponsor.tsx       │     │ api/onboarding.py               │
│   useEffect → loadArtist()       │     │   list_recommended_artists()    │
│     ↓                            │ ──▶ │     ↓                           │
│   fetchRecommendedArtists(1)     │     │   select(User, ArtistProfile)   │
│     ↓                            │     │     .where(role='artist',       │
│   setArtist / setArtistLoadFailed│     │            artist_index_rank    │
│     ↓                            │     │            IS NOT NULL)         │
│   render branches:               │     │     → fallback by follower      │
│     artist  → CTA button         │     │     → shuffle pool              │
│     loading → disabled button    │ ◀── │   {"data": RecommendedArtist[]} │
│     failed  → noArtists message  │     │                                 │
└──────────────────────────────────┘     └─────────────────────────────────┘
                                                          │
                                                          ▼
                                              PostgreSQL: users, artist_profiles,
                                                          follows, posts
```

### 2.2 Data Flow

```
Step2 mount
  → captureEvent(onboarding_step, 2)
  → fetchRecommendedArtists(1)
    → GET /v1/onboarding/recommended-artists?limit=1
      → rate_limit('onboarding_recommended_read')   # 60/min/IP
      → primary query: ranked artists (top 3 by limit)
      → if pool < target: fallback by follower count
      → shuffle + take limit
      → enrich with recent_works_count (posts where status='published')
      → return {"data": [{user_id, username, avatar_url, bio_short, tier_default, recent_works_count}]}
  → setLoadingArtist(false)
  → if data.length > 0: setArtist(data[0])
  → else: setArtistLoadFailed(true)
  → re-render branches
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `app/api/onboarding.py` | `app.models.user.{User, ArtistProfile}`, `app.models.post.{Follow, Post}`, `app.core.rate_limit.rate_limit`, `app.db.session.get_db` | DB models + rate limit + DB session |
| `app/main.py` | `app.api.onboarding` | Router registration |
| `app/core/rate_limit.py` | (none new) | Add `onboarding_recommended_read` entry to DEFAULT_LIMITS |
| `OnboardingStep2Sponsor.tsx` | `useI18n`, `captureEvent`, `fetchRecommendedArtists`, `BluebirdModal` | (unchanged dependencies) |

---

## 3. Data Model

### 3.1 Response Schema (no new DB entities)

```typescript
// RecommendedArtist — frontend type (existing, lib/api.ts:2599)
type RecommendedArtist = {
  user_id: string;            // UUID
  username: string;           // ← maps to user.display_name
  avatar_url: string | null;  // ← user.avatar_url
  bio_short: string | null;   // ← user.bio truncated to 100 chars with "…" ellipsis
  tier_default: string;       // ← artist_profile.badge_level (default "free")
  recent_works_count: number; // ← COUNT(posts) where author_id=u.id AND status='published'
};

// Response envelope
type RecommendedArtistsResponse = {
  data: RecommendedArtist[];
};
```

### 3.2 No new migrations

설계상 신규 컬럼/테이블/인덱스 없음. 기존 인덱스로 충분:
- `users.role` (queried, but small cardinality — table scan + filter OK)
- `users.artist_index_rank` (already indexed via Phase 6.A-6)
- `follows.followee_id` (PK, group-by 가능)
- `posts.author_id` (FK with index)

---

## 4. API Specification

### 4.1 GET /v1/onboarding/recommended-artists

| Field | Value |
|-------|-------|
| Method | GET |
| Path | `/v1/onboarding/recommended-artists` |
| Auth | None (anonymous) |
| Rate limit | 60/min/IP (`onboarding_recommended_read`) |
| Query: `limit` | int, 1 ≤ limit ≤ 20, default 5 |

**Response 200**:
```json
{
  "data": [
    {
      "user_id": "428c98b4-a84c-4814-9213-c98c345d5a94",
      "username": "kenji_osaka",
      "avatar_url": null,
      "bio_short": null,
      "tier_default": "emerging",
      "recent_works_count": 6
    }
  ]
}
```

**Response 422** (Pydantic Query validation): `limit` out of range.

**Response 429**: rate limit exceeded (envelope: `{"error": {"code": "RATE_LIMITED", ...}}`).

### 4.2 Ranking Algorithm

```python
# Pseudocode
pool_size = min(30, limit * 3)
primary = select(User, ArtistProfile)
           .where(role='artist', status='active', artist_index_rank IS NOT NULL)
           .order_by(artist_index_rank ASC)
           .limit(pool_size)

if len(primary) < pool_size:
    fallback = select(User, ArtistProfile)
               .where(role='artist', status='active')
               .order_by(COALESCE(follower_count, 0) DESC, created_at DESC)
               .limit(pool_size)
    pool = primary + (fallback - primary)

random.shuffle(pool)
selected = pool[:limit]

# Enrich with recent_works_count via single grouped query
works_count = SELECT author_id, COUNT(*) FROM posts
              WHERE author_id IN selected AND status='published'
              GROUP BY author_id
```

---

## 5. Frontend Design

### 5.1 State Machine (OnboardingStep2Sponsor)

```
                 mount
                   │
                   ▼
            loadingArtist=true
            artist=null
            artistLoadFailed=false
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
 fetch success            fetch error / 0 results
       │                       │
       ▼                       ▼
 artist=data[0]          artistLoadFailed=true
 loadingArtist=false     loadingArtist=false
```

### 5.2 Render Branches (priority order)

1. `sponsored=true`        → success card + "다음 단계로" 버튼
2. `artist !== null`       → CTA "@username 응원하기" 버튼 (활성, modal open)
3. `loadingArtist=true`    → CTA "지금 응원하기" 버튼 (disabled, opacity 60, cursor-wait)
4. `artistLoadFailed=true` → `<p>onboarding.step1.noArtists</p>` 안내(role="status")
5. 모든 케이스: "다음" 또는 "다음 단계로" 버튼 + "나중에" skip 링크

### 5.3 Existing Behavior Preserved

- `captureEvent` 호출 시점 동일 (onboarding_step / first_action / onboarding_skip)
- `BluebirdModal` props/콜백 동일 (artistId, artistName, onClose, onSuccess)
- i18n 키 추가 없음 — `onboarding.step1.noArtists` 재사용

---

## 6. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Unauthenticated PII exposure | 응답 필드는 공개 정보만 (display_name, avatar_url, badge_level, bio 100자) — DM/email 미포함 |
| Long bio leakage | `_truncate_bio` 100자 cap + ellipsis |
| Endpoint DDoS | `onboarding_recommended_read` rate limit 60/min/IP |
| Suspended/deleted artists 노출 | `User.status == 'active'` 필터 |
| Non-artist user 노출 | `User.role == 'artist'` 필터 |

---

## 7. Testing Strategy

### 7.1 Smoke Test (executed)

```python
# Verified via FastAPI TestClient
GET /v1/onboarding/recommended-artists?limit=3
→ 200, 3 items, shape matches RecommendedArtist[]
```

### 7.2 Frontend Validation (executed)

- `npx tsc --noEmit -p .` → 0 errors

### 7.3 Out of Scope (현 PDCA)

- pytest 통합 테스트 추가 (별도 follow-up PDCA)
- Playwright E2E 시나리오

---

## 8. Implementation Mapping

| Design item | File | Status |
|-------------|------|--------|
| Backend router | `v1/backend/app/api/onboarding.py` | ✅ Created |
| Router registration | `v1/backend/app/main.py` (import + include_router) | ✅ Done |
| Rate limit config | `v1/backend/app/core/rate_limit.py` (DEFAULT_LIMITS entry) | ✅ Done |
| State machine refactor | `v1/frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx` | ✅ Done |
| Loading branch | OnboardingStep2Sponsor.tsx CTA area | ✅ Done |
| Error branch | OnboardingStep2Sponsor.tsx CTA area | ✅ Done |

---

## 9. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-17 | Retroactive design (post-implementation) | itpe-ince (Claude Opus 4.7) |
