# Archive Index — 2026-04

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [domo-home-ia](./domo-home-ia/) | 2026-04-12 | 100.0% | 8 rounds | 홈/팔로잉/탐색 IA 재정의, CreateMenu, 트렌딩 스코어, 반응형 일관성 |
| [domo-artist-onboarding](./domo-artist-onboarding/) | 2026-04-14 | 97% | 2 rounds | 작가 가입 Phase 1: 프로필 필드 확장, 4단계 위저드, 등급 체계 변경 |
| [domo-search](./domo-search/) | 2026-04-18 | 96.5% | 1 round | 통합 검색: 3탭(작가/작품/포스트), SearchBar, 최근 검색, oEmbed |
| [domo-post-editor](./domo-post-editor/) | 2026-04-18 | 94% | 0 rounds | 미디어 리치 에디터: 7개 툴바, 이모지, oEmbed, 스케줄, 태그 자동완성 |
| [domo-admin-panel](./domo-admin-panel/) | 2026-04-18 | - | 0 rounds | 관리자 패널 P1: 유저/학교/콘텐츠/거래 관리 4페이지 + admin 앱 분리 |
| [backend](./backend/) | 2026-04-25 | 99% | 3 rounds | Backend 전체(Phase 0~4 + P3): M1~M6 + KYC + Settlement + 커뮤니티/리워드/배송/PDF/i18n, 23 gaps 해결 |
| [editor-role-gating](./editor-role-gating/) | 2026-04-30 | 98% | 1 round | 에디터 #1: 비작가에게 product 옵션 비활성 + 작가신청 CTA, PostTypeSelector 컴포넌트 분리, OQ-1 pending/rejected 분기 |
| [editor-draft-autosave](./editor-draft-autosave/) | 2026-04-30 | 100% | 1 round | 에디터 #2: 임시저장 — localStorage debounce + 서버 draft API 4개 + drafts 목록 페이지 + 멀티탭 storage 이벤트 + 90일 cleanup cron, 5 locale i18n |

