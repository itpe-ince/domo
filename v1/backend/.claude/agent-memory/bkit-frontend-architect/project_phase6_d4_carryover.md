---
name: Phase 6 D'-4 i18n+a11y carry-over status
description: D'-4 completed items and remaining carry-overs after 2026-05-04 PDCA sprint
type: project
---

D'-4 (phase5-i18n-cleanup) completed 2026-05-04.

**Completed:**
- es.json artist.* 26 keys added (was pre-existing gap since before Phase 5)
- common.close added to all 5 locales (ko/en/ja/zh/es)
- post.editor.scheduledLabel added to all 5 locales
- AuctionShareCard aria-label="닫기" → t("common.close") (B-1 carry-over resolved)
- EditorWorkspace toLocaleString("ko-KR") → toLocaleString(locale), "예약" → t("post.editor.scheduledLabel") (D-1 carry-over resolved)

**Why:** 5-locale parity is now clean for the touched namespaces. Visual regression risk = 0 (text-only changes).

**Carry-over to Phase 6.5:**
- text.muted (#7A6F60) contrast ~3.8:1 — below 4.5:1 AA for normal text — design token change needed in tailwind.config.ts
- border (#3D2F24) contrast ~1.4:1 — below 3:1 SC 1.4.11 for UI boundaries
- OEmbedInput + SchedulePicker: <h4> orphan heading levels + hardcoded Korean strings
- VoiceOver/NVDA manual user testing
- axe-core CI integration
- Skip navigation link
- zh.json simplified/traditional Chinese consistency cleanup (pre-existing)

**How to apply:** When reviewing a11y tasks in Phase 6.5+, start with text.muted contrast fix — it has the widest impact (placeholder text everywhere).
