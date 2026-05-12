---
name: Phase 8 H'-1 a11y voiceover-nvda-test-fix
description: H'-1 완료: SkipLink 컴포넌트 신규, AppShell id="main-content", 11페이지 ARIA fix, 5 locale a11y.skip.* 10 keys; tsc 0
type: project
---

H'-1 ARIA audit + fix 완료.

**Why:** Phase 7 G'-11 deferred 흡수. WCAG 2.4.1 Bypass Blocks (Level A) 미충족 상태였음.

**How to apply:** Phase 9+에서 real VoiceOver/NVDA 사용자 테스트 진행 시 이 작업을 기반으로 시작. 색상 대비 이슈는 D'-4 carry-over 메모리 참고.

Key deliverables:
- `/src/components/SkipLink.tsx` — 신규 (WCAG 2.4.1)
- `AppShell.tsx` — SkipLink + `id="main-content"` 추가
- i18n: `a11y.skip.toMain` / `a11y.skip.toNav` 5 locale × 2 = 10 entries
- Audit report: `v1/docs/03-analysis/i18n-a11y-audit-v0.4.md`
- 14 page/component files modified (ARIA landmark labels, role=tab, aria-pressed, aria-live, role=alert, aria-expanded)
- tsc 0, 336 baseline 유지
