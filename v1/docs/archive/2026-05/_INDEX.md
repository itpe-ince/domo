# Archive Index — 2026-05

| Feature | Archived | Match Rate | Iterations | Summary |
|---|---|---|---|---|
| [editor-responsive-redesign](./editor-responsive-redesign/) | 2026-05-01 | 96% | 0 rounds | 에디터 #3: 데스크탑 2-pane(편집+미리보기 토글) + 모바일 3·4단 wizard, 803줄 page.tsx 컴포넌트 분해(547줄, -32%), 3 hooks + 9 신규 컴포넌트 + 23 i18n × 5 locale, DB·API 변경 0 |

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
