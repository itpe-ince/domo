"""Artist bio multi-locale endpoints — C-3 multi-language-story.

POST  /me/bio/translate?source_locale=ko  — auto-translate bio to 5 locales (LLM)
PATCH /me/bio/{locale}                    — manually edit one locale bio
GET   /me/bio                             — list all locale bios for self
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.models.user_bio_translation import SUPPORTED_LOCALES, UserBioTranslation
from app.schemas.bio import BioLocaleOut, BioTranslateResponse, PatchBioRequest
from app.services.story_translator import translate_bio_to_all_locales, upsert_bio_locale

log = logging.getLogger(__name__)

router = APIRouter(prefix="/me/bio", tags=["me-bio"])


def _row_to_out(row: UserBioTranslation) -> dict:
    return BioLocaleOut(
        user_id=str(row.user_id),
        locale=row.locale,
        bio=row.bio,
        is_machine_translated=row.is_machine_translated,
        last_edited_at=row.last_edited_at,
        last_translated_at=row.last_translated_at,
    ).model_dump(mode="json")


# ─── GET /me/bio ──────────────────────────────────────────────────────────────


@router.get("")
async def get_my_bio_translations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all locale bios for the current user."""
    result = await db.execute(
        select(UserBioTranslation).where(UserBioTranslation.user_id == user.id)
    )
    rows = result.scalars().all()
    return {"data": [_row_to_out(r) for r in rows]}


# ─── POST /me/bio/translate ───────────────────────────────────────────────────


@router.post("/translate", status_code=200)
async def translate_my_bio(
    source_locale: str = Query(
        "ko", pattern="^(ko|en|ja|zh|es)$", description="Source locale of User.bio"
    ),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("bio_translate"),
):
    """Auto-translate the current user's bio to all 5 supported locales.

    Uses User.bio (plain text) as the source. If User.bio is empty, returns 422.
    Rate limit: 5 per day per user (LLM cost protection).

    Returns:
        200 + { translations: { ko: "...", en: "...", ... } }
    """
    if not user.bio:
        raise ApiError(
            "BIO_EMPTY",
            "Please set your bio before requesting translation.",
            http_status=422,
        )

    translations = await translate_bio_to_all_locales(
        db=db,
        user_id=user.id,
        source_text=user.bio,
        source_locale=source_locale,
    )

    log.info(
        "AUDIT action=bio_translate user=%s source_locale=%s locales=%s",
        user.id,
        source_locale,
        list(translations.keys()),
    )
    return {"data": BioTranslateResponse(translations=translations).model_dump()}


# ─── PATCH /me/bio/{locale} ───────────────────────────────────────────────────


@router.patch("/{locale}")
async def patch_my_bio_locale(
    locale: str,
    body: PatchBioRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually edit bio for a specific locale.

    Sets is_machine_translated=False to mark as human-edited.
    Locale must be one of: ko en ja zh es.
    """
    if locale not in SUPPORTED_LOCALES:
        raise ApiError(
            "INVALID_LOCALE",
            f"Locale must be one of: {', '.join(sorted(SUPPORTED_LOCALES))}",
            http_status=422,
        )

    row = await upsert_bio_locale(
        db=db,
        user_id=user.id,
        locale=locale,
        bio_text=body.bio,
    )
    return {"data": _row_to_out(row)}
