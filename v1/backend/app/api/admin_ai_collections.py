"""Admin AI 큐레이션 컬렉션 검수 API — Phase 10 K-7 / Phase 11 A-2 보강.

LLM이 자동 생성한 컬렉션을 admin이 검수하고 공개/보류하는 워크플로우.
autopublish OFF 정책 — 모든 AI 생성 컬렉션은 admin 검수 후 공개된다.

Phase 7 G'-7 admin 검수 큐 패턴 계승:
  - GET   /admin/ai-collections/queue        — 검수 대기 목록 (week_start 필터 지원)
  - POST  /admin/ai-collections/{id}/publish — 공개 (generating → published)
  - POST  /admin/ai-collections/{id}/archive — 보류 (generating → archived)
  - PATCH /admin/ai-collections/{id}         — 제목/설명 편집 + 5 locale 재번역 (A-2 신규)
  - DELETE /admin/ai-collections/{id}        — 완전 삭제 (reason 필수, A-2 신규)

PATCH published 정책:
  published 상태도 편집 허용 (오타 정정 등 실용적 필요).
  대규모 변경은 archive 후 재생성을 권장하지만 강제하지 않는다.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User
from app.services.audit_log import record_audit

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai-collections", tags=["admin-ai-collections"])

# 번역 대상 locale (한국어 원본 제외)
_TARGET_LOCALES = ["en", "ja", "zh", "es"]


class AdminCollectionActionRequest(BaseModel):
    admin_note: str | None = None


class CollectionPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    retranslate: bool = True  # 한국어 변경 시 5 locale 자동 재번역


class CollectionDeleteRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)


@router.get("/queue")
async def admin_get_collection_queue(
    week_start: date | None = Query(default=None),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """generating/pending 상태 컬렉션 목록 (admin 검수 큐).

    week_start 지정 시 해당 주에 생성된 컬렉션만 반환.
    미지정 시 현재 주 (월요일 00:00 UTC ~ 일요일 23:59 UTC) 자동 계산.
    생성 시각 최신순 반환. 검수 후 publish 또는 archive한다.
    """
    # week_start 미지정 시 이번 주 월요일 자동 계산
    if week_start is None:
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=7)

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
        WHERE ac.status IN ('generating', 'pending')
          AND ac.generated_at >= :week_start
          AND ac.generated_at < :week_end
        GROUP BY ac.id
        ORDER BY ac.generated_at DESC
    """), {
        "week_start": datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc),
        "week_end": datetime.combine(week_end, datetime.min.time()).replace(tzinfo=timezone.utc),
    })
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

    return {"items": items, "week_start": week_start.isoformat()}


