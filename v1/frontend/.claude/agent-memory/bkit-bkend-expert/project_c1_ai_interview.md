---
name: C-1 ai-artist-interview-generation
description: Phase 7 C-1 implementation: LLM-generated artist interviews with admin review workflow + artist consent (GDPR)
type: project
---

Phase 7 C-1 Critical Path — artist interview generation via tuzigroup LLM Gateway (gemma4-e4b).

**Why:** C-2 (press kit PDF), C-3 (multi-language), C-5 (newsletter) all depend on ArtistInterview content. C-1 must complete first.

**How to apply:** When implementing C-2/C-3/C-5, query ArtistInterview model (status='published') for content sourcing.

## Key files

**Backend:**
- `app/models/artist_interview.py` — ArtistInterview model (id, artist_id, locale, title, body_markdown, status, artist_consent_at, reviewed_by_admin_id, etc.)
- `alembic/versions/0054_artist_interviews.py` — migration (down_revision: 0053_post_engagement_cache)
- `app/services/llm_gateway.py` — LLMGatewayClient (Mock mode when LLM_GATEWAY_API_KEY empty)
- `app/services/interview_generator.py` — collect_artist_summary + _build_prompt + generate_artist_interview
- `app/api/admin_interviews.py` — 4 admin endpoints (generate/list/patch/publish)
- `app/api/me_interviews.py` — 3 artist endpoints (list/consent/reject)
- `app/api/users.py` — GET /users/{id}/interviews (public, published only)

**Frontend:**
- `app/admin/artist-interviews/page.tsx` — admin management UI
- `app/me/interviews/page.tsx` — artist consent UI
- `app/users/[id]/interviews/[locale]/page.tsx` — public interview view
- `app/users/[id]/timeline/page.tsx` — A-7 booster: interview section added
- `components/admin/InterviewGenerateModal.tsx` — LLM trigger modal
- `components/admin/InterviewReviewModal.tsx` — review/approve/reject with markdown editor
- `components/admin/InterviewsList.tsx` — status-tabbed list
- `components/interviews/InterviewCard.tsx` — public preview card
- `lib/hooks/useAdminInterviews.ts` — admin interview hook
- `lib/hooks/useMyInterviews.ts` — artist interview hook

## Status flow

`draft → admin_review → approved → published | rejected`
`archived` = previous published replaced by newer one

## Rate limits added

- `interview_generate`: 5/hour/admin (LLM cost protection)
- `interview_consent`: 10/hour/user

## LLM credentials

`LLM_GATEWAY_URL=https://llm.tuzigroup.com/v1`, `LLM_MODEL_NAME=gemma4-e4b`. API key from `.env` (not committed).

## Tests

- `tests/integration/test_artist_interviews.py` — 13 tests
- `tests/unit/test_llm_gateway_mock.py` — 3 tests
- New total: 263 + 16 = 279

## i18n

`interview.*` namespace: 25 keys × 5 locales (ko/en/ja/zh/es) = 125 entries
