"""Admin artist interview management — C-1 + C-3 booster.

POST   /admin/artist-interviews/generate             — trigger LLM generation (admin)
GET    /admin/artist-interviews                      — list with status filter (admin)
PATCH  /admin/artist-interviews/{id}                 — review: approve/reject + edit (admin)
POST   /admin/artist-interviews/{id}/publish         — publish after consent (admin)
POST   /admin/artist-interviews/{id}/translate       — C-3: translate to another locale (admin)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.artist_interview import ArtistInterview
from app.models.user import User
from app.schemas.artist_interview import (
    AdminGenerateInterviewRequest,
    AdminPatchInterviewRequest,
    ArtistInterviewOut,
)
from app.services.interview_generator import generate_artist_interview
from app.services.llm_gateway import LLMGatewayClient

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/artist-interviews", tags=["admin-interviews"])


def _row_to_out(row: ArtistInterview) -> dict:
    return ArtistInterviewOut(
        id=row.id,
        artist_id=row.artist_id,
        locale=row.locale,
        title=row.title,
        body_markdown=row.body_markdown,
        status=row.status,
        llm_model=row.llm_model,
        reviewed_by_admin_id=row.reviewed_by_admin_id,
        reviewed_at=row.reviewed_at,
        review_note=row.review_note,
        artist_consent_at=row.artist_consent_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


# ─── POST /admin/artist-interviews/generate ──────────────────────────────────


@router.post("/generate", status_code=201)
async def admin_generate_interview(
    body: AdminGenerateInterviewRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("interview_generate"),
):
    """Trigger LLM generation for an artist interview.

    - Rate-limited: 5/hour per admin (LLM cost protection).
    - Idempotent: returns existing draft/admin_review if generated within 24h.
    - Mock mode: when LLM_GATEWAY_API_KEY is not set, returns placeholder interview.
    """
    interview = await generate_artist_interview(
        db=db,
        artist_id=body.artist_id,
        locale=body.locale,
        admin_id=admin.id,
    )
    return {"data": _row_to_out(interview)}


# ─── GET /admin/artist-interviews ────────────────────────────────────────────


@router.get("")
async def admin_list_interviews(
    status: str | None = Query(
        None, pattern="^(draft|admin_review|approved|published|rejected|archived)$"
    ),
    artist_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """List artist interviews with optional status and artist filter.

    Default: returns up to 20, newest first.
    """
    stmt = (
        select(ArtistInterview)
        .order_by(ArtistInterview.created_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(ArtistInterview.status == status)
    if artist_id:
        try:
            aid = uuid.UUID(artist_id)
        except ValueError as exc:
            raise ApiError(
                "INVALID_ARTIST_ID", "artist_id must be a valid UUID", http_status=422
            ) from exc
        stmt = stmt.where(ArtistInterview.artist_id == aid)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"data": [_row_to_out(r) for r in rows]}


# ─── PATCH /admin/artist-interviews/{interview_id} ───────────────────────────


@router.patch("/{interview_id}")
async def admin_patch_interview(
    interview_id: str,
    body: AdminPatchInterviewRequest,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Review an interview: approve/reject + optional inline edits.

    Allowed status transitions:
      admin_review → approved | rejected
    Title and body_markdown can be edited by admin at any time (except published/archived).
    """
    try:
        iid = uuid.UUID(interview_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(ArtistInterview).where(ArtistInterview.id == iid)
    )
    interview = result.scalar_one_or_none()
    if interview is None:
        raise ApiError("NOT_FOUND", "Interview not found", http_status=404)

    if interview.status in ("published", "archived"):
        raise ApiError(
            "IMMUTABLE_STATUS",
            f"Cannot edit an interview with status '{interview.status}'",
            http_status=422,
        )

    if body.status is not None:
        # Validate transition
        if body.status in ("approved", "rejected") and interview.status not in (
            "admin_review",
            "draft",
        ):
            raise ApiError(
                "INVALID_TRANSITION",
                f"Cannot transition from '{interview.status}' to '{body.status}'",
                http_status=422,
            )
        interview.status = body.status
        interview.reviewed_by_admin_id = admin.id
        interview.reviewed_at = datetime.now(timezone.utc)

    if body.title is not None:
        interview.title = body.title
    if body.body_markdown is not None:
        interview.body_markdown = body.body_markdown
    if body.review_note is not None:
        interview.review_note = body.review_note

    await db.commit()
    await db.refresh(interview)

    log.info(
        "AUDIT action=admin_patch_interview admin=%s interview=%s status=%s",
        admin.id,
        iid,
        interview.status,
    )
    return {"data": _row_to_out(interview)}


