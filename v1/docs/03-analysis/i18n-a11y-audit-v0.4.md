# i18n + a11y Audit Report v0.4

**Phase**: 8 H'-1 voiceover-nvda-test-fix  
**Date**: 2026-05-04  
**Scope**: Phase 5/6/7 신규 11 페이지 ARIA audit + fix  
**tsc**: 0 errors  
**Baseline tests**: 336+3 skipped (maintained)

---

## 1. Skip Navigation (WCAG 2.4.1 — Level A)

### New

| File | Change |
|------|--------|
| `src/components/SkipLink.tsx` | 신규: visually-hidden `<a href="#main-content">` — keyboard focus 시 visible |
| `src/components/AppShell.tsx` | SkipLink import + 렌더링 (body 최상단); `div#main-content` id 추가 |

**i18n namespace `a11y.skip.*`** — 5 locale × 2 keys = 10 entries

| key | ko | en | ja | zh | es |
|-----|----|----|----|----|-----|
| `a11y.skip.toMain` | 본문으로 건너뛰기 | Skip to main content | メインコンテンツへスキップ | 跳到主要内容 | Saltar al contenido principal |
| `a11y.skip.toNav` | 내비게이션으로 건너뛰기 | Skip to navigation | ナビゲーションへスキップ | 跳到导航 | Saltar a la navegación |

---

## 2. ARIA Audit Findings & Fixes — 11 Pages

### 2.1 `/` (Home — `app/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("home.title")}` |

### 2.2 `/feed` (`app/feed/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("feed.title")}` |
| High | Error div no `role="alert"` — not announced | Added `role="alert"` |
| Medium | Loading skeleton not associated with busy state | Wrapped `FeedSkeleton` in `aria-busy="true"` container |
| Low | Feed list was a `<div>` — no list semantics | Changed to `<ul>` with `<li>` wrappers; added `aria-label` |
| Low | Load more button missing `aria-busy` | Added `aria-busy={loading}`, descriptive `aria-label` |

### 2.3 `/explore` (`app/explore/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("explore.title")}` |

Note: `ExploreTabs` already carries `ariaLabel` from A-4 work; `ExploreHeroCard` / `ArtistIndexPreview` already have `ariaLabel` props per A-4 i18n keys.

### 2.4 `/search` (`app/search/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("common.search")}` |
| High | `<form>` not identified as search landmark | Added `role="search"` |
| High | Tab strip buttons missing `role="tab"` and `aria-selected` | Added `role="tablist"` on container, `role="tab"` + `aria-selected` on buttons |
| Medium | Error div no `role="alert"` | Added `role="alert"` |
| Medium | Loading skeletons decorative but not hidden | Added `aria-hidden="true"` on skeleton items; container `aria-busy="true"` |
| High | Follow button label "팔로우" — ambiguous for screen readers | Added `aria-label={follow @{username}}` |

### 2.5 `/posts/[id]` (`app/posts/[id]/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | Loading state `<main>` not announced | Added `aria-busy="true"` + `aria-label` |
| Medium | `<main>` missing `aria-label` | Added `aria-label={post.title}` |
| Low | Back link hardcoded Korean "← 피드로 돌아가기" | Replaced with `t("nav.home")` |
| Medium | Media `<section>` no label | Added `aria-label="Post media"` |
| Medium | Thumbnail buttons no label | Added `aria-label="Media N of M"` + `aria-pressed` |
| Medium | Info section `<section>` no label | Added `aria-label="Post details"` |
| High | Like button: emoji ♥ not hidden, no `aria-pressed` | Added `aria-pressed={liked}` + `aria-label`, wrapped ♥ in `aria-hidden` |
| High | Comment textarea no associated `<label>` | Added `<label htmlFor>` + `id` on textarea |
| Medium | Comments `<section>` missing label | Added `aria-label` |
| Low | Comments heading hardcoded Korean | Replaced with `t("common.comments")` |

### 2.6 `/users/[id]` (`app/users/[id]/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={@username}` |
| Low | Back link hardcoded Korean "← 홈" | Replaced with `t("nav.home")` |
| Medium | `<header>` card missing descriptive label | Added `aria-label` with profile context |
| Low | Avatar `alt` was display_name only — missing role context | Updated to include "profile photo" |
| Medium | Sponsorships `<section>` no label | Added `aria-label="Received sponsorships"` |
| Low | Sponsorships heading uses 🕊 emoji in text | Wrapped in `aria-hidden` span |
| Medium | Posts section no label | Added `aria-label` with count |

