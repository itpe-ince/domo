---
name: patronage-retention-ux B-5 completion
description: B-5 retention UX done; 5 components; 2 hooks; 26 keys×5 locales; retention.* namespace; cancel reason backend-forwarded
type: project
---

B-5 patronage-retention-ux implemented (2026-05-04).

**Why:** Churn prevention for Blue Bird patronage — core growth-hack funnel goal per README.

**How to apply:** B-6 i18n/a11y audit should cover `retention.*` namespace and all new components.

## Files modified/created

### New hooks
- `src/lib/hooks/useWinbackBanner.ts` — 7-day cooldown localStorage (SSR-safe typeof window guard)
- `src/lib/hooks/useResubscribe.ts` — one-click resubscribe via existing createSubscription

### New components
- `src/components/sponsorships/WinbackBanner.tsx` — artist profile win-back prompt
- `src/components/sponsorships/ChurnList.tsx` — artist dashboard churn section (fetches /me/patronage/churn, degrades gracefully if 404)

### Modified components
- `src/components/BluebirdModal.tsx` — Step 5 enhanced thank-you: welcome message, next-steps links (/users/[id], /explore, /me/sponsorships)
- `src/components/sponsorships/CancelSubscriptionModal.tsx` — 2-step flow: reason → win-back (conditional offers + feedback textarea)
- `src/components/sponsorships/SubscriptionCard.tsx` — accepts feedback param + resubscribe button for cancelled cards
- `src/components/PostCard.tsx` — converted to "use client" for hover state; mini BluebirdButton on hover (desktop only via hidden md:flex)

### Modified pages
- `src/app/me/patronage/page.tsx` — ChurnList section added (section 5, before payout)
- `src/app/me/sponsorships/page.tsx` — useResubscribe hook; resubscribe button in inactive subscriptions
- `src/app/users/[id]/page.tsx` — WinbackBanner above header (shown when hasPastSponsorship && !hasActiveSubscription && not dismissed)

### API
- `src/lib/api.ts` — cancelSubscription body extended (reason/feedback/immediate optional); ChurnItem type + fetchChurnList added

### i18n
- `retention.*` namespace (26 keys × 5 locales = 130 entries)
- Key groups: retention.thankyou.*, retention.cancel.winback.*, retention.winback.banner.*, retention.churn.*, retention.postCard.*, retention.resubscribe.*
- Namespace strictly separated from B-4's `tierBenefits.*`

## Architecture decisions
- Win-back offers (discount/pause) are UI placeholders with "준비 중" badges — actual Stripe coupon carry-over to Phase 6
- DM for "not_satisfied" → feedback textarea (no DM infra yet, carry-over)
- ChurnList degrades gracefully if backend endpoint 404s (B-5 optional backend)
- PostCard became client component — minor: was import-only server component, now needs hover state
- useMySponsorships cancelSubscriptionById signature extended with optional feedback param (backward compat)