@router.post("/{collection_id}/publish")
async def admin_publish_collection(
    collection_id: UUID,
    request: Request,
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
    await record_audit(
        db,
        actor=admin,
        action="admin.ai_collection_publish",
        target_type="ai_collection",
        target_id=collection_id,
        metadata={"collection_id": str(collection_id)},
        request=request,
    )
    return {
        "id": str(collection_id),
        "status": "published",
        "published_at": now.isoformat(),
    }


@router.post("/{collection_id}/archive")
async def admin_archive_collection(
    collection_id: UUID,
    request: Request,
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
    await record_audit(
        db,
        actor=admin,
        action="admin.ai_collection_archive",
        target_type="ai_collection",
        target_id=collection_id,
        metadata={"collection_id": str(collection_id)},
        request=request,
    )
    return {
        "id": str(collection_id),
        "status": "archived",
    }


@router.patch("/{collection_id}")
async def patch_collection(
    collection_id: UUID,
    body: CollectionPatchRequest,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """AI 컬렉션 제목/설명 편집 (admin 검수 시).

    published 포함 모든 상태 편집 허용 (오타 정정 등).
    한국어 원본 변경 시 retranslate=True (default)면 translation_cache 활용해
    5 locale (ko/en/ja/zh/es) 자동 재번역. LLM 미설정 시 graceful (한국어만 갱신).
    """
    # 1. 컬렉션 조회
    coll_result = await db.execute(text("""
        SELECT id, title, description, title_translations, description_translations, status
        FROM ai_collections
        WHERE id = :cid
    """), {"cid": str(collection_id)})
    coll = coll_result.fetchone()
    if not coll:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    # 2. 변경할 필드 결정 (None이면 기존 값 유지)
    new_title = body.title if body.title is not None else coll.title
    new_description = body.description if body.description is not None else coll.description

    title_changed = body.title is not None and body.title != coll.title
    desc_changed = body.description is not None and body.description != coll.description

    # 3. 기존 translations 로드
    existing_title_tr = dict(coll.title_translations) if coll.title_translations else {}
    existing_desc_tr = dict(coll.description_translations) if coll.description_translations else {}

    # 4. retranslate=True이고 한국어 원본이 변경된 경우 재번역
    if body.retranslate and (title_changed or desc_changed):
        try:
            from app.services.translation_cache import get_cached_translation, save_translation
            from app.services.llm_gateway import LLMGatewayClient

            llm = LLMGatewayClient()

            for locale in _TARGET_LOCALES:
                # 제목 재번역
                if title_changed and new_title:
                    cached = await get_cached_translation(db, new_title, "ko", locale)
                    if cached:
                        existing_title_tr[locale] = cached
                    elif not llm.is_mock:
                        try:
                            res = await llm.generate_interview(
                                f"다음 한국어 텍스트를 {locale} 언어로 번역해주세요. "
                                f"번역 결과만 출력하세요:\n{new_title}",
                                max_tokens=100,
                                temperature=0.3,
                            )
                            translated = res.get("content", "").strip()
                            if translated:
                                existing_title_tr[locale] = translated
                                await save_translation(
                                    db, new_title, "ko", locale, translated,
                                    model_version=llm.model,
                                )
                        except Exception as exc:
                            log.warning(
                                "admin_ai_collections: PATCH title translation to %s failed: %s",
                                locale, exc,
                            )

                # 설명 재번역
                if desc_changed and new_description:
                    cached = await get_cached_translation(db, new_description, "ko", locale)
                    if cached:
                        existing_desc_tr[locale] = cached
                    elif not llm.is_mock:
                        try:
                            res = await llm.generate_interview(
                                f"다음 한국어 텍스트를 {locale} 언어로 번역해주세요. "
                                f"번역 결과만 출력하세요:\n{new_description}",
                                max_tokens=300,
                                temperature=0.3,
                            )
                            translated = res.get("content", "").strip()
                            if translated:
                                existing_desc_tr[locale] = translated
                                await save_translation(
                                    db, new_description, "ko", locale, translated,
                                    model_version=llm.model,
                                )
                        except Exception as exc:
                            log.warning(
                                "admin_ai_collections: PATCH desc translation to %s failed: %s",
                                locale, exc,
                            )

            if llm.is_mock:
                log.warning(
                    "admin_ai_collections: PATCH retranslate=True but LLM Gateway not configured "
                    "— Korean original updated, 4 locales unchanged (id=%s)",
                    collection_id,
                )
        except Exception as exc:
            log.warning(
                "admin_ai_collections: PATCH translation setup failed — graceful skip: %s", exc
            )

    # 5. DB 갱신
    await db.execute(text("""
        UPDATE ai_collections
        SET title = :title,
            description = :description,
            title_translations = :title_tr::jsonb,
            description_translations = :desc_tr::jsonb
        WHERE id = :cid
    """), {
        "cid": str(collection_id),
        "title": new_title,
        "description": new_description,
        "title_tr": json.dumps(existing_title_tr, ensure_ascii=False),
        "desc_tr": json.dumps(existing_desc_tr, ensure_ascii=False),
    })
    await db.commit()

    log.info(
        "AUDIT action=admin_patch_collection admin=%s id=%s retranslated=%s",
        admin.id, collection_id, body.retranslate and (title_changed or desc_changed),
    )
    changed_fields = []
    if title_changed:
        changed_fields.append("title")
    if desc_changed:
        changed_fields.append("description")
    await record_audit(
        db,
        actor=admin,
        action="admin.ai_collection_edit",
        target_type="ai_collection",
        target_id=collection_id,
        metadata={"collection_id": str(collection_id), "changed_fields": changed_fields},
        request=request,
    )
    return {
        "id": str(collection_id),
        "status": coll.status,
        "title": new_title,
        "description": new_description,
        "title_translations": existing_title_tr,
        "description_translations": existing_desc_tr,
    }


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: UUID,
    body: CollectionDeleteRequest,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """AI 컬렉션 거부 (완전 삭제). reject 사유 필수.

    published 상태도 삭제 허용 (잘못 publish된 경우 회수).
    ai_collection_posts는 FK CASCADE로 자동 삭제.
    Audit log에 reason 기록 (모델 학습 negative signal).
    """
    # 1. 컬렉션 조회
    coll_result = await db.execute(text("""
        SELECT id, status FROM ai_collections WHERE id = :cid
    """), {"cid": str(collection_id)})
    coll = coll_result.fetchone()
    if not coll:
        raise ApiError("NOT_FOUND", "Collection not found", http_status=404)

    # 2. 완전 삭제 (ai_collection_posts FK CASCADE로 자동 삭제)
    await db.execute(text("""
        DELETE FROM ai_collections WHERE id = :cid
    """), {"cid": str(collection_id)})
    await db.commit()

    log.info(
        "AUDIT action=admin_reject_collection admin=%s id=%s reason=%s",
        admin.id, collection_id, body.reason[:100],
    )
    await record_audit(
        db,
        actor=admin,
        action="admin.ai_collection_delete",
        target_type="ai_collection",
        target_id=collection_id,
        metadata={"collection_id": str(collection_id), "reason": body.reason},
        request=request,
    )
    return {"data": {"id": str(collection_id), "deleted": True}}
