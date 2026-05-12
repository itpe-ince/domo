---
title: i18n + a11y Audit Report v0.2
phase: D'-4 (Phase 6)
date: 2026-05-04
---

# i18n + Accessibility Audit Report v0.2

## 1. 5-Locale Parity Status

### Summary (post D'-4 fixes)

| Locale | Keys before D'-4 | New keys added | Status |
|--------|-----------------|----------------|--------|
| ko | baseline | +`common.close`, +`post.editor.scheduledLabel` | reference |
| en | missing `common.close`, `post.editor.scheduledLabel` | +2 | FIXED |
| ja | missing `common.close`, `post.editor.scheduledLabel` | +2 | FIXED |
| zh | missing `common.close`, `post.editor.scheduledLabel` | +2 | FIXED |
| es | missing 28 keys (26 `artist.*` + `common.close` + `post.editor.scheduledLabel`) | +28 | FIXED |

### New keys added D'-4

- `common.close` — "닫기" / "Close" / "閉じる" / "關閉" / "Cerrar"
- `post.editor.scheduledLabel` — "예약" / "Scheduled" / "予約" / "預約" / "Programado"
- `artist.*` (26 keys, es only) — full artist application namespace

### Remaining parity gaps (carry-over)

None detected in the 5 primary namespaces touched by D'-4. Legacy gaps in zh.json (simplified Chinese mixing in some zh.json entries — e.g. `post.editor.media.error.*` uses simplified Chinese characters) are pre-existing style issues, not key parity failures. Flagged for Phase 6.5.

---

## 2. AuctionShareCard aria-label (B-1 carry-over)

**Issue**: Close button `aria-label="닫기"` hardcoded Korean string.

**Fix applied**: `AuctionShareCard.tsx` line 203 → `aria-label={t("common.close")}`

**Status**: FIXED. All 5 locales now have `common.close`.

---

## 3. EditorWorkspace 예약 배지 (D-1 carry-over)

**Issue**: `new Date(scheduledAt).toLocaleString("ko-KR")` hardcodes Korean locale; "예약" text hardcoded.

**Fix applied** (`EditorWorkspace.tsx`):
- `const { t, locale } = useI18n()` — destructure locale from i18n context
- `toLocaleString("ko-KR")` → `toLocaleString(locale)` — renders in user's selected locale
- `"예약"` → `{t("post.editor.scheduledLabel")}` — i18n key added to all 5 locales

**Status**: FIXED. No behavior change — date format adapts to user locale.

---

## 4. Heading Hierarchy Audit

### Pages checked
- `app/me/tier-benefits/page.tsx` — h1 → h2: PASS
- `app/me/patronage/page.tsx` — h1 → h2: PASS
- `app/me/sponsorships/page.tsx` — h1 → h2 × 2: PASS
- `app/me/account/page.tsx` — h1 → h2 × 4: PASS
- `app/users/[id]/page.tsx` — h1 → h2 × 2: PASS
- `app/users/[id]/series/page.tsx` — h1 only: PASS
- `app/posts/drafts/page.tsx` — h1 only: PASS
- `app/posts/[id]/page.tsx` — h1 → h3 (section title): PASS
- `app/support/page.tsx` — h1 → h2 × 3 → h3: PASS

### Violations found (carry-over)

| File | Issue | Risk |
|------|-------|------|
| `components/post-editor/OEmbedInput.tsx:57` | `<h4>` with no h1-h3 context (floating popover) | Low — widget context |
| `components/post-editor/SchedulePicker.tsx:39` | `<h4>` with no h1-h3 context (floating popover) + hardcoded Korean | Low — widget context |

These are floating popover panels, not page sections. They create orphaned heading levels in the document outline. Recommended fix: replace `<h4>` with `<p className="text-sm font-semibold" role="heading" aria-level="2">` or add `aria-label` to the container div. Deferred to Phase 6.5 (low user impact in current form).

### Additional hardcoded strings in editor components (carry-over)

- `OEmbedInput.tsx`: "지원하지 않는 URL이거나 가져올 수 없습니다.", "확인", "임베드 추가", "YouTube, Instagram, TikTok, X URL을 붙여넣으세요."
- `SchedulePicker.tsx`: "예약 게시", "설정한 시간에 자동으로 공개됩니다.", "예약 취소"

These are pre-existing and out of D'-4 scope.

---

## 5. WCAG 2.1 AA Color Contrast Audit — Top 10

Theme: Domo "두쫀쿠" dark palette (`tailwind.config.ts`)

