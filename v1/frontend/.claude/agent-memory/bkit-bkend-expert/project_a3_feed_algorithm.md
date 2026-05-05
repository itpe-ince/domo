---
name: A-3 feed-algorithm-v1
description: Phase 6 A-3 implementation: SQL+Python hybrid personalized feed, PostHog A/B algo toggle, cursor pagination
type: project
---

Phase 6 A-3 implementation completed 2026-05-04.

**Why:** README "그로스해킹 깔때기" — phase 6 growth funnel. Feed algorithm v1 is the discovery engine for the funnel.

**How to apply:** When working on feed-related code, algo scoring, or PostHog feature flags related to feed.

## Key files

### Backend
- `/Users/sangincha/dev/domo/v1/backend/app/services/feed_scoring.py` — Pure scoring logic (compute_score, score_posts, encode_cursor, decode_cursor, apply_cursor)
- `/Users/sangincha/dev/domo/v1/backend/app/api/posts.py` — `home_feed` endpoint + `_personalized_feed_v1` helper (algo=v1 branch)
- `/Users/sangincha/dev/domo/v1/backend/tests/unit/test_feed_scoring.py` — 6 unit tests
- `/Users/sangincha/dev/domo/v1/backend/tests/integration/test_personalized_feed.py` — 4 integration tests

### Frontend
- `/Users/sangincha/dev/domo/v1/frontend/src/app/feed/page.tsx` — Feed page with PostHog flag + algo toggle + cursor pagination + A-2 onboarding wizard preserved
- `/Users/sangincha/dev/domo/v1/frontend/src/components/feed/FeedAlgorithmToggle.tsx` — Radio toggle (latest/personalized)
- `/Users/sangincha/dev/domo/v1/frontend/src/components/feed/RecommendedReasonBadge.tsx` — "팔로잉" / "인기" badge
- `/Users/sangincha/dev/domo/v1/frontend/src/lib/api.ts` — fetchHomeFeed(limit, algo, cursor) → FeedResponse
- `/Users/sangincha/dev/domo/v1/frontend/src/lib/analytics/events.ts` — FeedAlgorithmViewEvent added
- i18n: 10 new keys × 5 locales (feed.titlePersonalized, feed.subtitlePersonalized, feed.algoToggleLabel, feed.algoDefault, feed.algoPersonalized, feed.loadMore, feed.reasonFollowing, feed.reasonTrending, feed.reasonSimilarGenre, feed.reasonLabel)

## Score formula
```
score = followed_weight(0.5) + recency_weight(0.3 * exp(-h/24)) + engagement_weight(0.15 * E/age_days) + trending_weight(0.05 * T/sqrt(age_hours)) - own_post_penalty(1.0)
```

## Algo query param
- `GET /posts/feed?algo=default` — legacy chronological (backward compat)
- `GET /posts/feed?algo=v1&cursor=...` — A-3 personalized with cursor pagination

## PostHog feature flag
- Flag key: `feed-algorithm-v2`
- true → algo=v1 default, show toggle
- false → algo=default, toggle hidden
