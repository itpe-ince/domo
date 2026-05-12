# Redis Cache Operations Guide

G''-2 redis-cache-layer — Phase 8

## Overview

Domo uses Redis as an optional read-through cache layer for hot, read-heavy
endpoints.  When `REDIS_URL` is not set the system degrades gracefully: all
cache calls are no-ops and every request hits PostgreSQL directly.

---

## AWS ElastiCache Deployment

### Recommended Configuration

| Parameter | Value | Notes |
|---|---|---|
| Engine | Redis 7.x (Valkey 8 compatible) | TLS in-transit required |
| Mode | Cluster mode disabled (single shard) | Sufficient for Phase 8 load |
| Instance | `cache.t4g.small` (dev) / `cache.m7g.large` (prod) | Right-size per load test |
| Multi-AZ | Enabled with automatic failover | Production only |
| Auth token | Yes (`REDIS_PASSWORD`) | AUTH command on every connection |
| Encryption in-transit | TLS `rediss://` scheme | Required |
| Encryption at-rest | AWS-managed KMS | Enabled by default on ElastiCache |

### Network

- Place ElastiCache in the same VPC as ECS/EKS workloads.
- Security Group: allow inbound TCP 6379 from backend task SG only.
- No public internet access.

### Environment Variables

```
REDIS_URL=rediss://<cluster-endpoint>:6379/0
REDIS_PASSWORD=<auth-token>
REDIS_MAX_CONNECTIONS=50
```

`rediss://` (double-s) enables TLS.  `redis://` is plain-text (dev only).

---

## Redis 6/7 Compatibility

| Feature | Redis 6 | Redis 7 |
|---|---|---|
| ACL Users | Basic | Full (recommended) |
| LMPOP / ZMPOP | No | Yes |
| Pub/sub sharding | No | Yes |
| Functions | No | Yes (Lua replacement) |
| Used by G''-2 | INCR, EXPIRE, GET, SET, SETEX, DEL, SCAN | Same |

G''-2 uses only commands available in Redis 6+.  Upgrading to Redis 7 is
safe with no code changes.

---

## Cache Key Naming Convention

```
{domain}:{resource}:{dimension1}:{dimension2}:...
```

| Prefix | TTL | Example Key | Notes |
|---|---|---|---|
| `search` | 300 s (5 min) | `search:popular:10:24h` | Popular searches, global |
| `artists` | 3600 s (1 h) | `artists:index:KR:painting:50:start` | Artist index, per-filter combo |
| `feed` | 300 s (5 min) | `feed:v1:{user_id}:first` | Feed per user+cursor |
| `ratelimit` | window_sec | `ratelimit:search:127.0.0.1:1714800000` | Rate limit buckets |

Rules:
1. No PII in key or value (no email, phone, card data).
2. Keys are namespaced by domain prefix — never use bare identifiers.
3. All user-scoped keys include `{user_id}` to prevent data leakage.

---

## TTL Policy

| Cache | TTL | Rationale |
|---|---|---|
| Popular searches | 5 min | Frequently changing; stale data acceptable for 5 min |
| Artist index | 1 hour | Recalculated hourly by cron — TTL matches cron interval |
| Feed (per user/cursor) | 5 min | User feed freshness vs. DB load trade-off |
| Rate limit buckets | window_sec + 5 | Slightly longer than window to avoid off-by-one race |

Expired keys are reclaimed automatically by Redis.  No manual cleanup needed.

---

## Invalidation Strategy

| Trigger | Keys Invalidated | Method |
|---|---|---|
| `artist_index_cron_loop` completes | `artists:index:*` | `SCAN` + `DEL` (pattern delete) |
| New search submitted | `search:popular:*` | Natural TTL expiry (no explicit invalidation) |
| Feed mutation (post, follow, etc.) | `feed:v1:{user_id}:*` | Not yet implemented — Phase 9 carry-over |

Pattern delete (`SCAN + DEL`) is O(N) — only used in cron context, not
hot paths.

---

## Prometheus Metrics

| Metric | Labels | Description |
|---|---|---|
| `domo_cache_hit_total` | `cache_key_prefix` | Cache hits per domain prefix |
| `domo_cache_miss_total` | `cache_key_prefix` | Cache misses per domain prefix |
| `domo_cache_set_total` | `cache_key_prefix` | Cache writes per domain prefix |
| `domo_cache_invalidate_total` | `reason` | Keys invalidated by reason |

Useful PromQL queries:

```promql
# Cache hit rate by prefix
rate(domo_cache_hit_total[5m])
  / (rate(domo_cache_hit_total[5m]) + rate(domo_cache_miss_total[5m]))

# Artist index invalidation rate (should spike once per hour)
rate(domo_cache_invalidate_total{reason="cron_artist_index"}[1h])
```

---

## Development / CI

Leave `REDIS_URL` unset.  The `CacheClient` detects this at startup and
logs:

```
Redis disabled (REDIS_URL not set) — cache is a no-op
```

All cache calls are no-ops; the application reads directly from PostgreSQL.
Tests pass without a Redis instance.

---

## Production Checklist

- [ ] `REDIS_URL` uses `rediss://` (TLS) scheme
- [ ] `REDIS_PASSWORD` set to ElastiCache auth token
- [ ] Security Group restricts inbound 6379 to backend SG only
- [ ] Multi-AZ with automatic failover enabled
- [ ] CloudWatch alarms on `CacheHits`, `CacheMisses`, `Evictions`, `DatabaseMemoryUsagePercentage`
- [ ] Prometheus scraping `/metrics` for `domo_cache_*` metrics
- [ ] `REDIS_MAX_CONNECTIONS` tuned to `(ECS_TASK_COUNT * 50) < ElastiCache maxmemory-clients`

---

## Phase 9+ Carry-overs

- Feed invalidation on post/follow mutation (Pub/Sub or targeted key delete)
- Cache warming cron (pre-populate cold cache after deployment)
- Cache stampede protection (distributed lock / singleflight pattern)
- Redis Cluster mode for horizontal scaling beyond single shard
- AlertManager rule: alert when cache hit rate drops below 60%
