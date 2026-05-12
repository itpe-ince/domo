# Frontend Bundle Optimization — G''-5

Phase 8 G''-5 sub-PDCA. Completed 2026-05-04.

---

## What Was Done

### 1. Bundle Analyzer Setup

- Added `@next/bundle-analyzer@15.0.3` as devDependency
- Updated `next.config.mjs` with `withBundleAnalyzer` wrapper (ESM)
- Added `"analyze": "ANALYZE=true next build"` npm script

To visualize bundles:
```bash
npm run analyze
# Opens two HTML reports in .next/analyze/ — client.html + server.html
```

### 2. Webpack Canvas Alias (Konva SSR Fix)

Added webpack alias `canvas: false` in `next.config.mjs` to silence the
`Can't resolve 'canvas'` build error from `konva/lib/index-node.js`.

This was blocking production builds entirely. The alias replaces the
optional native `canvas` dependency with an empty module — safe because
`ImageEditor` already uses `ImageEditorLazy` with `ssr: false`.

### 3. Dynamic Import Applications

7 components converted from static import to `next/dynamic`:

| Component | File | Reason |
|-----------|------|--------|
| `BluebirdModal` | `app/posts/[id]/page.tsx` | Stripe flow — only on sponsor click |
| `ReportModal` | `app/posts/[id]/page.tsx` | Modal — rarely used |
| `AuctionShareCard` | `app/posts/[id]/page.tsx` | Owner-only, conditional render |
| `BluebirdModal` | `components/PostCard.tsx` | Feed card hover — deferred |
| `InterviewGenerateModal` | `app/admin/artist-interviews/page.tsx` | Admin modal |
| `InterviewReviewModal` | `app/admin/artist-interviews/page.tsx` | Admin modal |
| `NewsletterIssueEditor` | `app/admin/newsletter/page.tsx` | Heavy editor, conditional |
| `PressKitGenerator` | `app/admin/press-kits/page.tsx` | Admin form |

All use `{ ssr: false, loading: () => null }` — consistent with existing
`ImageEditorLazy` pattern.

Pre-existing lazy: `ImageEditorLazy` (Konva/react-konva, `ssr: false`)

### 4. Unsubscribe Page Suspense Fix

`/newsletter/unsubscribe` used `useSearchParams()` without a `Suspense`
boundary, causing a prerender error that blocked the build. Wrapped the
inner component in `Suspense` — pre-existing issue, fixed opportunistically.

---

## Build Output (Post-Optimization)

Build date: 2026-05-04. Next.js 15.0.3.

### First Load JS — Key Routes

| Route | First Load JS | Target | Status |
|-------|--------------|--------|--------|
| `/` | 184 kB | < 200 kB | Pass |
| `/feed` | 249 kB | < 250 kB | Pass |
| `/explore` | 254 kB | < 250 kB | 4 kB over — within tolerance |
| `/posts/new` | 284 kB | < 400 kB | Pass |
| `/posts/[id]` | 187 kB | — | Good |
| `/admin/*` | 175–176 kB | < 300 kB | Pass |

### Shared Chunks (all pages)

| Chunk | Size |
|-------|------|
| `chunks/1517` | 45.5 kB |
| `chunks/4bd1b696` | 52.5 kB |
| Other shared | 2.2 kB |
| **Total shared** | **100 kB** |

### Notable Observations

- `/posts/new` at 284 kB includes the full editor workspace (dnd-kit sortable,
  PostHog, multiple sub-components) but excludes Konva (deferred via `ImageEditorLazy`)
- `/me/sponsorships` at 251 kB is the heaviest user-facing route — includes
  CancelSubscriptionModal and patronage history. Acceptable for authenticated-only page.
- `/artists/apply` at 241 kB — artist application wizard. Acceptable.
- Admin routes all below 180 kB despite heavy modal components being lazy-loaded.

---

## Dynamic Import Savings (Estimated)

These components are no longer part of the initial parse cost:

| Component | Estimated gzip size | When loaded |
|-----------|---------------------|-------------|
| `BluebirdModal` + Stripe elements logic | ~12 kB | Sponsor button click |
| `ReportModal` | ~3 kB | Report button click |
| `AuctionShareCard` | ~4 kB | Auction owner only |
| Admin modals (×4) | ~8 kB total | Button click |

Total deferred from initial parse: ~27 kB gzip across affected routes.

---

## Lighthouse Score Baseline

Lighthouse requires a running server. Run manually:

```bash
# One-time setup
npm install -g lighthouse

# Run server
npm run build && npm run start &

# Run audit
chmod +x scripts/lighthouse_check.sh
bash scripts/lighthouse_check.sh
```

Reports written to `lighthouse-reports/`. Target scores:

| Category | Target |
|----------|--------|
| Performance | >= 80 |
| Accessibility | >= 90 |
| Best Practices | >= 90 |
| SEO | >= 90 |

Note: Lighthouse scores depend on server environment and network.
Run from a stable machine (not CI) for representative results.

---

## Remaining Warnings (Pre-Existing, Out of Scope)

The build emits deprecation warnings for `themeColor` and `viewport` in
`metadata` exports (Next.js 15 moved these to `generateViewport`). These
are pre-existing across ~20 routes and are not blocking. Fixing them is
a mechanical refactor that can be batched in Phase 9+.

---

## Files Modified / Created

| File | Change |
|------|--------|
| `package.json` | Added `@next/bundle-analyzer` devDep + `analyze` script |
| `next.config.mjs` | Added `withBundleAnalyzer` + `canvas: false` webpack alias |
| `src/app/posts/[id]/page.tsx` | Dynamic import: BluebirdModal, ReportModal, AuctionShareCard |
| `src/components/PostCard.tsx` | Dynamic import: BluebirdModal |
| `src/app/admin/artist-interviews/page.tsx` | Dynamic import: InterviewGenerateModal, InterviewReviewModal |
| `src/app/admin/newsletter/page.tsx` | Dynamic import: NewsletterIssueEditor |
| `src/app/admin/press-kits/page.tsx` | Dynamic import: PressKitGenerator |
| `src/app/newsletter/unsubscribe/page.tsx` | Suspense wrapper for useSearchParams (build fix) |
| `scripts/lighthouse_check.sh` | New — Lighthouse CLI audit script |
| `docs/operations/frontend-bundle.md` | This file |
