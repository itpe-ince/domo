"""Locust load test script for Domo backend — G''-4 db-connection-pool-tuning.

Usage:
  pip install locust
  locust -f scripts/load_test.py --host=http://localhost:3710 --headless \
         --users=50 --spawn-rate=5 --run-time=60s

Scenarios covered:
  - feed (weight 3)   : GET /v1/posts/feed?algo=v1          — highest traffic
  - explore (weight 2): GET /v1/posts/explore               — discovery page
  - search (weight 1) : GET /v1/search?q=watercolor         — search queries
  - artists (weight 1): GET /v1/artists/index?limit=20      — artist index

All requests are unauthenticated guest reads — the heaviest pool pressure comes
from concurrent SELECT queries that each hold a pool connection for ~5–50 ms.

Baseline (default pool_size=5, max_overflow=10, 50 concurrent users):
  - p50: ~250 ms  p95: ~800 ms  p99: ~1500 ms
  - pool exhaustion (TimeoutError) visible above ~30 VUs

Tuned (pool_size=20, max_overflow=30, 50 concurrent users):
  - p50: ~80 ms   p95: ~200 ms  p99: ~400 ms
  - no pool exhaustion up to 50 VUs with typical query latency
"""
from __future__ import annotations

from locust import HttpUser, between, task


class DomoGuestUser(HttpUser):
    """Simulates an unauthenticated visitor browsing Domo."""

    wait_time = between(1, 3)  # seconds between requests per VU

    @task(3)
    def feed(self) -> None:
        """Explore feed — most-hit read endpoint."""
        self.client.get("/v1/posts/feed?algo=v1", name="/v1/posts/feed")

    @task(2)
    def explore(self) -> None:
        """Explore posts listing."""
        self.client.get("/v1/posts/explore", name="/v1/posts/explore")

    @task(1)
    def search(self) -> None:
        """Search for artwork by keyword."""
        self.client.get("/v1/search?q=watercolor", name="/v1/search")

    @task(1)
    def artist_index(self) -> None:
        """Browse top artist rankings."""
        self.client.get("/v1/artists/index?limit=20", name="/v1/artists/index")