## editor-role-gating

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #1 (Phase 1 Foundation, XS) — 비작가 사용자가 `/posts/new`에서 product 타입을 선택 자체를 못 하도록 UI 게이트 강화. 백엔드 role guard는 이미 완전 구현(`api/posts.py:206-210`)되어 있어 검증/문서화만 진행.
- **Artifacts**: [plan](./editor-role-gating/editor-role-gating.plan.md), [design](./editor-role-gating/editor-role-gating.design.md), [analysis](./editor-role-gating/editor-role-gating.analysis.md), [report](./editor-role-gating/editor-role-gating.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Key Files Touched**:
  - Frontend (신규): `components/post-editor/PostTypeSelector.tsx` (135줄, controlled component, OQ-1 pending/rejected 분기 포함)
  - Frontend (수정): `app/posts/new/page.tsx` (인라인 type JSX → PostTypeSelector + applicationStatus useEffect + URL fallback + i18n error)
  - Frontend (i18n): `i18n/{ko,en,ja,zh,es}.json` — `post.type.product.*` 7개 키 추가 (zh는 Traditional Chinese)
  - Backend (테스트): `scripts/smoke_test_role_gating.sh` (curl 기반 — pytest 부재로 대체)
  - Backend (미변경): `api/posts.py:206-210` 검증 완료
- **Decisions**:
  - Q-1 = B (PostTypeSelector 별도 컴포넌트 분리 — #3 reusable)
  - Q-2 = A 변형 (인라인 텍스트 + 클릭 차단 — disabled + apply CTA)
  - Q-3 = C (알림 시스템 활용 — `Notification` + `revoke_user_tokens` + `AUTH_CHANGED_EVENT` 인프라 이미 존재)
  - OQ-1 = B (pending/rejected 사용자 별도 안내 텍스트 분기)
  - OQ-2 = A (deep link 변경 안 함 — `#12 notifications-ux-audit` 신규 sub-PDCA로 분리)
- **Match Rate Progression**: 96% (initial) → 98% (m-1 useRole undefined guard + m-2 zh.json Traditional 정정 후)
- **Iteration**: 1 round (m-1, m-2 minor fix)
- **Lessons Learned**:
  1. Plan 단계의 "scope 초과" 판단 전 사전 코드 탐색 필수 (Q-3 인프라가 이미 존재해 zero-cost였음)
  2. 사용자 우려가 PDCA scope를 벗어나면 새 sub-PDCA로 분리 (#12 추가)
  3. 테스트 인프라 부재 발견 → `test-infra-bootstrap` 신규 sub-PDCA 후보 식별
  4. 백엔드 사전 조사로 작업 범위가 줄어들면 PDCA 규모 즉시 재평가
- **Production Readiness**: ✅ Frontend 컴포넌트 + i18n 5 locale 완비. Backend 검증 완료. Manual QA 4개 케이스 (작가/일반/admin/비로그인) 권장.

## editor-draft-autosave

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #2 (B-1: 임시저장, M) — 포스트 에디터에 localStorage 자동저장(2초 debounce + beforeunload flush) + 서버 draft 영속화(4개 endpoint + 사용자별 20개 한도) + 전용 drafts 목록 페이지 + F5 새로고침 복원 다이얼로그 + 멀티탭 storage 이벤트 경고 배너 + 90일 cleanup cron job 추가.
- **Artifacts**: [plan](./editor-draft-autosave/editor-draft-autosave.plan.md), [design](./editor-draft-autosave/editor-draft-autosave.design.md), [analysis](./editor-draft-autosave/editor-draft-autosave.analysis.md), [report](./editor-draft-autosave/editor-draft-autosave.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Key Files Touched**:
  - Backend (신규): `app/api/drafts.py`, `app/schemas/draft.py`, `app/services/draft_cleanup_jobs.py`, `alembic/versions/0035_draft_limit_index.py`, `scripts/smoke_test_drafts.sh`
  - Backend (수정): `app/api/posts.py` (`from_draft_id` 같은 트랜잭션 삭제), `app/main.py` (cleanup job lifespan 등록)
  - Frontend (신규): `src/lib/hooks/useDraftAutosave.ts`, `src/lib/formatRelativeTime.ts`, `src/components/DraftRestoreDialog.tsx`, `src/app/posts/drafts/page.tsx`
  - Frontend (수정): `src/app/posts/new/page.tsx` (autosave hook 통합 + 멀티탭 storage useEffect + 경고 배너 JSX), `src/components/Sidebar.tsx` (UserDropdown 메뉴), `src/components/icons.tsx` (DraftIcon), `src/lib/api.ts` (Draft helpers)
  - i18n: `i18n/{ko,en,ja,zh,es}.json` — `nav.draftsList` + `post.draft.*` 21개 키 (multiTabWarning 포함)
- **Decisions**:
  - Q-D1 = B (Permissive role check — update 경로는 role 검증 skip, create 경로만 검증)
  - Q-D2 = A (`formatRelativeTime` 별도 유틸로 추출 — notifications와 재사용)
  - Q-D3 = A (cleanup job lifespan 등록 — `webhook_cleanup_jobs.py` 패턴 따름)
  - Q-5 (last-write-wins by timestamp — 멀티탭 충돌 시 데이터 안전성 보장)
- **Match Rate Progression**: 94% (initial v1.0, AC-7 미구현 false-negative) → **100%** (iterate v1.1, 코드 점검 결과 AC-7이 design §3.8 명세대로 이미 완전 구현된 상태 확인 — 실제 코드 변경 0줄)
- **Iteration**: 1 round (코드 변경 없음, analysis 문서만 정정)
- **Lessons Learned**:
  1. Analyze 단계의 false-negative 가능성 — gap-detector가 대규모 페이지(800+줄) 내 분산 구현(state line 111, useEffect line 255-266, JSX line 474-489)을 누락 판정. 다음 PDCA부터 analyze 직전 git status sync 명시화.
  2. Design 문서가 매우 구체적이었던 점이 가장 큰 성공 요인 — §3.8의 코드 스니펫을 그대로 이식 가능했고, OQ traceability 100%로 모든 결정이 코드에 정확히 반영됨.
  3. Additive alembic 마이그레이션(`0035_draft_limit_index.py`) — 기존 데이터 무영향, 다운그레이드 가능.
  4. 5 locale 동시 출시 — 번역 누락 risk를 design 단계에서 명시(`§3.9 i18n Keys`)하여 0 회귀.
  5. 잔존 minor `lastSavedAgo` 키는 호출부 미참조로 가중 제외 — 별도 sub-PDCA(`i18n-time-formatting`)로 이관 권장.
- **Production Readiness**: ✅ Backend 4 endpoint + alembic 마이그레이션 + cleanup cron 등록 + smoke test 8 시나리오. Frontend hook + 페이지 + 배너 + 5 locale i18n 완비. AC 7/7 Pass.

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
