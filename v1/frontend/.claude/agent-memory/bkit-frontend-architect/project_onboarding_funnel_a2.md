---
name: onboarding-funnel A-2 completion
description: A-2 growth-funnel wizard + PostHog events + empty feed CTA + Sidebar indicator; 8 new files; 5 modified; 20 keys × 5 locales
type: project
---

A-2 onboarding-funnel PDCA implementation complete (2026-05-04).

**New files (8)**
- `src/lib/hooks/useOnboarding.ts` — first-session detection + state machine (idle/1/2/3/done) + localStorage WIZARD_SEEN_KEY + custom event `domo-onboarding-reopen` for cross-component sync
- `src/components/onboarding/OnboardingProgress.tsx` — progress dot indicator (3 steps)
- `src/components/onboarding/OnboardingStep1Follow.tsx` — recommended artist grid; bulk follow via `followArtist()`; partial-failure tolerant
- `src/components/onboarding/OnboardingStep2Sponsor.tsx` — BluebirdModal integration; auto-selects first recommended artist
- `src/components/onboarding/OnboardingStep3Discover.tsx` — Explore preview grid (decorative gradient tiles) + completion summary
- `src/components/onboarding/OnboardingWizard.tsx` — overlay wrapper; z-50; ESC close → skip event

**Modified files (5)**
- `src/lib/analytics/events.ts` — +4 onboarding event types: OnboardingStartEvent, OnboardingStepEvent, OnboardingSkipEvent, OnboardingCompleteEvent; also added FeedAlgorithmViewEvent (A-3 parallel)
- `src/lib/api.ts` — +RecommendedArtist type; +fetchRecommendedArtists(); +followArtist(); +unfollowArtist()
- `src/components/AppShell.tsx` — wizard rendered here for first-session users; `useOnboarding` + `useMe` integration
- `src/components/Sidebar.tsx` — onboarding indicator button (bg-primary/10) for isFirstSession users; calls reopenWizard() → dispatches domo-onboarding-reopen
- `src/app/feed/page.tsx` — empty feed CTA (🎨 + follow CTA + sponsor link); integrated with A-3 algo toggle

**i18n**: `onboarding.*` namespace (21 keys) × 5 locales + `feed.emptyTitle/emptySubtitle/emptyCtaFollow/emptyCtaSponsor` (4 keys) × 5 locales = 125 entries total

**Analytics events fired**:
- `onboarding_start` — wizard opens
- `onboarding_step { step: 1|2|3 }` — per step
- `onboarding_skip { step }` — ESC or "skip" click
- `onboarding_complete { followed, sponsored }` — step 3 CTA or step 3 skip
- `first_action { action: "follow" }` — per artist followed in step 1
- `first_action { action: "sponsor" }` — on BluebirdModal success in step 2

**Architecture decisions**:
- Wizard lives in AppShell (always rendered); Sidebar indicator calls `reopenWizard()` which dispatches `domo-onboarding-reopen` custom event picked up by AppShell's useOnboarding effect
- `fetchRecommendedArtists` uses `auth: false` (endpoint accepts anonymous) but wizard only shown to authenticated users
- BluebirdModal regression: 0 — Step 2 uses existing BluebirdModal unchanged with just `artistId/artistName/onClose/onSuccess` props

**Why:** `onboarding_start` + step events allow PostHog funnel analysis of drop-off; first-session localStorage flag prevents repeat shows after dismiss

**How to apply:** Backend endpoint `GET /v1/onboarding/recommended-artists?limit=5` must be implemented separately (A-2 backend scope); currently returns empty array gracefully if 404.
