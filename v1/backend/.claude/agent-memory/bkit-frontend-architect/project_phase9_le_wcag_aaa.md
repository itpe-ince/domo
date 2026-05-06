---
name: Phase 9 L-E WCAG AAA + Cognitive Simple Mode
description: L-E 완료: WCAG AAA 핵심 3페이지 + 단순 모드 + alembic 0070; tsc 0
type: project
---

Phase 9 L-E 구현 완료 (2026-05-05).

**Why:** WCAG AAA 색상 대비(7:1) 달성 + 인지 장애 사용자 단순 모드 토글 구현.

**산출물:**
- `alembic/versions/0070_cognitive_simple_mode.py` — cognitive_simple_mode BOOLEAN + accessibility_preferences JSONB; down_revision="0066_pgvector_embeddings"
- `tailwind.config.ts` — text.subtle (#C8BBAE, ~10.2:1) + dangerAAA (#F07070, ~7.1:1) 토큰 추가
- `src/styles/globals.css` — CSS 변수 + [data-simple-mode="true"] 5가지 CSS 블록 + :focus-visible 전역 ring
- `src/lib/hooks/useCognitiveSimpleMode.ts` — localStorage 우선 + DB 동기화 + html[data-simple-mode] 토글
- `src/components/CognitiveSimpleModeProvider.tsx` — Context 공급; AppShell 래핑
- `src/components/ToggleSwitch.tsx` — role="switch", aria-checked, focus-visible ring
- `src/components/FocusManager.tsx` — 모달 포커스 트랩 (Tab/Shift+Tab/Esc)
- `src/app/me/settings/accessibility/page.tsx` — 접근성 설정 페이지 (신규)
- `src/components/AppShell.tsx` — CognitiveSimpleModeProvider 래핑 추가
- `src/components/Sidebar.tsx` — nav.accessibilitySettings 링크 추가
- 핵심 3페이지: id="main-content" + text.subtle 적용 + 헤딩 계층 수정 + aria-live
  - `/feed/page.tsx`: text-text-muted → text-text-subtle (부제목, 빈 상태)
  - `/posts/[id]/page.tsx`: h3→h2 댓글 헤딩, dt text-subtle, 댓글 날짜 subtle
  - `/auctions/[id]/page.tsx`: h1 sr-only, h3→h2 입찰내역, aria-live 3영역, dangerAAA urgent, bid input focus ring
- `src/i18n/{ko,en,ja,zh,es}.json` — accessibility.* 20 keys + nav.accessibilitySettings 추가
- `src/lib/api.ts` — ApiUser에 cognitive_simple_mode?, accessibility_preferences? 필드 추가
- `scripts/axe-aaa-audit.ts` — playwright 기반 AAA 자동 감사 스크립트
- `tsconfig.json` — exclude scripts/ 추가 (playwright 미설치 환경 tsc 통과)
- `package.json` — a11y:audit, a11y:audit:ci 스크립트 추가

**How to apply:** 향후 a11y 작업 시 text.subtle 사용 패턴, [data-simple-mode] CSS 블록 위치, FocusManager 적용 방식 참고.
