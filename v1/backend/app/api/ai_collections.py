"""AI 큐레이션 컬렉션 공개 API — Phase 10 K-7.

Editor's Pick: AI가 매주 자동 생성한 주제별 컬렉션을 공개한다.

README 비전 "스토리텔링 hub" 직접 구현:
  - GET /ai-collections         — 활성 컬렉션 목록 (공개, 인증 불필요)
  - GET /ai-collections/{id}    — 컬렉션 상세 + 작품 리스트 (공개)
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.db.session import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-collections", tags=["ai-collections"])

_VALID_LOCALES = {"ko", "en", "ja", "zh", "es"}


def _localize(row_dict: dict, locale: str) -> tuple[str | None, str | None]:
    """locale에 맞는 제목/설명 반환.

    ko 또는 번역 없으면 원본 한국어 반환.
    """
    title = row_dict.get("title")
    description = row_dict.get("description")

    if locale and locale != "ko" and locale in _VALID_LOCALES:
        title_tr = row_dict.get("title_translations") or {}
        desc_tr = row_dict.get("description_translations") or {}
        title = title_tr.get(locale) or title
        description = desc_tr.get(locale) or description

    return title, description


@router.get("")
async def list_ai_collections(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=20),
    locale: str = Query("ko"),
    db: AsyncSession = Depends(get_db),
):
    """활성(published) AI 큐레이션 컬렉션 목록.

    인증 불필요. locale 파라미터로 번역 자동 매칭.
    """
    if locale not in _VALID_LOCALES:
        locale = "ko"

    offset = (page - 1) * limit

    # published 컬렉션 총 개수
    count_result = await db.execute(text("""
        SELECT COUNT(*) FROM ai_collections WHERE status = 'published'
    """))
    total = count_result.scalar() or 0

    # published 컬렉션 목록 (최신순)
    rows_result = await db.execute(text("""
        SELECT
            ac.id,
            ac.week_start,
            ac.theme,
            ac.title,
            ac.description,
            ac.title_translations,
            ac.description_translations,
            ac.cover_post_id,
            ac.published_at,
            COUNT(acp.post_id) AS post_count
        FROM ai_collections ac
        LEFT JOIN ai_collection_posts acp ON acp.collection_id = ac.id
        WHERE ac.status = 'published'
        GROUP BY ac.id
        ORDER BY ac.published_at DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset})
    rows = rows_result.fetchall()

    items = []
    for r in rows:
        row_dict = dict(r._mapping)
        title, description = _localize(row_dict, locale)

        # cover_post_id → 썸네일 URL 조회
        cover_image_url = None
        if r.cover_post_id:
            media_result = await db.execute(text("""
                SELECT m.url FROM media m
                JOIN posts p ON p.id = :post_id
                WHERE m.post_id = :post_id AND m.type = 'image'
                ORDER BY m.order_index ASC
                LIMIT 1
            """), {"post_id": str(r.cover_post_id)})
            media_row = media_result.fetchone()
            if media_row:
                cover_image_url = media_row.url

        items.append({
            "id": str(r.id),
            "week_start": r.week_start.isoformat() if r.week_start else None,
            "theme": r.theme,
            "title": title,
            "description": description,
            "cover_image_url": cover_image_url,
            "post_count": r.post_count or 0,
            "published_at": r.published_at.isoformat() if r.published_at else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/{collection_id}")
async def get_ai_collection(
    collection_id: UUID,
    locale: str = Query("ko"),
    db: AsyncSession = Depends(get_db),
):
    """AI 큐레이션 컬렉션 상세 + 작품 리스트 (position 순).

    인증 불필요. published 상태가 아니면 404 반환.
    """
    if locale not in _VALID_LOCALES:
        locale = "ko"

    # 컬렉션 조회 (published 상태만)
    coll_result = await db.execute(text("""
        SELECT
            id, week_start, theme, title, description,
            title_translations, description_translations,
            cover_post_id, status, published_at
        FROM ai_collections
        WHERE id = :cid AND status = 'published'
    """), {"cid": str(collection_id)})
    coll = coll_result.fetchone()
    if not coll:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    coll_dict = dict(coll._mapping)
    title, description = _localize(coll_dict, locale)

    # cover_post_id → 썸네일 URL
    cover_image_url = None
    if coll.cover_post_id:
        media_result = await db.execute(text("""
            SELECT m.url FROM media m
            WHERE m.post_id = :post_id AND m.type = 'image'
            ORDER BY m.order_index ASC
            LIMIT 1
        """), {"post_id": str(coll.cover_post_id)})
        media_row = media_result.fetchone()
        if media_row:
            cover_image_url = media_row.url

    # 작품 리스트 (position 순)
    posts_result = await db.execute(text("""
        SELECT
            acp.position,
            acp.post_id,
            p.title AS post_title,
            p.author_id,
            u.display_name AS author_name,
            u.avatar_url AS author_avatar
        FROM ai_collection_posts acp
        JOIN posts p ON p.id = acp.post_id
        JOIN users u ON u.id = p.author_id
        WHERE acp.collection_id = :cid
        ORDER BY acp.position ASC
    """), {"cid": str(collection_id)})
    post_rows = posts_result.fetchall()

    # 각 작품 썸네일 조회
    posts_list = []
    for pr in post_rows:
        thumb_result = await db.execute(text("""
            SELECT url FROM media
            WHERE post_id = :pid AND type = 'image'
            ORDER BY order_index ASC
            LIMIT 1
        """), {"pid": str(pr.post_id)})
        thumb_row = thumb_result.fetchone()

        posts_list.append({
            "position": pr.position,
            "post_id": str(pr.post_id),
            "title": pr.post_title,
            "thumbnail_url": thumb_row.url if thumb_row else None,
            "author": {
                "id": str(pr.author_id),
                "name": pr.author_name,
                "avatar_url": pr.author_avatar,
            },
        })

    return {
        "id": str(coll.id),
        "week_start": coll.week_start.isoformat() if coll.week_start else None,
        "theme": coll.theme,
        "title": title,
        "description": description,
        "cover_image_url": cover_image_url,
        "published_at": coll.published_at.isoformat() if coll.published_at else None,
        "posts": posts_list,
    }