# ─── POST /admin/artist-interviews/{interview_id}/publish ────────────────────


@router.post("/{interview_id}/publish")
async def admin_publish_interview(
    interview_id: str,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Publish an approved interview.

    Preconditions:
      1. status == 'approved'
      2. artist_consent_at IS NOT NULL (artist has opted in)

    Side effect: any previously published interview for the same
    (artist_id, locale) is moved to 'archived' status.
    """
    try:
        iid = uuid.UUID(interview_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(ArtistInterview).where(ArtistInterview.id == iid)
    )
    interview = result.scalar_one_or_none()
    if interview is None:
        raise ApiError("NOT_FOUND", "Interview not found", http_status=404)

    if interview.status != "approved":
        raise ApiError(
            "NOT_APPROVED",
            f"Interview must be in 'approved' status to publish (current: '{interview.status}')",
            http_status=422,
        )

    if interview.artist_consent_at is None:
        raise ApiError(
            "CONSENT_REQUIRED",
            "Artist must provide consent before the interview can be published.",
            http_status=422,
        )

    # Archive any existing published interview for same artist+locale
    await db.execute(
        update(ArtistInterview)
        .where(
            ArtistInterview.artist_id == interview.artist_id,
            ArtistInterview.locale == interview.locale,
            ArtistInterview.status == "published",
            ArtistInterview.id != iid,
        )
        .values(status="archived")
    )

    interview.status = "published"
    await db.commit()
    await db.refresh(interview)

    log.info(
        "AUDIT action=admin_publish_interview admin=%s interview=%s artist=%s locale=%s",
        admin.id,
        iid,
        interview.artist_id,
        interview.locale,
    )
    return {"data": _row_to_out(interview)}


# ─── POST /admin/artist-interviews/{id}/translate ─────────────────────────────


@router.post("/{interview_id}/translate", status_code=201)
async def admin_translate_interview(
    interview_id: str,
    target_locale: str = Query(..., pattern="^(ko|en|ja|zh|es)$"),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("interview_translate"),
):
    """Translate a published/approved interview to a target locale.

    C-3 booster: creates a new ArtistInterview row for target_locale
    with status='admin_review' using LLM Gateway translation.

    Returns 409 if a non-archived interview already exists for (artist_id, target_locale).
    """
    try:
        iid = uuid.UUID(interview_id)
    except ValueError as exc:
        raise ApiError("INVALID_ID", "Invalid UUID format", http_status=422) from exc

    result = await db.execute(
        select(ArtistInterview).where(ArtistInterview.id == iid)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise ApiError("NOT_FOUND", "Interview not found", http_status=404)

    if source.locale == target_locale:
        raise ApiError(
            "SAME_LOCALE",
            "Source and target locale must be different",
            http_status=422,
        )

    # Check for existing non-archived interview for same artist + target locale
    existing_stmt = select(ArtistInterview).where(
        ArtistInterview.artist_id == source.artist_id,
        ArtistInterview.locale == target_locale,
        ArtistInterview.status.not_in(["archived", "rejected"]),
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none() is not None:
        raise ApiError(
            "ALREADY_EXISTS",
            f"An interview for locale '{target_locale}' already exists for this artist.",
            http_status=409,
        )

    # Translate body_markdown + title via LLM Gateway
    client = LLMGatewayClient()
    translated_body = await client.translate_text(
        text=source.body_markdown,
        source_locale=source.locale,
        target_locale=target_locale,
    )
    translated_title = await client.translate_text(
        text=source.title,
        source_locale=source.locale,
        target_locale=target_locale,
    )

    new_interview = ArtistInterview(
        artist_id=source.artist_id,
        locale=target_locale,
        title=translated_title,
        body_markdown=translated_body,
        status="admin_review",
        llm_model=f"translation-from-{source.locale}",
        llm_input_summary=f"Translated from interview {source.id} ({source.locale} → {target_locale})",
        reviewed_by_admin_id=admin.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(new_interview)
    await db.commit()
    await db.refresh(new_interview)

    log.info(
        "AUDIT action=admin_translate_interview admin=%s source=%s target_locale=%s new_interview=%s",
        admin.id,
        iid,
        target_locale,
        new_interview.id,
    )
    return {"data": _row_to_out(new_interview)}