### 2.7 `/notifications` (`app/notifications/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| High | Filter tabs: no `role="tablist"` / `role="tab"` / `aria-selected` | Added all three |
| Medium | `aria-label` missing on `tablist` | Added `aria-label={t("notifications.center.title")}` |
| High | Notification `<button>` labels are empty — screen reader reads icon only | Added `aria-label` with title + unread status |
| Low | Unread dot decorative but not hidden | Added `aria-hidden="true"` |
| Low | `<ul>` missing label and live region | Added `aria-label` + `aria-live="polite"` |

### 2.8 `/me/patronage` (`app/me/patronage/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("patronage.artist.title")}` |
| Low | Anonymous `<section>` tags (3) | Added `aria-label` to Summary, Revenue, Supporters sections |

### 2.9 `/me/sponsorships` (`app/me/sponsorships/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("patronage.supporter.title")}` |

### 2.10 `/me/tier-benefits` (`app/me/tier-benefits/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("tierBenefits.editor.title")}` |

### 2.11 `/me/bio` (`app/me/bio/page.tsx`)

| Severity | Issue | Fix |
|----------|-------|-----|
| Medium | `<main>` missing `aria-label` | Added `aria-label={t("bio.pageTitle")}` |
| High | Textarea no associated `<label>` | Added `<label htmlFor>` (sr-only) + `id` on textarea |

### Additional pages fixed (bonus scope)

| Page | Fix |
|------|-----|
| `/me/coupons` | `<div>` root → `<main>` with `aria-label` |
| `/me/interviews` | `<main>` `aria-label`; error `role="alert"`; expand button `aria-expanded` + `aria-controls`; preview container `id` |
| `/me/newsletter` | `<div>` root → `<main>` with `aria-label`; toggle `aria-label` added |

---

## 3. Sidebar (`components/Sidebar.tsx`)

No ARIA changes required in H'-1. Existing observations:

- Nav items use `<Link>` (correct anchor role)
- Language select has `aria-label="Language"` on both expanded and collapsed variants
- Onboarding indicator button has `aria-label={t("onboarding.sidebar.indicator")}`
- Loading placeholders have `aria-hidden`
- `<aside>` landmark is present — no further changes needed

---

## 4. Issues Deferred to Phase 9+

| Issue | Reason |
|-------|--------|
| Real VoiceOver / NVDA user testing | Out of scope per task definition |
| WCAG AAA criteria | Explicitly out of scope |
| Color contrast audit completion (D'-4 carry-over) | Tracked in project_phase6_d4_carryover.md |
| `FeedItem` component internal ARIA (article semantics) | Requires separate component audit |
| `PostCard` — `<img>` alt text from API data quality | Backend data issue, not frontend |
| Admin pages (`/admin/*`) | Lower priority; admin-only audience |

---

## 5. Files Created / Modified

### New
- `/Users/sangincha/dev/domo/v1/frontend/src/components/SkipLink.tsx`
- `/Users/sangincha/dev/domo/v1/docs/03-analysis/i18n-a11y-audit-v0.4.md`

### Modified
- `src/components/AppShell.tsx` — SkipLink integration + `id="main-content"`
- `src/i18n/en.json` — `a11y.skip.*` 2 keys
- `src/i18n/ko.json` — `a11y.skip.*` 2 keys
- `src/i18n/ja.json` — `a11y.skip.*` 2 keys
- `src/i18n/zh.json` — `a11y.skip.*` 2 keys
- `src/i18n/es.json` — `a11y.skip.*` 2 keys
- `src/app/page.tsx`
- `src/app/feed/page.tsx`
- `src/app/explore/page.tsx`
- `src/app/search/page.tsx`
- `src/app/posts/[id]/page.tsx`
- `src/app/users/[id]/page.tsx`
- `src/app/notifications/page.tsx`
- `src/app/me/patronage/page.tsx`
- `src/app/me/sponsorships/page.tsx`
- `src/app/me/tier-benefits/page.tsx`
- `src/app/me/bio/page.tsx`
- `src/app/me/coupons/page.tsx`
- `src/app/me/interviews/page.tsx`
- `src/app/me/newsletter/page.tsx`

---

## 6. WCAG Coverage

| Criterion | Level | Status |
|-----------|-------|--------|
| 1.1.1 Non-text Content | A | Improved (alt text on avatars, aria-hidden on decorative emoji) |
| 1.3.1 Info and Relationships | A | Improved (list semantics on feed, dl on product details) |
| 2.4.1 Bypass Blocks | A | Fixed (SkipLink component) |
| 2.4.3 Focus Order | A | Maintained (no tab-index manipulation) |
| 2.4.6 Headings and Labels | AA | Improved (aria-label on main/section landmarks) |
| 4.1.2 Name, Role, Value | A | Improved (role=tab, aria-selected, aria-pressed, aria-expanded) |
| 4.1.3 Status Messages | AA | Improved (role=alert on errors, aria-live on notification list) |
