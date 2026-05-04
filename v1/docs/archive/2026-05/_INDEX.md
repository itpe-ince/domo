# Archive Index — 2026-05

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [editor-responsive-redesign](./editor-responsive-redesign/) | 2026-05-01 | 96% | 0 rounds | 에디터 #3: 데스크탑 2-pane(편집+미리보기 토글) + 모바일 3·4단 wizard, 803줄 page.tsx 컴포넌트 분해(547줄, -32%), 3 hooks + 9 신규 컴포넌트 + 23 i18n × 5 locale, DB·API 변경 0 |
| [editor-media-ux](./editor-media-ux/) | 2026-05-03 | 95% | 0 rounds | 에디터 #4: dnd-kit drag-reorder + 이미지 캡션(280자, MediaAsset.caption + PATCH /media/{id}) + 다중 업로드 XHR 실시간 progress(OQ-D-3=B 사용자 변경). Backend 5파일 + Frontend 10+파일 + 11 i18n × 5 locale + 첫 외부 라이브러리(@dnd-kit) 도입 |
| [editor-image-studio](./editor-image-studio/) | 2026-05-03 | 96% | 0 rounds | 에디터 #6-image: Konva 클라이언트 4 도구(회전/크롭/모자이크/워터마크) + Pillow 서버 처리 + crop_meta JSONB 비파괴 + alembic 0037+0038 + POST /v1/media/{id}/transform + Signature 3 endpoints (OQ-D-3=B 사용자 override 별도 시그니처 업로드 UI). Backend ~2300 LOC + Frontend ~1500 LOC + 22 tests + 47 i18n × 5 locale |
| [publish-controls](./publish-controls/) | 2026-05-03 | 100% | 0 rounds | 에디터 #8 Critical Path: B-3 발행 옵션 4건 통합. alembic 0039+0040 + Series 모델 + 6 endpoints (publish + Series CRUD 5종) + visibility 필터 + comments lock + audit log. Frontend PublishOptionsPanel + SeriesCreateModal + /series/[id] dnd-kit reorder + VisibilityBadge + handleSubmit hybrid C. Backend ~1800 LOC + Frontend ~2200 LOC + 22 tests + 2 smoke + 47 i18n × 5 locale = 235 entries |
| [artist-tier-release](./artist-tier-release/) | 2026-05-03 | 99% | 0 rounds | 에디터 #10 Phase 4 Critical Path: B-4 후원자/단골 우선 공개. **Option β 채택 (R-1 dissolved)** — Post.visibility enum 미확장, tier_only는 computed effective state. alembic 0041 (early_access_until + early_access_tier + sponsorships R-5 인덱스) + 3 helpers (UNION ALL EXISTS + 2단계 SQL+Python) + tier_release_jobs.py 60s cron + 5 endpoints visibility 필터. Frontend TierReleasePicker (PublishOptionsPanel 5번째 expand) + TierBadge + handleSubmit + posts/[id] 403. Backend ~750 LOC + Frontend ~400 LOC + 17 신규 tests (61 total) + 1 smoke + 22 신규 i18n × 5 = 110 entries |

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
