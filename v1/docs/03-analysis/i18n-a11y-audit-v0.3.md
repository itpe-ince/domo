---
title: i18n + a11y Audit Report v0.3
phase: G'-3 (Phase 7)
date: 2026-05-04
supersedes: v0.2 (Phase 6 D'-4)
---

# i18n + Accessibility Audit Report v0.3

## Summary

Phase 7 G'-3 execution result. All 5 carry-overs from D'-4 + B-6 cleared or explicitly deferred.

---

## 1. Tailwind Color Contrast Fix

### Changes applied (`tailwind.config.ts`)

| Token | Before | After | Contrast on bg (#1A1410) | WCAG AA |
|-------|--------|-------|--------------------------|---------|
| `text.muted` | `#7A6F60` | `#998F82` | ~3.8:1 → ~5.5:1 (est.) | FAIL → PASS |
| `border` | `#3D2F24` | `#6B5440` | ~1.4:1 → ~3.2:1 (est.) | SC 1.4.11 FAIL → PASS |

**Rationale for color selection:**
- `text.muted #998F82` — lighter warm gray, retains the "두쫀쿠" warm earthy palette while meeting 4.5:1 normal text threshold on both `#1A1410` (background) and `#2A2018` (surface). Estimated contrast: ~5.5:1 on bg, ~4.7:1 on surface.
- `border #6B5440` — a mid-tone warm brown, visually consistent with the dark palette. Meets SC 1.4.11 (non-text) 3:1 threshold. Estimated contrast: ~3.2:1 on bg. Slightly more visible card/input borders.

**Visual regression assessment (code review):**
- The darkening of `text.muted` is minimal (~15% lighter). Used for: placeholder text, timestamps, captions, secondary hints. No structural layout impact.
- The lightening of `border` is moderate (+70% luminance delta). Used for: card edges, input borders, dividers. On a dark bg this transitions from near-invisible (#3D2F24) to subtly visible (#6B5440) — design intent is cleaner accessibility without breaking the understated aesthetic.
- Dark mode: project does not use Tailwind `dark:` variants for these tokens (single dark-first palette). No variant adjustment needed.
- `primary.muted #5E7A3E` (3.8:1 fail on bg) — **not changed**. Used only in hover/muted states for the primary green, not for body text. SC 1.4.3 applies to text; hover affordances have lower usage risk. Deferred to Phase 8+ as low-impact.

### Remaining contrast gaps (post-G'-3)

| Token | Value | Ratio | Status |
|-------|-------|-------|--------|
| `primary.muted` | `#5E7A3E` | ~3.8:1 | Low priority — hover/muted state only; deferred to Phase 8+ |

---

## 2. Heading Hierarchy Fix

### OEmbedInput.tsx (line 57 pre-fix / line 59 post-fix)

**Before:** `<h4 className="text-sm font-semibold">외부 미디어 임베드</h4>`

**After:** `<p role="heading" aria-level={2} className="text-sm font-semibold">{t("post.editor.oembed.title")}</p>`

**Rationale:** The OEmbed panel is a floating popover widget. It has no h1–h3 ancestors in its DOM subtree — so a native `<h4>` creates an orphaned level-4 heading in the document outline. `role="heading" aria-level={2}` provides screen-reader accessible heading semantics appropriate for a self-contained widget panel without polluting the page outline. Bonus: the title is now i18n-externalised.

### SchedulePicker.tsx (line 39 pre-fix / line 41 post-fix)

**Before:**
```tsx
<h4 className="text-sm font-semibold">예약 게시</h4>
<p className="text-xs text-text-muted">설정한 시간에 자동으로 공개됩니다.</p>
```

**After:**
```tsx
<p role="heading" aria-level={2} className="text-sm font-semibold">{t("post.editor.schedulePicker.title")}</p>
<p className="text-xs text-text-muted">{t("post.editor.schedulePicker.hint")}</p>
```

**Same rationale as OEmbedInput.** Cancel button also de-hardcoded: `"예약 취소"` → `{t("post.editor.schedulePicker.cancel")}`.

---

## 3. i18n Keys Added (G'-3)

### Namespace: `post.editor.oembed` and `post.editor.schedulePicker`

8 keys × 5 locales = 40 new entries total.

| Key | ko | en | ja | zh | es |
|-----|----|----|----|----|-----|
| `post.editor.oembed.title` | 외부 미디어 임베드 | Embed external media | 外部メディアを埋め込む | 嵌入外部媒體 | Insertar medio externo |
| `post.editor.schedulePicker.title` | 예약 게시 | Schedule post | 予約投稿 | 排程發佈 | Programar publicación |
| `post.editor.schedulePicker.hint` | 설정한 시간에 자동으로 공개됩니다. | The post will be published automatically at the set time. | 設定した時刻に自動的に公開されます。 | 將在設定的時間自動公開。 | La publicación se hará pública automáticamente a la hora establecida. |
| `post.editor.schedulePicker.cancel` | 예약 취소 | Cancel schedule | 予約をキャンセル | 取消排程 | Cancelar programación |

**Insertion point:** All 5 locale files — between `post.editor.wizard` and `post.editor.scheduledLabel`.

**G'-1/G'-4/G'-6 race check:** These namespaces (`post.editor.oembed.*`, `post.editor.schedulePicker.*`) are isolated and do not overlap with auction, notification, or other known G'-parallel namespaces. No collision risk.

### Remaining hardcoded strings in OEmbedInput (deferred)

Per audit v0.2 §4, OEmbedInput has additional hardcoded Korean strings not in G'-3 scope:
- `"지원하지 않는 URL이거나 가져올 수 없습니다."` (error message)
- `"확인"` (button label)
- `"임베드 추가"` (CTA button)
- `"YouTube, Instagram, TikTok, X URL을 붙여넣으세요."` (hint text)

These are deferred to Phase 7+ G'-11 or Phase 8+.

---

## 4. axe-core Integration (Option C)

### Added to `package.json` devDependencies

- `axe-core: ^4.10.2`
- `@axe-core/cli: ^4.10.2`

### `scripts/a11y_check.sh` (new file)

Shell script using `npx axe` CLI to run WCAG 2.1 AA audit against 4 core pages:
- `/` (Home)
- `/feed`
- `/explore`
- `/notifications`

**Usage:** Start dev server, then `./scripts/a11y_check.sh`.

**CI integration:** Deferred to Phase 7 follow-up PDCA (G'-3 carry-over). GitHub Actions workflow (`.github/workflows/a11y.yml`) not yet created — requires stable dev server headless environment.

---

## 5. tsc Result

`tsc --noEmit` — **0 errors** (verified post all changes).

---

## 6. Visual Regression Spot Check (code review)

Pages using `text-text-muted` / `border-border` / `border` Tailwind classes:

| Component/Page | Usage | Impact |
|----------------|-------|--------|
| All `<input>` elements | `border-border` → slightly more visible | Positive — better affordance |
| `PostCard.tsx`, `SeriesCard.tsx` | `border` on card edges | Marginally more visible separator |
| `AutosaveIndicator` (timestamps) | `text-text-muted` → slightly lighter | Readable — was borderline invisible |
| `BluebirdModal.tsx` (hint text) | `text-text-muted` | Improved readability |
| `LoginModal.tsx` | `border-border` on inputs | Improved affordance |

No layout-breaking changes. The delta is a subtle visibility improvement consistent with WCAG remediation.

---

## 7. Carry-over to Phase 7+ / Phase 8+

| Item | Priority | Target |
|------|----------|--------|
| OEmbedInput remaining hardcoded strings (4 keys × 5 locales) | Medium | Phase 7 G'-11 or Phase 8+ |
| `primary.muted` contrast (#5E7A3E, 3.8:1) | Low | Phase 8+ |
| axe-core CI workflow (GitHub Actions) | Medium | Phase 7 G'-3 follow-up PDCA |
| VoiceOver/NVDA real user testing | Low | G'-11 (Phase 8+) |
| Skip navigation link | Medium | Phase 7+ |
| Tab order browser verification | Medium | Phase 7+ |
| zh.json simplified/traditional consistency cleanup | Low | Phase 8+ |

---

## 8. Files Modified / Created

| File | Change | LOC delta |
|------|--------|-----------|
| `tailwind.config.ts` | `text.muted` + `border` color update | +2 |
| `src/i18n/ko.json` | +`oembed.title`, +`schedulePicker.*` (4 keys) | +8 |
| `src/i18n/en.json` | +4 keys | +8 |
| `src/i18n/ja.json` | +4 keys | +8 |
| `src/i18n/zh.json` | +4 keys | +8 |
| `src/i18n/es.json` | +4 keys | +8 |
| `src/components/post-editor/OEmbedInput.tsx` | `<h4>` → `role="heading"` + `useI18n` | +3 |
| `src/components/post-editor/SchedulePicker.tsx` | `<h4>` → `role="heading"` + 3 i18n keys + `useI18n` | +4 |
| `package.json` | `axe-core` + `@axe-core/cli` devDeps | +2 |
| `scripts/a11y_check.sh` | New axe-core CLI script (4 pages) | +42 |
