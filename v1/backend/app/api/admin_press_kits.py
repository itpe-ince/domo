"""Admin press kit management — C-2 press-kit-auto-export.

POST /admin/artists/{user_id}/press-kit/generate?locale=ko  — trigger PDF generation
GET  /admin/artists/{user_id}/press-kit/history             — list generation history
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.press_kit import PressKit
from app.models.user import User
from app.schemas.press_kit import PressKitGenerateRequest, PressKitOut
from app.services.press_kit_generator import generate_press_kit, press_kit_to_out

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/artists", tags=["admin-press-kits"])

_VALID_LOCALES = frozenset({"ko", "en", "ja", "zh", "es"})


# ─── POST /admin/artists/{user_id}/press-kit/generate ────────────────────────


@router.post("/{user_id}/press-kit/generate", status_code=200)
async def admin_generate_press_kit(
    user_id: str,
    locale: str = Query("ko", pattern="^(ko|en|ja|zh|es)$"),
    force: bool = Query(False, description="Bypass 30d cache and regenerate"),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("press_kit_generate"),
):
    """Trigger press kit PDF generation for an artist.

    - Rate-limited: 10/hour per admin (PDF generation is CPU/storage-intensive).
    - 30-day cache: same (artist_id, locale) pair returns cached PDF until expiry.
    - force=true bypasses cache and regenerates.
    - C-1 integration: if a published ArtistInterview exists for the locale,
      it is included as page 4.
    """
    try:
        artist_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise ApiError("INVALID_USER_ID", "user_id must be a valid UUID", http_status=422) from exc

    press_kit = await generate_press_kit(
        db=db,
        artist_id=artist_id,
        locale=locale,
        admin_id=admin.id,
        force=force,
    )

    log.info(
        "AUDIT action=admin_generate_press_kit admin=%s artist=%s locale=%s pk=%s",
        admin.id, artist_id, locale, press_kit.id,
    )
    return {"data": press_kit_to_out(press_kit).model_dump(mode="json")}


# ─── GET /admin/artists/{user_id}/press-kit/history ──────────────────────────


@router.get("/{user_id}/press-kit/history")
async def admin_press_kit_history(
    user_id: str,
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """List press kit generation history for an artist (newest first).

    Returns all records, including expired ones (for audit trail).
    """
    try:
        artist_id = uuid.UUID(user_id)
    except ValueError as exc:
        raise ApiError("INVALID_USER_ID", "user_id must be a valid UUID", http_status=422) from exc

    result = await db.execute(
        select(PressKit)
        .where(PressKit.artist_id == artist_id)
        .order_by(PressKit.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return {"data": [press_kit_to_out(r).model_dump(mode="json") for r in rows]}
