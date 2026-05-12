"""Unit tests for D-6: observability-monitoring-baseline.

5 test cases:
  1. cron_runs_total counter increments per worker label
  2. cron_duration_seconds histogram observes elapsed time
  3. share_card_cache_hits_total increments on cache hit
  4. share_card_cache_misses_total increments on cache miss
  5. record_cron_run context manager increments errors on exception

Works with or without prometheus_client installed:
- With prometheus_client: tests verify real counter/histogram behaviour
- Without prometheus_client: tests verify no-op stubs don't raise
"""
from __future__ import annotations

import pytest

from app.core.metrics import (
    _PROMETHEUS_AVAILABLE,
    cron_duration_seconds,
    cron_errors_total,
    cron_rows_processed_total,
    cron_runs_total,
    record_cron_run,
    share_card_cache_hits_total,
    share_card_cache_misses_total,
    share_card_generation_seconds,
)


# ─── Helper: snapshot metric values ──────────────────────────────────────────

def _counter_labeled(counter, **labels) -> float:
    """Return current value of a labeled prometheus Counter (or 0 for stubs)."""
    obj = counter.labels(**labels)
    return obj._value.get()


def _counter_unlabeled(counter) -> float:
    """Return current value of an unlabeled prometheus Counter (or 0 for stubs)."""
    if _PROMETHEUS_AVAILABLE:
        return counter._value.get()
    return counter._value.get()


def _histogram_sum(histogram, **labels) -> float:
    """Return _sum of a labeled Histogram for given labels (or 0 for stubs)."""
    obj = histogram.labels(**labels)
    return obj._sum.get()


# ─── Test 1: cron_runs_total increments per worker label ─────────────────────


def test_cron_runs_total_increments():
    """cron_runs_total counter increments by 1 for a given worker label."""
    before = _counter_labeled(cron_runs_total, worker="test_worker_1")
    cron_runs_total.labels(worker="test_worker_1").inc()
    after = _counter_labeled(cron_runs_total, worker="test_worker_1")
    # With real prometheus_client: after == before + 1
    # With no-op stubs: both return 0, increment is silent — no raise
    if _PROMETHEUS_AVAILABLE:
        assert after == before + 1.0
    else:
        assert after == 0.0  # no-op stub always returns 0


# ─── Test 2: cron_duration_seconds histogram observes ────────────────────────


def test_cron_duration_histogram_observes():
    """cron_duration_seconds histogram records observed values."""
    before_sum = _histogram_sum(cron_duration_seconds, worker="test_worker_2")
    cron_duration_seconds.labels(worker="test_worker_2").observe(0.25)
    after_sum = _histogram_sum(cron_duration_seconds, worker="test_worker_2")
    if _PROMETHEUS_AVAILABLE:
        assert after_sum == pytest.approx(before_sum + 0.25, rel=1e-6)
    else:
        assert after_sum == 0.0  # no-op stub


# ─── Test 3: share_card_cache_hits_total increments ──────────────────────────


def test_share_card_cache_hits_increment():
    """share_card_cache_hits_total increments on cache hit."""
    before = _counter_unlabeled(share_card_cache_hits_total)
    share_card_cache_hits_total.inc()
    after = _counter_unlabeled(share_card_cache_hits_total)
    if _PROMETHEUS_AVAILABLE:
        assert after == before + 1.0
    else:
        assert after == 0.0  # no-op stub


# ─── Test 4: share_card_cache_misses_total increments ────────────────────────


def test_share_card_cache_misses_increment():
    """share_card_cache_misses_total increments on cache miss."""
    before = _counter_unlabeled(share_card_cache_misses_total)
    share_card_cache_misses_total.inc()
    after = _counter_unlabeled(share_card_cache_misses_total)
    if _PROMETHEUS_AVAILABLE:
        assert after == before + 1.0
    else:
        assert after == 0.0  # no-op stub


# ─── Test 5: record_cron_run increments errors_total on exception ─────────────


def test_record_cron_run_error_increments():
    """record_cron_run context manager increments both runs_total and errors_total on exception."""
    worker = "test_worker_error"
    before_runs = _counter_labeled(cron_runs_total, worker=worker)
    before_errors = _counter_labeled(cron_errors_total, worker=worker)

    with pytest.raises(RuntimeError, match="boom"):
        with record_cron_run(worker):
            raise RuntimeError("boom")

    after_runs = _counter_labeled(cron_runs_total, worker=worker)
    after_errors = _counter_labeled(cron_errors_total, worker=worker)

    if _PROMETHEUS_AVAILABLE:
        assert after_runs == before_runs + 1.0
        assert after_errors == before_errors + 1.0
    else:
        # no-op stubs: no exception raised by context manager itself — pass
        assert after_runs == 0.0
        assert after_errors == 0.0
