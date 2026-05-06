# DB Performance — Query Plan Audit & N+1 Baseline

**G''-3 n-plus-one-audit** | Phase 8 | 2026-05-04

---

## 1. Overview

This document captures the results of the G''-3 database performance audit:
- EXPLAIN ANALYZE for 18 core queries (CI-gated)
- N+1 query audit across all list endpoints
- New performance indexes (alembic 0059)
- Response time baseline (p50/p95/p99)

---

## 2. EXPLAIN ANALYZE Gate (18 Queries)

CI workflow: `.github/workflows/db-perf.yml`
Script: `v1/backend/scripts/check_query_plans.sh`

All 18 queries must pass (no Seq Scan) before PR merge.

### D-6 Phase 5 Queries (1–8)

| # | Label | Table | Key Index |
|---|-------|-------|-----------|
| 1 | posts.visibility_filter | posts | `idx_posts_feed` (status, type, created_at) |
| 2 | posts.early_access_until_expiry | posts | `ix_posts_early_access_until` |
| 3 | auctions.promotion_24h_slot | auctions | `idx_auctions_status_end_at` |
| 4 | orders.expired_pending_payment | orders | `idx_orders_status_due` |
| 5 | posts.scheduled_publish | posts | `idx_posts_feed` (status, scheduled_at) |
| 6 | bids.by_auction_amount_desc | bids | `idx_bids_auction_amount` |
| 7 | notifications.unread_by_user | notifications | `idx_notifications_user` |
| 8 | drafts.expired_cleanup | drafts | `idx_drafts_user_updated` |

### Phase 6/7 New Queries (9–18)

| # | Label | Table | Key Index |
|---|-------|-------|-----------|
| 9 | posts.personalized_feed_follow | posts | `idx_posts_author` (author_id, created_at) |
| 10 | posts.trending_pool | posts | `idx_posts_feed` + visibility filter |
| 11 | artist_index.region_genre_ranking | artist_index | `idx_artist_index_score` |
| 12 | search_history.by_user | search_history | `ix_search_history_user_active` (0059) |
| 13 | search_logs.popular_24h | search_logs | `idx_search_logs_created_at` |
| 14 | notifications.unread_count | notifications | `ix_notifications_user_unread` (0059 partial) |
| 15 | artist_interviews.status_list | artist_interviews | `ix_artist_interviews_status_created` (0059) |
| 16 | press_kits.cache_lookup | press_kits | `ix_press_kits_artist_created` |
| 17 | media_coverage.published_locale | media_coverage | `ix_media_coverage_published_locale` (0059 partial) |
| 18 | newsletter_issues.sending_by_locale | newsletter_issues | `ix_newsletter_issues_status_locale` |

---

## 3. N+1 Audit Results

### Methodology

Each list endpoint was reviewed for the pattern:
```python
# N+1 (bad):
for item in items:
    related = item.related  # triggers lazy load → 1 query per item

# Fixed (good):
await db.execute(select(Related).where(Related.id.in_(ids)))
```

### Audit Findings by Endpoint

| Endpoint | N+1 Found | Fix Applied | Before | After |
|----------|:---------:|:-----------:|--------|-------|
| `GET /posts/feed` (legacy) | NO | Pre-existing batch fetch | Already optimized | — |
| `GET /posts/feed?algo=v1` (A-3) | NO | Pre-existing batch fetch | Already optimized | — |
| `GET /posts/explore` | NO | Pre-existing batch fetch | Already optimized | — |
| `GET /posts/search` | NO | Pre-existing batch fetch | Already optimized | — |
| `GET /posts/bookmarks/mine` | NO | Pre-existing batch fetch | Already optimized | — |
| `GET /notifications` | NO | Notification rows only, no joins | Already optimized | — |
| `GET /sponsorships/mine` | NO | No per-row related entity fetch | Already optimized | — |
| `GET /subscriptions/mine` | NO | No per-row related entity fetch | Already optimized | — |
| `GET /me/patronage/supporters` | NO | Pre-existing batch user fetch | Already optimized | — |
| `GET /me/patronage/churn` | NO | Pre-existing batch user fetch | Already optimized | — |
| `GET /admin/artist-interviews` | NO | No related entity per row | Already optimized | — |
| `GET /admin/artists/{id}/press-kit/history` | NO | PressKit rows only | Already optimized | — |
| `GET /media-coverage` | NO | MediaCoverage rows only | Already optimized | — |
| `GET /media-coverage/featured` | NO | MediaCoverage rows only | Already optimized | — |
| `GET /admin/newsletter/issues` | NO | NewsletterIssue rows only | Already optimized | — |
| `GET /posts/{id}/comments` | NO | Pre-existing batch author fetch | Already optimized | — |

