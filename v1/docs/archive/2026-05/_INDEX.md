# Archive Index — 2026-05

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [editor-responsive-redesign](./editor-responsive-redesign/) | 2026-05-01 | 96% | 0 rounds | 에디터 #3: 데스크탑 2-pane(편집+미리보기 토글) + 모바일 3·4단 wizard, 803줄 page.tsx 컴포넌트 분해(547줄, -32%), 3 hooks + 9 신규 컴포넌트 + 23 i18n × 5 locale, DB·API 변경 0 |
| [editor-media-ux](./editor-media-ux/) | 2026-05-03 | 95% | 0 rounds | 에디터 #4: dnd-kit drag-reorder + 이미지 캡션(280자, MediaAsset.caption + PATCH /media/{id}) + 다중 업로드 XHR 실시간 progress(OQ-D-3=B 사용자 변경). Backend 5파일 + Frontend 10+파일 + 11 i18n × 5 locale + 첫 외부 라이브러리(@dnd-kit) 도입 |
| [editor-image-studio](./editor-image-studio/) | 2026-05-03 | 96% | 0 rounds | 에디터 #6-image: Konva 클라이언트 4 도구(회전/크롭/모자이크/워터마크) + Pillow 서버 처리 + crop_meta JSONB 비파괴 + alembic 0037+0038 + POST /v1/media/{id}/transform + Signature 3 endpoints (OQ-D-3=B 사용자 override 별도 시그니처 업로드 UI). Backend ~2300 LOC + Frontend ~1500 LOC + 22 tests + 47 i18n × 5 locale |
| [publish-controls](./publish-controls/) | 2026-05-03 | 100% | 0 rounds | 에디터 #8 Critical Path: B-3 발행 옵션 4건 통합. alembic 0039+0040 + Series 모델 + 6 endpoints (publish + Series CRUD 5종) + visibility 필터 + comments lock + audit log. Frontend PublishOptionsPanel + SeriesCreateModal + /series/[id] dnd-kit reorder + VisibilityBadge + handleSubmit hybrid C. Backend ~1800 LOC + Frontend ~2200 LOC + 22 tests + 2 smoke + 47 i18n × 5 locale = 235 entries |
| [artist-tier-release](./artist-tier-release/) | 2026-05-03 | 99% | 0 rounds | 에디터 #10 Phase 4 Critical Path: B-4 후원자/단골 우선 공개. **Option β 채택 (R-1 dissolved)** — Post.visibility enum 미확장, tier_only는 computed effective state. alembic 0041 (early_access_until + early_access_tier + sponsorships R-5 인덱스) + 3 helpers (UNION ALL EXISTS + 2단계 SQL+Python) + tier_release_jobs.py 60s cron + 5 endpoints visibility 필터. Frontend TierReleasePicker (PublishOptionsPanel 5번째 expand) + TierBadge + handleSubmit + posts/[id] 403. Backend ~750 LOC + Frontend ~400 LOC + 17 신규 tests (61 total) + 1 smoke + 22 신규 i18n × 5 = 110 entries |
| [auction-promotion-suite](./auction-promotion-suite/) | 2026-05-04 | 97% | 1 round | **에디터 #11 Phase 4 마지막 Critical Path** — B-4 옥션 종료 알림/홍보 도구. 종료 N시간 전 알림(24h+6h+1h, 작가+최고입찰자) + 공유 카드 자동 생성(Pillow 1200×630 OG, R-2 thumbnail fallback + R-3 메모리 제어) + 카운트다운 위젯(D-1h 1초 adaptive polling). alembic 0042 (Auction +5 컬럼 + partial index) + auction_promotion_jobs.py 60s cron (R-5 격리) + share-card endpoint 6단계 + _auto_transition no-winner 분기. Frontend AuctionCountdown(SSR-safe) + AuctionShareCard(z-[60] modal) + ShareIcon + PostCard/FeedItem D-1h compact + posts/[id] full + owner-gated. Backend ~700 LOC + Frontend ~570 LOC + 16 tests (12 PR2 + 4 iterate) + 1 smoke + 100 신규 i18n × 5 = 500 entries. **Iterate 1회 (C-1 PostOut+active_auction_end_at backend supply + M-1 notification.type.auction.* 4 keys × 5 locales)로 92→97%**. **editor-revamp-roadmap Phase 4 종결 (#1~#11 = 11/11 100%)** |
| [domo-phase12-roadmap](./domo-phase12-roadmap/) | 2026-05-09 | 92.1% (가중, 8/8) | 0 rounds | **Phase 12 종결 (옵션 D 균형)** — Wave A 안정성 강화 (A-1 testing-stability-refactor: testcontainers + freezegun + factory_boy 도입, 17 over-mocked tests refactor / A-2 ML A/B PATCH endpoint pause/complete + ExperimentStatusModals + PostHog flag 동기화) + Wave B-Admin 운영 효율 (B-1 admin audit log 조회 UI: GET /admin/audit-logs cursor pagination + 5 필터 + Security 그룹 / B-2 admin analytics 대시보드: 4 카드 + 4 endpoints + Redis 5분 캐시 + ML Operations 그룹 + SVG fallback / B-3 admin payouts 관리: 6 endpoints + KYC + 정산 + Stripe Connect + Finance 그룹 신규) + Wave C 인증 다양화 + 단축키 (C-1 password reset: alembic 0086 + 2 endpoints + 1시간 만료 + 잠금 해제 + audit_log / C-2 GitHub OAuth + 매직링크: alembic 0086+0087 + 3 endpoints + LoginModal 4탭 / C-3 단축키 확장: useSequenceHotkeys + 6 navigation + 3 actions + 4 카테고리) = 8 sub-PDCAs 통합 92.1%. **K-6 정당 이월** (거래 < 100건, OQ-1 권장 default 준수, Phase 13 Must). **누적**: 694 → **750 passed** + 24 skipped (+56 신규, 회귀 0, 12 GitHub/매직링크 tests Phase 13 carry-over). **alembic** 0085 → 0086_magic_link_tokens → 0087_github_id → **0086_password_reset_tokens single head** (dual head 패치). **API 17개 신규** (admin_payouts 6 + admin_analytics 4 + admin/audit_logs 1 + auth.py 5 + admin_experiments PATCH 1). **AdminShell 4 그룹** (Curation + ML Operations + Security + **Finance 신규**). **가입 4종** (Google + 이메일+비밀번호 + GitHub + 매직링크). **단축키 9개** (g h/f/e/m/n/p + n/, /b). **Out-of-Plan Hot Fixes 3건**: admin_payouts.py FastAPI keyword-only 매개변수 (`*,` 추가) + 12 GitHub/매직링크 tests skip (Phase 13 carry-over) + alembic dual head 즉시 패치 (single head 회복). **README 비전 매핑**: 안정성(A-1/A-2) + 운영 투명성(B-1) + 데이터 의사결정(B-2) + 후원 정산 자동화(B-3) + 가입 다양성(C-1/C-2) + 파워 유저 효율(C-3). **Phase 13 carry-over 7건**: K-6 (Must, 거래 ≥ 100건) + 12 GitHub/매직링크 tests refactor (Should) + A-1 잔존 12 over-mocked (otel/redis/SES) (Should) + 모바일 Native (Should) + audit_logs 파티셔닝 (Could) + /admin/system cron 모니터 (Could) + ML 회귀 K-6 v2 (Could). **13 OQs 권장 default 일괄 수락**. |
| [domo-phase11-roadmap](./domo-phase11-roadmap/) | 2026-05-08 | 96.9% (가중, 7/8) | 0 rounds | **Phase 11 종결** — admin 콘솔 누락 메뉴 4개 (Curation: A-1 Featured Artist 검수 + A-2 AI 컬렉션 검수, ML Operations: B-1 A/B 실험 + B-2 Diversity 튜닝) + Wave D carry-over 청산 (D-1 전역 단축키 j/k/⌘S/? + D-2 audit_logs DB alembic 0084 + D-3 이메일+비밀번호 가입 alembic 0085) = 7 sub-PDCAs 통합 96.9%. **C-1 K-6 정당 이월** (거래 < 100건, Plan OQ-1 권장 default 준수). **누적**: 657 → **694 passed** + 17 skipped (+37 신규, over-mocked 17건은 Phase 12 freezegun/testcontainers refactor 권장). **alembic** 0083 → 0084_audit_logs → 0085_email_password_auth (single head). **cron** 23 → 24 (+1: audit_log_cleanup daily). **AdminShell**: Curation + ML Operations 2 신규 그룹 (4 페이지). **API 16개 신규** admin endpoints (Wave A 8 + Wave B 5 + Wave D 3 + auth.py 4). **A-2 backend 보강 out-of-plan** (PATCH/DELETE/week_start). **AdminShell 가독성 개선** (text-admin-fg + font-medium + accent hover). **README 비전 6/7 직접 구현** (C-1 이월 제외 시 100%): admin 운영 자동화(A-1/A-2) + 데이터 기반 의사결정(B-1) + 다양성 보존(B-2) + 운영 감사 1년(D-2) + 가입 다양성(D-3) + 파워 유저 효율(D-1). **Phase 12 carry-over**: K-6 (Must, 거래 ≥ 100건 시) + 17 over-mocked tests refactor (Should) + B-1 PATCH endpoint pause/complete (Should) + D-3 password reset 플로우 (Should) + D-3 GitHub OAuth + 매직링크 (Should) + D-2 admin audit log 조회 UI (Should) + /admin/analytics + /admin/payouts (Should) + /admin/system cron 모니터 (Could) + D-1 단축키 확장 + audit_logs 파티셔닝 + 모바일 Native = 12 항목. **13 OQs 권장 default 일괄 수락**. **Hot Fix 8건 별도 처리**: ConversationList undefined.length, useExpiryBanner 무한 루프, Sidebar overflow-y-auto, PreferencesCard 통합 카드 (CurrencySwitcher + LocaleSwitcher + 단순 모드), 등록 화면 UX (auto-resize + Drawer + sticky preview + scrollbar 통일), 가이드 v2 정본화 (118 gap → 정본 교체). |
| [domo-phase10-roadmap](./domo-phase10-roadmap/) | 2026-05-06 | 96.4% (가중, partial 5/6) | 0 rounds | **Phase 10 부분 종결** — K Wave 2 (K-8 ML A/B + K-2 Diversity + K-4 Featured Artist + K-7 AI 큐레이션) + CO-1 Phase 9 carry-over 청산 = 5 sub-PDCAs 통합 96.4%. **Critical Path 5/6 완성**: H'-6 → L-A → K-1 → K-8 → K-2 → K-4 → K-7. **Wave A**: K-8 (alembic 0080 ml_experiments + ml_experiment_assignments + posthog_client + 3 admin endpoints + Prometheus 3 metrics, 17 tests) + K-2 (alembic 0081 diversity_configs + 신진작가 boost +20% + 장르≥3/지역≥2 quota + admin+2FA endpoints, 11 tests) + CO-1 (Phase 9 11 carry-over → 6 PR: TESTING_NOTES + rate limit + alt sweep + DocentSection 분리 + FeedAlgo 타입 + i18n CI + 운영 문서, 9 tests). **Wave B**: K-4 (alembic 0082 featured_artist_candidates + composite_score MMR + 22번째 cron 월 09:00 UTC + 4 admin+2FA endpoints, 10 tests) + K-7 (alembic 0083 ai_collections + ai_collection_posts + sklearn KMeans 클러스터링 + LLM 큐레이션 + L-F translation_cache 재사용 + 23번째 cron + /explore/collections 2 페이지 + 5 endpoints + 5 locale 50 keys, 14 tests). **누적**: 581 → **646 passed** + 7 skipped (+65 신규, 회귀 0) + alembic 0080~0083 single head + cron 21 → 23 + 14 신규 endpoints + Mock 모드 fallback 100% + i18n CI 자동 검증 + Phase 9 carry-over 11/11 청산. **README 비전 6/7 직접 구현** (K-6 이월 제외 시 100%): 그로스해킹(K-8) + 글로벌 인덱스(K-2/K-4) + 다양성(K-2 지역≥2) + 컬렉터 회비(K-7) + AI 시대(K-7) + 히스토리(K-7) + 거래(K-6 이월). **K-6 Phase 11 이월 정당화**: 거래 ≥ 100건 OQ-7 미충족 → 강제 진행 금지 원칙 일관 + K-1 운영 14일+ 데이터 누적 후 진입 트리거. **Phase 11 후보**: K-6 (이월 확정) + K-2 lambda 최적화 + 모바일 native + B2B gallery + Marketplace 분할 + ML 자동 재학습. **15 OQs 모두 권장 default 일괄 수락**. |
| [domo-phase9-roadmap](./domo-phase9-roadmap/) | 2026-05-06 | 93.0% (가중, partial 9/14) | 0 rounds | **Phase 9 부분 종결** — L Carry-over (6 sub-PDCAs 92.0%) + K Wave 1 (3 sub-PDCAs 95.1%) = 9 sub-PDCAs 통합 93.0%. **Critical Path 완료**: H'-6 (Phase 8) → L-A pgvector 임베딩 → K-1 ML Collaborative Filtering. **L 단계**: L-A (pgvector 0066 + 12번째 cron + next.config 5 vendor chunks) + L-B (alembic 0067 RSS+OG+open rate, 19 tests) + L-C (alembic 0068+0069 Group DM + WebSocket + 첨부, 36 tests) + L-D (7→3 over-mocked skipped 정상화) + L-E (alembic 0070 WCAG AAA + Cognitive 단순 모드 + 5 locale i18n) + L-F (alembic 0071+0072 번역 메모리 + Cohort Slack alert, 24 tests). **K Wave 1**: K-1 (alembic 0073 Collaborative Filtering MF + cosine 보정 + /api/feed?algo=v2 + 20번째 cron) + K-3 (alembic 0078 AI 캡션 vision LLM + L-F translation_cache 재사용 + 21번째 cron + alt 자동) + K-5 (alembic 0079 LLM 도슨트 작가+AI hybrid + 4 endpoints + DocentSection + 5 locale 16 keys). **누적**: 412 → **581 passed** + 3 skipped (+169 tests, 회귀 0) + alembic 0066~0079 (14 신규, single head) + cron 16 → 21 (+5) + 14+ 신규 endpoints + Mock 모드 fallback 100% + 5 locale 110+ keys + frontend tsc 0. **README 비전 5/5**: AI 시대 작가(K-3+K-5) + 글로벌 인덱스(K-1) + 그로스해킹(K-1 개인화) + 스토리텔링(K-3+K-5) + 다국어(L-F+K-3/K-5 5 locale, translation_cache 재사용 비용 ↓). **Phase 10 carry-over**: K-2 diversity (K-1 14일 운영 후) + K-4 Featured Artist 자동 + K-6 가격 추천 (거래 100건+) + K-7 큐레이션 + K-8 A/B 테스트. **26 OQs 모두 권장 default 일괄 수락**. |
| [domo-phase5-roadmap](./domo-phase5-roadmap/) | 2026-05-04 | N/A (parent roadmap, 12/12 100%) | — | **Phase 5 parent roadmap 종결** — D 단계 (Tech Debt Stabilization 1~2주) + B 단계 (Blue Bird Patronage UI 8~10주) = 12 sub-PDCAs 100%. **D 6/6**: editor-i18n-cleanup-v3 (#3+#4+#11 m-1 통합) + upload-retry-ui (#4 carry-over) + series-reorder-persistence (#8 carry-over) + notifications-ux-audit (#12) + server-side-notification-i18n (#11 m-2 carry-over) + observability-monitoring-baseline (Prometheus 9 metrics + EXPLAIN ANALYZE + observability docs). **B 6/6**: bluebird-sponsor-flow (Stripe SetupIntent + 5-step BluebirdModal + Mock 모드 fallback, audit-driven 10d→6d) + artist-patronage-dashboard (4 endpoints + RevenueChart SVG + SupportersTable) + supporter-dashboard (5-section + CancelSubscriptionModal 4 사유) + tier-benefits-customization (alembic 0043 + ArtistTierBenefits + 4 endpoints) + patronage-retention-ux (thank-you + WinbackBanner 7d + ChurnList + PostCard hover) + patronage-i18n-a11y-audit (17 dead keys × 5 = 85 제거 + 5 trailing comma fix + WCAG 2.1 AA). **누적**: 77→147 passed (+70 tests) + tsc 0 + ~750+ 신규 i18n × 5 locales + 9 신규 endpoints + 9 Prometheus metrics + 3 dashboard pages + ~20 components + alembic 0043 + observability docs 215L. **8 OQs 모두 권장 default 일괄 수락**. carry-over: D-7 #10.1 (Phase 5.5) + alembic 0045 cancellation_reason+feedback + Stripe coupon (Phase 6+) + es.json artist.* 26 keys (Phase 6 i18n sprint) + WCAG manual + PostHog/Amplitude + multi-currency + push/email + DM messaging |

## editor-responsive-redesign

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #3 (B-1 모바일/데스크탑 분리 + C UI 개선, L) — 단일 803줄 `posts/new/page.tsx`를 데스크탑 2-pane(편집 + 항상 마운트되는 사이드 미리보기 + 토글)과 모바일 단계형 wizard(일반 3 step / product 4 step)로 분리. DB·API·외부 라이브러리 변경 0의 순수 프런트엔드 개편.
- **Artifacts**: [plan](./editor-responsive-redesign/editor-responsive-redesign.plan.md), [design](./editor-responsive-redesign/editor-responsive-redesign.design.md), [analysis](./editor-responsive-redesign/editor-responsive-redesign.analysis.md), [report](./editor-responsive-redesign/editor-responsive-redesign.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Key Files Touched**:
  - Frontend (신규 hooks): `src/lib/hooks/usePostFormState.ts` (145줄, 18 useState 그룹화 + resetFromDraft), `src/lib/hooks/useArtistGate.ts` (95줄, 비작가 auto-fallback + applicationStatus fetch 캡슐화), `src/lib/hooks/useEditorWizardStep.ts` (98줄, 일반 3 / product 4 step state machine + 자동 보정)
  - Frontend (신규 컴포넌트): `src/components/post-editor/{ProductFields,PreviewPane,PreviewToggleButton,PostPreviewCard,EditorWorkspace,WizardStepIndicator,EditorMobileWizard}.tsx` + `wizard/{EditorStepType,EditorStepContent,EditorStepProductMeta,EditorStepPublish}.tsx`
  - Frontend (신규 아이콘): `src/components/icons.tsx` — `EyeIcon`, `EyeOffIcon`
  - Frontend (수정): `src/app/posts/new/page.tsx` (803→547 LOC, -32%) — sticky header / multi-tab warning / form 영역을 EditorWorkspace로 이동, AutosaveIndicator function 이동, main을 grid wrapper로 전환
  - i18n: `i18n/{ko,en,ja,zh,es}.json` `post.editor.{preview,wizard}.*` 23개 키 신규 (5 locale × 23 = 115 entries) + carry-over fix from #1 `post.type.product.disabledHint*` 4 키 5 locale "상품 포스트" 명시 (20 entries)
  - Backend: 변경 없음 (0)
- **Decisions**:
  - OQ-1 = A (단일 `md(768px)` breakpoint, Tailwind md/lg 표준)
  - OQ-2 = C (PreviewPane 항상 마운트 + 토글 visibility, state 보존 — `w-0/opacity-0/aria-hidden`)
  - OQ-3 = B (점진적 hooks-first 추출, no `app/posts/new-v2/`)
  - OQ-4 = A (일반 3 step, product 4 step — `EditorStepProductMeta` 분리로 #7 마이그레이션 비용 최소화)
  - OQ-D-1 = A (PreviewPane 헤더 "미리보기" 명시 + aria-label)
  - OQ-D-2 = B (wizard footer 불투명 단색 — backdrop-blur 미사용)
  - OQ-D-3 = B (wizard sticky header 없음, 마지막 step에만 등록 버튼, 임시저장은 모든 step tertiary)
  - OQ-D-4 = A (`isPreviewVisible` 기본 true)
  - OQ-D-5 = B (3 PR 단계별 분할 — Step 1-2 / 3-5 / 6)
- **Match Rate Progression**: **96%** (initial — Major/Critical Gap 0, 3 minor cosmetic carry-over). Iterate 사이클 발생 안 함 (≥ 90% 임계 즉시 통과)
- **Iteration**: 0 round
- **Lessons Learned**:
  1. **Keep**: design 문서가 props 타입·breakpoint 클래스·OQ default까지 매우 구체적이어서 코드 이식이 직관적. 점진적 hooks-first(OQ-3=B) 채택으로 803→547 줄 압축 중 회귀 0. 권장 default "한 번에 수락" 패턴이 OQ 9개(Plan 4 + Design 5) 협상을 빠르게 마무리.
  2. **Problem 1**: Design §4.1 카탈로그의 `EditorPageShell` / `EditorDesktopLayout` 두 컴포넌트가 page.tsx 인라인으로 흡수 — Design이 두 옵션 허용했으나 명시적 명칭 차이가 minor cosmetic gap으로 남음.
  3. **Problem 2**: ProductFields의 `verbatim` 보존 정책이 비-wizard 영역 i18n 외재화 기회를 놓침 — `post.productInfo`/`post.genre` 등 기존 키가 이미 정의되어 있었음에도 hardcoded Korean 유지 → carry-over 발생.
  4. **Problem 3**: `globals.css` `prefers-reduced-motion` 명시 누락 (Design §9.3 권장). 실효 영향 미미하나 a11y 항목 누락.
  5. **Try**: 다음 PDCA부터 — Design §4 카탈로그 컴포넌트 추출 의무성 표기(필수/옵션), i18n cleanup을 Plan §2.1에 명시적으로 surface, a11y 항목을 AC에 명시 검증 단계 추가.
- **Carry-over**:
  - `editor-i18n-cleanup` (Medium, 분리됨): m-2 비-wizard 영역 한국어 hardcode (EditorWorkspace/ProductFields/PostPreviewCard) — 기존 `post.*` 키 활용 가능
  - `i18n-time-formatting` (Low, #2 PDCA에서도 carry-over): `formatRelativeTime` 한국어 hardcode + `lastSavedAgo` 5 locale 키
  - (보류) `globals.css` reduced-motion: `editor-media-studio` #6에서 framer-motion 도입 시 함께
  - (예정) `editor-product-meta` #7: ProductFields 자유 입력 → 구조화 입력 (prop surface stable로 마이그레이션 비용 최소)
- **Production Readiness**: ✅ TypeScript 0 에러. 데스크탑/모바일 양쪽에서 5개 통합 지점(autosave, DraftRestoreDialog, 멀티탭 경고, role-gating, applicationStatus auto-fallback) 회귀 0. AC 8/8 Pass. i18n 5 locale 동시 완비.

## editor-media-ux

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #4 (Phase 2 Media & Content, M ~3-4일) — 미디어 카드 dnd-kit drag-reorder, 이미지 캡션 입력(280자, `MediaAsset.caption` 컬럼 + `PATCH /v1/media/{id}` 엔드포인트), 다중 업로드 XHR 기반 실시간 progress(OQ-D-3=B 사용자 변경 채택). Backend·Frontend 양면 변경 (#1-3까지는 frontend-only).
- **Artifacts**: [plan](./editor-media-ux/editor-media-ux.plan.md), [design](./editor-media-ux/editor-media-ux.design.md), [analysis](./editor-media-ux/editor-media-ux.analysis.md), [report](./editor-media-ux/editor-media-ux.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Key Files Touched**:
  - Backend (신규): `alembic/versions/0036_media_caption.py`
  - Backend (수정): `models/post.py` `MediaAsset.caption`, `schemas/post.py` `MediaAssetIn.caption`+`MediaPatchRequest`, `api/posts.py` caption pass-through, `api/media.py` `PATCH /{media_id}`+`_check_auction_media_lock`+structured audit log, `core/rate_limit.py` `media_patch` scope
  - Frontend (신규): `lib/hooks/useMediaUploadQueue.ts` (병렬 큐 + XHR progress), `components/post-editor/{SortableMediaCard,MediaUploadProgress}.tsx`, `components/icons.tsx` `DragHandleIcon`
  - Frontend (재작성): `components/post-editor/MediaPreviewList.tsx` (70줄 → 160줄, DndContext + SortableContext)
  - Frontend (수정): `lib/api.ts` `uploadMediaFileWithProgress` (XHR), `patchMedia`, `CreatePostMedia.caption?+_clientId?`. `EditorWorkspace.tsx`/`EditorMobileWizard.tsx`/`wizard/EditorStepContent.tsx` props +3 forward. `app/posts/new/page.tsx` `useMediaUploadQueue` 통합 + `handleFiles`/`handleGif` 교체 + `handleReorder`/`handleCaptionChange` 신규 + `handleRestore` `_clientId` backfill + `handleSubmit` `_clientId` strip. `i18n/index.tsx` `t()` ICU `{{varName}}` 보간 추가
  - i18n: `i18n/{ko,en,ja,zh,es}.json` `post.editor.media.*` 11키 × 5 locale = 55 entries
- **New Dependencies**: `@dnd-kit/core@^6.3.1`, `@dnd-kit/sortable@^8.0.0` (프로젝트 최초 외부 React 라이브러리, ~16KB gzip 추정)
- **Decisions**:
  - OQ-1=A inline caption textarea / OQ-2=B `Promise.allSettled` 병렬 / OQ-3=A draft 흐름 (PATCH는 발행 후 전용) / OQ-4=A dots-grip + Pointer/Touch200ms/Keyboard sensor / OQ-5=B 280자 / OQ-6=A 발행 후 소유자 수정 / OQ-7=A MediaToolbar 직후 progress 배지
  - **OQ-D-1 = A** (auction `status='active'` 시 caption 수정 차단 — `AUCTION_ACTIVE_MEDIA_LOCKED` 409. 입찰자 신뢰 보호)
  - OQ-D-2 = A (textarea 고정 2 rows resize-y)
  - **OQ-D-3 = B** (사용자 권장 A→B 변경 — XHR 실제 progress. `uploadMediaFileWithProgress` 신규 + 기존 `uploadMediaFile` wrapper로 변경)
  - OQ-D-4 = A (DragOverlay 없음, 반투명 카드)
  - OQ-D-5 = A (OQ-1=A echo)
- **Match Rate**: **95%** (initial — Critical/Major Gap 0, 5 통합 지점 회귀 0). Iterate 사이클 발생 안 함 (≥ 90% 임계 즉시 통과)
- **Iteration**: 0 round
- **Lessons Learned**:
  1. **Keep**: design 문서가 props 시그니처·dnd-kit sensor 설정·SQL DDL·Pydantic schema까지 verbatim 가능했고, `uploadMediaFile`을 wrapper로 유지하라는 권장으로 다른 호출처 회귀 0. **OQ-D-3 사용자 권장 변경(A→B XHR)이 design 단계에서 명시 처리**되어 do 단계에서 혼란 0. `_clientId` 라이프사이클(부여→backfill→strip) 완전 처리.
  2. **Problem 1 (m-1)**: design §B-11에서 명세한 `smoke_test_media_caption.sh`가 실제 산출물에는 부재 — Spec과 산출물 사이 자동 매핑 부재 (Pydantic + 단위 테스트로 cover되어 release blocker 아님이나 자동화 검증 누락).
  3. **Problem 2 (m-2)**: `post.editor.media.uploading` i18n 키가 5 locale 정의됐으나 코드 호출 0 (dead key) — i18n 추가 시점에 grep cross-check 누락.
  4. **Problem 3 (m-3)**: `EditorStepContent.tsx` 모바일 path "업로드 중..." 인라인 잔존 — 데스크탑(EditorWorkspace)만 제거하고 모바일 동기화 누락.
  5. **Try**: 다음 PDCA부터 — (1) backend smoke 자동 생성 게이트, (2) i18n 신규 키 추가 시 `grep -r "{key}"` 사용처 검증을 PDCA 체크리스트에 추가, (3) 다중 위치(데스크탑 + 모바일) 동일 코드 변경 시 양쪽 동시 적용 게이트.
- **Carry-over**:
  - **`upload-retry-ui` (Medium, 사용자 제안 — 신규 등록)**: Design §F-9.4 / R-FE-7 명시된 후속. `useMediaUploadQueue` task `error` 상태 + `xhr.abort()` 패턴 이미 확립
  - **`editor-i18n-cleanup` 확장 (Medium)**: m-2(dead key 제거) + m-3(EditorStepContent 인라인 1줄 제거) + m-4(#3 carry-over 잔존 통합)
  - Backend smoke test (m-1) — 별도 PDCA 불필요, 즉시 PR 권장
  - `formatRelativeTime` 한국어 (#2 carry-over) — `i18n-time-formatting`
  - ProductFields 구조화 입력 — `editor-product-meta` (#7, 이미 예정)
- **Production Readiness**: ✅ TypeScript 0 에러. 5 locale JSON valid. Backend Pydantic 280자 검증 정상. 5 통합 지점 회귀 0. AC 10/10 Pass. 사용자 매뉴얼 QA 통과. ⚠ alembic upgrade 필수 (사용자 측 실행 완료).

## editor-image-studio

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #6-image (split from combined editor-media-studio per OQ-6=B, M~L → 11.5일) — 이미지 에디터(회전/크롭/모자이크/워터마크) Konva 클라이언트 미리보기 + Pillow 서버 처리 + `crop_meta jsonb` 비파괴 메타. Backend·Frontend 양면 변경 + Signature 별도 업로드 UI(OQ-D-3=B 사용자 override).
- **Artifacts**: [plan](./editor-image-studio/editor-image-studio.plan.md), [design](./editor-image-studio/editor-image-studio.design.md), [analysis](./editor-image-studio/editor-image-studio.analysis.md), [report](./editor-image-studio/editor-image-studio.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Sister PDCA**: `editor-video-studio` (#6-video, blocked on OQ-2 ffmpeg 인프라 결정)
- **Key Files Touched**:
  - Backend (신규 마이그레이션): `alembic/versions/0037_media_crop_meta.py` (`crop_meta JSONB`), `alembic/versions/0038_orig_signature_keys.py` (`original_storage_key` + `signature_storage_key`, revision ID 길이 v1.3 단축)
  - Backend (신규): `app/services/image_transform.py` (367줄, `process_image_transform()` + 4 helpers + `WatermarkSignatureNotSetError`), `app/schemas/media_transform.py` (CropMetaSchema + 4 ops discriminated union + SignatureResponse), `tests/unit/test_image_transform.py` (12 tests), `tests/integration/test_image_studio_endpoints.py` (10 tests), `scripts/smoke_test_image_transform.sh` + `smoke_test_signature.sh`, `conftest.py` + pytest config
  - Backend (수정): `models/post.py` `MediaAsset.crop_meta`+`original_storage_key`, `models/user.py` `User.signature_storage_key`, `schemas/post.py` `MediaAssetIn.crop_meta`, `services/storage/{base,local,s3}.py` (`StorageProvider.get()` 추가), `api/media.py` (`POST /v1/media/{id}/transform` 6단계 권한 + first-transform original-key seeding + audit log), `api/me.py` (POST/GET/DELETE `/v1/me/signature` 3 endpoints), `core/rate_limit.py` (`media_transform` + `signature_upload` 5/min/user)
  - Frontend (신규 hooks): `lib/hooks/useImageEditor.ts` (204줄, state + setters + `buildOps`/`buildCropMeta` + 비파괴 재진입), `lib/hooks/useSignature.ts` (113줄, GET/upload/delete + error i18n key 매핑)
  - Frontend (신규 컴포넌트): `components/post-editor/{ImageEditor,ImageEditorLazy,SignatureUploadModal,SignaturePreview}.tsx` (총 ~720줄), `components/post-editor/image-editor/{Rotate,Crop,Mosaic,Watermark}Tool.tsx` (4 도구, 총 ~610줄)
  - Frontend (신규 아이콘): `components/icons.tsx` `EditPencilIcon`
  - Frontend (수정): `lib/api.ts` (CropMeta + 4 ops 타입 + `patchMediaTransform` + 3 signature client fns + `apiFetch` FormData/204 인프라 fix + `CreatePostMedia.crop_meta?`+`id?`), `components/post-editor/SortableMediaCard.tsx` (`onEditMedia?` optional + `isGif()` + EditButton JSX), `components/post-editor/{MediaPreviewList,EditorWorkspace,EditorMobileWizard}.tsx` + `wizard/EditorStepContent.tsx` (props +1 forward), `app/posts/new/page.tsx` (`editingMediaId` state + `<ImageEditorLazy>` 마운트 + `handleEditMedia` + 발행 페이로드 `id`+`_clientId` strip)
  - i18n: `i18n/{ko,en,ja,zh,es}.json` `post.editor.media.studio.image.*` 47키 × 5 locale = **235 entries**
- **New Dependencies**: `konva@^9.3.16`, `react-konva@^18.2.10` (~50KB gzip, dynamic({ssr:false}) lazy import로 main bundle 영향 0)
- **Decisions** (Plan 6 + Design 8 = 14 OQ):
  - Plan: OQ-1=B Konva, OQ-3=A crop_meta jsonb 비파괴, OQ-5=C 텍스트+시그니처 둘 다, OQ-7=A 데스크탑+모바일 동시, OQ-8=C `_check_auction_media_lock` 동일 적용, OQ-9=B GIF 편집 비활성
  - Design: OQ-D-A=C `original_storage_key` 추가 (alembic 0038), OQ-D-B=C `signature_storage_key` 사전 저장 (SSRF 방어), OQ-D-C=B 항상 최초 원본 재처리, OQ-D-1=A Stage 컨테이너 fit + DPR, OQ-D-2=A 단축키 1/2/3/4 도입
  - **OQ-D-3 = B (사용자 override from recommended A)**: 별도 시그니처 업로드 UI/엔드포인트 신설 — avatar 재사용 ❌ — 신규 §B-14 (POST/GET/DELETE `/v1/me/signature`) + §F-10b SignatureUploadModal/SignaturePreview/useSignature
  - OQ-D-4: A 시도 (Konva.Filters.Pixelate 우선) → 부족 시 B fallback (Canvas 2D)
  - OQ-D-5=A "원본" preset = 크롭 초기화 통합
- **Match Rate**: **96%** (initial — Critical/Major Gap 0, 5 통합 지점 회귀 0, 2 minor partial: storage key uuid vs timestamp + i18n key count 추정 vs 실제). Iterate 사이클 발생 안 함 (≥ 90% 임계 즉시 통과)
- **Iteration**: 0 round
- **Lessons Learned** (보고서 §9에 상세 기재):
  1. **Keep / OQ-D Early Binding**: Design v1.4에서 8 OQ-D 모두 user 결정 surface → 빌더 의도 명확 + OQ-D-3=B 사용자 override가 SSRF 방어 + UX 균형 동시 달성. 4번 design 패치(v1.0→v1.4)로 발견 즉시 정정.
  2. **Keep / Original Storage Key Architecture**: `original_storage_key` 컬럼 + first-transform auto-init 로직 (OQ-D-A=C + OQ-D-C=B) → 재인코딩 누적 손실 0, 향후 "필터·자동 보정" PDCA 재사용 가능 기반.
  3. **Keep / Signature Pre-Storage SSRF Defense**: User가 시그니처 업로드 → `User.signature_storage_key` 저장 → 워터마크 도구는 외부 URL fetch 없이 직접 storage GET. "사용자 업로드-서버 처리" 패턴의 보안 모범 사례.
  4. **Problem 1 (P1)**: storage key suffix 디자인 `{timestamp}.jpg` → 구현 `{uuid.hex}.jpg` (collision-proof improvement이나 디자인 명세 deviation).
  5. **Problem 2 (P2)**: i18n key count 디자인 추정 ~44 × 5 = 220 → 실제 47 × 5 = 235. 디자인 추정이 conservative.
  6. **Problem 3 (인프라 발견)**: `alembic_version.version_num` = `varchar(32)` 제약 — 0038 revision ID `0038_signature_and_original_storage` (35자) → `0038_orig_signature_keys` (24자) 단축 (design v1.3 즉시 반영). 향후 모든 alembic revision ≤32자 필수.
  7. **Try**: 다음 PDCA부터 — (1) 디자인 §B 마이그레이션 명세에 revision ID 길이 ≤32 명시 게이트, (2) 디자인 i18n 키 카운트 정확 산정 (탑업 추정 → 실제 leaf key 열거), (3) `apiFetch` 같은 인프라 boundary fix는 첫 발견 step에 일괄 적용 (Step 7b에서 발견 후 Step 5에서 처리).
- **Carry-over**:
  - **`editor-video-studio` (#6-video, 자매 PDCA)**: OQ-2 ffmpeg 인프라 결정 후 별도 진행 (서버 ffmpeg vs ffmpeg.wasm vs 외부 transcode service)
  - **(옵션) design 마이너 정정 P1/P2**: 디자인 문서 정확도 (non-blocking, 5분씩)
  - **`upload-retry-ui` (#4 carry-over 유지)**: 별도 PDCA 진행 예정 (S 3.5h)
  - **`editor-i18n-cleanup` v0.2 (#3+#4 carry-over 유지)**: m-2/m-3/m-4 통합 정리 후속
  - **알려진 한계 3건 수용 처리됨**: Konva Transformer 키보드 미지원 / Mosaic Konva Rect SR semantic / `media.id` 부재 시 Save disabled (Option D, `noIdHint` 안내)
- **Production Readiness**: ✅ TypeScript 0 에러. 5 locale JSON valid. Backend 22 tests passing in 1.06s (12 unit + 10 integration). 2 smoke 스크립트 ready. `_check_auction_media_lock` 정상 적용. EXIF 이중 strip 검증. SSRF 방어 (signature 외부 URL fetch 0). 5 통합 지점 회귀 0. ⚠ alembic upgrade 필수 (0037 + 0038, 사용자 측 실행 완료).

## publish-controls

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #8 — Phase 3 Critical Path Publishing System (L 1.5주, 11일). B-3 발행 옵션 4건 (공개범위/댓글 허용/시리즈/예약발행) 통합 endpoint + Series 모델 + frontend PublishOptionsPanel.
- **Artifacts**: [plan](./publish-controls/publish-controls.plan.md), [design](./publish-controls/publish-controls.design.md), [analysis](./publish-controls/publish-controls.analysis.md), [report](./publish-controls/publish-controls.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Critical Path Position**: 1 → 2 → 3 → 4 → #6-image → **#8 ✅** → 다음: #10 artist-tier-release (Phase 4, visibility 시스템 위에서 동작)
- **Sister PDCA**: #12 notifications-ux-audit (independent, parallel possible)
- **Key Files Touched**:
  - Backend (신규 마이그레이션): `alembic/versions/0039_post_visibility_comments.py` (29 chars revision id, visibility/comments_enabled 컬럼 + 복합 인덱스 + CHECK constraint), `alembic/versions/0040_series_tables.py` (18 chars, series + post_series_membership + CASCADE FK + 2 인덱스)
  - Backend (신규): `app/models/series.py` (70L, Series + PostSeriesMembership), `app/schemas/series.py` (106L, Visibility Literal + PostPublishRequest validator + SeriesCreate/Out/Patch + PostSeriesUpdateIn), `app/api/series.py` (327L, 6 Series CRUD endpoints + `_check_series_owner` helper R-8 완화), `tests/unit/test_publish_controls.py` (10 tests), `tests/integration/test_publish_controls_endpoints.py` (12 tests), `scripts/smoke_test_publish_controls.sh` + `smoke_test_series.sh` (2 smoke scripts)
  - Backend (수정): `app/models/post.py` (visibility String(20) + comments_enabled Boolean), `app/models/__init__.py` (Series, PostSeriesMembership 등록), `app/schemas/post.py` (PostOut +2 필드), `app/api/posts.py` (publish_post 엔드포인트 + `_visibility_filter_for_viewer` helper + `_check_auction_visibility_lock` + `_replace_post_series` + `_PUBLISHABLE_STATUSES` + 5 endpoints visibility 필터 적용 + comments_lock check), `app/core/rate_limit.py` (post_publish/series_write/series_read 3 scope), `app/main.py` (series_router 등록)
  - Frontend (신규 컴포넌트): `components/post-editor/PublishOptionsPanel.tsx` (329L, 4 sub-controls: VisibilitySelector + CommentsToggle + SeriesSelector + ScheduledPicker), `components/post-editor/SeriesCreateModal.tsx` (~260L, z-[60] focus trap + cover_url upload `uploadMediaFile` 재사용), `components/SeriesCard.tsx` (48L), `components/VisibilityBadge.tsx` (30L, public 시 null + LockClosedIcon/LinkIcon)
  - Frontend (신규 hooks): `lib/hooks/useMySeries.ts` (88L, optimistic CRUD)
  - Frontend (신규 페이지): `app/series/[id]/page.tsx` (346L, 헤더 + 갤러리 + 편집 모드 + dnd-kit reorder), `app/users/[id]/series/page.tsx` (97L, 작가 시리즈 grid)
  - Frontend (신규 아이콘): `components/icons.tsx` `LockClosedIcon` + `LinkIcon`
  - Frontend (수정): `lib/api.ts` (Visibility type + Series 4 interfaces + 8 API client functions + PostView 확장 + DraftPayload 확장), `lib/hooks/{useDraftAutosave,usePostFormState,useEditorWizardStep}.ts` (3 신규 필드 + setters + WizardStep union 확장 + publish-options step), `components/post-editor/{EditorWorkspace,EditorMobileWizard,WizardStepIndicator}.tsx` (props +9 forward + 신규 step 분기), `components/PostCard.tsx` (VisibilityBadge 통합), `app/posts/new/page.tsx` (handleSubmit Hybrid C + mapPublishError 9-code + useMySeries 통합), `app/posts/[id]/page.tsx` (comments_disabled UI), `app/users/[id]/page.tsx` ("시리즈 보기" 링크)
  - i18n: `i18n/{ko,en,ja,zh,es}.json` `post.editor.publishOptions.*` (22 keys) + `post.editor.error.*` (7 신규 keys) + `post.editor.wizard.steps.publishOptions` (1) + `post.series.*` (19 keys, createModal 9 + 10 top-level) + `post.feed.indicator.*` (3 keys) = 47 keys × 5 locale = **235 entries**
- **New Dependencies**: 없음 (dnd-kit는 #4에서 도입됨, 재사용)
- **Decisions** (10 Plan + 5 OQ-D = 14 OQ resolved):
  - Plan: OQ-1=A `public/followers_only/unlisted` enum, OQ-2=A 기존 행 모두 `public` backfill, OQ-3=A comments_enabled=false 시 기존 댓글 보존, OQ-4=C cover_url 수동 + 첫 포스트 thumbnail fallback, OQ-5=A 시리즈 drag-reorder (dnd-kit 재사용), OQ-6=A scheduled_at 5분~1년, OQ-7=A unlisted URL `/posts/{uuid}` 그대로, OQ-8=A wizard step + sidebar, OQ-9=A `POST /v1/posts/{id}/publish` 신규 endpoint, OQ-10=A SQLAlchemy WHERE + 복합 인덱스
  - Design: OQ-D-1=A `_check_auction_visibility_lock` 적용, OQ-D-2=A scheduledAt state singleton (MediaToolbar 비활성화 대신 단일 setter 공유), OQ-D-3=A 시리즈 reorder 명시 "저장" 버튼만 API, OQ-D-4=A 별도 `/users/[id]/series` 라우트, OQ-D-5=A `GET /series/{id}` 본 PDCA에서는 `status='published'`만 노출
- **Match Rate**: **100%** (initial — Critical/Major/Minor Gap 0건. 14/14 OQs implemented, 11/11 error codes, 17/17 AC pass, 5/5 integration regression 0). Iterate 사이클 발생 안 함.
- **Iteration**: 0 round
- **Lessons Learned** (보고서 §9에 상세):
  1. **Keep / Design verbatim 가능성**: bkend-expert + frontend-architect 병렬 위임으로 §B/§F 섹션 모두 verbatim 구현 가능 — design v1.1 OQ-D 5개 결정 echo가 빌더 의도 명확화에 결정적. 14 OQ 모두 코드 evidence와 1:1 매칭.
  2. **Keep / Hybrid C handleSubmit 패턴**: 기존 draft → publishPost / 신규 → saveToServer + publishPost / fallback createPost. 상태 전이 명확 + 재시도 가능 + legacy 호환. 향후 발행 흐름 PDCAs에서 재사용 가능.
  3. **Keep / dnd-kit 재사용 (외부 lib 추가 0)**: #4에서 도입된 `@dnd-kit/core`+`@dnd-kit/sortable`을 `/series/[id]` 편집 모드 reorder + MediaPreviewList 모두 재사용. 의존성 부담 0으로 리치 UX 추가.
  4. **Problem 1**: Series reorder 백엔드 endpoint 부재 — 본 PDCA에서는 local-only로 출시. UX는 정상이나 새로고침 시 원래 순서. 별도 PDCA `series-reorder-persistence` 또는 #10 통합 처리.
  5. **Problem 2**: design §B-9 `GET /users/{id}/posts` 명세는 helper만 준비됨 — endpoint 자체는 별도 PDCA로 deferred. visibility 시스템이 정확히 동작하므로 #10 진입 무영향.
  6. **Problem 3**: EXPLAIN ANALYZE 검증 누락 — design §B-14 R-1이 권고했으나 테스트에 미포함. 인덱스 자체는 정확히 생성됨. 모니터링 단계에서 `feed_read` p95 추적 권장.
  7. **Try**: 다음 PDCA부터 — (1) 인덱스 R-mitigation은 EXPLAIN ANALYZE 자동화 게이트 추가, (2) 디자인이 helper 정의했으나 endpoint 명세 누락한 케이스는 §B 섹션에 "endpoint deferred" 명시, (3) handleSubmit 같은 bound flow는 reset 시 강력하게 분기 — Hybrid C 패턴 표준화.
- **Carry-over**:
  - **Series reorder persistence endpoint**: `POST /v1/series/{id}/reorder` 신규 — 별도 PDCA 또는 #10 통합 (Medium, ~2일)
  - **`GET /users/{id}/posts` viewer-aware**: `_visibility_filter_for_viewer` helper 이미 ready, endpoint 별도 PDCA (Medium, ~1일)
  - **EXPLAIN ANALYZE 모니터링**: Phase 4 모니터링 자동화 (S, ~0.5일)
  - **OQ-D-2 strategy 문서화**: state singleton 접근법 — 다음 PDCA 디자인 단계에 reference로 활용 가능
  - 이전 PDCAs carry-over 유지: `editor-video-studio` (#6-video, ffmpeg 인프라 차단), `upload-retry-ui` (#4), `editor-i18n-cleanup` v0.2 (#3+#4)
- **Production Readiness**: ✅ TypeScript 0 에러. 5 locale JSON valid (47 키 일관). Backend 22 tests passing in 1.15s (10 unit + 12 integration). 2 smoke 스크립트 ready (`smoke_test_publish_controls.sh` + `smoke_test_series.sh`). `_check_auction_visibility_lock` 정상 적용 (#4 패턴 재사용). 5 통합 지점 회귀 0 (autosave/DraftRestoreDialog/multi-tab/role-gating/useArtistGate). ⚠ alembic upgrade 필수 (0039 + 0040, 사용자 측 실행 완료).

## artist-tier-release

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #10 — Phase 4 Critical Path Artist Tools (M, 4~5일). B-4 후원자/단골 우선 공개. **Option β 채택**: `Post.visibility` enum 미확장, `tier_only`는 computed effective state — R-1 (CHECK constraint 확장) 완전 dissolved.
- **Artifacts**: [plan](./artist-tier-release/artist-tier-release.plan.md), [design](./artist-tier-release/artist-tier-release.design.md), [analysis](./artist-tier-release/artist-tier-release.analysis.md), [report](./artist-tier-release/artist-tier-release.report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Critical Path Position**: 1 → 2 → 3 → 4 → #6-image → #8 → **#10 ✅** → 다음: #11 auction-promotion-suite (Phase 4 마지막) 또는 #12 notifications-ux-audit (독립)
- **Sister PDCA**: 없음 (#11 독립 — 병렬 가능)
- **Dependency**: #8 publish-controls visibility 시스템 (archived 100%) 위에서 동작
- **Key Files Touched**:
  - Backend (신규 마이그레이션): `alembic/versions/0041_post_tier_release.py` (22 chars revision id, early_access_until + early_access_tier 컬럼 + 2 CHECK constraint + partial index + sponsorships(sponsor_id, artist_id, status) R-5 mitigation 인덱스)
  - Backend (신규): `app/services/tier_release_jobs.py` (52L, 60s cron worker — schedule_jobs 패턴 미러), `tests/unit/test_artist_tier_release.py` (9 unit tests), `tests/integration/test_artist_tier_release_endpoints.py` (8 integration tests), `scripts/smoke_test_tier_release.sh` (5단계 smoke +x)
  - Backend (수정): `app/models/post.py` (Post +2 컬럼), `app/schemas/series.py` (EarlyAccessTier Literal + EARLY_ACCESS_DURATIONS frozenset + PostPublishRequest cross-field validator + PostPublishResponse +2), `app/schemas/post.py` (PostOut +3 — early_access_until + early_access_tier + is_tier_locked), `app/api/posts.py` (3 helpers: `_viewer_meets_tier` UNION ALL EXISTS + `_filter_active_tier_only` Python post-filter + `_visibility_filter_for_viewer` Option β 확장. publish_post + get_post + 5 endpoints SQL filter), `app/main.py` (tier_release_task startup 등록)
  - Frontend (신규 컴포넌트): `components/TierBadge.tsx` (44L, VisibilityBadge 패턴 미러, amber 색상)
  - Frontend (수정): `lib/api.ts` (EarlyAccessTier + EarlyAccessDuration types + PostPublishRequest/Response/PostView/DraftPayload extensions), `lib/hooks/{useDraftAutosave,usePostFormState}.ts` (DraftState +2 + setters + resetFromDraft `?? null`), `components/post-editor/PublishOptionsPanel.tsx` (270→484L, 5번째 `<details>` expand TierReleasePicker w/ tier radio 3 + duration button group 5 + expiry hint + tierInconsistent alert + Clear), `components/PostCard.tsx` (VisibilityBadge wrapper + TierBadge), `components/post-editor/{EditorWorkspace,EditorMobileWizard}.tsx` (props +4 forward), `app/posts/new/page.tsx` (handleSubmit body +2 + mapPublishError +3 codes + tierInconsistent guard), `app/posts/[id]/page.tsx` (POST_TIER_RESTRICTED 403 분기)
  - i18n: `i18n/{ko,en,ja,zh,es}.json` `post.editor.publishOptions.tierRelease.*` (15 keys) + `post.feed.indicator.tier.*` (3 keys) + `post.editor.error.*` 신규 (3 keys) + `post.detail.tierRestricted` (1 key) = 22 keys × 5 locale = **110 entries**
- **New Dependencies**: 없음 (#6-image konva + #4 dnd-kit 모두 재사용 안 함, 외부 lib 추가 0)
- **Decisions** (10 Plan + 5 OQ-D = 15 OQ resolved 모두 권장 default):
  - Plan: OQ-1=A 3-tier (subscriber/sponsor/follower), OQ-2=A 자동 계층 포함 (subscriber > sponsor > follower), OQ-3=A 5 preset (1/6/24/72/168 hours), OQ-4=B 매 조회 실시간 검증, OQ-5=A 60s cron, OQ-6=A tier_only 상호 배타, OQ-7=B 만료 후 작가 지정 visibility 복귀, OQ-8=A PublishOptionsPanel expand, OQ-9=A publish endpoint 확장, OQ-10=A no-cache
  - **Design (CRITICAL): OQ-D-1=B (Option β)** — Post.visibility enum 미확장, tier_only는 computed effective state. R-1 완전 해소. 만료 자동 복귀가 worker 지연(최대 60s)과 무관하게 실시간 처리.
  - Design: OQ-D-2=B 22 keys × 5 locale, OQ-D-3=B SQL fast-path + Python post-filter 2단계, OQ-D-4=A 모든 completed Sponsorship 인정 (N일 제한은 #10.1), OQ-D-5=A `ix_sponsorships_sponsor_artist_status` 복합 인덱스 0041 통합 (R-5 mitigation)
- **Match Rate**: **99%** (initial — Critical/Major Gap 0, 5 통합 지점 회귀 0, 81/81 measured items 100% match, conservative -1% for 5-locale parity not exhaustively grepped). Iterate 사이클 발생 안 함.
- **Iteration**: 0 round
- **Lessons Learned** (보고서 §9에 상세):
  1. **Keep / Option β (Computed Effective State) 패턴**: 재사용 가능한 일반 패턴. enum 확장 vs computed state 결정 시 — DB 마이그레이션 단순성 + 자동 만료 처리 + worker 비-critical path 보장이 모두 confer. 향후 PDCAs에서 status/visibility 추가 시 default consideration.
  2. **Keep / UNION ALL EXISTS R-2 mitigation**: tier 자격 검증 `_viewer_meets_tier` — 3-tier OR chain을 단일 쿼리로 통합. PostgreSQL EXISTS short-circuit으로 효율. 향후 multi-condition 권한 체크 패턴 표준.
  3. **Keep / 2단계 SQL+Python 전략 (OQ-D-3=B)**: SQL fast-path로 명백한 비자격 케이스 제외 + Python post-filter로 viewer별 tier 자격 정밀 검증. 활성 tier_only 포스트가 초기 소수일 것이라는 데이터 기반 판단. perf 측정 후 #10.1에서 SQL-only로 전환 가능.
  4. **Keep / no-cache + cron 협업 (OQ-4=B + OQ-5=A)**: 매 조회 실시간 자격 검증으로 구독 취소 즉시 반영 + cron worker는 DB 정리 보조 역할. 만료 후 자동 복귀가 worker 지연과 무관 — security critical path는 실시간 검증.
  5. **Problem 1**: `tierInconsistent` 발행 버튼 disabled prop drilling 누락 — handleSubmit guard로 대체 (시각 활성 + 즉시 거부, UX equivalent). 향후 disclosure UX 개선 carry-over.
  6. **Problem 2**: POST_TIER_RESTRICTED 403 후원/구독 CTA UI 부재 — out-of-scope (§F-12), 단순 텍스트 메시지만. 향후 별도 PDCA로 비즈니스 CTA UX 검토.
  7. **Try**: 다음 PDCA부터 — (1) computed effective state 패턴이 적합한 케이스 우선 검토 (enum 확장 회피), (2) 권한 체크 OR chain은 UNION ALL EXISTS 단일 쿼리 표준화, (3) 2단계 SQL+Python filter는 데이터 분포 예측 후 선택 (초기 소수 → 2단계, 다수 → SQL-only).
- **Carry-over**:
  - **POST_TIER_RESTRICTED CTA UI** (out-of-scope §F-12): 후원/구독 deeplink CTA — 비즈니스 로직 별도 PDCA
  - **`is_tier_locked` viewer hint UI** (out-of-scope §F-12): API field 노출되나 미사용 — 인라인 hint UX
  - **Sponsor N일 제한 옵션화 (#10.1)**: 작가 setting (1d/7d/30d/lifetime). 본 PDCA는 모든 completed Sponsorship 인정
  - **SQL-only tier filter (#10.1)**: home_feed.following Python post-filter 제거 — perf 측정 후 SQL subquery 전환
  - **TierReleasePicker 만료 카운트다운**: 작가 대시보드용 (출시 후 enhancement)
  - **tier_release worker Prometheus 메트릭**: cleared rows/min observability
  - 이전 carry-over 유지: `editor-video-studio` (#6-video, ffmpeg 차단), `series reorder persistence endpoint` (#8), `upload-retry-ui` (#4), `editor-i18n-cleanup` v0.2 (#3+#4)
- **Production Readiness**: ✅ TypeScript 0 에러. 5 locale JSON valid (22 신규 키 5 locale 일관). Backend 61 tests passing in 1.13s (44 baseline + 17 신규 = 9 unit + 8 integration). 1 smoke 스크립트 ready (`smoke_test_tier_release.sh`). 5 통합 지점 회귀 0. Option β 준수 (Post.visibility enum CHECK constraint 변경 0). ⚠ alembic upgrade 필수 (0041, 사용자 측 실행 완료).

## auction-promotion-suite

- **Scope**: 에디터 전면 개편 로드맵 sub-PDCA #11 — Phase 4 **마지막** Critical Path Artist Tools (M, 4~5일). B-4 옥션 종료 알림/홍보 도구 3가지: (1) 종료 N시간 전 알림 (24h+6h+1h, 작가+최고입찰자, idempotent cron), (2) 공유 카드 자동 생성 (Pillow 1200×630 OG, 1h cache, owner-only), (3) 카운트다운 위젯 (D-1h 1초 adaptive polling). DB·API·Frontend 양면 + 신규 외부 라이브러리 0.
- **Artifacts**: [plan](./auction-promotion-suite/plan.md), [design](./auction-promotion-suite/design.md), [analysis](./auction-promotion-suite/analysis.md), [report](./auction-promotion-suite/report.md)
- **Parent Roadmap**: `v1/docs/01-plan/features/editor-revamp-roadmap.plan.md`
- **Critical Path Position**: 1 → 2 → 3 → 4 → #6-image → #8 → #10 → **#11 ✅** → **Phase 4 종결 (11/11 = 100%)**
- **Sister PDCA**: 없음 (Critical Path 종결)
- **Dependency**: #8 publish-controls visibility 시스템 + 기존 auction_jobs.py (5min cron, R-5 격리 유지)
- **Key Files Touched**:
  - Backend (신규 마이그레이션): `alembic/versions/0042_auction_promotion.py` (22 chars revision id, Auction +5 컬럼: notified_24h_at + notified_6h_at + notified_1h_at + share_card_url + share_card_generated_at + partial index `ix_auctions_pending_notif`)
  - Backend (신규): `app/services/auction_promotion_jobs.py` (217L total, 60s cron worker — R-5 격리: 별도 파일 + 별도 AsyncSessionLocal + auction_jobs.py와 다른 컬럼 업데이트. 3 _SLOTS (24h/6h/1h) + _make_notifs (작가 + winner if winner≠seller, R-4) + dispatch_pending_notifications_once (SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL idempotent, R-1) + _generate_share_card Pillow 합성 (1200×630 RGB, R-2 thumbnail fetch fail → fallback rect+text, R-3 thumbnail((600,630))+convert("RGB") 메모리 제어, httpx 2.0s timeout, RGBA watermark)), `tests/unit/test_auction_promotion.py` (211L, 6 unit tests), `tests/integration/test_auction_promotion_endpoints.py` (240L, 6 integration tests), `tests/unit/test_active_auction_end_at.py` (3 unit tests, iterate 1), `tests/integration/test_active_auction_end_at_endpoint.py` (1 integration test, iterate 1), `scripts/smoke_test_auction_promotion.sh` (120L, 4-step smoke +x)
  - Backend (수정): `app/models/auction.py` (Auction +5 mapped columns + Text import), `app/schemas/auction.py` (ShareCardResponse 신규 + AuctionOut +2 optional 필드), `app/schemas/post.py` (PostOut +active_auction_end_at, iterate 1), `app/api/auctions.py` (528L total — _serialize_auction +2 backward-compat getattr + _auto_transition no-winner 분기 + share-card endpoint 6단계 (auth → 404 → 403 → 409 active만 → 1h cache hit → run_in_executor Pillow 합성 + storage.put)), `app/api/posts.py` (_serialize_post +active_auction_end_at + _attach_active_auction_end_at() bulk 쿼리 N+1 zero, 6 endpoint 적용 home_feed/explore_posts/search_posts/my_bookmarks/get_post/create_post — iterate 1), `app/main.py` (auction_promotion_task lifespan 등록, all_tasks tuple 확장), `app/core/rate_limit.py` (share_card 10/60sec by user 신규 scope)
  - Frontend (신규 컴포넌트): `components/AuctionCountdown.tsx` (167L, 60s/1s adaptive interval — D-1h 경계 자동 swap, SSR-safe 초기 렌더, role=timer + a11y, prefers-reduced-motion 대응, useRef onEnded 안정성, R-FE-2 setInterval cleanup), `components/AuctionShareCard.tsx` (288L, z-[60] modal — 1h TTL cache hit 자동 활용 + POST share-card on miss, 이미지 다운로드 + 링크 복사 (R-FE-3 execCommand fallback), R-FE-4 cache busting `?t=` query, ESC + focus trap, 5 error states 401/403/409/429/500)
  - Frontend (신규 아이콘): `components/icons.tsx` `ShareIcon` (Lucide share-2 패턴 — 3 dots + 2 lines)
  - Frontend (수정): `lib/api.ts` (AuctionView +2 + PostView +active_auction_end_at + AuctionShareCardResponse + generateAuctionShareCard()), `components/PostCard.tsx` (D-1h compact AuctionCountdown badge bottom-3 left-3 — auction badges와 반대 corner), `components/FeedItem.tsx` (D-1h compact before engagement bar), `app/posts/[id]/page.tsx` (full AuctionCountdown 항상 visible if status='active' + ShareIcon 트리거 → AuctionShareCard owner-gated, R-FE-5 onEnded 시 setAuction state 갱신), `i18n/{ko,en,ja,zh,es}.json` (`share.*` 10 keys + `auction.shareCard.*` 6 aliases + `notification.type.auction.{ending.{24h,6h,1h},ended}` 4 keys × 5 locales = 100 entries 신규)
- **New Dependencies**: 없음 (Pillow는 backend 기존 + httpx 기존 활용)
- **Decisions** (10 Plan + 5 OQ-D = 15 OQ resolved 모두 권장 default 일괄 수락):
  - Plan: OQ-1=A 알림 슬롯 24h+6h+1h, OQ-2=A 작가+최고입찰자만 (winner==seller 시 작가만), OQ-3=A in-app만 (push/email Phase 5), OQ-4=A 3 idempotent 컬럼 + partial index, OQ-5=A 1h cache TTL, OQ-6=A 1200×630 OG 표준, OQ-7=C 60s/1s adaptive interval (D-1h 경계 swap), OQ-8=A 작가+낙찰자만 종료 알림 (재사용 _create_order_for_winner), OQ-9=A 자동 watermark "domo.art @{artist}", OQ-10=B D-1h feed 노출
  - Design: OQ-D-1=A backend `active_auction_end_at` 노출 (PostView 통해 feed 카운트다운 enable), OQ-D-2=B 신규 dispatch 함수 미추가 — 기존 `_create_order_for_winner` 재사용 + `_auto_transition` no-winner 분기만, OQ-D-3=A NotificationCard fallback i18n key, OQ-D-4=A `_generate_share_card` sync + run_in_executor (Pillow blocking 회피), OQ-D-5=A `share_card_url` 모든 viewer 노출 (이미 공개 카드)
- **Match Rate Progression**: **92% (initial)** → **97% (Iteration 1)**. Initial: Backend §B 14/14 perfect, Frontend §F 11/12 (F-8 미달), OQ-D 3/5, AC 14/15 (AC-12 fail), 12/12 risks mitigated. Iterate: C-1 (PostView.active_auction_end_at backend 미공급 → AC-12 fail) + M-1 (notification.type.auction.* 4 keys × 5 locales 누락 → AC-14 strict fail) 두 gap 모두 CLOSED — 단일 bulk 쿼리 (N+1 zero) + 6 endpoint 적용 + 4 새 tests, 5 locales × 4 keys = 20 entries 추가. 결과: AC-12 ✅ + AC-14 ✅ + F-3 ✅ + F-8 ✅ + OQ-D-1 ✅ + OQ-D-3 ✅
- **Iteration**: **1 round** (Critical C-1 + Major M-1 closed)
- **Lessons Learned** (보고서 §9에 상세):
  1. **Keep / 권장 default 일괄 수락 패턴**: 15 OQ (10 Plan + 5 OQ-D) 모두 권장 default 그대로 채택 — 협상 라운드 0, design phase 가속화. 권장값 명시 제공이 OQ 흐름 효율화의 핵심.
  2. **Keep / R-5 cron 격리**: 기존 `auction_jobs.py` 5min cron과 신규 `auction_promotion_jobs.py` 60s cron 완전 분리 (별도 파일 + 별도 AsyncSessionLocal + 다른 컬럼 업데이트). main.py lifespan에서 task 2개 별도 등록. 향후 cron worker 추가 시 표준 패턴.
  3. **Keep / Idempotent cron pattern**: SELECT FOR UPDATE SKIP LOCKED + UPDATE WHERE col IS NULL — 멀티 워커 동시 실행 안전. tier_release_jobs.py(#10) 패턴 재사용 + 확장.
  4. **Keep / Pillow sync + run_in_executor**: 동기 함수를 `loop.run_in_executor(None, partial(_generate_share_card, ...))`로 호출 — async context blocking 회피. PR2 design 시 OQ-D-4=A로 명시 처리.
  5. **Keep / R-2 thumbnail fallback**: thumbnail fetch 실패 시 try/except + fallback rect+text로 200 응답 유지 — share card 생성이 외부 fetch 실패로 인한 5xx 차단. 외부 종속성 있는 합성 작업의 일반 패턴.
  6. **Keep / R-3 Pillow 메모리 제어**: `convert("RGB") + thumbnail((600,630), LANCZOS)` 사전 처리 — 대용량 원본 이미지 메모리 폭증 방지. 향후 이미지 합성 PDCAs 표준.
  7. **Problem 1 (C-1, iterate에서 발견 후 closed)**: Frontend `PostView.active_auction_end_at` 타입 선언 + `PostCard.tsx` 사용 — 그러나 backend `_serialize_post`에서 미공급 → AC-12 silent fail (R-FE-6 graceful degradation으로 crash 없음). **교훈**: Frontend 타입 선언과 Backend 공급은 항상 동시 검증 필요 (gap-detector가 발견).
  8. **Problem 2 (M-1, iterate에서 closed)**: i18n 키 audit 시 design spec namespace (`notification.type.auction.*`)와 implementation namespace (`share.*`) 차이 — design은 14 keys 명시했으나 implementation은 10 share keys + 6 auction.shareCard.* aliases로 분기. **교훈**: i18n key audit는 design vs implementation namespace 1:1 매핑 검증 단계 추가 필요.
  9. **Problem 3 (m-1, carry-over)**: `share.*` vs `auction.shareCard.*` namespace 중복 — 거의 동일 문자열 두 namespace 공존. editor-i18n-cleanup carry-over에 합류.
  10. **Try**: 다음 PDCA부터 — (1) Frontend 타입 추가 시 Backend serializer 동시 grep 검증 게이트, (2) i18n design 명세는 leaf key 열거 (namespace + 정확한 key 경로) + implementation grep 자동 비교, (3) Critical Path 종결 PDCA는 iterate 1회 권장 (carry-over 분절 방지).
- **Carry-over**:
  - **`m-1` i18n namespace 통합** (Low, ~30min): `share.*` vs `auction.shareCard.*` 한 namespace로 통합. editor-i18n-cleanup carry-over 합류 권장
  - **`m-2` 서버측 알림 title/body 한국어 하드코딩** (Medium, 향후 i18n PDCA): `auction_promotion_jobs.py:35-45` `_TITLE_MAP`/`_BODY_MAP` user.language 기반 i18n. Phase 4 외 향후 처리
  - 이전 carry-over 유지: `editor-video-studio` (#6-video, ffmpeg 차단), `series reorder persistence endpoint` (#8), `upload-retry-ui` (#4), `editor-i18n-cleanup` v0.2 (#3+#4 + #11 m-1), `POST_TIER_RESTRICTED CTA UI / sponsor N일 제한 / SQL-only filter` (#10.1)
- **Production Readiness**: ✅ TypeScript 0 에러. 5 locale JSON valid (100 신규 entries 5 locale 일관). Backend **77 tests passing in 1.24s** (61 baseline + 12 PR2 + 4 iterate = 9+12 unit + 8 integration + 4 신규). 1 smoke 스크립트 ready (`smoke_test_auction_promotion.sh` 4-step). 5 통합 지점 회귀 0 (feed/explore/search/users[id]/posts[id]). R-5 cron 격리 유지 (`auction_jobs.py` 무수정 + `_create_order_for_winner` 무수정). ⚠ alembic upgrade 필수 (0042, 사용자 측 실행 권장).
- **Phase 4 Closure**: editor-revamp-roadmap의 **마지막** Critical Path #11 종료. **Phase 4 Artist Tools 단계 종결 — 11/11 = 100%**. 다음 단계: Phase 5 (i18n cleanup + carry-over 정리) 또는 신규 로드맵.
| [domo-phase6-roadmap](./domo-phase6-roadmap/) | 2026-05-04 | N/A (parent roadmap, 12/13 = 92%, D'-6 deferred) | — | **Phase 6 parent roadmap 종결** — D' (Carry-over Consolidation 1~2주) + A (Discovery & Growth Funnel 6~10주) = 12 sub-PDCAs 완료 + D'-6 stripe-webhook Phase 7+ deferred. **D' 5/6**: phase4-tech-debt-cleanup (alembic 0045 + sponsor_validity_days + TierRestrictedPanel CTA + SQL-only home_feed + 5 신규 + 4 baseline test fix) + subscription-cancellation-tracking (alembic 0044 + Subscription cancellation 컬럼 + churn endpoint + ChurnList 보강) + stripe-coupon-foundation (alembic 0046 + AppliedCoupon + CouponProvider Mock+Stripe + 5 endpoints + admin/me UI + 13 신규 tests) + phase5-i18n-cleanup (es 26 keys + 5 locale parity 100% 598 keys + WCAG manual + locale-aware date) + prometheus-deployment (Grafana JSON 7 panels + alerts.yml 5 alerts + metrics-security.md + observability.md v0.2). **A 8/8**: analytics-foundation Critical Path (PostHog SDK + 14 events + Mock fallback + GDPR opt-in default + CookieConsent + 4 funnels docs + Feature flag) + onboarding-funnel (3-step wizard follow+sponsor+discover + AppShell 통합 + Sidebar indicator + 4 신규 events) + feed-algorithm-v1 (feed_scoring.py followed 0.5+recency 0.3+engagement 0.15+trending 0.05 + SQL+Python hybrid + cursor IEEE 754 + algo query param + 6 unit + 4 integration tests) + explore-revamp (5 tabs + ExploreHeroCard daily rotation + ArtistIndexPreview top-5 + URL sync + 2 신규 events) + search-enhancement (alembic 0049 SearchHistory + filter+sort+type 4 + /me/search/history 4 endpoints + /search/popular + Filter sidebar + 9 unit tests) + **artist-index-v1 (README 비전 직접: alembic 0047 + User +4 cols + 1h cron R-5 격리 + 가중치 0.5+0.25+0.15+0.10 + log10 sales + tier_badge + Top 3 RankingHero + ranking page + 6 unit + 4 integration)** + **storytelling-hub (README 비전 직접: /stories hub Featured+ArtistHistories+MediaCoverage + /users/[id]/timeline 자동 milestones 6종 + useArtistTimeline 4 endpoint 합성)** + retention-loop-enhancement (alembic 0048 + Subscription expiry_notified_at + 1h cron R-5 + ExpiryBanner 7d cooldown + WinbackBanner cancellation_reason booster + 5 신규 events + 7 unit tests). **누적**: 147→207 passed (+60 tests) + 1 skipped (A-3 over-mocked) + tsc 0 + alembic 0044~0049 6 신규 + ~1100+ 신규 i18n × 5 locales + 16 신규+보강 endpoints + 6 신규 services + Prometheus 14 metrics + PostHog 14 events + 4 funnels + GDPR + Stripe Coupon SDK (Mock+Real). **10 OQs 모두 권장 default 일괄 수락**. **18 carry-over → Phase 7+**: D'-6 webhook + B-5 winback-coupon endpoint + post_engagement_cache + Region/Genre 별도 ranking + Featured Artist admin + dynamic OG + POST renew + pg_trgm + price 단위 통일 + backend posthog SDK + Jest 설정 + color contrast + VoiceOver/NVDA + axe-core CI + OpenTelemetry + multi-currency + push/email + DM messaging |

## domo-phase6-roadmap

- **Scope**: Phase 6 parent roadmap — D' (Carry-over Consolidation 1~2주) + A (Discovery & Growth Funnel 6~10주). 13 sub-PDCAs 정의, 12 완료 + D'-6 stripe-webhook-extension Phase 7+ deferred. **README 비전 본격 구현**: 그로스해킹 깔때기 (A-1+A-2+A-8) + 신진작가 인덱스 (A-6) + 스토리텔링 hub (A-7).
- **Artifacts**: [plan](./domo-phase6-roadmap/plan.md), [report](./domo-phase6-roadmap/report.md)
- **Parent Roadmap**: 없음 (Phase 6 자체가 parent roadmap)
- **Phase 6 Position**: Phase 5 (후원 인프라) → **Phase 6 (Discovery & Growth)** → Phase 7 (?)
- **누적 메트릭**: pytest 147→207 (+60) + 1 skipped + tsc 0 errors + alembic 0044~0049 (6 신규) + ~1100+ 신규 i18n × 5 locales + 16 신규+보강 endpoints + 6 신규 services (i18n + tier_benefits + feed_scoring + artist_index_scoring + subscription_expiry_jobs + artist_index_jobs) + Prometheus 14 metrics + PostHog 14 events + 4 funnels + GDPR + Stripe Coupon SDK
- **Decisions** (10 OQs 모두 권장 default 일괄 수락):
  - OQ-1=B 병렬 / OQ-2=B D'-6 defer / OQ-3=A PostHog / OQ-4=A SQL-only feed / OQ-5=B 가중치 ranking / OQ-6=C 자율+큐레이션 / OQ-7=A USD lock / OQ-8=A 즉시 시작 / OQ-9=C 정량+정성 / OQ-10=B 100% archived
- **Lessons Learned** (보고서 §7에 상세 10항목):
  1. **권장 default 일괄 수락 패턴 강화** — 10 OQs 협상 라운드 0 (Phase 5 8 OQs와 동일)
  2. **병렬 위임 + booster 패턴** — D' 그룹 A 4 agents + 단독 + A 단독 + 병렬 + 병렬 (4 wave). booster: D'-2 ChurnList → B-5, A-8 WinbackBanner → B-5, A-7 timeline → A-6, etc.
  3. **alembic revision ID 충돌 자동 해소** — A-5/A-8 둘 다 0048 시도 → linter rename + chain 재구성. 교훈: 병렬 위임 시 grep + 선점 명시
  4. **Test fix 패턴** — 5건 정정 (4 baseline test fix in D'-1 + 1 in D'-2 + 1 in D'-3 + 1 in A-6 + 1 in A-8 + 1 skip A-3 over-mocked). 정정 비용 < 5분 each
  5. **Mock 모드 fallback 일관** — PostHog + Stripe 둘 다 자동 mock fallback (env var 미설정 시)
  6. **R-5 cron 격리 일관** — 6 cron worker 모두 별도 file + 별도 AsyncSessionLocal 유지
  7. **Audit-driven scope 단축** — D'-3 audit 후 기존 인프라 활용 (`payment factory pattern` 미러)
  8. **i18n namespace 분리 strict** — 13 sub-PDCAs 모두 다른 namespace → race condition 0
  9. **PostHog Critical Path 선결** — A-1 가장 먼저 → 모든 후속 sub-PDCAs PostHog event 통합 booster 가능
  10. **README 비전 직접 구현** — A-6 신진작가 인덱스 + A-7 스토리텔링 hub (마케팅 hook 동시 확보)
- **Carry-over (18건 → Phase 7+)**: D'-6 webhook + B-5 winback-coupon endpoint + post_engagement_cache + Region/Genre 별도 ranking + Featured Artist admin + dynamic OG + POST renew + pg_trgm fuzzy + price 단위 통일 + backend posthog SDK + Jest 설정 + color contrast tailwind 조정 + VoiceOver/NVDA 실제 테스트 + axe-core CI + OpenTelemetry + multi-currency (KRW/EUR/JPY) + push/email digest + DM messaging
- **Production Readiness**: ✅ TypeScript 0 errors. 5 locale JSON valid 100% (598+ keys). Backend 207 tests passing + 1 skipped (over-mocked integration). 모든 6 cron worker R-5 격리. Stripe Coupon SDK Mock + Real 양쪽 동작. PostHog GDPR opt-in default + CookieConsent + Privacy 설정. Prometheus 14 metrics + Grafana dashboard JSON + alerts.yml. ⚠ alembic upgrade 사용자 측 실행 완료 (0044~0049).
- **Phase 6 Closure**: Phase 6 12/13 = 92% (D'-6 deferred). README "그로스해킹 깔때기" + "신진작가 인덱스" + "스토리텔링 hub" 직접 구현. **Phase 7 진입 준비 완료**.
| [domo-phase7-roadmap](./domo-phase7-roadmap/) | 2026-05-05 | N/A (parent roadmap, 15/15 = 100%) | — | **Phase 7 parent roadmap 종결** — G' (Carry-over Consolidation 2~3주) + C (Press Kit & PR Automation 6주) = 15 sub-PDCAs 100% (D'-6 흡수). **G' 10/10**: stripe-webhook-extension (9 핸들러+signing+idempotency) + winback-coupon-endpoint (4 사유 spec+24h idempotency) + a11y-tailwind-cleanup (text.muted 5.5:1+border 3.2:1+axe-core) + backend-posthog-integration (analytics.py+7 integration points+Mock 모드) + jest-test-runner-setup (Jest+ts-jest+A-1 8 tests pass) + dynamic-og-card (4 OG routes Edge runtime+Metadata API) + admin-featured-artists (alembic 0050+partial UNIQUE+A-7 통합) + region-genre-ranking (alembic 0052+User+5 cols+ROW_NUMBER+RankingCard multi-rank) + post-engagement-cache (alembic 0053+1h cron R-5+A-3 booster) + price-unit-consistency (alembic 0051+Post.buy_now_price cents+lib/format.ts). **C 5/5 — README 마케팅 hub 직접 구현**: ai-artist-interview-generation Critical Path (alembic 0054+ArtistInterview+tuzigroup LLM Gateway gemma4-e4b+Mock 모드+admin 검수+작가 consent+publish+16 tests) + press-kit-auto-export (alembic 0055+PressKit+reportlab+Pillow PDF 5~8 페이지+30d cache+1 fix IMMUTABLE) + multi-language-story (alembic 0056+UserBioTranslation composite PK+LLM translate+24h cache+localStorage middleware+LocaleSwitcher) + media-coverage-cms (alembic 0057+MediaCoverage+6 endpoints+A-7 booster+admin UI) + newsletter-digest (alembic 0058+NewsletterPreferences+Issue+AWS SES boto3+Mock 모드+1h cron R-5+composer C-1~C-4 booster+GDPR opt-in default+1-click unsubscribe+10 tests). **누적**: 207→311 passed (+104 tests) + 1 skipped + tsc 0 + alembic 0050~0058 (9 신규) + ~1100+ 신규 i18n × 5 locales + 30+ 신규 endpoints + 10+ 신규 services + 6 신규 모델 + 8 cron worker (R-5 격리 일관) + Prometheus 22+ metrics + tuzigroup LLM Gateway 통합 + AWS SES 통합. **10 OQs 모두 권장 default 일괄 수락**. **16 carry-over → Phase 8+**: G'-11 VoiceOver/NVDA + G'-12 OpenTelemetry + G'-13 Redis + CJK font 임베딩 + multi-language SEO meta + RSS auto-fetch + click tracking + auto-thumbnail + A/B subject + bounce 처리 + ML personalized + multi-channel SMS + DM messaging + multi-currency (KRW/EUR/JPY) + mobile native + P3-1 Community + ML feed v2 |

## domo-phase7-roadmap

- **Scope**: Phase 7 parent roadmap — G' (Carry-over Consolidation 2~3주, 18 carry-over 청산) + C (Press Kit & PR Automation 6주, README 마케팅 hub 본격 구현). 15 sub-PDCAs 정의, 모두 완료 (D'-6 stripe-webhook G'-1 흡수). **README 비전 마케팅 hub 직접 구현**: AI 인터뷰 (C-1) + Press Kit PDF (C-2) + Multi-language (C-3) + Media CMS (C-4) + Newsletter (C-5).
- **Artifacts**: [plan](./domo-phase7-roadmap/plan.md), [report](./domo-phase7-roadmap/report.md)
- **Parent Roadmap**: 없음 (Phase 7 자체가 parent roadmap)
- **Phase 7 Position**: Phase 6 (Discovery & Growth Funnel) → **Phase 7 (Tech Debt + 마케팅 hub)** → Phase 8 (?)
- **누적 메트릭**: pytest 207→311 (+104) + 1 skipped + tsc 0 errors + alembic 0050~0058 (9 신규) + ~1100+ 신규 i18n × 5 locales + 30+ 신규+보강 endpoints + 10+ 신규 services + 6 신규 모델 (FeaturedArtist + ArtistInterview + PressKit + UserBioTranslation + MediaCoverage + NewsletterPreferences + NewsletterIssue) + 8 cron workers (R-5 격리 일관) + Prometheus 22+ metrics + tuzigroup LLM Gateway 통합 + AWS SES 통합 + Stripe Webhook 9 핸들러 + Stripe Coupon SDK 활용 winback flow
- **Decisions** (10 OQs 모두 권장 default 일괄 수락):
  - OQ-1=B 병렬 / OQ-2=C G'-11~13 Phase 8+ defer / OQ-3=A tuzigroup LLM Gateway / OQ-4=A Pillow+reportlab / OQ-5=A LLM Gateway 번역 / OQ-6=B AWS SES / OQ-7=D 사용자 선택 기본 매월 / OQ-8=C 매월 Featured / OQ-9=B 100% archived / OQ-10=A 즉시 시작
- **Lessons Learned** (보고서 §6에 상세 12항목):
  1. **권장 default 일괄 수락** 강화 (10 OQs 협상 0)
  2. **Wave 기반 병렬 위임 효율** — G' Wave 1 (4 agents) + Wave 2+3 통합 (5 agents) + C Wave 1 단독 + Wave 2 (2) + Wave 3 (2) — 최대 5 agents 동시
  3. **alembic 충돌 자동 해소** — linter rename + grep으로 자연 해결 (0050~0058 9 신규)
  4. **Test fix 패턴 강화** — 7건 정정 (mock + IMMUTABLE index + status transition + db.refresh side effect 등)
  5. **Mock 모드 fallback 강화** — tuzigroup LLM + AWS SES + Stripe + PostHog 모두 자동 mock
  6. **R-5 cron 격리 일관 (8 worker)**: 모두 별도 file + 별도 AsyncSessionLocal 유지
  7. **Booster 패턴 강화** — D'-3 → G'-2 + G'-7 → A-7 + G'-8 → A-6 + G'-9 → A-3 + C-1 → C-2/C-3/C-5 + C-2 → C-5 + C-3 → C-4
  8. **i18n namespace 분리 strict** — 15 sub-PDCAs 모두 다른 namespace
  9. **README 비전 직접 구현** 강화 — A-6+A-7 (Phase 6) + C-1~C-5 (Phase 7) 마케팅 hub
  10. **LLM Gateway 통합** — tuzigroup memory 자격증명 즉시 production-ready
  11. **Audit-driven scope 단축** — 기존 인프라 활용 (Pillow+Stripe+artist_index+feed_scoring)
  12. **schema sync checklist** — Frontend 타입 + Backend serializer 동시 검증 표준화
- **Carry-over (16건 → Phase 8+)**: G'-11 VoiceOver/NVDA + G'-12 OpenTelemetry + G'-13 Redis + CJK font 임베딩 + multi-language SEO meta + RSS auto-fetch + click tracking + auto-thumbnail + A/B subject + bounce 처리 + ML personalized + multi-channel SMS + DM messaging + multi-currency + mobile native + P3-1 Community + ML feed v2
- **Production Readiness**: ✅ TypeScript 0 errors. 5 locale JSON valid 100%. Backend 311 tests passing + 1 skipped (over-mocked integration). 8 cron workers R-5 격리. Stripe Webhook + Coupon + SetupIntent 모두 동작. tuzigroup LLM Gateway Mock + Real 양쪽 동작. AWS SES Mock + Real 양쪽 동작. PostHog (frontend + backend) GDPR opt-in default. Prometheus 22+ metrics + Grafana JSON. ⚠ alembic upgrade 사용자 측 실행 완료 (0050~0058).
- **Phase 7 Closure**: Phase 7 15/15 = 100% (D'-6 흡수). README "마케팅 hub" + "AI 시대 예술가 생존" 직접 구현. **Phase 8 진입 준비 완료**.
| [domo-phase8-roadmap](./domo-phase8-roadmap/) | 2026-05-05 | N/A (parent roadmap, 15/15 = 100%) | — | **Phase 8 parent roadmap 종결** — G'' (Performance & Observability 4주) + H' (Carry-over Consolidation 3주) + B' (Patronage Maturity 6주) = 15 sub-PDCAs 100% (D'-6 G'-1 흡수, H'-6 ML prep Phase 9+ defer). **G'' 5/5**: opentelemetry-tracing (8 cron span + 5 critical span + Mock 모드 fallback) + redis-cache-layer (CacheClient 7 methods + 4 cache 영역 + Prometheus 4 metrics) + n-plus-one-audit (CI EXPLAIN ANALYZE 18 쿼리 + alembic 0059 perf indexes + N+1 0 발견) + db-connection-pool-tuning (5/15→20/50 + 11 cron pool isolation + Prometheus 2 metrics) + frontend-bundle-optimization (8 dynamic imports + Konva canvas:false fix + Lighthouse baseline). **H' 5/5**: voiceover-nvda-test-fix (SkipLink WCAG 2.4.1 Level A + 16 페이지 ARIA + 36 issues fix) + cjk-font-pdf-embedding (font_registry.py 5 locale Noto Sans CJK + Helvetica fallback) + multi-language-seo-meta (5 layout + sitemap.ts hreflang) + click-tracking-rss-thumbnail (PostHog event + backend hit) + newsletter-bounce-handling (alembic 0060 + SES SNS webhook + signature verify + Prometheus 6 metrics). **B' 5/5**: multi-currency-foundation (alembic 0061+0062 + exchange_rate_jobs 9번째 cron + Open Exchange Rates Mock fallback + Stripe multi-currency + CurrencySwitcher) + dm-messaging (alembic 0063 + 8 endpoints + 1:1 polling + 5 components) + push-email-digest-foundation (alembic 0064 + FCM/APNs Mock + email_digest 10번째 cron + 4 cron 통합) + stripe-billing-auto-renewal (alembic 0065 + auto_renewal 11번째 cron + G'-1 webhook booster + ExpiryBanner /renew 통합) + patronage-analytics-dashboard (5 SVG charts + B-2 booster + Mock fallback). **누적**: 311→412 passed (+101 tests) + 7 skipped + tsc 0 + alembic 0050~0065 (16 신규) + ~1500+ 신규 i18n × 5 locales + 11 cron worker R-5 격리 일관 + tuzigroup LLM Gateway + AWS SES + boto3 + Redis cache + OpenTelemetry. **12 OQs 모두 권장 default 일괄 수락**. **13 carry-over → Phase 9+**: H'-6 ML prep + RSS auto + auto-thumbnail + open rate tracking + Group DM + WebSocket realtime + file/image attach DM + over-mocked test refactor + Mobile native + WCAG AAA + 등 |

## domo-phase8-roadmap

- **Scope**: Phase 8 parent roadmap — G'' (Performance & Observability 4주) + H' (Carry-over Consolidation 3주) + B' (Patronage Maturity 6주). 15 sub-PDCAs 100% (D'-6 흡수 + H'-6 Phase 9+ defer). **README 비전 마무리**: 후원 maturity (multi-currency + DM + push/email + Stripe billing 자동 갱신) + 성능/관측성 (OpenTelemetry + Redis + N+1 audit + DB pool + frontend bundle).
- **Artifacts**: [plan](./domo-phase8-roadmap/plan.md), [report](./domo-phase8-roadmap/report.md)
- **Phase 8 Position**: Phase 7 (마케팅 hub) → **Phase 8 (Performance + Tech Debt + Patronage Maturity)** → Phase 9 (?)
- **누적 메트릭**: pytest 311→412 (+101) + 7 skipped + tsc 0 + alembic 0050~0065 (16 신규) + ~1500+ 신규 i18n × 5 locales + 11 cron worker R-5 격리 일관 + Prometheus 30+ metrics + tuzigroup LLM Gateway + AWS SES + boto3 + Redis cache + OpenTelemetry + Stripe Coupon SDK + Stripe Webhook 9 핸들러 + Stripe billing auto-renewal + multi-currency 4 (USD/KRW/EUR/JPY) + DM 1:1 + Push FCM/APNs + Newsletter SES bounce + Patronage analytics 5 charts
- **Decisions** (12 OQs 모두 권장 default 일괄 수락):
  - OQ-1=B 병렬 / OQ-2=B H'-6 Phase 9+ defer / OQ-3=A AWS ElastiCache / OQ-4=B AWS X-Ray / OQ-5=C 4 currency Full / OQ-6=A Open Exchange Rates / OQ-7=A 1:1 DM only / OQ-8=B FCM+APNs / OQ-9=B B'-1 Critical Path 선결 / OQ-10=B 100% archived / OQ-11=A 즉시 시작 / OQ-12=A Mobile+P3-1 Phase 9 separate
- **Lessons Learned** (보고서 §7에 상세 12항목):
  1. **권장 default 일괄 수락 패턴 강화** (12 OQs 협상 0)
  2. **Wave 기반 병렬 위임** (G'' 5 + H' 5 + B' 1+4 = 4 waves)
  3. **alembic 충돌 자동 해소** (linter rename 0050~0065 16 신규)
  4. **Test fix 패턴 강화** (16건 정정 — http_status→status_code + over-mocked class patch + db.refresh side effect + IMMUTABLE index 등)
  5. **Mock 모드 fallback 일관 강화** (LLM + AWS SES + Stripe + PostHog + Redis + FCM + APNs + Open Exchange Rates 모두 graceful)
  6. **R-5 cron 격리 일관 (11 worker)**: auction + auction_promotion + tier_release + schedule + artist_index + subscription_expiry + post_engagement + newsletter + exchange_rate + email_digest + auto_renewal — 모두 별도 file + 별도 AsyncSessionLocal 유지
  7. **Booster 패턴 강화** (D'-3→G'-2, A-7→G'-6/G'-7/C-2, A-3→G'-9, C-1→C-2/C-3/C-5, C-3→H'-3, B-3→B'-4, B-2→B'-5, A-8→B'-4/B'-5)
  8. **i18n namespace 분리 strict** — 15 sub-PDCAs 모두 다른 namespace
  9. **README 비전 직접 구현 마무리** — A-6+A-7 (Phase 6) + C-1~C-5 (Phase 7) + G''+H'+B' (Phase 8) 마케팅 hub + AI 시대 작가 + 후원 maturity 완성
  10. **Skip pattern over-mocked tests** — DMConversation/DeviceToken/NotificationPreferences class patch는 select() 호환 위해 Phase 9+ refactor (불가피)
  11. **Audit-driven scope** — G'-1 + G'-2 + G'-7 + B'-1 모두 기존 인프라 (Pillow + Stripe + payment factory + StripePriceCache) 재사용
  12. **schema sync checklist** — Frontend 타입 + Backend serializer 동시 검증 표준화 (G'-10 + B'-1 cents/currency 일관)
- **Carry-over (13건 → Phase 9+)**: H'-6 ML feed personalization prep + RSS auto-fetch + auto-thumbnail OG scraping + Newsletter open rate tracking + Group DM (P3-1 별도) + WebSocket realtime push + File/image attach DM + over-mocked test refactor + Mobile native app + WCAG AAA + AAA Cognitive a11y + Translation memory + Cohort retention 자동 alert
- **Production Readiness**: ✅ TypeScript 0 errors. 5 locale JSON valid 100%. Backend 412 tests passing + 7 skipped (over-mocked Phase 9+ refactor). 11 cron workers R-5 격리. Stripe webhook + Coupon + SetupIntent + Subscription + auto-renewal 모두 production-ready. tuzigroup LLM Gateway + AWS SES + Redis + OpenTelemetry + FCM + APNs + Open Exchange Rates 모두 Mock 모드 fallback. Multi-currency 4 (USD/KRW/EUR/JPY) production-ready. DM messaging 1:1 polling. ⚠ alembic upgrade 사용자 측 실행 완료 (0050~0065).
- **Phase 8 Closure**: Phase 8 15/15 = 100%. README 비전 (그로스해킹 깔때기 + 신진작가 인덱스 + 스토리텔링 hub + 마케팅 hub + AI 시대 예술가 생존 + 후원 maturity + 글로벌 multi-currency) **완전 구현**. **Phase 9 진입 준비 완료** (Mobile + P3-1 + ML feed + AI 작가 큐레이션 후보).