| # | Pair (foreground / background) | Ratio (est.) | WCAG AA Normal | WCAG AA Large | Status |
|---|-------------------------------|--------------|----------------|---------------|--------|
| 1 | text.primary #F5EFE4 / background #1A1410 | 17.3:1 | PASS | PASS | ✓ |
| 2 | text.secondary #B5A99A / background #1A1410 | 8.1:1 | PASS | PASS | ✓ |
| 3 | text.muted #7A6F60 / background #1A1410 | 3.8:1 | FAIL | PASS | ✗ |
| 4 | primary #A8D76E / background #1A1410 | 11.0:1 | PASS | PASS | ✓ |
| 5 | primary #A8D76E / surface #2A2018 | 9.6:1 | PASS | PASS | ✓ |
| 6 | danger #E85D5D / background #1A1410 | 5.4:1 | PASS | PASS | ✓ |
| 7 | warning #F0B14A / background #1A1410 | 9.8:1 | PASS | PASS | ✓ |
| 8 | text.muted #7A6F60 / surface #2A2018 | 3.3:1 | FAIL | PASS | ✗ |
| 9 | primary.muted #5E7A3E / background #1A1410 | 3.8:1 | FAIL | PASS | ✗ |
| 10 | border #3D2F24 / background #1A1410 | 1.4:1 | N/A (non-text) | FAIL (3:1) | ✗ |

### Findings

**FAIL items:**

1. **`text.muted` (#7A6F60) — ~3.8:1** — Used for placeholder text, secondary hints, muted labels. Below 4.5:1 AA for normal text. This is the highest-impact issue.
   - Affected: all input `placeholder:text-text-muted`, `AutosaveIndicator` timestamps, search hints, caption hints
   - Recommended fix: Lighten to `#8A7E6E` (est. ~4.6:1) or `#998F82` (est. ~5.5:1)

2. **`text.muted` on surface (#2A2018) — ~3.3:1** — Even lower contrast. Same class, darker background.

3. **`primary.muted` (#5E7A3E) — ~3.8:1** — Used rarely; primarily for `primary` hover states. Low usage, medium priority.

4. **`border` (#3D2F24) on background — ~1.4:1** — SC 1.4.11 Non-text contrast requires 3:1 for UI component boundaries. The visible border between cards and background is currently below this threshold.
   - This is a design-level trade-off (subtle dark-on-dark aesthetic). Recommended: raise to `#5A4535` (est. ~2.7:1, closer but still below 3:1) or `#6B5440` (~3.2:1).

### Focus indicators (PASS)

`focus-visible:ring-2 focus-visible:ring-primary` — primary (#A8D76E) has ~11:1 contrast, well above 3:1. PASS across all checked components.

### Carry-over

- `text.muted` contrast fix — design token change in `tailwind.config.ts` — requires visual regression review
- `border` contrast fix — aesthetic trade-off decision by product/design

---

## 6. ARIA Code Audit (Screen Reader Simulation)

### Checked: AuctionShareCard

- **Modal role**: `role="dialog" aria-modal="true" aria-label={t("auction.shareCard.title")}` — correct
- **Close button**: `aria-label={t("common.close")}` — FIXED (was hardcoded "닫기")
- **Focus trap**: `closeBtnRef` receives focus on open via `requestAnimationFrame` — correct
- **ESC key**: handled — correct
- **Backdrop**: `aria-hidden="true"` — correct

### Checked: EditorWorkspace

- **Multi-tab warning**: `role="status"` — correct live region
- **Title h1**: single h1 in sticky header — correct
- **Scheduled badge**: now reads locale-appropriate date + i18n label — FIXED

### Checked: BluebirdModal

- **closeAriaLabel**: uses `bluebird_modal.closeAriaLabel` i18n key — correct (all 5 locales have this)
- **Type/amount selects**: use aria-label i18n keys — correct

### Checked: Tier-related pages

- `app/me/tier-benefits/page.tsx`: single h1 with `t("tierBenefits.editor.title")` — correct
- `app/me/patronage/page.tsx`: h1 + section h2s — correct
- `app/me/sponsorships/page.tsx`: h1 + section h2s — correct

### Remaining manual test items (carry-over)

- VoiceOver/NVDA live user testing — Phase 6.5
- Tab order verification with real browser — Phase 6.5
- Skip navigation link — not yet implemented — Phase 6.5
- `axe-core` CI integration — Phase 6+

---

## 7. Summary of D'-4 Changes

### Files modified

| File | Change | LOC delta |
|------|--------|-----------|
| `src/i18n/ko.json` | +`common.close`, +`post.editor.scheduledLabel` | +2 |
| `src/i18n/en.json` | +`common.close`, +`post.editor.scheduledLabel` | +2 |
| `src/i18n/ja.json` | +`common.close`, +`post.editor.scheduledLabel` | +2 |
| `src/i18n/zh.json` | +`common.close`, +`post.editor.scheduledLabel` | +2 |
| `src/i18n/es.json` | +`common.close`, +`post.editor.scheduledLabel`, +`artist.*` (26 keys) | +30 |
| `src/components/AuctionShareCard.tsx` | `aria-label` hardcode → `t("common.close")` | ~0 |
| `src/components/post-editor/EditorWorkspace.tsx` | locale-aware date + `t("post.editor.scheduledLabel")` | +1 |

### Carry-over to Phase 6.5

1. `text.muted` contrast fix (tailwind.config.ts) — design decision required
2. `border` contrast fix — design decision required
3. OEmbedInput / SchedulePicker heading level + hardcoded strings
4. VoiceOver/NVDA manual user test
5. axe-core CI integration
6. Skip navigation link
7. zh.json simplified/traditional Chinese consistency cleanup
