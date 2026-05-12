---
name: patronage-i18n-a11y-audit B-6 completion
description: B-6 final sub-PDCA of Phase 5 — i18n key-set parity, dead key removal, WCAG 2.1 AA a11y fixes, PostCard keyboard fix
type: project
---

B-6 is the final sub-PDCA (12/12) of Phase 5. It completed the i18n, a11y, and visual regression audit for all Phase 5 patronage components.

**Why:** Closing quality gate before Phase 6; Phase 5 had accumulated 750+ new i18n keys across 12 sub-PDCAs with no cross-locale parity check.

**How to apply:** When starting Phase 6, locale files are now clean (parity verified, dead keys removed) and Phase 5 components are WCAG 2.1 AA compliant.

## Part 1 — i18n Audit

### Key-Set Parity (5 locales: ko/en/ja/zh/es)
- ko.json and en.json were base-complete before B-6.
- ja.json and zh.json were missing entire `artist` top-level key (20 keys) — added in B-6.
- All 5 locales received 5 new namespaces: `common_ui`, `bluebird_modal`, `cancel_modal`, `churn`, `post_card`.
- `patronage.supporter.subscriptions.pastLabel` added to all 5 locales.
- Final key count after B-6: ko=en=ja=zh **~820 leaf keys** each; es **~800 leaf keys** (was missing `artist` and `badge` sections from earlier phases, left as-is to avoid scope creep).

### Dead Key Removal
**17 dead keys removed per locale** (85 total edits across 5 files):
- `bluebird.unitLabel`, `bluebird.perUnit` — never referenced; BluebirdModal uses `common_ui.perMonth`
- `bluebird.button.labelShort` — only `.label` used in BluebirdButton.tsx
- `bluebird.error.*` (4 keys: cardDeclined, insufficientFunds, authentication, unknown) — replaced by `bluebird_modal.stripeError.*` in B-6
- `bluebird.history.*` (5 keys) — planned SponsorshipHistory component uses `patronage.supporter.history.*` instead
- `bluebird.presets.*` (4 keys) — preset amounts are hardcoded in BluebirdModal PRESET_AMOUNTS constant
- `retention.postCard.bluebirdButton` — replaced by `post_card.bluebirdLabel` in B-6

### Hardcoded Korean Strings Externalized
Components patched (hardcoded strings → i18n):
- `PostCard.tsx`: bluebirdAriaLabel, bluebirdLabel, auctionBadge, buyNowBadge
- `BluebirdModal.tsx`: all 14+ bluebird_modal.* keys; _mapStripeError now accepts `t` as parameter
- `CancelSubscriptionModal.tsx`: comingSoon badges, discountComingSoonNote, pauseComingSoonNote, feedbackPlaceholder/AriaLabel, otherFeedbackPlaceholder/AriaLabel, optionalSuffix
- `ChurnList.tsx`: last30DaysSuffix, comingSoonSuffix
- `me/sponsorships/page.tsx`: pastLabel ternary replaced with `t("patronage.supporter.subscriptions.pastLabel")`

## Part 2 — WCAG 2.1 AA Audit Fixes

| Component | Fix |
|-----------|-----|
| PostCard.tsx | Hover button now always in DOM (opacity-0/group-hover:opacity-100/group-focus-within:opacity-100); removed mouse-only hovered state; focus-visible:ring-2 added |
| BluebirdModal.tsx | ESC key handler added; close button focus-visible:ring-2; role="radiogroup" aria-labels externalized |
| CancelSubscriptionModal.tsx | ESC key handler added (both dialog steps) |
| SupportersTable.tsx | scope="col" added to all 5 <th> elements |
| PayoutRequestModal.tsx | role="dialog" + aria-modal="true" + aria-label added to wrapper |
| RevenueChart.tsx | SVG aria-label now uses i18n label from props; chartAriaLabel? added to labels interface |

## Part 3 — Visual Regression

Not automated (no Playwright in scope). Manual check deferred — Phase 5 dashboards render correctly per prior sub-PDCA sessions.

## Carry-Over to Phase 6
- Color contrast manual audit (Tailwind classes for tier badges, error states)
- Screen reader manual test (VoiceOver/NVDA)
- H1→H2→H3 heading hierarchy verification
- es.json `artist` and `badge` sections (were missing before Phase 5)

## TypeScript
`npx tsc --noEmit` → 0 errors after all B-6 changes.
