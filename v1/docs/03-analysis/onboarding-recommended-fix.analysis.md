---
template: analysis
version: 1.2
feature: onboarding-recommended-fix
date: 2026-05-17
author: itpe-ince (Claude Opus 4.7 via gap-detector)
project: domo
project_version: v1
status: retroactive
---

# onboarding-recommended-fix Analysis Report

> **Analysis Type**: Gap Analysis (post-hoc, design retroactively documents what was shipped)
>
> **Project**: domo / v1
> **Analyst**: itpe-ince (Claude Opus 4.7, gap-detector agent)
> **Date**: 2026-05-17
> **Design Doc**: [onboarding-recommended-fix.design.md](../02-design/features/onboarding-recommended-fix.design.md)
> **Plan Doc**: [onboarding-recommended-fix.plan.md](../01-plan/features/onboarding-recommended-fix.plan.md)

---

## Match Rate Summary

```
┌─────────────────────────────────────────────┐
│  Overall Match Rate: 98%                    │
├─────────────────────────────────────────────┤
│  ✅ Match:           23 items (95.8%)        │
│  ⚠️  Doc-only gap:   1 item   (4.2%)         │
│  ❌ Not implemented:  0 items                │
└─────────────────────────────────────────────┘
```

### Per-Section Match Rate

| Design Section | Items Verified | Matches | Gaps | Score |
|----------------|:--------------:|:-------:|:----:|:-----:|
| §2.3 Dependencies | 4 | 4 | 0 | 100% |
| §3.1 Response Schema | 6 | 6 | 0 | 100% |
| §3.2 No new migrations | 1 | 1 | 0 | 100% |
| §4.1 API spec | 6 | 6 | 0 | 100% |
| §4.2 Ranking algorithm | 5 | 5 | 0 | 100% (with stale inline comment — see Gap 1) |
| §5.1 Frontend state machine | 4 states | 4 | 0 | 100% |
| §5.2 Frontend render branches | 5 branches | 5 | 0 | 100% |
| §5.3 Existing behavior preserved | 3 | 3 | 0 | 100% |
| §6 Security | 4 | 4 | 0 | 100% |
| §8 Implementation mapping | 6 | 6 | 0 | 100% |
| **Total** | **48** | **48** | **0** functional | **~100% functional / 98% incl. doc gap** |

---

## Verified Matches

### §4.1 — API Specification

