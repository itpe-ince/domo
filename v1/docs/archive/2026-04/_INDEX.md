# Archive Index — 2026-04

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [domo-home-ia](./domo-home-ia/) | 2026-04-12 | 100.0% | 8 rounds | 홈/팔로잉/탐색 IA 재정의, CreateMenu, 트렌딩 스코어, 반응형 일관성 |
| [domo-artist-onboarding](./domo-artist-onboarding/) | 2026-04-14 | 97% | 2 rounds | 작가 가입 Phase 1: 프로필 필드 확장, 4단계 위저드, 등급 체계 변경 |

## domo-home-ia

- **Scope**: X/TikTok 스타일 사이드바 IA 구축, 홈(혼합 피드) / 팔로잉(독립) / 탐색 역할 분리, CreateMenu 2옵션 팝오버, 모바일/데스크탑 반응형 일관성, 알림 뱃지 공유 훅, 트렌딩 스코어 SQL 구현, A11y 보강
- **Artifacts**: [analysis](./domo-home-ia/domo-home-ia.analysis.md), [report](./domo-home-ia/domo-home-ia.report.md)
- **Design References**: 전체 `docs/02-design/design.md`의 §4.1, §4.2, §5, §6.7 섹션 갱신 (문서 자체는 이동하지 않음, 프로젝트 공용)
- **Key Files Touched**:
  - Frontend: `app/layout.tsx`, `app/page.tsx`, `app/following/page.tsx`, `app/explore/page.tsx`, `app/notifications/page.tsx`, `app/posts/new/page.tsx`, `components/AppShell.tsx`, `components/Sidebar.tsx`, `components/MobileTabBar.tsx`, `components/CreateMenu.tsx`, `components/LoginModal.tsx`, `components/icons.tsx`, `lib/useMe.ts`, `lib/useUnreadCount.ts`, `lib/api.ts`
  - Backend: `app/api/posts.py`
- **Final Match Rate Progression**: 63.5% → 89.75% → 95.0% → 100.0%

## domo-artist-onboarding

- **Scope**: 작가 가입 Phase 1 — ArtistApplication/ArtistProfile 모델 확장 (13개 필드), 4단계 위저드 신청 폼, 등급 체계 변경 (student/emerging/recommended/popular), 대표 작품 JSONB, 컴포넌트 6개 분리
- **Artifacts**: [plan](./domo-artist-onboarding/domo-artist-onboarding.plan.md), [design](./domo-artist-onboarding/domo-artist-onboarding.design.md), [analysis](./domo-artist-onboarding/domo-artist-onboarding.analysis.md), [report](./domo-artist-onboarding/domo-artist-onboarding.report.md)
- **Key Files Touched**:
  - Backend: `models/user.py`, `schemas/artist.py`, `api/artists.py`, `api/admin.py`, `api/users.py`, `alembic/versions/0014_*`
  - Frontend: `app/artists/apply/page.tsx`, `components/artist-apply/*` (7 files), `lib/api.ts`
- **Final Match Rate**: 93% → 97%
- **Next Phases**: Phase 2 (학교 이메일 인증), Phase 3 (KYC), Phase 4 (자동 전환 크론잡)
