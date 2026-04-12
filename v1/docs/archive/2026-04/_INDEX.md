# Archive Index — 2026-04

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [domo-home-ia](./domo-home-ia/) | 2026-04-12 | 100.0% | 8 rounds | 홈/팔로잉/탐색 IA 재정의, CreateMenu, 트렌딩 스코어, 반응형 일관성 |

## domo-home-ia

- **Scope**: X/TikTok 스타일 사이드바 IA 구축, 홈(혼합 피드) / 팔로잉(독립) / 탐색 역할 분리, CreateMenu 2옵션 팝오버, 모바일/데스크탑 반응형 일관성, 알림 뱃지 공유 훅, 트렌딩 스코어 SQL 구현, A11y 보강
- **Artifacts**: [analysis](./domo-home-ia/domo-home-ia.analysis.md), [report](./domo-home-ia/domo-home-ia.report.md)
- **Design References**: 전체 `docs/02-design/design.md`의 §4.1, §4.2, §5, §6.7 섹션 갱신 (문서 자체는 이동하지 않음, 프로젝트 공용)
- **Key Files Touched**:
  - Frontend: `app/layout.tsx`, `app/page.tsx`, `app/following/page.tsx`, `app/explore/page.tsx`, `app/notifications/page.tsx`, `app/posts/new/page.tsx`, `components/AppShell.tsx`, `components/Sidebar.tsx`, `components/MobileTabBar.tsx`, `components/CreateMenu.tsx`, `components/LoginModal.tsx`, `components/icons.tsx`, `lib/useMe.ts`, `lib/useUnreadCount.ts`, `lib/api.ts`
  - Backend: `app/api/posts.py`
- **Final Match Rate Progression**: 63.5% → 89.75% → 95.0% → 100.0%
