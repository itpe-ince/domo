"""Admin AI 큐레이션 컬렉션 검수 API — Phase 10 K-7.

LLM이 자동 생성한 컬렉션을 admin이 검수하고 공개/보류하는 워크플로우.
autopublish OFF 정책 — 모든 AI 생성 컬렉션은 admin 검수 후 공개된다.

Phase 7 G'-7 admin 검수 큐 패턴 계승:
  - GET  /admin/ai-collections/queue        — 검수 대기 목록 (generating 상태)
  - POST /admin/ai-collections/{id}/publish — 공개 (generating → published)
  - POST /admin/ai-collections/{id}/archive — 보류 (generating → archived)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai-collections", tags=["admin-ai-collections"])


class AdminCollectionActionRequest(BaseModel):
    admin_note: str | None = None


@router.get("/queue")
async def admin_get_collection_queue(
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """generating 상태 컬렉션 목록 (admin 검수 큐).

    생성 시각 최신순 반환. 검수 후 publish 또는 archive한다.
    """
    rows_result = await db.execute(text("""
        SELECT
            ac.id,
            ac.week_start,
            ac.theme,
            ac.title,
            ac.description,
            ac.title_translations,
            ac.description_translations,
            ac.cluster_k,
            ac.llm_model_version,
            ac.generated_at,
            COUNT(acp.post_id) AS post_count
        FROM ai_collections ac
        LEFT JOIN ai_collection_posts acp ON acp.collection_id = ac.id
        WHERE ac.status = 'generating'
        GROUP BY ac.id
        ORDER BY ac.generated_at DESC
    """))
    rows = rows_result.fetchall()

    items = []
    for r in rows:
        items.append({
            "id": str(r.id),
            "week_start": r.week_start.isoformat() if r.week_start else None,
            "theme": r.theme,
            "title": r.title,
            "description": r.description,
            "title_translations": dict(r.title_translations) if r.title_translations else {},
            "description_translations": dict(r.description_translations) if r.description_translations else {},
            "cluster_k": r.cluster_k,
            "llm_model_version": r.llm_model_version,
            "post_count": r.post_count or 0,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        })

    return {"items": items}


@router.post("/{collection_id}/publish")
async def admin_publish_collection(
    collection_id: UUID,
    body: AdminCollectionActionRequest | None = None,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """컬렉션 공개. status: generating → published, published_at 설정.

    이미 published 상태이면 409 반환.
    """
    # 컬렉션 존재 확인
    coll_result = await db.execute(text("""
        SELECT id, status FROM ai_collections WHERE id = :cid
    """), {"cid": str(collection_id)})
    coll = coll_result.fetchone()
    if not coll:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    if coll.status == "published":
        raise ApiError(
            "ALREADY_PUBLISHED", "Collection is already published", http_status=409
        )

    now = datetime.now(timezone.utc)
    admin_note = (body.admin_note if body else None) or None

    await db.execute(text("""
        UPDATE ai_collections
        SET status = 'published',
            published_at = :now,
            admin_note = COALESCE(:note, admin_note)
        WHERE id = :cid
    """), {
        "cid": str(collection_id),
        "now": now,
        "note": admin_note,
    })
    await db.commit()

    log.info(
        "admin_ai_collections: published collection_id=%s by admin_id=%s",
        collection_id, admin.id,
    )
    return {
        "id": str(collection_id),
        "status": "published",
        "published_at": now.isoformat(),
    }


@router.post("/{collection_id}/archive")
async def admin_archive_collection(
    collection_id: UUID,
    body: AdminCollectionActionRequest | None = None,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """컬렉션 보류(숨김). status: generating → archived.

    공개 API에서 더 이상 조회되지 않는다.
    """
    # 컬렉션 존재 확인
    coll_result = await db.execute(text("""
        SELECT id, status FROM ai_collections WHERE id = :cid
    """), {"cid": str(collection_id)})
    coll = coll_result.fetchone()
    if not coll:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    admin_note = (body.admin_note if body else None) or None

    await db.execute(text("""
        UPDATE ai_collections
        SET status = 'archived',
            admin_note = COALESCE(:note, admin_note)
        WHERE id = :cid
    """), {
        "cid": str(collection_id),
        "note": admin_note,
    })
    await db.commit()

    log.info(
        "admin_ai_collections: archived collection_id=%s by admin_id=%s",
        collection_id, admin.id,
    )
    return {
        "id": str(collection_id),
        "status": "archived",
    }
