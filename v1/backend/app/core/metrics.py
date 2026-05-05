"""Prometheus metrics definitions for Domo backend.

All metrics are registered at module import time.
Import this module to access metric objects.

If prometheus_client is not installed, all metrics fall back to no-op stubs
so that existing tests continue to run without the optional dependency.

Usage example (cron worker):
    from app.core.metrics import cron_runs_total, cron_duration_seconds, record_cron_run

    async def my_cron_loop():
        worker = "schedule"
        with record_cron_run(worker):
            rows = await do_work()
            cron_rows_processed_total.labels(worker=worker).inc(rows)
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager

log = logging.getLogger(__name__)

# ─── Optional prometheus_client import ───────────────────────────────────────

try:
    from prometheus_client import Counter, Histogram  # type: ignore[import]
    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PROMETHEUS_AVAILABLE = False
    log.warning(
        "prometheus_client not installed — metrics are no-ops. "
        "Install with: pip install 'prometheus-client>=0.21'"
    )

    # Minimal no-op stubs so the rest of the module can be imported unconditionally.

    class _Labels:
        """Stub returned by .labels() — all operations are no-ops."""

        def inc(self, amount: float = 1) -> None:
            pass

        def observe(self, amount: float) -> None:
            pass

        # Expose _value for test introspection compatibility
        class _Value:
            def get(self) -> float:
                return 0.0

        _value = _Value()
        _sum = _Value()

    class Counter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self._labels = _Labels()
            self._value = _Labels._Value()

        def labels(self, **kwargs) -> _Labels:
            return self._labels

        def inc(self, amount: float = 1) -> None:
            pass

    class Histogram:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self._labels = _Labels()

        def labels(self, **kwargs) -> _Labels:
            return self._labels

        def observe(self, amount: float) -> None:
            pass


# ─── Cron worker metrics ─────────────────────────────────────────────────────

cron_runs_total = Counter(
    "domo_cron_runs_total",
    "Total number of cron worker sweep invocations",
    labelnames=["worker"],
)

cron_errors_total = Counter(
    "domo_cron_errors_total",
    "Total number of cron worker sweep errors",
    labelnames=["worker"],
)

cron_rows_processed_total = Counter(
    "domo_cron_rows_processed_total",
    "Total rows processed by cron workers",
    labelnames=["worker"],
)

cron_duration_seconds = Histogram(
    "domo_cron_duration_seconds",
    "Cron worker sweep duration in seconds",
    labelnames=["worker"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0),
)

# ─── Share card metrics ───────────────────────────────────────────────────────

share_card_cache_hits_total = Counter(
    "domo_share_card_cache_hits_total",
    "Total number of share card cache hits (1h TTL)",
)

share_card_cache_misses_total = Counter(
    "domo_share_card_cache_misses_total",
    "Total number of share card cache misses (generation required)",
)

share_card_generation_seconds = Histogram(
    "domo_share_card_generation_seconds",
    "Share card Pillow synthesis duration in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

# ─── Tier release metrics ─────────────────────────────────────────────────────

tier_release_cleared_rows_total = Counter(
    "domo_tier_release_cleared_rows_total",
    "Total expired early_access rows cleared by tier_release worker",
)

# ─── Notification dispatch metrics ───────────────────────────────────────────

notification_dispatched_total = Counter(
    "domo_notification_dispatched_total",
    "Total notifications dispatched by auction_promotion cron",
    labelnames=["type"],
)

# ─── Subscription expiry notification metrics (A-8) ──────────────────────────

subscription_expiry_notif_total = Counter(
    "domo_subscription_expiry_notif_total",
    "Total subscription expiry notifications dispatched by cron",
    labelnames=["result"],
)

subscription_expiring_count = Counter(
    "domo_subscription_expiring_count",
    "Snapshot count of active subscriptions expiring within window_days (incremented each sweep)",
    labelnames=["window_days"],
)

# ─── Artist Index metrics (A-6) ──────────────────────────────────────────────

artist_index_calc_duration_seconds = Histogram(
    "domo_artist_index_calc_duration_seconds",
    "Duration of artist index score recalculation sweep in seconds",
    labelnames=["phase"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

artist_index_artists_total = Counter(
    "domo_artist_index_artists_total",
    "Total artists processed by artist_index cron (cumulative inc per sweep)",
    labelnames=["status"],
)

# ─── Stripe webhook metrics (G'-1) ───────────────────────────────────────────

webhook_received_total = Counter(
    "domo_webhook_received_total",
    "Total Stripe webhook events received",
    labelnames=["event_type", "result"],
)

webhook_duration_seconds = Histogram(
    "domo_webhook_duration_seconds",
    "Stripe webhook event processing duration in seconds",
    labelnames=["event_type"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

webhook_idempotent_skip_total = Counter(
    "domo_webhook_idempotent_skip_total",
    "Total Stripe webhook events skipped due to idempotency (already processed)",
    labelnames=["event_type"],
)

# ─── Post Engagement Cache metrics (G'-9) ────────────────────────────────────

post_engagement_cache_calc_duration_seconds = Histogram(
    "domo_post_engagement_cache_calc_duration_seconds",
    "Duration of post engagement cache recalculation sweep in seconds",
    labelnames=["phase"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

post_engagement_cache_rows_total = Counter(
    "domo_post_engagement_cache_rows_total",
    "Total post engagement cache rows processed by cron (cumulative inc per sweep)",
    labelnames=["result"],
)

# ─── Helper context manager ──────────────────────────────────────────────────


# ─── Newsletter metrics (C-5) ─────────────────────────────────────────────────

newsletter_sent_total = Counter(
    "domo_newsletter_sent_total",
    "Total newsletter emails successfully sent by cron",
    labelnames=["locale"],
)

newsletter_failed_total = Counter(
    "domo_newsletter_failed_total",
    "Total newsletter email send failures by cron",
    labelnames=["locale"],
)

newsletter_opt_in_total = Counter(
    "domo_newsletter_opt_in_total",
    "Total newsletter opt-in actions (PATCH preferences is_subscribed=True)",
)

newsletter_opt_out_total = Counter(
    "domo_newsletter_opt_out_total",
    "Total newsletter opt-out actions (PATCH preferences or unsubscribe link)",
)

# ─── Helper context manager ──────────────────────────────────────────────────


@contextmanager
def record_cron_run(worker: str):
    """Context manager: records run count, duration, and errors for a cron sweep.

    Usage:
        with record_cron_run("schedule"):
            rows = await do_work()
            cron_rows_processed_total.labels(worker="schedule").inc(rows)
    """
    cron_runs_total.labels(worker=worker).inc()
    start = time.perf_counter()
    try:
        yield
    except Exception:
        cron_errors_total.labels(worker=worker).inc()
        raise
    finally:
        elapsed = time.perf_counter() - start
        cron_duration_seconds.labels(worker=worker).observe(elapsed)
