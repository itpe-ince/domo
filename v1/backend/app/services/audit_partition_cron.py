"""audit_logs 월별 파티션 자동 생성 cron — Phase 13 B-2.

다음 달 파티션이 없으면 생성, 이미 있으면 skip (멱등성 보장).
매일 실행되지만 파티션 생성은 한 달에 한 번만 실질적으로 동작.

DEFAULT 파티션이 존재하므로 파티션 누락 시 데이터 손실은 없지만,
DEFAULT 파티션으로 라우팅된 행은 partition pruning 혜택을 받지 못함.

Pattern: audit_log_cleanup_jobs.py 동일 패턴 (asyncio loop + AsyncSessionLocal)
"""
from __future__ import annotations

import asyncio
import logging
from calendar import monthrange
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.cron_monitor import record_cron_run as _push_cron_status

log = logging.getLogger(__name__)


def _next_month(today: date) -> date:
    """오늘 날짜 기준 다음 달의 첫째 날을 반환한다.

    12월이면 다음 해 1월로 처리.

    Args:
        today: 기준 날짜 (주로 date.today(), 테스트 시 주입 가능)

    Returns:
        다음 달 1일 (예: 2026-05-09 → 2026-06-01)
    """
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def _partition_name(target: date) -> str:
    """파티션 이름 생성.

    Args:
        target: 파티션 대상 달의 1일

    Returns:
        예: 2026-06-01 → "audit_logs_2026_06"
    """
    return f"audit_logs_{target.year}_{target.month:02d}"


def _partition_range(target: date) -> tuple[str, str]:
    """파티션 경계 날짜 문자열 반환 (FROM, TO).

    Args:
        target: 파티션 대상 달의 1일

    Returns:
        (from_date, to_date) 형식 — 예: ("2026-06-01", "2026-07-01")
    """
    from_date = target.strftime("%Y-%m-%d")
    # 다음 달 1일 계산 (월말 경계 처리)
    if target.month == 12:
        to_date = date(target.year + 1, 1, 1).strftime("%Y-%m-%d")
    else:
        to_date = date(target.year, target.month + 1, 1).strftime("%Y-%m-%d")
    return from_date, to_date


async def _partition_exists(db: AsyncSession, partition_name: str) -> bool:
    """pg_class를 조회해 파티션 존재 여부를 확인한다.

    Args:
        db: AsyncSession
        partition_name: 확인할 파티션 테이블명

    Returns:
        True if partition exists, False otherwise
    """
    result = await db.execute(
        text(
            "SELECT 1 FROM pg_class "
            "WHERE relname = :name AND relkind = 'r'"
        ),
        {"name": partition_name},
    )
    return result.scalar() is not None


async def create_next_month_audit_partition(db: AsyncSession) -> str | None:
    """다음 달 audit_logs 파티션을 생성한다.

    이미 존재하면 skip (멱등). 생성 시 파티션 이름 반환, skip 시 None 반환.

    Args:
        db: AsyncSession — 트랜잭션 커밋은 이 함수가 담당

    Returns:
        생성된 파티션 이름 또는 None (skip)
    """
    today = date.today()
    next_month_first = _next_month(today)
    partition_name = _partition_name(next_month_first)
    from_date, to_date = _partition_range(next_month_first)

    if await _partition_exists(db, partition_name):
        log.debug(
            "audit_partition: %s already exists, skip",
            partition_name,
        )
        return None

    # CREATE TABLE ... PARTITION OF는 DDL이므로 autocommit 필요
    # AsyncSession의 경우 execute 후 commit 호출
    await db.execute(
        text(
            f"CREATE TABLE {partition_name} "  # noqa: S608 — DDL, not user input
            f"PARTITION OF audit_logs "
            f"FOR VALUES FROM ('{from_date}') TO ('{to_date}')"
        )
    )
    await db.commit()

    log.info(
        "audit_partition: created %s (FROM %s TO %s)",
        partition_name,
        from_date,
        to_date,
    )
    return partition_name


async def audit_partition_cron_loop(interval_seconds: int = 86400) -> None:
    """Background task — 매일 1회 실행하여 다음 달 파티션을 미리 생성.

    25번째 cron worker. main.py lifespan에서 등록.
    interval_seconds 기본값 86400 (1일).

    월별 파티션 생성은 실질적으로 달이 바뀔 때만 동작하지만,
    매일 실행으로 누락 복구도 겸한다.
    """
    log.info(
        "audit_partition_cron_loop started (interval=%ss)",
        interval_seconds,
    )
    while True:
        await _push_cron_status("audit_partition", "running")
        try:
            async with AsyncSessionLocal() as db:
                result = await create_next_month_audit_partition(db)
                if result:
                    log.info(
                        "audit_partition_cron: new partition created → %s",
                        result,
                    )
            await _push_cron_status("audit_partition", "success")
        except Exception as e:  # noqa: BLE001
            log.exception("audit_partition cron failed: %s", e)
            await _push_cron_status("audit_partition", "failed", error=str(e)[:500])
        await asyncio.sleep(interval_seconds)
