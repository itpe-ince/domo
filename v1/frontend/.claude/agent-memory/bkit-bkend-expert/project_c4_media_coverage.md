---
name: C-4 media-coverage-cms
description: Phase 7 C-4: media coverage CMS — admin CRUD + public API + storyhub A-7 booster + artist profile section. alembic 0057. 8 new tests.
type: project
---

Phase 7 C-4 media-coverage-cms implementation.

**Why:** A-7 storyhub MediaCoverageGrid was hardcoded with 3 placeholder items. C-4 replaces with real DB-driven CMS.

**How to apply:** When working on media coverage features, storyhub integration, or admin CMS extensions.

## Deliverables

### Backend (alembic 0057_media_coverage)
- `app/models/media_coverage.py` — MediaCoverage model (UUID PK, coverage_type, locale, is_featured, artist_id FK nullable)
- `alembic/versions/0057_media_coverage.py` — 3 indexes (type, locale+published+date DESC, partial featured)
- `app/schemas/media_coverage.py` — Create/Patch/Out schemas with HTML sanitization (_strip_html)
- `app/api/admin_media_coverage.py` — 4 admin endpoints: POST/GET/PATCH/DELETE
- `app/api/media_coverage.py` — 2 public endpoints: GET /media-coverage + GET /media-coverage/featured
- `app/core/rate_limit.py` — admin_media_coverage_write (60/min/user) + media_coverage_read (60/min/IP)
- `app/main.py` — 2 routers registered
- `tests/integration/test_media_coverage.py` — 8 tests (201, 403, list, patch publish, delete, locale filter, artist_id filter, featured)

### Frontend
- `lib/api.ts` — 6 client functions + MediaCoverageOut/AdminCreateMediaCoverageBody/AdminPatchMediaCoverageBody types
- `lib/hooks/useAdminMediaCoverage.ts` — admin CRUD hook with pagination
- `components/admin/MediaCoverageForm.tsx` — create/edit form
- `components/admin/MediaCoverageList.tsx` — admin table with publish toggle + delete
- `app/admin/media-coverage/page.tsx` — admin page with auth gate
- `components/stories/MediaCoverageGrid.tsx` — A-7 booster: replaced hardcoded placeholders with fetchFeaturedMediaCoverage (locale-aware, graceful degrade)
- `components/users/UserMediaCoverage.tsx` — artist profile media coverage section
- `app/users/[id]/page.tsx` — added UserMediaCoverage for artist profiles
- `i18n/{ko,en,ja,zh,es}.json` — mediaCoverage.* namespace (15 keys × 5 = 75 entries)

## Constraints
- C-5 parallel: newsletter models/routes already added by C-5 during this session (in __init__.py, rate_limit.py, main.py)
- A-7 MediaCoverageGrid backward-compatible: `items` prop override still works
- Graceful degrade: empty state returns null (no placeholder)
- HTML sanitized: title/description strip all tags
- alembic chain: 0056 → 0057
