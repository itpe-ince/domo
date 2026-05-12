---
name: B-2 artist-patronage-dashboard implementation
description: Phase 5 B-2 complete — 4 backend endpoints + full frontend dashboard page for artist patronage
type: project
---

Implementation complete as of 2026-05-04.

Backend files created/modified:
- `app/api/me_patronage.py` (NEW) — 4 endpoints under /me/patronage/
- `app/schemas/patronage.py` (NEW) — Pydantic models
- `app/core/rate_limit.py` (MOD) — 3 new scopes added
- `app/main.py` (MOD) — me_patronage_router registered
- `tests/integration/test_patronage_dashboard.py` (NEW) — 14 tests

Frontend files created/modified:
- `src/app/me/patronage/page.tsx` (NEW) — main dashboard page
- `src/app/me/patronage/layout.tsx` (NEW) — artist auth gate
- `src/components/patronage/SummaryCard.tsx` (NEW)
- `src/components/patronage/RevenueChart.tsx` (NEW) — SVG, no deps
- `src/components/patronage/SupportersTable.tsx` (NEW)
- `src/components/patronage/TierDistribution.tsx` (NEW)
- `src/components/patronage/PayoutRequestModal.tsx` (NEW)
- `src/lib/hooks/usePatronageDashboard.ts` (NEW)
- `src/lib/api.ts` (MOD) — 4 new client functions + types
- `src/components/Sidebar.tsx` (MOD) — patronageDashboard link for artists
- `src/i18n/ko.json`, `en.json`, `ja.json`, `zh.json`, `es.json` (MOD) — patronage.artist.* namespace

Key decisions:
- Revenue chart: SVG-only (no recharts/chart lib added) to avoid dependency
- Currency conversion: KRW→USD via fixed rate (FX service in Phase 6)
- Payout endpoint: stub (KYC gated, returns pending_review; settlement integration Phase 6)
- i18n namespace: patronage.artist.* (B-3 will use patronage.supporter.*)
- N+1 zero: all stats use single aggregate SQL per table

**Why:** Phase 5 B stage requires artist-facing patronage visibility. B-3 (supporter-dashboard) follows in parallel.
**How to apply:** When extending or debugging patronage dashboard, check the me_patronage.py router and the /me/patronage page components. Rate limits in DEFAULT_LIMITS dict.
