---
name: editor-a11y-tailwind-cleanup G'-3 complete
description: Phase 7 G'-3 execution: tailwind contrast fixes + heading hierarchy + i18n externalization + axe-core setup; tsc 0 errors
type: project
---

Phase 7 G'-3 (a11y-tailwind-cleanup) shipped.

**Why:** Phase 6 D'-4 + B-6 carry-over clearing; WCAG 2.1 AA compliance for dark-palette tokens.

**How to apply:** When continuing a11y work, this step is done. Outstanding items are in audit v0.3 carry-over table.

## Changes shipped

- `tailwind.config.ts` — `text.muted` #7A6F60 → #998F82 (~5.5:1 est.), `border` #3D2F24 → #6B5440 (~3.2:1 est.)
- `OEmbedInput.tsx` — `<h4>` → `<p role="heading" aria-level={2}>` + `useI18n` + `t("post.editor.oembed.title")`
- `SchedulePicker.tsx` — `<h4>` → `<p role="heading" aria-level={2}>` + 3 i18n keys de-hardcoded
- `i18n/{ko,en,ja,zh,es}.json` — 4 keys × 5 locales = 20 new entries in `post.editor.oembed` + `post.editor.schedulePicker` namespaces
- `package.json` — `axe-core ^4.10.2` + `@axe-core/cli ^4.10.2` devDeps
- `scripts/a11y_check.sh` — axe-core CLI script (4 pages, WCAG 2.1 AA, Option C)
- `docs/03-analysis/i18n-a11y-audit-v0.3.md` — audit report

## Remaining carry-overs

- OEmbedInput remaining hardcoded strings (error, button, CTA, hint) — Phase 7+ G'-11
- `primary.muted` contrast #5E7A3E (3.8:1) — Phase 8+ (low priority)
- axe-core CI GitHub Actions workflow — Phase 7 G'-3 follow-up PDCA
- Skip nav link, tab order browser test — Phase 7+
