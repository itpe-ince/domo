---
name: G'-7 admin-featured-artists
description: Phase 7 G'-7 implementation: backend admin endpoints + frontend admin UI for monthly featured artist curation
type: project
---

Monthly featured artist curation system (OQ-8 = C, monthly cycle).

**Why:** A-7 storytelling-hub had hardcoded `artist_index rank 1` fallback — no admin control over who gets featured. Phase 7 G'-7 adds proper curation with history.

**Key decisions:**
- Alembic revision: `0050_featured_artists` (next after 0049_search_history)
- Partial unique index on `featured_artists(month) WHERE is_active = TRUE` — allows multiple historical deactivated entries per month
- Public endpoint `GET /v1/featured/artist/current` — graceful fallback to artist_index rank 1 when no curated entry
- A-7 booster: stories/page.tsx uses `fetchFeaturedArtist()` in parallel with `fetchArtistIndex()` — fallback shape is inline ArtistFeaturedView from ArtistIndexEntry
- FeaturedArtistHero updated to accept `ArtistFeaturedView` (not ArtistIndexEntry) + shows curation_note as blockquote
- `admin.featuredArtists.*` i18n namespace (13 keys × 5 locales = 65 entries)
- Rate limits: `featured_artist_write` (60/min admin), `featured_artist_read` (60/min IP)

**How to apply:** When extending featured artist logic (multi-region, AI curation, newsletter), reference featured_artists table + `GET /v1/featured/artist/current` endpoint in api/featured.py.
