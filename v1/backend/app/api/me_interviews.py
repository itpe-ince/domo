"""Artist-facing interview endpoints — C-1 ai-artist-interview-generation.

GET  /me/interviews                  — list my interviews (own artist)
POST /me/interviews/{id}/consent     — artist opt-in (GDPR consent to publish)
POST /me/interviews/{id}/reject      — artist reject (refuse publication)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.artist_interview import ArtistInterview
from app.models.user import User
from app.schemas.artist_interview import ArtistInterviewOut

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me/interviews", tags=["me-interviews"])


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


@router.get("")
async def list_my_interviews(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("interview_consent"),
):
    """List all interviews for the current artist."""
    result = await db.execute(
        select(ArtistInterview)
        .where(ArtistInterview.artist_id == user.id)
        .order_by(ArtistInterview.created_at.desc())
    )
    rows = result.scalars().all()
    return {"data": [_row_to_out(r) for r in rows]}


@router.post("/{interview_id}/consent", status_code=200)
async def artist_consent_interview(
    interview_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("interview_consent"),
):
    """Artist provides GDPR consent for interview publication.

    - Only the interview's target artist can consent.
    - Consent is only meaningful when status == 'approved'.
    - Sets artist_consent_at = now().
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

    # Only the interview's target artist may consent
    if interview.artist_id != user.id:
        raise ApiError(
            "FORBIDDEN",
            "You can only consent to your own interviews.",
            http_status=403,
        )

    if interview.status != "approved":
        raise ApiError(
            "NOT_APPROVED",
            f"Consent can only be given for 'approved' interviews (current: '{interview.status}')",
            http_status=422,
        )

    if interview.artist_consent_at is not None:
        # Idempotent — already consented
        return {"data": _row_to_out(interview)}

    interview.artist_consent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(interview)

    log.info(
        "AUDIT action=artist_consent_interview artist=%s interview=%s",
        user.id,
        iid,
    )
    return {"data": _row_to_out(interview)}


@router.post("/{interview_id}/reject", status_code=200)
async def artist_reject_interview(
    interview_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("interview_consent"),
):
    """Artist rejects publication of their interview.

    Sets status to 'rejected'. Only possible when status == 'approved'.
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

    if interview.artist_id != user.id:
        raise ApiError(
            "FORBIDDEN",
            "You can only reject your own interviews.",
            http_status=403,
        )

    if interview.status not in ("approved", "admin_review"):
        raise ApiError(
            "INVALID_STATUS",
            f"Cannot reject an interview with status '{interview.status}'",
            http_status=422,
        )

    interview.status = "rejected"
    await db.commit()
    await db.refresh(interview)

    log.info(
        "AUDIT action=artist_reject_interview artist=%s interview=%s",
        user.id,
        iid,
    )
    return {"data": _row_to_out(interview)}
