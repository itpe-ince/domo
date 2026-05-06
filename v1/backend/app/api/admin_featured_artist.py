"""Admin Featured Artist 후보 검수 큐 API — Phase 10 K-4.

GET  /admin/featured-artist/candidates           — pending 후보 목록
POST /admin/featured-artist/candidates/{id}/approve  — status='approved'
POST /admin/featured-artist/candidates/{id}/publish  — featured_artists INSERT + status='published'
POST /admin/featured-artist/candidates/{id}/reject   — status='rejected' + 사유 저장

모든 엔드포인트: admin 전용 (require_admin_with_2fa).
autopublish OFF 정책: approve 후 별도 publish 액션 필수.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/featured-artist",
    tags=["admin-featured-artist"],
)


# ─── 스키마 ───────────────────────────────────────────────────────────────────

class RejectRequest(BaseModel):
    reason: str


class PublishRequest(BaseModel):
    notes: str | None = None


# ─── Helper ──────────────────────────────────────────────────────────────────

def _current_week_start() -> date:
    """이번 주 월요일 날짜 반환."""
    from datetime import timedelta

    today = date.today()
    return today - timedelta(days=today.weekday())


def _parse_uuid(value: str, field: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ApiError(
            "INVALID_ID", f"Invalid UUID format for {field}", http_status=422
        ) from exc


def _row_to_dict(row: Any) -> dict:
    """DB row → dict 변환."""
    return {
        "id": str(row.id),
        "artist_id": str(row.artist_id),
        "artist_name": getattr(row, "artist_name", None),
        "artist_avatar_url": getattr(row, "artist_avatar_url", None),
        "follower_count": getattr(row, "follower_count", None),
        "week_start": row.week_start.isoformat() if row.week_start else None,
        "composite_score": row.composite_score,
        "reasoning": row.reasoning if isinstance(row.reasoning, dict) else {},
        "status": row.status,
        "admin_id": str(row.admin_id) if row.admin_id else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ─── 1. GET candidates ───────────────────────────────────────────────────────

@router.get("/candidates")
async def list_candidates(
    week_start: str | None = Query(
        None, description="YYYY-MM-DD (optional, default: 이번 주 월요일)"
    ),
    status: str | None = Query(
        None, description="pending|approved|rejected|published (optional, default: pending)"
    ),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """현재 주 pending 후보 목록 반환 (admin 전용).

    week_start, status 필터 지원.
    """
    # week_start 파싱
    if week_start:
        try:
            parsed_week = date.fromisoformat(week_start)
        except ValueError as exc:
            raise ApiError(
                "INVALID_DATE",
                "week_start must be YYYY-MM-DD",
                http_status=422,
            ) from exc
    else:
        parsed_week = _current_week_start()

    # status 기본값 pending
    status_filter = status or "pending"
    valid_statuses = {"pending", "approved", "rejected", "published", "expired"}
    if status_filter not in valid_statuses:
        raise ApiError(
            "INVALID_STATUS",
            f"status must be one of: {', '.join(sorted(valid_statuses))}",
            http_status=422,
        )

    result = await db.execute(
        text("""
            SELECT
                fac.id,
                fac.artist_id,
                u.display_name   AS artist_name,
                u.avatar_url     AS artist_avatar_url,
                u.follower_count,
                fac.week_start,
                fac.composite_score,
                fac.reasoning,
                fac.status,
                fac.admin_id,
                fac.reviewed_at,
                fac.published_at,
                fac.created_at
            FROM featured_artist_candidates fac
            JOIN users u ON u.id = fac.artist_id
            WHERE fac.week_start = :week_start
              AND fac.status = :status
            ORDER BY fac.composite_score DESC
        """),
        {"week_start": parsed_week, "status": status_filter},
    )
    rows = result.fetchall()

    candidates = [_row_to_dict(r) for r in rows]
    return {
        "data": {
            "week_start": parsed_week.isoformat(),
            "candidates": candidates,
            "total": len(candidates),
        }
    }


# ─── 2. POST approve ─────────────────────────────────────────────────────────

@router.post("/candidates/{candidate_id}/approve")
async def approve_candidate(
    candidate_id: str,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """pending → approved 전환.

    이미 approved/rejected/published 상태면 409 Conflict.
    """
    cid = _parse_uuid(candidate_id)

    row = await db.execute(
        text("""
            SELECT id, status FROM featured_artist_candidates
            WHERE id = :id
        """),
        {"id": cid},
    )
    candidate = row.fetchone()

    if candidate is None:
        raise ApiError("NOT_FOUND", "Candidate not found", http_status=404)

    if candidate.status != "pending":
        raise ApiError(
            "CONFLICT",
            f"Candidate is already in '{candidate.status}' status",
            http_status=409,
        )

    now = datetime.now(timezone.utc)
    await db.execute(
        text("""
            UPDATE featured_artist_candidates
            SET status = 'approved',
                admin_id = :admin_id,
                reviewed_at = :reviewed_at
            WHERE id = :id
        """),
        {"id": cid, "admin_id": admin.id, "reviewed_at": now},
    )
    await db.commit()

    log.info(
        "AUDIT action=approve_featured_artist_candidate admin=%s candidate=%s",
        admin.id,
        cid,
    )
    return {
        "data": {
            "id": str(cid),
            "status": "approved",
            "admin_id": str(admin.id),
            "reviewed_at": now.isoformat(),
        }
    }


# ─── 3. POST publish ─────────────────────────────────────────────────────────

@router.post("/candidates/{candidate_id}/publish")
async def publish_candidate(
    candidate_id: str,
    body: PublishRequest = PublishRequest(),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """approved → published 전환 + featured_artists 테이블 INSERT (G'-7 통합).

    autopublish OFF 정책: approve 후 별도 publish 액션 필수.
    status != 'approved' 시 409 Conflict.
    """
    cid = _parse_uuid(candidate_id)

    row = await db.execute(
        text("""
            SELECT id, artist_id, status FROM featured_artist_candidates
            WHERE id = :id
        """),
        {"id": cid},
    )
    candidate = row.fetchone()

    if candidate is None:
        raise ApiError("NOT_FOUND", "Candidate not found", http_status=404)

    if candidate.status != "approved":
        raise ApiError(
            "CONFLICT",
            f"Candidate must be in 'approved' status before publishing (current: '{candidate.status}')",
            http_status=409,
        )

    now = datetime.now(timezone.utc)
    current_month = date(now.year, now.month, 1)

    # Phase 8 G'-7 featured_artists 테이블 INSERT
    fa_result = await db.execute(
        text("""
            INSERT INTO featured_artists
                (artist_id, month, curation_note, is_active, created_by_admin_id)
            VALUES (:artist_id, :month, :curation_note, true, :admin_id)
            RETURNING id
        """),
        {
            "artist_id": candidate.artist_id,
            "month": current_month,
            "curation_note": body.notes,
            "admin_id": admin.id,
        },
    )
    fa_row = fa_result.fetchone()
    featured_artist_id = str(fa_row.id) if fa_row else None

    # 후보 상태 published로 전환
    await db.execute(
        text("""
            UPDATE featured_artist_candidates
            SET status = 'published',
                published_at = :published_at,
                admin_id = :admin_id,
                reviewed_at = COALESCE(reviewed_at, :published_at)
            WHERE id = :id
        """),
        {"id": cid, "published_at": now, "admin_id": admin.id},
    )
    await db.commit()

    log.info(
        "AUDIT action=publish_featured_artist admin=%s candidate=%s featured_artist_id=%s",
        admin.id,
        cid,
        featured_artist_id,
    )
    return {
        "data": {
            "id": str(cid),
            "status": "published",
            "featured_artist_id": featured_artist_id,
            "published_at": now.isoformat(),
        }
    }


# ─── 4. POST reject ──────────────────────────────────────────────────────────

@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: str,
    body: RejectRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """pending 또는 approved → rejected 전환 + 사유 저장.

    reasoning JSONB에 reject_reason 키 merge.
    """
    cid = _parse_uuid(candidate_id)

    row = await db.execute(
        text("""
            SELECT id, status, reasoning FROM featured_artist_candidates
            WHERE id = :id
        """),
        {"id": cid},
    )
    candidate = row.fetchone()

    if candidate is None:
        raise ApiError("NOT_FOUND", "Candidate not found", http_status=404)

    if candidate.status not in ("pending", "approved"):
        raise ApiError(
            "CONFLICT",
            f"Cannot reject candidate in '{candidate.status}' status",
            http_status=409,
        )

    now = datetime.now(timezone.utc)

    # reasoning JSONB에 reject_reason merge
    existing_reasoning = (
        candidate.reasoning
        if isinstance(candidate.reasoning, dict)
        else {}
    )
    existing_reasoning["reject_reason"] = body.reason
    updated_reasoning = json.dumps(existing_reasoning)

    await db.execute(
        text("""
            UPDATE featured_artist_candidates
            SET status = 'rejected',
                admin_id = :admin_id,
                reviewed_at = :reviewed_at,
                reasoning = :reasoning::jsonb
            WHERE id = :id
        """),
        {
            "id": cid,
            "admin_id": admin.id,
            "reviewed_at": now,
            "reasoning": updated_reasoning,
        },
    )
    await db.commit()

    log.info(
        "AUDIT action=reject_featured_artist_candidate admin=%s candidate=%s reason=%s",
        admin.id,
        cid,
        body.reason,
    )
    return {
        "data": {
            "id": str(cid),
            "status": "rejected",
            "reviewed_at": now.isoformat(),
        }
    }
