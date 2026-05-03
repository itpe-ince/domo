# Archive Index — 2026-05

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [editor-responsive-redesign](./editor-responsive-redesign/) | 2026-05-01 | 96% | 0 rounds | 에디터 #3: 데스크탑 2-pane(편집+미리보기 토글) + 모바일 3·4단 wizard, 803줄 page.tsx 컴포넌트 분해(547줄, -32%), 3 hooks + 9 신규 컴포넌트 + 23 i18n × 5 locale, DB·API 변경 0 |
| [editor-media-ux](./editor-media-ux/) | 2026-05-03 | 95% | 0 rounds | 에디터 #4: dnd-kit drag-reorder + 이미지 캡션(280자, MediaAsset.caption + PATCH /media/{id}) + 다중 업로드 XHR 실시간 progress(OQ-D-3=B 사용자 변경). Backend 5파일 + Frontend 10+파일 + 11 i18n × 5 locale + 첫 외부 라이브러리(@dnd-kit) 도입 |

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
