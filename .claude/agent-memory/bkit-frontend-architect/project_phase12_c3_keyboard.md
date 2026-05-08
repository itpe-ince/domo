---
name: phase12-C-3 keyboard expansion complete
description: Phase 12 C-3: useSequenceHotkeys + g-시퀀스 6개 + n/slash/b + 4 카테고리 모달 + i18n 9 keys × 5 locale; tsc 0 errors
type: project
---

Phase 12 C-3 키보드 단축키 확장 완료.

**Why:** Phase 11 D-1 useGlobalHotkeys 인프라 위에 GitHub/Slack 표준 g-시퀀스 navigation 단축키 추가. 단일 키 → 두 키 시퀀스 패턴 분리.

**How to apply:** 이후 시퀀스 단축키 추가 시 useSequenceHotkeys hook에 배열 항목으로 등록. AppShell에서 두 hook 병렬 호출 패턴 유지.

## 변경/생성 파일

| 파일 | 변경 내용 |
|------|---------|
| `v1/frontend/src/lib/hooks/useSequenceHotkeys.ts` | 신규 — 두 키 시퀀스 처리, timeoutMs 1000ms 기본값, lastKeyRef+타임아웃 |
| `v1/frontend/src/lib/hooks/__tests__/useSequenceHotkeys.test.ts` | 신규 — 7개 unit test 케이스 |
| `v1/frontend/src/components/AppShell.tsx` | useSequenceHotkeys import + g-시퀀스 6개 + useGlobalHotkeys에 n/slash/b 추가 |
| `v1/frontend/src/components/KeyboardShortcutsHelp.tsx` | 4 카테고리 재편(navigation/feed/editor/general), SequenceKeys 컴포넌트 추가 |
| `v1/frontend/src/components/SearchBar.tsx` | input에 data-search-input 속성 추가 |
| `v1/frontend/src/components/FeedItem.tsx` | article에 data-feed-item/data-post-id, 북마크 버튼 data-bookmark-btn 추가 |
| `v1/frontend/src/i18n/ko.json` | keyboardShortcuts.* 9 keys 추가 (navigation 카테고리 + 6 goto + newPost/searchFocus/bookmarkToggle) |
| `v1/frontend/src/i18n/en.json` | 동일 구조 영어 번역 |
| `v1/frontend/src/i18n/ja.json` | 동일 구조 일본어 번역 |
| `v1/frontend/src/i18n/zh.json` | 동일 구조 중국어 번역 |
| `v1/frontend/src/i18n/es.json` | 동일 구조 스페인어 번역 |

## 주요 설계 결정

- timeoutMs 기본값: 300ms(plan 원문) → **1000ms** (OQ 명시, 타이핑 실패율 고려)
- 북마크 버튼: FeedItem engagement bar에 data-bookmark-btn 버튼 신규 추가 (PostCard는 북마크 없음)
- data-feed-item: FeedItem article 요소에 신규 추가 (D-1 getActiveIndex에서 이미 조회하던 속성)
- useGlobalHotkeys 수정 없음 — D-1 호환성 유지
- n 단축키: isFeedPage 조건 없이 전역 등록 (새 포스트는 모든 페이지에서 진입 가능)
