---
name: phase11-D-1 keyboard shortcuts complete
description: Phase 11 D-1: useGlobalHotkeys hook + KeyboardShortcutsHelp modal + j/k feed nav + ⌘S draft save + 10 i18n keys × 5 locales; tsc 0 errors
type: project
---

Phase 11 D-1 구현 완료: 전역 키보드 단축키 시스템

**Why:** 기존에 단축키가 각 컴포넌트(PublishDrawer ESC, ImageEditor 1/2/3/4)에 분산되어 있었으나 전역 j/k/⌘S/? 단축키를 재사용 가능한 인프라로 통합 필요.

**How to apply:** 향후 전역 단축키 추가 시 `useGlobalHotkeys` hook 배열에 항목 추가. 폼 내부 단축키는 `preventInInputs: false` 설정 필수.

## 생성/수정 파일

| 파일 | 타입 |
|------|------|
| `src/lib/hooks/useGlobalHotkeys.ts` | 신규 — 전역 keydown 등록 hook |
| `src/components/KeyboardShortcutsHelp.tsx` | 신규 — 도움말 모달 (커스텀 dialog, aria-modal) |
| `src/components/AppShell.tsx` | 수정 — usePathname + helpOpen state + navigateFeed + useGlobalHotkeys |
| `src/app/feed/page.tsx` | 수정 — FeedItem wrapper에 data-feed-item + tabIndex={0} |
| `src/app/posts/new/page.tsx` | 수정 — useGlobalHotkeys ⌘S → handleManualSave |
| `src/i18n/ko.json` | 수정 — keyboardShortcuts.* 10 keys |
| `src/i18n/en.json` | 수정 — keyboardShortcuts.* 10 keys |
| `src/i18n/ja.json` | 수정 — keyboardShortcuts.* 10 keys |
| `src/i18n/zh.json` | 수정 — keyboardShortcuts.* 10 keys |
| `src/i18n/es.json` | 수정 — keyboardShortcuts.* 10 keys |

## 핵심 설계 결정

- Dialog 구현: shadcn/ui 없이 커스텀 (기존 DraftRestoreDialog 패턴 동일)
- ESC 닫기: KeyboardShortcutsHelp 내부 capture:true keydown으로 처리 (useGlobalHotkeys와 충돌 방지)
- j/k DOM 쿼리: `[data-feed-item]` 속성 + `tabIndex={0}` wrapper div (FeedItem 컴포넌트 props 변경 없음)
- ⌘S: modifier "cmd" → macOS metaKey + Windows ctrlKey 동시 지원, preventInInputs:false
- 모달 열린 동안: j/k/? 모두 enabled:false (AppShell helpOpen state 기반)
