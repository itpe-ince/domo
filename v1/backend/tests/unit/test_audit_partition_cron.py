"""Unit tests — audit_partition_cron (Phase 13 B-2).

테스트 항목:
  1. _partition_name: 파티션 이름 생성 규칙 (audit_logs_YYYY_MM 형식)
  2. _next_month: 12월 → 다음 해 1월 처리 (연말 경계)
  3. _next_month: 일반 월 처리 (1~11월)
  4. _partition_range: FROM/TO 경계 문자열 정확성
  5. create_next_month_audit_partition: 파티션 이미 존재 시 skip (멱등성)
  6. create_next_month_audit_partition: 파티션 미존재 시 CREATE + COMMIT 호출
  7. _partition_name + _next_month 조합: end-to-end 이름 생성
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 import
# ──────────────────────────────────────────────────────────────────────────────

from app.services.audit_partition_cron import (
    _next_month,
    _partition_name,
    _partition_range,
    create_next_month_audit_partition,
)


# ──────────────────────────────────────────────────────────────────────────────
# 1. _partition_name — 파티션 이름 생성 규칙
# ──────────────────────────────────────────────────────────────────────────────

def test_partition_name_format():
    """audit_logs_YYYY_MM 형식이어야 한다."""
    assert _partition_name(date(2026, 6, 1)) == "audit_logs_2026_06"
    assert _partition_name(date(2026, 12, 1)) == "audit_logs_2026_12"
    assert _partition_name(date(2027, 1, 1)) == "audit_logs_2027_01"


def test_partition_name_zero_padded_month():
    """1~9월은 0-padded (01, 02, ..., 09)."""
    for month in range(1, 10):
        name = _partition_name(date(2026, month, 1))
        assert f"_{month:02d}" in name, f"month={month} should be zero-padded"


# ──────────────────────────────────────────────────────────────────────────────
# 2. _next_month — 12월 → 다음 해 1월 (연말 경계)
# ──────────────────────────────────────────────────────────────────────────────

def test_next_month_december_wraps_to_january():
    """12월이면 다음 해 1월 1일을 반환한다."""
    result = _next_month(date(2026, 12, 15))
    assert result == date(2027, 1, 1)


def test_next_month_december_last_day():
    """12월 31일도 동일하게 다음 해 1월 1일."""
    result = _next_month(date(2026, 12, 31))
    assert result == date(2027, 1, 1)


# ──────────────────────────────────────────────────────────────────────────────
# 3. _next_month — 일반 월 처리 (1~11월)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("month,expected_month", [
    (1, 2), (5, 6), (11, 12),
])
def test_next_month_normal(month, expected_month):
    """1~11월 → 같은 해 다음 달 1일."""
    today = date(2026, month, 15)
    result = _next_month(today)
    assert result.year == 2026
    assert result.month == expected_month
    assert result.day == 1


# ──────────────────────────────────────────────────────────────────────────────
# 4. _partition_range — FROM/TO 경계 문자열
# ──────────────────────────────────────────────────────────────────────────────

def test_partition_range_june():
    """2026-06 파티션의 경계: FROM 2026-06-01, TO 2026-07-01."""
    from_date, to_date = _partition_range(date(2026, 6, 1))
    assert from_date == "2026-06-01"
    assert to_date == "2026-07-01"


def test_partition_range_december():
    """12월 파티션 경계: FROM 2026-12-01, TO 2027-01-01 (연말 처리)."""
    from_date, to_date = _partition_range(date(2026, 12, 1))
    assert from_date == "2026-12-01"
    assert to_date == "2027-01-01"


# ──────────────────────────────────────────────────────────────────────────────
# 5. create_next_month_audit_partition — 이미 존재 시 skip (멱등성)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_partition_skip_if_exists():
    """파티션이 이미 존재하면 None 반환, execute 미호출, commit 미호출.

    _partition_exists 와 date.today 를 patch하여 격리 테스트.
    """
    mock_db = AsyncMock()

    with (
        patch(
            "app.services.audit_partition_cron._partition_exists",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.services.audit_partition_cron.date"
        ) as mock_date_cls,
    ):
        # today() 반환값 → 실제 date 객체 (생성자는 original)
        mock_date_cls.today.return_value = date(2026, 5, 9)
        # date() 생성자 호출은 실제 date 클래스로 위임
        mock_date_cls.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        result = await create_next_month_audit_partition(mock_db)

    assert result is None
    mock_db.execute.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


# ──────────────────────────────────────────────────────────────────────────────
# 6. create_next_month_audit_partition — 파티션 미존재 시 CREATE + COMMIT
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_partition_creates_when_missing():
    """파티션 미존재 시 CREATE TABLE DDL execute + commit 호출 + 파티션 이름 반환.

    _partition_exists를 False로 patch, date.today를 고정.
    """
    mock_db = AsyncMock()

    with (
        patch(
            "app.services.audit_partition_cron._partition_exists",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.services.audit_partition_cron.date"
        ) as mock_date_cls,
    ):
        mock_date_cls.today.return_value = date(2026, 5, 9)
        # date() 생성자는 실제 date로 위임 (_next_month 내부 date(...) 호출 보호)
        mock_date_cls.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

        result = await create_next_month_audit_partition(mock_db)

    # 다음 달: 2026-06 → audit_logs_2026_06
    assert result == "audit_logs_2026_06"
    # CREATE TABLE DDL execute 1회 + commit 1회
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────────────────
# 7. end-to-end 이름 생성 조합 (_partition_name + _next_month)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("today,expected_name", [
    (date(2026, 5, 9),  "audit_logs_2026_06"),
    (date(2026, 11, 1), "audit_logs_2026_12"),
    (date(2026, 12, 1), "audit_logs_2027_01"),
    (date(2027, 1, 31), "audit_logs_2027_02"),
])
def test_next_partition_name_e2e(today, expected_name):
    """today 기준 다음 달 파티션 이름이 정확히 생성된다."""
    next_first = _next_month(today)
    name = _partition_name(next_first)
    assert name == expected_name