**Conclusion**: Codebase already follows batch-fetch pattern throughout. No N+1 repairs required.

### Key Patterns in Use

**1. selectinload for one-to-many (Post → media, product)**
```python
select(Post)
    .options(selectinload(Post.media), selectinload(Post.product))
    .where(...)
```
Used in: `_load_post_full`, `home_feed`, `_personalized_feed_v1`, `explore_posts`, `search_posts`, `my_bookmarks`.

**2. Batch author fetch (Post/Comment → User)**
```python
author_ids = list({p.author_id for p in posts})  # deduplicate
authors = await db.execute(select(User).where(User.id.in_(author_ids)))
author_map = {u.id: u for u in authors.scalars()}
for p in posts:
    p.author = author_map.get(p.author_id)
```
Used in: `home_feed`, `_personalized_feed_v1`, `explore_posts`, `search_posts`, `list_comments`, `my_bookmarks`.

**3. Single bulk query for related data (_attach_active_auction_end_at)**
```python
# ONE query for ALL product posts in the list:
rows = await db.execute(
    select(Auction.product_post_id, Auction.end_at)
    .where(Auction.product_post_id.in_(product_post_ids), ...)
)
end_at_map = {pid: end_at for pid, end_at in rows}
for p in posts:
    p._active_auction_end_at = end_at_map.get(p.id)
```

**4. Aggregate SQL (no per-row queries)**
All patronage dashboard endpoints (`/me/patronage/summary`, `/revenue`, `/supporters`, `/churn`) use aggregate SQL — no per-row follow-up queries.

---

## 4. New Indexes (alembic 0059_perf_indexes)

Added 3 new indexes. 3 others were verified already present in earlier migrations.

### New in 0059

| Index Name | Table | Columns | Type | Covers |
|-----------|-------|---------|------|--------|
| `ix_notifications_user_unread` | notifications | user_id, created_at | Partial (`is_read = false`) | Unread count badge (hot path) |
| `ix_sponsorships_artist_status_created` | sponsorships | artist_id, status, created_at | Composite | Tier eligibility + winback cron |
| `ix_artist_interviews_status_created` | artist_interviews | status, created_at | Composite | C-1 admin list with status filter |

### Pre-existing (verified, no duplicate added)

| Migration | Index | Covers |
|-----------|-------|--------|
| 0049 | `idx_search_history_user_active` | A-5 search history list |
| 0057 | `ix_media_coverage_locale_published_at` | C-4 media coverage public list |
| 0058 | `ix_newsletter_issues_status_locale` | C-5 newsletter cron worker |
| 0041 | `ix_sponsorships_sponsor_artist_status` | Sponsor-side tier check (separate from artist-side 0059) |
| 0002 | `idx_posts_author`, `idx_posts_feed` | Personalized feed, explore, trending |
| 0001 | `idx_notifications_user` | General notification list (unread partial added in 0059) |

---

## 5. Response Time Baseline

Run `scripts/perf_baseline.sh` against a live instance to measure p50/p95/p99.

### Target KPIs (Phase 8 G'' AC)

| Metric | Target |
|--------|--------|
| p50 latency | ≤ 100ms |
| p95 latency | ≤ 200ms |
| p99 latency | ≤ 500ms |

### Usage

```bash
# Against local dev server (unauthenticated endpoints only):
./v1/backend/scripts/perf_baseline.sh

# Against staging with auth:
AUTH_TOKEN="<bearer_token>" BASE_URL="https://api.domo.example/v1" \
  ./v1/backend/scripts/perf_baseline.sh 200 10

# Write results to this doc:
WRITE_DOCS=1 ./v1/backend/scripts/perf_baseline.sh
```

### Baseline — Pre-optimization (2026-05-04)

Baseline to be measured after first production deployment with alembic 0059 applied.
Run `perf_baseline.sh` and append results here.

---

## 6. CI Integration

`.github/workflows/db-perf.yml` runs on every PR that touches `v1/backend/**`:

1. Spins up postgres:16 service container
2. Installs backend dependencies
3. Runs `alembic upgrade head`
4. Runs `scripts/check_query_plans.sh` (18 queries)
5. Fails PR if any Seq Scan detected

This prevents performance regression from landing on main.

---

## 7. Phase 9+ Improvements (Out of Scope)

| Improvement | Reason | Target |
|-------------|--------|--------|
| Read replica routing | Infer DB level — infra PDCA | Phase 9+ |
| Materialized view for artist_index | Precompute ranking | Phase 9+ |
| pg_trgm fuzzy search | DB extension, DBA approval needed | Phase 9+ |
| Query plan analyzer dashboard | Ops tooling | Phase 9+ |
| Sharding strategy | Scale milestone: 1M+ posts | Phase 10+ |
