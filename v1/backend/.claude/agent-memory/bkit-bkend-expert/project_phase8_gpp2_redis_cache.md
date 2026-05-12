---
name: Phase 8 G''-2 Redis Cache Layer
description: G''-2 완료: CacheClient singleton, 4 cache 영역, invalidation, 4 Prometheus metrics, 9 tests
type: project
---

G''-2 redis-cache-layer 구현 완료.

**Key files:**
- `app/services/cache.py` (신규) — CacheClient singleton, 7 methods, Mock fallback
- `app/core/redis_client.py` (수정) — redis_url optional → returns None when unset
- `app/core/config.py` (수정) — redis_url: str|None=None, redis_password, redis_max_connections
- `app/core/metrics.py` (수정) — 4 cache metrics added
- `app/main.py` (수정) — cache.connect() / cache.shutdown() in lifespan
- `app/api/search.py` (수정) — popular searches cache, TTL 5min
- `app/api/artists.py` (수정) — artist index cache, TTL 1h
- `app/api/posts.py` (수정) — feed:v1 cache per user+cursor, TTL 5min
- `app/core/rate_limit.py` (수정) — in-memory fallback when Redis disabled
- `app/services/artist_index_jobs.py` (수정) — cache.delete_pattern("artists:index:*") after sweep
- `tests/unit/test_cache_service.py` (신규) — 9 unit tests
- `tests/integration/test_cache_integration.py` (신규) — 5 integration tests
- `v1/docs/operations/redis-cache.md` (신규) — operations guide

**Cache key convention:**
- `search:popular:{limit}:24h` — TTL 300s
- `artists:index:{region}:{genre}:{limit}:{cursor}` — TTL 3600s
- `feed:v1:{user_id}:{cursor}` — TTL 300s
- `ratelimit:{scope}:{key}:{window_start}` — TTL window_sec+5

**Mock mode:** REDIS_URL unset → all cache ops are no-ops, DB queried directly.

**Why:** redis_url changed from `str = "redis://localhost:6379/0"` to `str | None = None`. This means CI/dev never requires Redis. Production sets REDIS_URL=rediss://<elasticache>:6379/0.
