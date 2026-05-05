"""Story translation service — C-3 multi-language-story.

Orchestrates LLM-powered multi-locale translation for:
  1. Artist bio (User.bio → UserBioTranslation × 5 locales)
  2. ArtistInterview body_markdown (C-1 booster — create translated interview row)
  3. Milestone text (A-7 booster — future use, in-memory helper)

LLM cost controls:
  - 24h in-memory translation cache (per user_id+locale+content_hash)
  - Rate limit enforced at API layer (5/day/user for bio_translate)
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_bio_translation import SUPPORTED_LOCALES, UserBioTranslation
from app.services.llm_gateway import LLMGatewayClient

log = logging.getLogger(__name__)

# ─── 24-hour in-memory translation cache ─────────────────────────────────────
# Key: (content_hash, target_locale) → (translated_text, expires_at_unix)
_TRANSLATION_CACHE: dict[tuple[str, str], tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 86400  # 24 hours


def _cache_key(text: str, target_locale: str) -> tuple[str, str]:
    digest = hashlib.sha256(text.encode()).hexdigest()[:16]
    return (digest, target_locale)


def _cache_get(text: str, target_locale: str) -> str | None:
    key = _cache_key(text, target_locale)
    entry = _TRANSLATION_CACHE.get(key)
    if entry is None:
        return None
    translated, expires_at = entry
    if time.time() > expires_at:
        del _TRANSLATION_CACHE[key]
        return None
    return translated


def _cache_set(text: str, target_locale: str, translated: str) -> None:
    key = _cache_key(text, target_locale)
    _TRANSLATION_CACHE[key] = (translated, time.time() + _CACHE_TTL_SECONDS)


# ─── Bio translation ──────────────────────────────────────────────────────────


async def translate_bio_to_all_locales(
    db: AsyncSession,
    user_id: uuid.UUID,
    source_text: str,
    source_locale: str = "ko",
) -> dict[str, str]:
    """Translate artist bio to all 5 supported locales using LLM Gateway.

    Skips the source locale (stores original text directly without LLM call).
    Uses 24h in-memory cache to avoid redundant LLM calls on repeated requests.

    Returns:
        dict mapping locale → translated text (includes source_locale with original).

    Side effect:
        Upserts UserBioTranslation rows for all 5 locales.
    """
    client = LLMGatewayClient()
    target_locales = SUPPORTED_LOCALES - {source_locale}
    results: dict[str, str] = {source_locale: source_text}

    for locale in sorted(target_locales):  # deterministic order
        cached = _cache_get(source_text, locale)
        if cached is not None:
            log.debug("story_translator: cache hit %s→%s", source_locale, locale)
            results[locale] = cached
        else:
            translated = await client.translate_text(
                text=source_text,
                source_locale=source_locale,
                target_locale=locale,
            )
            _cache_set(source_text, locale, translated)
            results[locale] = translated

    # Upsert all 5 locales
    now = datetime.now(timezone.utc)
    for locale, bio_text in results.items():
        is_machine = locale != source_locale
        stmt = pg_insert(UserBioTranslation).values(
            user_id=user_id,
            locale=locale,
            bio=bio_text,
            is_machine_translated=is_machine,
            last_edited_at=now,
            last_translated_at=now if is_machine else None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "locale"],
            set_={
                "bio": bio_text,
                "is_machine_translated": is_machine,
                "last_edited_at": now,
                "last_translated_at": now if is_machine else stmt.excluded.last_translated_at,
            },
        )
        await db.execute(stmt)

    await db.commit()
    return results


async def upsert_bio_locale(
    db: AsyncSession,
    user_id: uuid.UUID,
    locale: str,
    bio_text: str,
) -> UserBioTranslation:
    """Upsert a single locale bio (artist manual edit).

    Sets is_machine_translated=False — marks as human-edited.
    """
    now = datetime.now(timezone.utc)
    stmt = pg_insert(UserBioTranslation).values(
        user_id=user_id,
        locale=locale,
        bio=bio_text,
        is_machine_translated=False,
        last_edited_at=now,
        last_translated_at=None,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "locale"],
        set_={
            "bio": bio_text,
            "is_machine_translated": False,
            "last_edited_at": now,
        },
    )
    await db.execute(stmt)
    await db.commit()

    result = await db.execute(
        select(UserBioTranslation).where(
            UserBioTranslation.user_id == user_id,
            UserBioTranslation.locale == locale,
        )
    )
    return result.scalar_one()


async def get_bio_for_locale(
    db: AsyncSession,
    user_id: uuid.UUID,
    locale: str,
    fallback_locale: str = "ko",
) -> str | None:
    """Retrieve bio for a locale, falling back to fallback_locale if not found."""
    result = await db.execute(
        select(UserBioTranslation).where(
            UserBioTranslation.user_id == user_id,
            UserBioTranslation.locale == locale,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return row.bio

    if locale != fallback_locale:
        fallback_result = await db.execute(
            select(UserBioTranslation).where(
                UserBioTranslation.user_id == user_id,
                UserBioTranslation.locale == fallback_locale,
            )
        )
        fallback = fallback_result.scalar_one_or_none()
        if fallback:
            return fallback.bio

    return None


# ─── Milestone text translation (A-7 booster) ────────────────────────────────


async def translate_milestone_text(
    text: str,
    source_locale: str,
    target_locale: str,
) -> str:
    """Translate a single milestone text string (no DB upsert — caller handles storage).

    Uses 24h cache to reduce LLM calls for repeated milestone strings.
    """
    if source_locale == target_locale:
        return text

    cached = _cache_get(text, target_locale)
    if cached is not None:
        return cached

    client = LLMGatewayClient()
    translated = await client.translate_text(
        text=text,
        source_locale=source_locale,
        target_locale=target_locale,
    )
    _cache_set(text, target_locale, translated)
    return translated