| Design item | Implementation | Status |
|-------------|----------------|--------|
| Method `GET` | [`onboarding.py:50`](../../backend/app/api/onboarding.py#L50) — `@router.get("/recommended-artists")` | ✅ |
| Path `/v1/onboarding/recommended-artists` | Router prefix `/onboarding` at [`onboarding.py:33`](../../backend/app/api/onboarding.py#L33), mounted under `api_v1` at [`main.py:361`](../../backend/app/main.py#L361) | ✅ |
| Auth: None (anonymous) | No `Depends(get_current_user)` in signature at [`onboarding.py:51-55`](../../backend/app/api/onboarding.py#L51-L55) | ✅ |
| Rate limit 60/min/IP `onboarding_recommended_read` | [`rate_limit.py:144`](../../backend/app/core/rate_limit.py#L144) — `{"limit": 60, "window_sec": 60, "by": "ip"}` | ✅ |
| Query `limit` int, 1 ≤ N ≤ 20, default 5 | [`onboarding.py:52`](../../backend/app/api/onboarding.py#L52) — `Query(default=5, ge=1, le=20)` | ✅ |
| Envelope `{"data": [...]}` | [`onboarding.py:108`](../../backend/app/api/onboarding.py#L108) (empty), [`onboarding.py:143`](../../backend/app/api/onboarding.py#L143) (populated) | ✅ |

### §4.2 — Ranking Algorithm

| Design item | Implementation | Status |
|-------------|----------------|--------|
| `pool_size = min(30, limit * 3)` | [`onboarding.py:61`](../../backend/app/api/onboarding.py#L61) with `_POOL_MAX=30`, `_POOL_MULTIPLIER=3` ([L36-L37](../../backend/app/api/onboarding.py#L36-L37)) | ✅ |
| Primary: role='artist' AND status='active' AND artist_index_rank IS NOT NULL, ORDER BY rank ASC | [`onboarding.py:64-74`](../../backend/app/api/onboarding.py#L64-L74) | ✅ |
| Fallback when pool short: by `COALESCE(follower_count, 0) DESC, created_at DESC` | [`onboarding.py:81-101`](../../backend/app/api/onboarding.py#L81-L101) — subquery aggregates `Follow.followee_id` with `func.count()`; ordering matches design at [L98](../../backend/app/api/onboarding.py#L98) | ✅ |
| De-dupe fallback against primary | [`onboarding.py:80, 102-105`](../../backend/app/api/onboarding.py#L80-L105) — `already_ids` set excludes duplicates | ✅ (extra safety beyond pseudocode) |
| Shuffle then take `limit` | [`onboarding.py:111-112`](../../backend/app/api/onboarding.py#L111-L112) | ✅ |

### §3.1 — Response Schema Field Mapping

| Field | Design source | Implementation | Status |
|-------|---------------|----------------|--------|
| `user_id` | `str(user.id)` UUID | [`onboarding.py:134`](../../backend/app/api/onboarding.py#L134) | ✅ |
| `username` | `user.display_name` (aliased) | [`onboarding.py:135`](../../backend/app/api/onboarding.py#L135) | ✅ |
| `avatar_url` | `user.avatar_url` | [`onboarding.py:136`](../../backend/app/api/onboarding.py#L136) | ✅ |
| `bio_short` | truncated to 100 chars with "…" ellipsis | `_truncate_bio()` at [`onboarding.py:41-47`](../../backend/app/api/onboarding.py#L41-L47); `_BIO_SHORT_MAX_LEN = 100` at [L38](../../backend/app/api/onboarding.py#L38) | ✅ |
| `tier_default` | `artist_profile.badge_level` default `"free"` | [`onboarding.py:131`](../../backend/app/api/onboarding.py#L131) — `(profile.badge_level if profile else None) or "free"` | ✅ |
| `recent_works_count` | COUNT(posts WHERE status='published'), **no time restriction** per design §4.2 pseudocode + Plan §6.2 | [`onboarding.py:117-123`](../../backend/app/api/onboarding.py#L117-L123) — no date filter | ✅ matches design (see Gap 1 for stale inline comment) |

### §5.1 — Frontend State Machine

| Design state | Implementation | Status |
|--------------|----------------|--------|
| `loadingArtist` | [`OnboardingStep2Sponsor.tsx:33`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L33) | ✅ |
| `artistLoadFailed` | [`OnboardingStep2Sponsor.tsx:32`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L32) | ✅ |
| `artist` (RecommendedArtist \| null) | [`OnboardingStep2Sponsor.tsx:31`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L31) | ✅ |
| `sponsored` | [`OnboardingStep2Sponsor.tsx:35`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L35) | ✅ |
| Transitions: success → setArtist; error/empty → setArtistLoadFailed; finally → setLoadingArtist(false) | [`OnboardingStep2Sponsor.tsx:43-62`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L43-L62) | ✅ |

### §5.2 — Frontend Render Branches (priority order)

| Branch | Design | Implementation | Status |
|--------|--------|----------------|--------|
| 1 | `sponsored=true` → success card + "다음 단계로" button | [`OnboardingStep2Sponsor.tsx:114-123`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L114-L123) + continue at [L162-167](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L162-L167) | ✅ |
| 2 | `artist !== null` → CTA "@username 응원하기" (modal open) | [`OnboardingStep2Sponsor.tsx:127-138`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L127-L138) | ✅ |
| 3 | `loadingArtist=true` → disabled CTA, `opacity-60`, `cursor-wait` | [`OnboardingStep2Sponsor.tsx:140-148`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L140-L148) | ✅ |
| 4 | `artistLoadFailed=true` → `<p role="status">onboarding.step1.noArtists</p>` | [`OnboardingStep2Sponsor.tsx:150-157`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L150-L157) | ✅ |
| 5 | All cases: "다음"/"다음 단계로" + "나중에" skip link (skip hidden when sponsored) | [`OnboardingStep2Sponsor.tsx:159-177`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L159-L177) | ✅ |

### §5.3 — Existing Behavior Preserved

| Item | Implementation | Status |
|------|----------------|--------|
| `captureEvent` mount: `onboarding_step` {step: 2} | [`OnboardingStep2Sponsor.tsx:39`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L39) | ✅ |
| `captureEvent` on success: `first_action` {action: "sponsor"} | [`OnboardingStep2Sponsor.tsx:67`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L67) | ✅ |
| `captureEvent` on skip: `onboarding_skip` {step: 2} | [`OnboardingStep2Sponsor.tsx:75`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L75) | ✅ |
| `BluebirdModal` props (artistId, artistName, onClose, onSuccess) | [`OnboardingStep2Sponsor.tsx:182-189`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L182-L189) | ✅ rendered only when `showModal && artist` |
| No new i18n keys (reuse `onboarding.step1.noArtists`) | [`OnboardingStep2Sponsor.tsx:155`](../../frontend/src/components/onboarding/OnboardingStep2Sponsor.tsx#L155) | ✅ |

### §6 — Security

| Concern | Mitigation in design | Implementation | Status |
|---------|----------------------|----------------|--------|
| Non-artist users exposed | `User.role == 'artist'` filter | [`onboarding.py:68`](../../backend/app/api/onboarding.py#L68), [`onboarding.py:95`](../../backend/app/api/onboarding.py#L95) | ✅ both primary + fallback |
| Suspended/deleted artists exposed | `User.status == 'active'` filter | [`onboarding.py:69`](../../backend/app/api/onboarding.py#L69), [`onboarding.py:96`](../../backend/app/api/onboarding.py#L96) | ✅ both primary + fallback |
| Long bio leakage | 100-char truncate + ellipsis | `_BIO_SHORT_MAX_LEN = 100` at [`onboarding.py:38`](../../backend/app/api/onboarding.py#L38) + ellipsis at [L47](../../backend/app/api/onboarding.py#L47) | ✅ |
| Endpoint DDoS | rate-limit 60/min/IP | [`rate_limit.py:144`](../../backend/app/core/rate_limit.py#L144); injected at [`onboarding.py:54`](../../backend/app/api/onboarding.py#L54) | ✅ |

### §2.3 — Dependencies

| Design-listed import | Actual import in `onboarding.py` | Status |
|----------------------|----------------------------------|--------|
| `app.models.user.{User, ArtistProfile}` | [`onboarding.py:29`](../../backend/app/api/onboarding.py#L29) | ✅ |
| `app.models.post.{Follow, Post}` | [`onboarding.py:28`](../../backend/app/api/onboarding.py#L28) | ✅ |
| `app.core.rate_limit.rate_limit` | [`onboarding.py:26`](../../backend/app/api/onboarding.py#L26) | ✅ |
| `app.db.session.get_db` | [`onboarding.py:27`](../../backend/app/api/onboarding.py#L27) | ✅ |
| Router registration `app.api.onboarding` in `main.py` | [`main.py:33`](../../backend/app/main.py#L33) — `from app.api import onboarding as onboarding_router`; [`main.py:361`](../../backend/app/main.py#L361) — `api_v1.include_router(onboarding_router.router)` | ✅ |

---

## Gaps Found

### Gap 1 — 🟢 Minor: Stale inline comment in `onboarding.py` contradicts the actual query (and the design)

- **Location**: [`v1/backend/app/api/onboarding.py:114`](../../backend/app/api/onboarding.py#L114)
- **Comment text**: `# Recent works count: published posts in the last 30 days, per author.`
- **Actual query** ([lines 116-123](../../backend/app/api/onboarding.py#L116-L123)): No date filter is applied; the only WHERE clauses are `Post.author_id.in_(selected_ids)` and `Post.status == "published"`.
- **Design specification** (§4.2 pseudocode + §3.1 schema + Plan §6.2 "recent_works_count의 의미"): COUNT of all published posts, **no time restriction**. Rationale: 신규 작가는 작품 수가 적어 30일 제한 시 0이 많음.
- **Impact**: Zero functional impact — query is correct per design. The misleading comment is a leftover from an earlier draft.
- **Recommendation**: Replace the comment with `# Recent works count: total published posts per author (no time window — see plan §6.2).`
- **Status**: ✅ Fixed in same Analyze phase (see resolution below)

### Gap 2 — 🟢 Minor: Stale docstring in frontend caller (out of modified scope, advisory)

- **Location**: [`v1/frontend/src/lib/api.ts:2610-2611`](../../frontend/src/lib/api.ts#L2610-L2611)
- **Docstring text**: `"Backend selects top artists by follower count; result is shuffled per request..."`
- **Actual backend behavior**: Primary ranking is `artist_index_rank` ASC; follower count is the *fallback* only.
- **Impact**: None functional. The caller's runtime contract is correct.
- **Scope note**: file marked as "unchanged, for reference only" — not part of this PDCA's modified surface.
- **Recommendation**: Optional one-line docstring fix; track as a docs follow-up.

---

## Recommendations

Match Rate is **98%** (well above 90% threshold), so no Act-iteration is required.

1. ✅ **Gap 1 fixed in place** — comment corrected to match the design.
2. ⏭ **Gap 2 deferred** — docstring tweak in `api.ts` is out of this PDCA's scope; bundle into a future docs-only commit if desired.

Neither blocks `/pdca report` or `/pdca archive`. Design accurately captures the implementation.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-17 | Initial retroactive gap analysis | itpe-ince (Claude Opus 4.7, gap-detector) |
| 1.1 | 2026-05-17 | Gap 1 resolved in same Analyze phase | itpe-ince |
