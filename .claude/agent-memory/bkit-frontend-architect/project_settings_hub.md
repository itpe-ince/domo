---
name: settings-hub consolidation complete
description: /me/settings Hub 페이지 + 6 sub-page로 파편화 8개 페이지 통합 완료
type: project
---

8개 설정 페이지를 /me/settings Hub + 6 카테고리 구조로 통합.

**Why:** UX 파편화 해소 — 사용자가 설정을 여러 URL에서 찾아야 했던 문제 제거.

**How to apply:** 설정 관련 링크는 항상 /me/settings/{category} 형식 사용.

## URL 매핑 (구 → 신)
- /me/account → /me/settings/account (sponsor-validity 섹션 통합)
- /me/bio → /me/settings/profile
- /me/newsletter → /me/settings/notifications (뉴스레터 섹션 통합)
- /me/notifications/preferences → /me/settings/notifications
- /me/settings/preferences → /me/settings/display
- /me/settings/sponsor-validity → /me/settings/account

## 신규 파일
- /me/settings/page.tsx (Hub, 6 카드 그리드)
- /me/settings/profile/page.tsx
- /me/settings/display/page.tsx
- /me/settings/notifications/page.tsx
- /me/settings/account/page.tsx

## 기존 유지 (breadcrumb 업데이트만)
- /me/settings/accessibility/page.tsx
- /me/settings/privacy/page.tsx

## i18n: settings.hub.* 추가 (12 keys × 5 locales = 60 entries)
