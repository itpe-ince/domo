---
name: supporter-dashboard B-3 completion
description: B-3 done; supporter dashboard at /me/sponsorships; 5 components; 27 keys×5 locales; patronageDashboard key also synced across all 5 locales from B-2 linter diff
type: project
---

Phase 5 B-3 `supporter-dashboard` implementation complete (2026-05-04).

**Why:** Phase 5 B-3 scope —후원자 본인용 dashboard for viewing/managing sponsorships and subscriptions.

**Files created:**
- `/Users/sangincha/dev/domo/v1/frontend/src/app/me/sponsorships/page.tsx` — main dashboard (5 sections)
- `/Users/sangincha/dev/domo/v1/frontend/src/lib/hooks/useMySponsorships.ts` — data hook + cancel mutation + client-side summary computation
- `/Users/sangincha/dev/domo/v1/frontend/src/components/sponsorships/SubscriptionCard.tsx`
- `/Users/sangincha/dev/domo/v1/frontend/src/components/sponsorships/SponsorshipHistory.tsx`
- `/Users/sangincha/dev/domo/v1/frontend/src/components/sponsorships/CancelSubscriptionModal.tsx` — z-[60], reason select + immediate/period-end toggle
- `/Users/sangincha/dev/domo/v1/frontend/src/components/sponsorships/TierBenefitsPanel.tsx`
- `/Users/sangincha/dev/domo/v1/frontend/src/components/sponsorships/SupporterStats.tsx`

**Files modified:**
- `src/components/icons.tsx` — added HeartHandshakeIcon
- `src/components/Sidebar.tsx` — HeartHandshakeIcon import + `/me/sponsorships` nav link (B-2 linter also added `/me/patronage` for artists)
- `src/app/support/page.tsx` — Blue Bird landing redesign (tier benefits grid + hero + CTA links)
- All 5 i18n locales — `patronage.supporter.*` namespace (27 leaf keys) + `nav.mySponsoring` + `nav.patronageDashboard`

**Architecture decisions:**
- Summary stats computed client-side (no new backend endpoint) — acceptable for MVP volume
- artist_id shown as abbreviated ID (first 8 chars) — full name hydration deferred to B-4/B-5 batch endpoint
- `cancelSubscription` reuses existing DELETE `/v1/subscriptions/{id}` endpoint; reason/timing params are UI-only (Stripe already handles cancel_at_period_end on backend)
- Tier mapping from monthly_bluebird count: ≥10 → sponsor, ≥3 → subscriber, else follower

**i18n namespace:** `patronage.supporter.*` (B-3) kept separate from `patronage.artist.*` (B-2) per B-3 constraint.

**How to apply:** `/me/sponsorships` is the canonical path; `/subscriptions` still exists as the old subscription page. B-5 retention UX will build on top of these components.
