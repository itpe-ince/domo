---
name: C-3 multi-language-story
description: Phase 7 C-3 implementation: LLM bio translation + Next.js i18n LocaleSwitcher + 5-locale bio editor
type: project
---

Phase 7 C-3 — artist bio multi-locale + LLM translation + frontend locale switcher.

**Why:** Global reach for emerging artists — bio translated to ko/en/ja/zh/es via tuzigroup LLM Gateway (Mock mode fallback). Next.js App Router locale switcher (cookie/localStorage based, not subpath routing).

**How to apply:** C-4/C-5 can use story_translator.translate_milestone_text() for milestone text. LocaleSwitcher component is reusable across pages.

## Backend key files

- `alembic/versions/0056_user_bio_translations.py` — composite PK (user_id, locale). down_revision: 0055_press_kits
- `app/models/user_bio_translation.py` — UserBioTranslation model (user_id, locale, bio, is_machine_translated, last_edited_at, last_translated_at)
- `app/services/llm_gateway.py` — added `translate_text(text, source_locale, target_locale)` method (C-1 booster)
- `app/services/story_translator.py` — translate_bio_to_all_locales + upsert_bio_locale + get_bio_for_locale + translate_milestone_text. 24h in-memory cache.
- `app/api/me_bio.py` — POST /me/bio/translate, PATCH /me/bio/{locale}, GET /me/bio
- `app/api/users.py` — GET /users/{id}/bio?locale=ko|en|ja|zh|es (fallback: ko → User.bio)
- `app/api/admin_interviews.py` — POST /admin/artist-interviews/{id}/translate?target_locale=en (C-1 booster)
- `app/schemas/bio.py` — BioTranslationOut, BioTranslateResponse, PatchBioRequest
- `app/core/rate_limit.py` — bio_translate (5/day/user), interview_translate (10/hour/user)
- `app/main.py` — me_bio_router registered
- `app/models/__init__.py` — UserBioTranslation added

## Frontend key files

- `components/LocaleSwitcher.tsx` — 5-locale dropdown, syncs with I18nProvider via setLocale(). Key: "domo-locale" (matches i18n/index.tsx)
- `lib/hooks/useMyBio.ts` — fetch/translate/save bio hook
- `app/me/bio/page.tsx` — 5-locale tabs + auto-translate button + per-locale save
- `app/stories/page.tsx` — LocaleSwitcher added to header (A-7 booster)
- `app/users/[id]/page.tsx` — locale-aware bio display + LOCALE_CHANGED_EVENT listener (A-7 booster)
- `lib/api.ts` — fetchMyBioTranslations, translateMyBio, patchMyBioLocale, fetchUserBio

## Tests

- `tests/integration/test_bio_translation.py` — 5 tests (translate success, empty bio 422, patch locale, invalid locale 422, public bio fallback)
- `tests/integration/test_interview_translation.py` — 3 tests (translate 201, conflict 409, same locale 422)
- New baseline: 279 + 8 = 287 tests

## i18n

`bio.*` + `localeSwitcher.*` namespace: ~10 keys × 5 locales = 50 entries added

## Rate limits

- `bio_translate`: 5/day/user (window_sec=86400) — LLM cost protection
- `interview_translate`: 10/hour/user — admin C-1 booster

## Alembic chain

0054_artist_interviews → 0055_press_kits → 0056_user_bio_translations (down_revision: "0055_press_kits")

## Carry-over for C-4/C-5

- Multi-language SEO meta (twitter:card + og:image locale): G'-6 + C-3 booster, not yet done
- OG image multi-language: app/users/[id]/timeline/opengraph-image.tsx locale param — out of C-3 scope
