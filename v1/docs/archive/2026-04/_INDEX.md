# Archive Index — 2026-04

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [domo-home-ia](./domo-home-ia/) | 2026-04-12 | 100.0% | 8 rounds | 홈/팔로잉/탐색 IA 재정의, CreateMenu, 트렌딩 스코어, 반응형 일관성 |
| [domo-artist-onboarding](./domo-artist-onboarding/) | 2026-04-14 | 97% | 2 rounds | 작가 가입 Phase 1: 프로필 필드 확장, 4단계 위저드, 등급 체계 변경 |
| [domo-search](./domo-search/) | 2026-04-18 | 96.5% | 1 round | 통합 검색: 3탭(작가/작품/포스트), SearchBar, 최근 검색, oEmbed |
| [domo-post-editor](./domo-post-editor/) | 2026-04-18 | 94% | 0 rounds | 미디어 리치 에디터: 7개 툴바, 이모지, oEmbed, 스케줄, 태그 자동완성 |
| [domo-admin-panel](./domo-admin-panel/) | 2026-04-18 | - | 0 rounds | 관리자 패널 P1: 유저/학교/콘텐츠/거래 관리 4페이지 + admin 앱 분리 |
| [backend](./backend/) | 2026-04-25 | 99% | 3 rounds | Backend 전체(Phase 0~4 + P3): M1~M6 + KYC + Settlement + 커뮤니티/리워드/배송/PDF/i18n, 23 gaps 해결 |

## backend

- **Scope**: Backend v1/backend/ 전체 PDCA — Phase 0~4 Production Hardening (M1 Stripe / M2 JWT 회전 / M3 GDPR / M4 S3 / M5 Guardian / M6 Rate Limit) + KYC 시스템 + Settlement 정산 + P3 후속 (communities + comments + auto seed, rewards, shipping tracking, B2B PDF, i18n)
- **Artifacts**: [analysis](./backend/backend.analysis.md), [report](./backend/backend.report.md)
- **Design References**: `v1/docs/02-design/phase4.design.md` (902 라인), `v1/docs/02-design/features/domo-kyc.design.md`, `v1/docs/02-design/features/domo-settlement.design.md` (문서 자체는 이동하지 않음, 활성 설계 문서)
- **Key Files Touched**:
  - Backend (신규): `services/payments/{base,mock_stripe,stripe_real}.py` refund 추가, `services/email/templates/{payment_receipt,auction_won,account_deleted,warning_issued}.py`, `services/community_jobs.py`, `services/webhook_cleanup_jobs.py`, `api/admin/{__init__,users,schools,content,transactions}.py` (admin.py 분할), `api/communities.py` (+ comments), `models/community.py` (+CommunityComment), `models/sponsorship.py` (+StripePriceCache)
  - Backend (수정): `services/kyc.py` (require_kyc_verified), `services/guardian.py` (cascade), `services/settlement_jobs.py` (3-state), `services/storage/{base,local,s3}.py` (presign), `core/rate_limit.py` (+gdpr_export scope), `api/me.py`, `api/orders.py`, `api/sponsorships.py`, `api/auctions.py`, `api/artists.py`, `api/settlements.py`, `api/media.py`, `api/reports.py` (+PDF), `services/settings.py` (KRW)
  - Frontend/Admin (N5 reports prefix): `v1/frontend/src/lib/api.ts`, `v1/admin/src/lib/api.ts`
  - Migrations: `0027_order_refunded_at`, `0028_community_comments`, `0029_user_stripe_customer`, `0030_drop_users_birth_date`, `0031_kyc_status_check`
- **New Dependencies**: `reportlab>=4.2` (pure Python, system 의존 없음)
- **Final Match Rate Progression**: 92% (initial) → ~95% (Critical fix) → ~98% (Major fix) → ~98% (Minor fix) → **99%** (재검증 follow-up 포함)
- **Iteration Resolution**: Critical 3 + Major 11 + Minor 9 = **23 gaps + 3 follow-up = 26 issues 전부 해결**
- **Production Readiness**: ✅ KYC 게이트는 default `off`로 시작, 운영 cutover 시 admin 콘솔에서 `enforce`로 전환 가능. 외부 의존성(Stripe live key / AWS S3 / Resend / 법률 검토) 대기.

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
