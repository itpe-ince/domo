"""Unit tests for G''-4: db-connection-pool-tuning.

3 test cases:
  1. db_pool_size config matches engine pool_size
  2. db_max_overflow config matches engine max_overflow
  3. db_pool_recycle config matches engine pool_recycle

These tests are config-level assertions — they verify that the pool tuning
settings from config.py are actually wired into the SQLAlchemy engine.
No database connection is required; the engine attributes are inspectable
without connecting to PostgreSQL.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.db.session import engine


@pytest.fixture(scope="module")
def settings():
    return get_settings()


@pytest.fixture(scope="module")
def pool():
    """Return the sync engine's underlying connection pool."""
    return engine.sync_engine.pool


# ─── Test 1: pool_size ────────────────────────────────────────────────────────


def test_pool_size_matches_config(settings, pool):
    """Engine pool_size must match settings.db_pool_size."""
    assert pool.size() == settings.db_pool_size, (
        f"Expected pool_size={settings.db_pool_size}, got {pool.size()}"
    )


# ─── Test 2: max_overflow ─────────────────────────────────────────────────────


def test_max_overflow_matches_config(settings, pool):
    """Engine max_overflow must match settings.db_max_overflow."""
    assert pool._max_overflow == settings.db_max_overflow, (
        f"Expected max_overflow={settings.db_max_overflow}, got {pool._max_overflow}"
    )


# ─── Test 3: pool_recycle ─────────────────────────────────────────────────────


def test_pool_recycle_matches_config(settings):
    """Engine pool_recycle must match settings.db_pool_recycle."""
    actual_recycle = engine.sync_engine.pool._recycle
    assert actual_recycle == settings.db_pool_recycle, (
        f"Expected pool_recycle={settings.db_pool_recycle}, got {actual_recycle}"
    )
