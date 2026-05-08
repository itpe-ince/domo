"""Admin Diversity Config API — Phase 10 K-2.

GET   /admin/diversity-config         — 모든 diversity_configs 목록 조회 (admin 전용)
PATCH /admin/diversity-config/{name}  — 특정 설정 수정 (admin 전용, 즉시 적용)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User
from app.services.audit_log import record_audit

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/diversity-config", tags=["admin-diversity"])


# ──────────────────────────────────────────────────────────────────────────────
# 응답 스키마
# ──────────────────────────────────────────────────────────────────────────────

class DiversityConfigOut(BaseModel):
    """diversity_configs 행 응답 스키마."""
    id: str
    name: str
    emerging_artist_boost: float
    genre_min_diversity: int
    region_min_diversity: int
    top_k_window: int
    candidate_pool_size: int
    status: str
    created_at: str
    updated_at: str


class DiversityConfigPatch(BaseModel):
    """PATCH 요청 본문 — 부분 수정 가능."""
    emerging_artist_boost: Optional[float] = Field(
        None,
        ge=1.0,
        le=2.0,
        description="신진작가 스코어 배수 (1.0 ~ 2.0, 과도한 부스팅 방지)",
    )
    genre_min_diversity: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="top_k_window 내 최소 unique 장르 수 (1 ~ 10)",
    )
    region_min_diversity: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="top_k_window 내 최소 unique 지역 수 (1 ~ 10)",
    )
    top_k_window: Optional[int] = Field(
        None,
        ge=10,
        le=50,
        description="다양성 제약 적용 window 크기 (10 ~ 50)",
    )
    candidate_pool_size: Optional[int] = Field(
        None,
        ge=20,
        le=500,
        description="K-1에서 가져올 후보 수 (20 ~ 500)",
    )


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _row_to_out(row) -> DiversityConfigOut:
    """DB row → DiversityConfigOut 변환."""
    return DiversityConfigOut(
        id=str(row.id),
        name=row.name,
        emerging_artist_boost=float(row.emerging_artist_boost),
        genre_min_diversity=int(row.genre_min_diversity),
        region_min_diversity=int(row.region_min_diversity),
        top_k_window=int(row.top_k_window),
        candidate_pool_size=int(row.candidate_pool_size),
        status=row.status,
        created_at=row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
        updated_at=row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else str(row.updated_at),
    )


# ──────────────────────────────────────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[DiversityConfigOut])
async def list_diversity_configs(
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """모든 diversity_configs 목록 조회 (admin 전용).

    현재 active/archived 모든 설정을 반환한다.
    운영 중 가중치 확인 및 히스토리 조회에 사용.
    """
    result = await db.execute(
        text("""
            SELECT
                id, name, emerging_artist_boost, genre_min_diversity,
                region_min_diversity, top_k_window, candidate_pool_size,
                status, created_at, updated_at
            FROM diversity_configs
            ORDER BY name ASC, created_at DESC
        """)
    )
    rows = result.fetchall()
    return [_row_to_out(row) for row in rows]


@router.patch("/{name}", response_model=DiversityConfigOut)
async def patch_diversity_config(
    name: str,
    body: DiversityConfigPatch,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """특정 diversity_config 수정 (admin 전용, 즉시 적용).

    부분 수정 가능 — 명시한 필드만 업데이트.
    수정 즉시 새 피드 요청부터 적용됨 (Redis cache TTL 5분 후 완전 반영).
    """
    # 수정할 필드 동적 생성
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise ApiError("VALIDATION_ERROR", "수정할 필드가 없습니다.", http_status=400)

    # 해당 config 존재 여부 확인
    check_result = await db.execute(
        text("""
            SELECT id, emerging_artist_boost, genre_min_diversity,
                   region_min_diversity, top_k_window, candidate_pool_size
            FROM diversity_configs WHERE name = :name
        """),
        {"name": name},
    )
    existing = check_result.fetchone()
    if existing is None:
        raise ApiError("NOT_FOUND", f"diversity_config '{name}'을 찾을 수 없습니다.", http_status=404)

    # before 상태 저장
    before_values = {k: getattr(existing, k, None) for k in updates}

    # SET 절 동적 생성
    set_clauses = ", ".join(f"{col} = :{col}" for col in updates)
    set_clauses += ", updated_at = now()"
    params = {**updates, "name": name}

    await db.execute(
        text(f"UPDATE diversity_configs SET {set_clauses} WHERE name = :name"),
        params,
    )
    await db.commit()

    log.info(
        "admin diversity_config 수정: name=%s, fields=%s, admin=%s",
        name, list(updates.keys()), admin.id,
    )
    await record_audit(
        db,
        actor=admin,
        action="admin.diversity_config_update",
        target_type="diversity_config",
        metadata={"name": name, "before": before_values, "after": updates},
        request=request,
    )

    # 수정된 row 반환
    result = await db.execute(
        text("""
            SELECT
                id, name, emerging_artist_boost, genre_min_diversity,
                region_min_diversity, top_k_window, candidate_pool_size,
                status, created_at, updated_at
            FROM diversity_configs
            WHERE name = :name
        """),
        {"name": name},
    )
    updated_row = result.fetchone()
    return _row_to_out(updated_row)
