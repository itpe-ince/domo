"""Database engine and session factory.

Pool tuning (G''-4 db-connection-pool-tuning):
  pool_size     — steady-state connections held open (configurable via DB_POOL_SIZE)
  max_overflow  — additional connections allowed at peak (configurable via DB_MAX_OVERFLOW)
  pool_pre_ping — validate connection health before checkout (prevents stale errors)
  pool_recycle  — replace connections older than N seconds (prevents OS-level TCP drops)
  pool_timeout  — raise TimeoutError instead of blocking forever under saturation

All 8 cron workers (R-5 격리) share this single engine/pool via the global
AsyncSessionLocal.  Session-level isolation (per-cron context, separate transactions)
is preserved by using separate `async with AsyncSessionLocal()` blocks in each cron.
Pool-level sharing is intentional: asyncpg multiplexes fine at the OS-socket level
and max_overflow absorbs burst concurrency across all workers simultaneously.

Prometheus DB pool metrics are registered here via SQLAlchemy sync-engine event
listeners so that Grafana can alert on pool exhaustion before it affects p95 latency.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

log = logging.getLogger(__name__)

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    # ── Pool configuration (G''-4) ──────────────────────────────────────────
    pool_size=settings.db_pool_size,          # steady-state open connections
    max_overflow=settings.db_max_overflow,    # extra connections at peak
    pool_pre_ping=True,                        # health-check before checkout
    pool_recycle=settings.db_pool_recycle,    # seconds — avoids OS TCP timeout drops
    pool_timeout=settings.db_pool_timeout,    # seconds — fail fast under saturation
    # ── asyncpg connect_args ────────────────────────────────────────────────
    connect_args={
        "server_settings": {
            # JIT compiles query plans — only beneficial for long OLAP queries.
            # Domo queries are short OLTP; JIT adds overhead with no gain.
            "jit": "off",
            "application_name": "domo-backend",
        },
    },
    # ── Echo ────────────────────────────────────────────────────────────────
    echo=settings.environment == "development",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Prometheus DB pool event listeners (G''-4 booster) ──────────────────────
# Import lazily so the module stays importable even when prometheus_client is
# absent (e.g. CI / unit tests that don't install the optional dependency).

try:
    from app.core.metrics import db_pool_connections, db_query_duration_seconds  # type: ignore[attr-defined]
    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    log.debug("DB pool Prometheus metrics not available — pool events are no-ops")


if _METRICS_AVAILABLE:
    @event.listens_for(engine.sync_engine, "checkout")
    def _on_pool_checkout(dbapi_conn, conn_record, conn_proxy) -> None:  # type: ignore[misc]
        """Increment checked-out gauge on connection checkout."""
        db_pool_connections.labels(state="checked_out").inc()

    @event.listens_for(engine.sync_engine, "checkin")
    def _on_pool_checkin(dbapi_conn, conn_record) -> None:  # type: ignore[misc]
        """Decrement checked-out gauge on connection return."""
        db_pool_connections.labels(state="checked_out").dec()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
