---
template: design
version: 1.0
feature: editor-responsive-redesign
sub-pdca: "#3"
date: 2026-04-30
author: itpe-ince (Claude Sonnet 4.6 + bkit frontend-architect agent)
project: domo
project_version: v1
status: Draft
parent_plan: editor-responsive-redesign.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
oq_resolved: 2026-04-30
---

# editor-responsive-redesign Design Document

> **Summary**: 803줄 단일 컴포넌트 `posts/new/page.tsx`를 데스크탑 2-pane(편집 + 미리보기) + 모바일 3단계 wizard로 분리하는 순수 프런트엔드 개편. OQ-3=B 원칙에 따라 hooks-first 점진적 추출로 기존 5개 통합 지점(autosave/DraftRestoreDialog/멀티탭/role-gating/PostTypeSelector)을 모든 추출 단계에서 보존한다.

---

## 0. OQ 결정 요약 (잠금 — 재논의 금지)

| ID | 결정 | 설계 영향 |
|----|------|-----------|
| OQ-1 = A | 단일 breakpoint `md(768px)` | `< 768px` → wizard, `≥ 768px` → 2-pane. Tailwind `md:` prefix 하나만 사용 |
| OQ-2 = C | 사이드 고정 + 토글 on/off | PreviewPane은 DOM에 항상 마운트, `isPreviewVisible` state로 CSS 숨김 처리 |
| OQ-3 = B | hooks-first 점진적 추출 | `new-v2/` 평행 디렉토리 금지. 기존 page.tsx를 단계별로 수술 |
| OQ-4 = A | 기본 3단계 wizard | product 타입일 때만 4단계 확장. 구체적 분기 로직은 §3.3에서 결정 |

---

## 1. Goals & Non-Goals

### 1.1 기술적 목표

1. **반응형 레이아웃**: `md(768px)` 단일 breakpoint 기준으로 데스크탑 2-pane과 모바일 wizard를 완전 분리한다.
2. **page.tsx 컴포넌트 분해**: 803줄 단일 파일을 역할 단위 컴포넌트로 점진 추출하여 향후 `#4 editor-media-ux`, `#7 editor-product-meta`, `#8 publish-controls` PDCA가 각자 담당 컴포넌트만 건드릴 수 있도록 한다.
3. **5개 통합 지점 회귀 0**: `useDraftAutosave`, `DraftRestoreDialog`, 멀티탭 storage event, `PostTypeSelector`(role-gating), `applicationStatus` fetch — 이 5개는 분해 후에도 완전히 동일하게 동작한다.
4. **모바일 wizard 상태 보존**: step 이동 시(앞·뒤) 입력 데이터 유실 없음. 모든 formState는 page 최상위가 소유하여 step 간 공유된다.
5. **5 locale i18n 완결**: `ko/en/ja/zh/es` 신규 키 동시 출시, 일본어·중국어 긴 라벨 레이아웃 검증 포함.
6. **접근성**: 키보드 탐색, ARIA landmark, `prefers-reduced-motion` 대응.

### 1.2 명시적 비목표 (다른 sub-PDCA)

| 항목 | 담당 sub-PDCA |
|------|--------------|
| DB / API 변경 | 해당 없음 — 이 PDCA에서 백엔드 변경 0 |
| 본문 마크다운·서식 에디터 | #5 `editor-rich-content` |
| 미디어 드래그 순서·파일별 진행률·이미지 캡션 | #4 `editor-media-ux` |
| 메이킹 영상 모달·이미지/영상 에디터 | #6 `editor-media-studio` |
| 상품 메타데이터 구조화 입력(dimensions/medium/year), 협업자 태그 | #7 `editor-product-meta` |
| 공개 범위·댓글·시리즈·예약발행 패널 | #8 `publish-controls` |
| 미디어 업로더 내부 동작 변경 | 이 PDCA에서 MediaToolbar·MediaPreviewList 수정 최소화 |
| shadcn/ui, framer-motion 등 신규 라이브러리 도입 | package.json 의존성은 현행 유지 — Next.js + React + Tailwind만 사용 |

> **주의**: `package.json`을 확인한 결과 `shadcn/ui`, `@radix-ui`, `framer-motion`, `zustand`, `@tanstack/react-query` 등이 모두 미설치 상태다. 모든 UI 컴포넌트는 HTML + Tailwind 네이티브로 구현한다.

---

## 2. Architecture Overview

### 2.1 컴포넌트 트리 다이어그램

```
app/posts/new/page.tsx                   ← Suspense boundary, export dynamic
  └── CreatePostPageInner                ← 모든 state 소유. 분해 후에도 최상위 유지
        │
        ├── DraftRestoreDialog           ← [기존 유지] 진입 시 표시
        │
        ├── LoginModal                   ← [기존 유지]
        │
        ├── EditorPageShell              ← [신규] breakpoint 분기 + AppShell 적응
        │     │
        │     │ ── [≥ md] 데스크탑 2-pane ──────────────────────────────────
        │     ├── EditorDesktopLayout    ← [신규] grid/flex 데스크탑 wrapper
        │     │     ├── EditorWorkspace  ← [신규] 편집 폼 영역
        │     │     │     ├── (sticky header: title + AutosaveIndicator + 임시저장 + 등록)
        │     │     │     ├── 멀티탭 경고 배너
        │     │     │     ├── PostTypeSelector      ← [기존 유지]
        │     │     │     ├── title input
        │     │     │     ├── content textarea
        │     │     │     ├── MediaPreviewList      ← [기존 유지]
        │     │     │     ├── MediaToolbar          ← [기존 유지]
        │     │     │     ├── TagAutocomplete       ← [기존 유지]
        │     │     │     └── ProductFields         ← [신규] product type일 때만
        │     │     │
        │     │     └── PreviewPane      ← [신규] 항상 DOM 마운트, CSS로 숨김
        │     │           ├── PreviewToggleButton   ← 패널 상단 or 에디터 상단에 위치
        │     │           └── PostPreviewCard       ← [신규] 실제 미리보기 렌더
        │     │
        │     │ ── [< md] 모바일 wizard ─────────────────────────────────────
        │     └── EditorMobileWizard     ← [신규] step 컨테이너 + step state machine
        │           ├── WizardStepIndicator          ← [신규] 상단 step 인디케이터
        │           ├── step === "type"  → EditorStepType    ← [신규]
        │           ├── step === "content" → EditorStepContent ← [신규]
        │           │     └── (product type 시 ProductFields inline 포함)
        │           ├── step === "product_meta" (product only) → EditorStepProductMeta ← [신규]
        │           └── step === "publish" → EditorStepPublish ← [신규]
        │
        └── AutosaveIndicator            ← [기존 유지, 위치 이동 가능]
```

### 2.2 State 소유 모델

**핵심 원칙**: `CreatePostPageInner`가 모든 formState를 소유하고 props drilling으로 하위에 전달한다. Context API, Zustand 등은 이 PDCA에서 도입하지 않는다.

```
CreatePostPageInner (page.tsx)
  │
  ├── formState (18개 useState — §6에서 그룹화 검토)
  ├── UI state: uploading, submitting, error
  ├── draft state: currentDraftId, showRestoreDialog, serverDraftForRestore, multiTabWarning
  ├── applicationStatus
  ├── isPreviewVisible (신규 — 데스크탑 미리보기 토글)
  └── wizardStep (신규 — 모바일 step machine, page-level 소유)
        │
        ├── EditorWorkspace
        │     props: formState 전체 + setters, uploading, submitting,
        │            draftStatus, lastSavedAt, onManualSave, onSubmit,
        │            isPreviewVisible, onTogglePreview, multiTabWarning, onDismissWarning
        │
        └── EditorMobileWizard
              props: formState 전체 + setters, wizardStep, onStepChange,
                     uploading, submitting, draftStatus, lastSavedAt,
                     onManualSave, onSubmit, multiTabWarning, onDismissWarning
```

props drilling 깊이 검토: 현재 구조에서 최대 3단계(page → EditorMobileWizard → EditorStepContent)이므로 Context 불필요. 4단계 이상이 되는 경우(#4, #7 등 후속 PDCA에서 필드 추가 시) 검토한다.

### 2.3 반응형 분기 다이어그램

```
뷰포트 너비
      │
      ├── < 768px ─── 모바일 wizard
      │     - 풀스크린 단계형 UI
      │     - AppShell의 MobileTabBar는 pb-16으로 이미 padding 처리됨
      │     - Sidebar는 `hidden md:flex`이므로 모바일에서 미표시 (기존 동작)
      │     - wizard는 main column 전체 너비 사용
      │
      └── ≥ 768px ─── 데스크탑 2-pane
            - 좌측 EditorWorkspace + 우측 PreviewPane
            - AppShell: Sidebar(80px) + main column(flex-1)
            - 2-pane은 main column 내부에서만 구성 → AppShell 수정 0
```

### 2.4 데이터 흐름

```
사용자 입력
   │
   ├─ setters 호출 → CreatePostPageInner의 useState 갱신
   │
   ├─ formState 변경 → useDraftAutosave 2s debounce → localStorage
   │
   ├─ [데스크탑] formState → PreviewPane props → PostPreviewCard 즉시 re-render
   │   (isPreviewVisible=true일 때만 시각적으로 보임, DOM은 항상 마운트)
   │
   └─ [모바일] formState → 현재 step 컴포넌트 props → 해당 step 입력 UI
```

---

## 3. Responsive Layout Specification

### 3.1 Breakpoint

- **단일 분기**: `md(768px)` — Tailwind 표준 `md:` prefix 하나만 사용
- `< 768px`: 모바일 wizard 렌더
- `≥ 768px`: 데스크탑 2-pane 렌더
- Sidebar는 `hidden md:flex`이므로 md 이상에서 80px(축소) 또는 260px(확장) 공간 차지
- 2-pane이 차지할 실제 영역 = `전체 너비 - Sidebar 너비`. AppShell `flex-1 min-w-0`의 main column 내부에서 2-pane grid/flex를 구성하므로 AppShell 구조 변경 없음

### 3.2 데스크탑 2-pane (≥ md)

#### 레이아웃 방식

CSS Grid를 사용한다:

```
md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]
```

- 좌측(EditorWorkspace): `minmax(0, 1fr)` — 남은 공간 전체. `minmax(0, ...)`으로 오버플로우 방지
- 우측(PreviewPane): `minmax(0, 24rem)` — 고정 최대 너비 384px. 좁은 뷰포트(768~1024px)에서 `min-content`로 축소 허용
- PreviewPane이 숨김(`isPreviewVisible=false`)일 때: 우측 컬럼을 `md:grid-cols-[minmax(0,1fr)_0]`으로 전환하면 재흐름 발생. 대신 PreviewPane에 `w-0 overflow-hidden opacity-0 pointer-events-none` 클래스 적용 + `aria-hidden`으로 시각적으로만 숨김. React state는 살아있어 토글 on 시 데이터 즉시 표시 (OQ-2=C).

```tsx
// EditorDesktopLayout 예시 구조
<div className="md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] md:gap-0">
  <EditorWorkspace ... />
  <PreviewPane
    isVisible={isPreviewVisible}
    ...
  />
</div>
```

#### PreviewPane width 처리

| 상태 | CSS 클래스 | 동작 |
|------|-----------|------|
| 표시(isVisible=true) | `w-auto` | 정상 24rem 너비 표시 |
| 숨김(isVisible=false) | `w-0 overflow-hidden opacity-0 pointer-events-none` | 너비 0, 불가시, 클릭 불가. DOM 유지 |

grid 컨테이너의 두 번째 컬럼은 `minmax(0, 24rem)` 고정이므로 PreviewPane이 width 0이 되면 해당 컬럼은 0으로 수축하여 EditorWorkspace가 넓어진다. CLS(Cumulative Layout Shift)는 미리보기 토글 시 발생하는 구조적 변화이므로 완전 회피는 불가능하나, `transition-all duration-200`으로 부드럽게 처리한다.

#### PreviewToggleButton 위치 및 스펙

- **위치**: EditorWorkspace sticky header 우측 영역 — 임시저장 버튼과 등록 버튼 사이
- **아이콘**: 눈 아이콘(`EyeIcon` / `EyeOffIcon`) — `components/icons.tsx`에 신규 추가
- **ARIA**:
  ```tsx
  <button
    aria-controls="preview-pane"
    aria-expanded={isPreviewVisible}
    aria-label={isPreviewVisible ? t("post.editor.preview.toggle.hide") : t("post.editor.preview.toggle.show")}
  >
    {isPreviewVisible ? <EyeOffIcon /> : <EyeIcon />}
  </button>
  ```
- **isPreviewVisible state 소유**: `CreatePostPageInner` — 데스크탑/모바일 분기 위에서 관리. 모바일에서는 이 state를 사용하지 않음

### 3.3 모바일 Wizard (< md)

#### Step State Machine

기본 3단계, product 타입일 때 임시 4단계:

```
[일반 포스트 기본]
type → content → publish

[product 포스트]
type → content → product_meta → publish
```

**OQ-4 후속 — product 분기 결정:**

**옵션 ①**: step 2(content)에 product 메타 인라인 포함 — step 수 3 고정
**옵션 ②**: `type === "product"`일 때 step 2.5(product_meta) 추가 — step 수 4 가변

**권장: 옵션 ② (임시 4단계)**, 근거:
- `#7 editor-product-meta` PDCA가 product 메타 입력을 구조화할 때 `EditorStepProductMeta` 컴포넌트만 교체하면 됨. 마이그레이션 비용 최소화.
- step 2(content)가 `type === "product"`일 때도 미디어·본문·태그에만 집중 → 단일 책임 유지
- 옵션 ①은 step 2의 스크롤 길이가 product 시 과도하게 길어지고, #7 작업 시 content step 내부 수술 필요 → 회귀 위험 증가

**step 전환 조건 (검증 게이트)**:

| 현재 step | 다음 step | 통과 조건 |
|-----------|-----------|-----------|
| type | content | `type` 선택됨 (`"general"` 또는 `"product"`) — `PostTypeSelector`가 이미 기본값 "general" 제공하므로 항상 통과 가능. 단, 비작가가 product를 선택한 상태면 `type`을 자동으로 "general"로 재설정(기존 useEffect 유지) |
| content | product_meta (product only) | 검증 없음 — 빈 내용도 진행 허용. 발행 시점에 서버 검증 |
| content | publish (general) | 검증 없음 |
| product_meta | publish | 검증 없음 |

> step 미선택 차단 정책: Plan FR-05에서 "타입 미선택 시 다음 차단"을 요구하나, `PostTypeSelector` 기본값이 `"general"`이므로 항상 선택 상태. 실제로 차단이 필요한 케이스는 존재하지 않음. 단, 비작가가 product로 강제 진입 시(URL 파라미터 등) 기존 useEffect([me?.role, type])가 "general"로 복원하므로 안전.

#### 진행률 표시

**방식**: 상단 step 인디케이터 (점 + 레이블)
- 3단계: `● ○ ○` → `● ● ○` → `● ● ●`
- product 4단계: `● ○ ○ ○` → ... 동일 패턴
- 레이블: "포스트 종류", "내용 작성", "상품 정보"(product only), "발행 설정"
- 구현: `WizardStepIndicator` 컴포넌트 — 점과 라인 연결. 애니메이션은 `transition-colors`만 사용 (framer-motion 없음)

#### 다음/이전 버튼

- **위치**: 하단 fixed/sticky — `sticky bottom-0` 방식 채택
  - 이유: `position: fixed`는 키보드 노출 시 가려짐 문제가 동일함. `sticky bottom-0`은 콘텐츠가 버튼 뒤로 스크롤되어 접근 가능. 모바일 키보드 노출 시 버튼이 키보드 위로 밀리는 동작은 기본 브라우저 scroll-into-view로 처리
- **구조**:
  ```
  [이전] [다음 또는 등록]
  ```
  - 첫 step(type): 이전 버튼 숨김
  - 마지막 step(publish): 다음 대신 등록(submit) 버튼
- **배경**: `bg-background/90 backdrop-blur-sm border-t border-border` — sticky 시 콘텐츠와 구분

#### 모바일 wizard에서 autosave 인디케이터 위치

각 step 상단에 `AutosaveIndicator`를 표시한다. sticky header 패턴을 모바일에서는 각 step 컴포넌트 상단에 고정. WizardStepIndicator 바로 아래에 위치:

```
[WizardStepIndicator]  ← step 1/3 ● ○ ○
[AutosaveIndicator]    ← "저장됨 · 3초 전"
[현재 step 콘텐츠]
[이전][다음] sticky bottom
```

---

## 4. Component Tree & Decomposition Plan

### 4.1 신규 컴포넌트 카탈로그

#### `EditorPageShell`
- **책임**: 모바일/데스크탑 레이아웃 분기 컨테이너. Suspense boundary와 props 중계 역할
- **위치**: `v1/frontend/src/app/posts/new/page.tsx` 내 또는 `components/post-editor/EditorPageShell.tsx`
- **props**: formState 전체 + 모든 handler + isPreviewVisible + wizardStep
- **실제 구현**: page.tsx 내부 `<main>` 영역을 대체. `className="md:hidden"` vs `className="hidden md:block"` 분기로 wizard / 2-pane 선택

#### `EditorDesktopLayout`
- **책임**: 데스크탑 2-pane grid wrapper
- **위치**: `components/post-editor/EditorDesktopLayout.tsx`
- **props**: `children: [EditorWorkspace, PreviewPane]`
- **구현**: grid 컨테이너. isPreviewVisible을 직접 받지 않고 PreviewPane에 위임

#### `EditorWorkspace`
- **책임**: 편집 폼 전체 영역 — title, content, media, tags, product fields, MediaToolbar, sticky header 포함
- **위치**: `components/post-editor/EditorWorkspace.tsx`
- **props**:
  ```ts
  interface EditorWorkspaceProps {
    // form state
    type: PostType; onTypeChange: (v: PostType) => void;
    title: string; onTitleChange: (v: string) => void;
    content: string; onContentChange: (v: string) => void;
    genre: string; onGenreChange: (v: string) => void;
    tags: string[]; onTagsChange: (v: string[]) => void;
    media: CreatePostMedia[]; onMediaChange: (v: CreatePostMedia[]) => void;
    embeds: OEmbedData[]; onEmbedsChange: (v: OEmbedData[]) => void;
    isMakingVideo: boolean; onMakingVideoChange: (v: boolean) => void;
    scheduledAt: string; onScheduledAtChange: (v: string) => void;
    locationName: string; onLocationNameChange: (v: string) => void;
    locationLat: number | null; onLocationLatChange: (v: number | null) => void;
    locationLng: number | null; onLocationLngChange: (v: number | null) => void;
    isAuction: boolean; onIsAuctionChange: (v: boolean) => void;
    isBuyNow: boolean; onIsBuyNowChange: (v: boolean) => void;
    buyNowPrice: number | ""; onBuyNowPriceChange: (v: number | "") => void;
    dimensions: string; onDimensionsChange: (v: string) => void;
    medium: string; onMediumChange: (v: string) => void;
    year: number | ""; onYearChange: (v: number | "") => void;
    // artist gate
    userRole: ApiUser["role"] | undefined;
    applicationStatus: ArtistApplicationStatus | undefined;
    // upload/submit
    uploading: boolean; submitting: boolean; error: string | null;
    // draft
    draftStatus: DraftSaveStatus; lastSavedAt: Date | null;
    onManualSave: () => Promise<void>;
    onSubmit: () => Promise<void>;
    // ui
    isPreviewVisible: boolean; onTogglePreview: () => void;
    multiTabWarning: boolean; onDismissWarning: () => void;
    // refs
    textareaRef: React.RefObject<HTMLTextAreaElement>;
    tagRef: React.RefObject<HTMLDivElement>;
  }
  ```
- **의존성**: PostTypeSelector, TagAutocomplete, MediaToolbar, MediaPreviewList, AutosaveIndicator, ProductFields

#### `PreviewPane`
- **책임**: 데스크탑 전용 실시간 미리보기. 항상 DOM에 마운트, `isVisible` prop으로 CSS 토글
- **위치**: `components/post-editor/PreviewPane.tsx`
- **props**:
  ```ts
  interface PreviewPaneProps {
    isVisible: boolean;
    type: PostType;
    title: string;
    content: string;
    media: CreatePostMedia[];
    embeds: OEmbedData[];
    tags: string[];
    genre: string;
    // product preview
    isAuction: boolean;
    isBuyNow: boolean;
    buyNowPrice: number | "";
    me: ApiUser | null;
  }
  ```
- **숨김 처리**: `isVisible ? "" : "w-0 overflow-hidden opacity-0 pointer-events-none"` + `aria-hidden={!isVisible}`

#### `PostPreviewCard`
- **책임**: 미리보기 실제 렌더. Feed 카드와 시각적 일관성 유지 (단, 클릭·좋아요 등 인터랙션 없음)
- **위치**: `components/post-editor/PostPreviewCard.tsx`
- **props**: PreviewPane이 받는 content 관련 props 그대로
- **표시 항목**: 제목(있으면), 본문(있으면), 미디어 thumbnail grid, 태그 badge, 장르(product일 때), 가격 정보(product일 때)
- **빈 상태**: 모든 입력이 비었을 때 placeholder 표시 (`t("post.editor.preview.empty")`)

#### `EditorMobileWizard`
- **책임**: 모바일 step 컨테이너. step state machine, WizardStepIndicator, 하단 이전/다음 버튼 포함
- **위치**: `components/post-editor/EditorMobileWizard.tsx`
- **props**: formState 전체 + setters + wizardStep + onStepChange + upload/submit handlers + draftStatus + 등
- **내부 step 타입**: `type WizardStep = "type" | "content" | "product_meta" | "publish"`

#### `WizardStepIndicator`
- **책임**: 상단 진행률 표시 (점 + 라인 + 레이블)
- **위치**: `components/post-editor/WizardStepIndicator.tsx`
- **props**:
  ```ts
  interface WizardStepIndicatorProps {
    steps: Array<{ id: WizardStep; label: string }>;
    currentStep: WizardStep;
  }
  ```

#### `EditorStepType`
- **책임**: step 1 — PostTypeSelector 래핑
- **위치**: `components/post-editor/wizard/EditorStepType.tsx`
- **props**: type, onTypeChange, userRole, applicationStatus, disabled

#### `EditorStepContent`
- **책임**: step 2 — title, content, media, tags, making video 체크박스, MediaToolbar
- **위치**: `components/post-editor/wizard/EditorStepContent.tsx`
- **props**: content 관련 formState + setters + upload handlers + refs

#### `EditorStepProductMeta`
- **책임**: step 3 (product only) — genre, dimensions, medium, year, isAuction, isBuyNow, buyNowPrice
- **위치**: `components/post-editor/wizard/EditorStepProductMeta.tsx`
- **props**: product 관련 formState + setters
- **설계 의도**: #7 `editor-product-meta` PDCA가 이 컴포넌트 내부만 교체하면 구조화 입력으로 마이그레이션 가능

#### `EditorStepPublish`
- **책임**: 마지막 step — scheduledAt, locationName, 최종 확인 UI
- **위치**: `components/post-editor/wizard/EditorStepPublish.tsx`
- **props**: scheduledAt, locationName/Lat/Lng setters + error + submitting

#### `ProductFields`
- **책임**: product 타입일 때 공통 상품 정보 폼. 데스크탑 EditorWorkspace와 EditorStepProductMeta 모두에서 재사용
- **위치**: `components/post-editor/ProductFields.tsx`
- **props**: genre, dimensions, medium, year, isAuction, isBuyNow, buyNowPrice + 각 setter

#### 기존 컴포넌트 — 변경 없음

| 컴포넌트 | 변경 여부 | 위치 |
|----------|-----------|------|
| `PostTypeSelector` | 변경 없음 | `components/post-editor/PostTypeSelector.tsx` |
| `DraftRestoreDialog` | 변경 없음 | `components/DraftRestoreDialog.tsx` |
| `MediaToolbar` | 변경 없음 | `components/post-editor/MediaToolbar.tsx` |
| `MediaPreviewList` | 변경 없음 | `components/post-editor/MediaPreviewList.tsx` |
| `TagAutocomplete` | 변경 없음 | `components/post-editor/TagAutocomplete.tsx` |
| `AutosaveIndicator` | 변경 없음 (page.tsx 내 함수) | page.tsx 내 또는 추출 |
| `LoginModal` | 변경 없음 | `components/LoginModal.tsx` |

### 4.2 신규/추출 Hooks 카탈로그

현재 `useDraftAutosave`는 이미 분리 완료. 추가 hook 추출 후보:

#### `usePostFormState` (권장)
- **책임**: 18개 useState를 그룹화. 필드 초기화(`handleRestore` 시) 단일 setter 제공
- **위치**: `lib/hooks/usePostFormState.ts`
- **반환**: `{ formState, setters, resetFromDraft }`
- **장점**: `handleRestore`의 18줄 개별 setter 호출을 1줄로 단순화

#### `useArtistGate`
- **책임**: `me`, `applicationStatus` fetch + 비작가 자동 fallback useEffect 캡슐화
- **위치**: `lib/hooks/useArtistGate.ts`
- **반환**: `{ userRole, applicationStatus, autoFalledBackToGeneral }`
- **장점**: page.tsx의 두 useEffect(lines 123~163)를 hook으로 추출

#### `useEditorWizardStep`
- **책임**: 모바일 step state machine — currentStep, canGoNext, goNext, goPrev
- **위치**: `lib/hooks/useEditorWizardStep.ts`
- **반환**: `{ step, steps, canGoNext, goNext, goPrev, isFirstStep, isLastStep }`
- **product 분기 포함**: `type === "product"`일 때 steps 배열에 "product_meta" 자동 삽입

#### 미추출 권장 (현행 유지)

`usePostMediaState`(media/embeds/uploading), `useScheduleState`(scheduledAt/location) 분리는 Do 단계 실제 컴포넌트 경계 확정 후 결정. 과도한 사전 분리는 오히려 props drilling을 복잡하게 만들 수 있음.

### 4.3 점진 추출 순서 (OQ-3=B 핵심)

각 Step은 독립적으로 커밋 가능하며, 완료 후 즉시 회귀 체크리스트를 실행한다.

---

**Step 1: Hooks 추출** (page.tsx 줄 수 감소, UI 변화 없음)

| 추출 대상 | 현재 위치 | 이동 위치 | 추출 우선순위 |
|-----------|-----------|-----------|--------------|
| `usePostFormState` | page.tsx 70~90줄 useState 18개 | `lib/hooks/usePostFormState.ts` | 1순위 |
| `useArtistGate` | page.tsx 123~163줄 2개 useEffect | `lib/hooks/useArtistGate.ts` | 2순위 |
| `useEditorWizardStep` | 신규 (아직 없음) | `lib/hooks/useEditorWizardStep.ts` | 3순위 (Step 4 전에 필요) |

Step 1 완료 후 회귀 체크:
- [ ] DraftRestoreDialog 진입 시 표시됨
- [ ] autosave 2초 debounce 정상 동작
- [ ] 멀티탭 경고 배너 표시됨
- [ ] PostTypeSelector — artist/user 분기 정상
- [ ] 발행(submit) 성공 → `/posts/{id}` 리다이렉트

---

**Step 2: ProductFields 분리 + PreviewPane 신규 작성**

- `ProductFields.tsx` 신규 — page.tsx 634~719줄의 product 필드 UI 추출
- `PreviewPane.tsx` + `PostPreviewCard.tsx` 신규 작성
- `EyeIcon`, `EyeOffIcon` → `components/icons.tsx` 추가
- `isPreviewVisible` state + `PreviewToggleButton` → page.tsx에 추가
- 데스크탑에서 PreviewPane이 우측에 표시되는지 확인 (모바일에서 숨김 확인)

Step 2 완료 후 회귀 체크: (Step 1 체크 전체 + 아래 추가)
- [ ] 데스크탑: 2-pane 나란히 표시
- [ ] 미리보기 토글 on/off — 데이터 유지
- [ ] 모바일: 2-pane 미표시 (PreviewPane hidden)

---

**Step 3: EditorWorkspace 추출**

- `EditorWorkspace.tsx` 신규 — 편집 폼 전체 (sticky header + 모든 입력 필드 + ProductFields 포함)
- page.tsx의 `<main>` 내 JSX를 EditorWorkspace로 이동
- `EditorDesktopLayout.tsx` 신규 — grid wrapper

Step 3 완료 후 회귀 체크: (Step 2 체크 전체 반복)

---

**Step 4: 모바일 wizard step 컴포넌트 추출**

- `wizard/EditorStepType.tsx` — PostTypeSelector 래핑
- `wizard/EditorStepContent.tsx` — 미디어·본문·태그 필드
- `wizard/EditorStepProductMeta.tsx` — 상품 정보 (ProductFields 재사용)
- `wizard/EditorStepPublish.tsx` — 발행 설정 최종 확인
- `WizardStepIndicator.tsx` 신규

Step 4 완료 후 회귀 체크: (Step 3 체크 전체 + 아래 추가)
- [ ] 모바일: 각 step 이동 시 데이터 보존
- [ ] product 타입 선택 시 4단계 표시

---

**Step 5: EditorMobileWizard 통합 + `useEditorWizardStep` 연결**

- `EditorMobileWizard.tsx` 신규 — step 컨테이너 + 하단 버튼
- `useEditorWizardStep` hook 연결
- 모바일 `< md` 조건으로 wizard 표시, 데스크탑 `md:` 조건으로 2-pane 표시 분기

Step 5 완료 후 회귀 체크: (Step 4 체크 전체 반복)

---

**Step 6: i18n 신규 키 추가 + page.tsx 정리**

- 5 locale 파일에 `post.editor.*` 키 추가 (§8 전체 목록)
- page.tsx는 Suspense wrapper + CreatePostPageInner(최상위 state 소유)만 남음
- 임시 하드코딩된 한국어 텍스트가 있다면 i18n 키로 교체

Step 6 완료 후 최종 회귀 체크: 수동 테스트 시나리오 전체 (§12)

---

## 5. Critical Integration Points — 5개 회귀 지점 보존 명세

### 5.1 `useDraftAutosave` 훅

| 항목 | 내용 |
|------|------|
| **현재 위치** | page.tsx 165~186줄 — formState 구성 + hook 호출 |
| **분해 후 위치** | `CreatePostPageInner` (page.tsx)에 잔류. formState는 `usePostFormState` hook으로 추출되나 hook 호출부는 page에서 계속 관리 |
| **동작 보장 조건** | `formState` 객체가 18개 필드 모두 포함된 채로 hook에 전달될 것. `currentDraftId`는 page-level state로 유지. `storageKey`는 `me.id` 또는 "guest"를 포함한 정확한 키 유지 |
| **회귀 검증** | 제목 입력 → 2초 대기 → localStorage에 `domo-draft-{id}-new` 키 존재 확인 (DevTools) |

### 5.2 `DraftRestoreDialog` 마운트 + `currentDraftId` state

| 항목 | 내용 |
|------|------|
| **현재 위치** | page.tsx 403~429줄 — DraftRestoreDialog JSX. `showRestoreDialog`, `serverDraftForRestore`, `currentDraftId` state는 page 70~110줄 |
| **분해 후 위치** | `DraftRestoreDialog`는 `EditorPageShell` 또는 `CreatePostPageInner`에서 렌더. `currentDraftId`는 page-level state 유지. `handleRestore`는 `usePostFormState.resetFromDraft`로 단순화 가능 |
| **동작 보장 조건** | 진입 시 useEffect(meLoading, storageKey, draftParam)가 항상 실행되고, dialog open 상태가 정확히 전달될 것 |
| **회귀 검증** | 임시저장 후 `/posts/new` 재진입 → DraftRestoreDialog 표시 확인 (데스크탑·모바일 양쪽) |

### 5.3 멀티탭 `storage` event useEffect + 경고 배너

| 항목 | 내용 |
|------|------|
| **현재 위치** | page.tsx 255~266줄 — storage event listener. 경고 배너는 473~489줄 |
| **분해 후 위치** | storage event listener는 `CreatePostPageInner`에 잔류(page-level). 경고 배너 JSX는 `EditorWorkspace`의 sticky header 바로 아래 또는 각 wizard step 상단에 위치 |
| **동작 보장 조건** | `storageKey`가 event handler 클로저에 최신 값으로 전달될 것. `multiTabWarning` state와 `onDismissWarning` handler가 EditorWorkspace / EditorMobileWizard 양쪽에 props로 전달될 것 |
| **회귀 검증** | 두 탭에서 `/posts/new` 동시 접속 → 두 번째 탭에 경고 배너 표시 확인 |

### 5.4 `PostTypeSelector` 사용 (role-gating UX)

| 항목 | 내용 |
|------|------|
| **현재 위치** | page.tsx 512~518줄 — `<PostTypeSelector value={type} onChange={setType} userRole={me.role} applicationStatus={applicationStatus} disabled={uploading \|\| submitting} />` |
| **분해 후 위치** | 데스크탑: `EditorWorkspace` 내부 유지. 모바일: `EditorStepType` 내부. 두 경우 모두 동일한 props 전달 |
| **동작 보장 조건** | `userRole` = `me?.role` (undefined 허용). `applicationStatus` 전달. `disabled` = `uploading \|\| submitting`. `onChange` = `setType` (page-level setter 또는 usePostFormState의 setter) |
| **회귀 검증** | 비작가 계정으로 모바일 wizard step 1 → "상품 포스트" 버튼 비활성 + 인라인 안내 표시 |

### 5.5 `applicationStatus` fetch + 비작가 자동 fallback useEffect

| 항목 | 내용 |
|------|------|
| **현재 위치** | page.tsx 123~163줄 — 두 개의 useEffect |
| **분해 후 위치** | `useArtistGate` hook으로 추출. hook이 `{ userRole, applicationStatus }` 반환하면 page.tsx에서 hook 호출만 남음 |
| **동작 보장 조건** | `fetchMyApplications()` 호출이 `me.role === "user"` 조건에서만 실행. `setType("general")` fallback이 `me.role !== "artist" && me.role !== "admin" && type === "product"` 조건에서 항상 발동 |
| **회귀 검증** | 비작가가 `?type=product`로 진입 → type이 자동으로 "general"로 변경되는지 확인 |

---

## 6. State Management Detail

### 6.1 formState 그룹 정의

현재 18개 useState를 목적별 그룹으로 분류:

| 그룹 | 필드 | 이동 위치 |
|------|------|-----------|
| **콘텐츠** | type, title, content, genre, tags | usePostFormState (또는 page 잔류) |
| **미디어** | media, embeds, isMakingVideo | usePostFormState (또는 별도 hook — #4 PDCA에서 결정) |
| **위치·일정** | scheduledAt, locationName, locationLat, locationLng | usePostFormState |
| **상품** | isAuction, isBuyNow, buyNowPrice, dimensions, medium, year | usePostFormState |
| **UI-only** | uploading, submitting, error | page 잔류 — draft/wizard와 분리 |
| **draft** | currentDraftId, showRestoreDialog, serverDraftForRestore, multiTabWarning | page 잔류 |
| **wizard** | wizardStep | page 잔류 또는 useEditorWizardStep |
| **preview** | isPreviewVisible | page 잔류 |

`usePostFormState`는 `formState` 전체를 하나의 객체로 관리하거나 개별 state + setters를 반환하는 방식 중 하나를 선택한다. `handleRestore`가 18개 필드를 한 번에 리셋해야 하므로 `resetFromDraft(DraftState)` 단일 함수를 노출하는 구조가 유리하다.

### 6.2 lift state vs co-locate 결정

- **page-level 소유**: formState, draft state, wizardStep, isPreviewVisible — 데스크탑/모바일 양쪽 레이아웃이 동일 state를 공유하므로 lift 필요
- **co-locate 가능**: UI-only state(hover 상태, focus 등) — 각 컴포넌트 내부에서 관리

### 6.3 props drilling 깊이 평가

```
page.tsx (CreatePostPageInner)
  └── EditorMobileWizard   (depth 1)
        └── EditorStepContent  (depth 2)
              └── MediaToolbar  (depth 3 — 기존과 동일)
```

최대 3단계. `MediaToolbar`는 이미 기존에 page에서 직접 렌더되었으나 분해 후에도 3단계 이내. Context 미도입 유지.

### 6.4 `wizardStep` 위치

`wizardStep` state는 `CreatePostPageInner`(page-level)에서 소유한다. 이유:
- wizard step 변경 시 autosave indicator, DraftRestoreDialog 등 page-level 기능과 연동 가능
- 모바일/데스크탑 전환 시(뷰포트 리사이즈) step 상태가 보존됨 (리사이즈 자체는 rare하나 안전)
- `useEditorWizardStep` hook이 step 계산 로직을 담당하되 state는 page-level에서 관리

---

## 7. Preview Implementation

### 7.1 PreviewPane 표시 항목

피드 카드와 시각적 일관성을 유지하되, 클릭·좋아요·팔로우 등 인터랙션은 제거한 "읽기 전용 카드":

| 항목 | 조건 | 표시 방식 |
|------|------|-----------|
| 작가 아바타 + 이름 | 항상 | `me.avatar_url` / `me.display_name` |
| 제목 | `title.length > 0` | `text-xl font-bold` |
| 본문 | `content.length > 0` | `text-sm` 최대 5줄, 이후 fade out |
| 미디어 | `media.length > 0` | 이미지: thumbnail grid (최대 4개), 영상: 첫 프레임 또는 video 요소, 외부 임베드: oembed 썸네일 |
| 태그 | `tags.length > 0` | `badge-primary` pill 나열 |
| 장르 badge | `type === "product"` | `text-text-secondary text-xs` |
| 가격 | `type === "product" && (isAuction \|\| isBuyNow)` | 경매 / 즉시구매가 표시 |
| 빈 상태 | 모든 입력이 비었을 때 | `t("post.editor.preview.empty")` 중앙 안내 |

### 7.2 갱신 빈도 및 debounce

OQ-2=C에서 PreviewPane은 항상 마운트되고 `isPreviewVisible=true`일 때 시각적으로 표시된다. formState props 변경 시 React의 일반 re-render로 자동 갱신된다.

**debounce 필요 여부**: PostPreviewCard는 순수 렌더 컴포넌트(side effect 없음)이므로 React의 batched re-render로 충분하다. 타이핑 매번 렌더가 우려되는 경우 `React.memo(PostPreviewCard)`를 적용하여 props가 변경되지 않은 경우 re-render를 생략한다. 명시적 debounce(setTimeout)는 추가하지 않는다 — 정확한 성능 임계값은 측정 후 결정.

### 7.3 미디어 미리보기 처리

| 미디어 타입 | 표시 방법 |
|------------|-----------|
| `image` | `<img src={url}>` — thumbnail_url 우선, 없으면 url |
| `video` | `<video src={url} muted playsInline poster={thumbnail_url}>` |
| `external_embed` | oembed 썸네일 또는 플랫폼 favicon + URL 미리보기 카드 |

### 7.4 빈 상태 (Empty State)

```tsx
// PostPreviewCard 내부
if (!title && !content && media.length === 0) {
  return (
    <div className="flex flex-col items-center justify-center h-48 text-text-muted text-sm gap-2">
      <span className="text-2xl">✏️</span>
      <p>{t("post.editor.preview.empty")}</p>
    </div>
  );
}
```

---

## 8. i18n Keys

### 8.1 신규 prefix: `post.editor.*`

기존 `post.draft.*`, `post.type.*` 키와 충돌 없이 병존. 5 locale 동시 출시.

### 8.2 신규 키 전체 목록

```json
// ko.json — post.editor 블록 신규 추가
"editor": {
  "preview": {
    "toggle": {
      "show": "미리보기 표시",
      "hide": "미리보기 숨기기"
    },
    "empty": "내용을 입력하면 미리보기가 표시됩니다",
    "title": "미리보기"
  },
  "wizard": {
    "step": {
      "type": "포스트 종류",
      "content": "내용 작성",
      "productMeta": "상품 정보",
      "publish": "발행 설정"
    },
    "next": "다음",
    "previous": "이전",
    "submit": "등록",
    "submitScheduled": "예약 등록",
    "validation": {
      "typeRequired": "포스트 종류를 선택해 주세요"
    }
  }
}
```

### 8.3 5 locale 번역 표

| 키 | ko | en | ja | zh | es |
|----|----|----|----|----|-----|
| `post.editor.preview.toggle.show` | 미리보기 표시 | Show preview | プレビューを表示 | 显示预览 | Mostrar vista previa |
| `post.editor.preview.toggle.hide` | 미리보기 숨기기 | Hide preview | プレビューを非表示 | 隐藏预览 | Ocultar vista previa |
| `post.editor.preview.empty` | 내용을 입력하면 미리보기가 표시됩니다 | Start writing to see a preview | 内容を入力するとプレビューが表示されます | 输入内容后将显示预览 | Escribe algo para ver la vista previa |
| `post.editor.preview.title` | 미리보기 | Preview | プレビュー | 预览 | Vista previa |
| `post.editor.wizard.step.type` | 포스트 종류 | Post type | 投稿タイプ | 投稿类型 | Tipo de publicación |
| `post.editor.wizard.step.content` | 내용 작성 | Content | 内容作成 | 内容编写 | Contenido |
| `post.editor.wizard.step.productMeta` | 상품 정보 | Product info | 商品情報 | 商品信息 | Info del producto |
| `post.editor.wizard.step.publish` | 발행 설정 | Publish settings | 公開設定 | 发布设置 | Publicación |
| `post.editor.wizard.next` | 다음 | Next | 次へ | 下一步 | Siguiente |
| `post.editor.wizard.previous` | 이전 | Previous | 前へ | 上一步 | Anterior |
| `post.editor.wizard.validation.typeRequired` | 포스트 종류를 선택해 주세요 | Please select a post type | 投稿タイプを選択してください | 请选择投稿类型 | Selecciona el tipo de publicación |

> 일본어·중국어 레이아웃 주의: `post.editor.wizard.step.productMeta`의 일본어("商品情報")와 `post.editor.preview.empty`의 일본어가 step 인디케이터에서 잘릴 수 있음. WizardStepIndicator에서 `truncate` + `title` 속성으로 방어 처리.

### 8.4 기존 키 — 변경 없음

`post.draft.*`, `post.type.*`, `nav.*`, `common.*` — 건드리지 않음.

---

## 9. Accessibility

### 9.1 키보드 탐색

| 컴포넌트 | Tab 순서 | 특이사항 |
|----------|----------|----------|
| sticky header | PreviewToggleButton → 임시저장 버튼 → 등록 버튼 | `tabIndex` 명시 불필요 (DOM 순서 따름) |
| WizardStepIndicator | 인디케이터는 aria-hidden 처리 (장식 요소) | |
| wizard 이전/다음 버튼 | step 콘텐츠 → 이전 → 다음 | Enter로 다음 step 진행 |
| PreviewPane | `aria-hidden={!isVisible}` 적용 시 Tab 순서에서 제외 | |

### 9.2 ARIA 적용

```tsx
// EditorDesktopLayout
<section aria-label={t("post.editor.preview.title")}> // PreviewPane wrapper

// PreviewToggleButton
<button
  aria-controls="editor-preview-pane"
  aria-expanded={isPreviewVisible}
  aria-label={...}
>

// PreviewPane
<div
  id="editor-preview-pane"
  aria-hidden={!isPreviewVisible}
  role="complementary"
>

// WizardStepIndicator
<nav aria-label="포스트 작성 단계">
  <ol>
    <li aria-current={step === "type" ? "step" : undefined}>...</li>
  </ol>
</nav>

// EditorMobileWizard 하단 버튼 영역
<div role="navigation" aria-label="단계 이동">
```

### 9.3 `prefers-reduced-motion`

```css
/* globals.css에 추가 */
@media (prefers-reduced-motion: reduce) {
  .wizard-step-transition {
    transition: none !important;
  }
}
```

또는 Tailwind `motion-safe:transition-all` / `motion-reduce:transition-none` 유틸리티 활용:

```tsx
<div className={`motion-safe:transition-all motion-safe:duration-200 motion-reduce:transition-none`}>
```

step 전환 시 fade 또는 slide 애니메이션을 적용한다면 반드시 이 조건을 적용한다.

### 9.4 focus 관리

wizard step 이동 시 다음 step의 첫 번째 입력 요소로 focus를 이동한다:

```tsx
// EditorMobileWizard 내부
function goNext() {
  const nextStep = getNextStep(currentStep);
  setWizardStep(nextStep);
  // step 변경 후 첫 포커스 가능 요소로 이동
  requestAnimationFrame(() => {
    const firstFocusable = stepContentRef.current?.querySelector<HTMLElement>(
      'button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
    );
    firstFocusable?.focus();
  });
}
```

### 9.5 viewport meta 확인

`layout.tsx` 20~24줄에 이미 설정됨:
```ts
viewport: {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}
```
모바일 wizard에서 input 탭 시 자동 확대 없음. 별도 변경 불필요.

---

## 10. Performance

### 10.1 PreviewPane 자동 갱신

PreviewPane은 formState props 변경마다 React re-render를 받는다. `React.memo(PostPreviewCard)`를 적용하면 props 미변경 시 렌더 생략. 구체적인 성능 임계값(Lighthouse score, FPS)은 측정 후 결정.

```tsx
export const PostPreviewCard = React.memo(function PostPreviewCard(props: PostPreviewCardProps) {
  // ...
});
```

### 10.2 layout shift 최소화

PreviewPane 토글 시 grid 컬럼 너비 변화가 EditorWorkspace 너비를 변경한다. `transition-all duration-200`으로 부드럽게 처리하되, CLS는 토글 상호작용(사용자 의도적 행동)에서 발생하므로 Lighthouse CLS 기준 위반으로 간주하지 않는다.

### 10.3 wizard step 전환

step 전환은 CSS `opacity`/`display` 전환 또는 조건부 렌더(`{step === "type" && <EditorStepType />}`)를 사용한다. 조건부 렌더 방식은 unmount/mount로 각 step 입력 요소가 리셋될 위험이 없다 — formState는 page-level에서 소유하므로 step 언마운트되어도 state 보존됨.

### 10.4 `React.memo` 적용 후보

| 컴포넌트 | 적용 이유 |
|----------|-----------|
| `PostPreviewCard` | 미리보기 — formState 타이핑마다 렌더 방지 |
| `WizardStepIndicator` | step 변경 시에만 필요 |
| `ProductFields` | product 관련 필드만 변경 시 재렌더 |

---

## 11. Acceptance Criteria 매핑

Plan §5의 AC-1~AC-10과 이 design의 대응 항목:

| AC | 검증 기준 | 이 design 대응 항목 |
|----|-----------|---------------------|
| AC-1 | ≥ 768px에서 2-pane 나란히 표시 | §3.2 데스크탑 2-pane grid |
| AC-2 | < 768px에서 wizard + step 인디케이터 | §3.3 모바일 wizard + WizardStepIndicator |
| AC-3 | wizard step 이동 시 데이터 보존 | §6 State Management — page-level 소유 |
| AC-4 | 미리보기 pane 갱신 (토글 on 상태에서) | §7.2 갱신 빈도 — props 변경 시 즉시 re-render |
| AC-5 | AutosaveIndicator 모든 step에서 가시 | §3.3 — 각 wizard step 상단에 표시 |
| AC-6 | 비작가 — 상품 포스트 탭 비활성 | §5.4 PostTypeSelector 통합 지점 보존 |
| AC-7 | 5 locale 레이아웃 깨짐 0 | §8.3 번역 표 + 일본어·중국어 truncate 방어 |
| AC-8 | reduced-motion 시 애니메이션 비활성 | §9.3 prefers-reduced-motion |
| AC-9 | DraftRestoreDialog 데스크탑·모바일 양쪽 표시 | §5.2 DraftRestoreDialog 보존 명세 |
| AC-10 | 멀티탭 경고 모바일·데스크탑 양쪽 표시 | §5.3 멀티탭 경고 보존 명세 |

---

## 12. Test/Verification Strategy

현 프로젝트에 자동 테스트 인프라(Jest/Vitest/Playwright)가 없으므로 수동 회귀 시나리오로 검증한다. Browser DevTools Responsive 모드(Chrome) 활용.

### 12.1 수동 회귀 시나리오 (8개)

**시나리오 1 — 데스크탑 2-pane 기본 동작**
- 뷰포트 ≥ 768px, `/posts/new` 접속
- 좌측 편집 폼 + 우측 미리보기 나란히 표시 확인
- 제목 입력 → 미리보기에 즉시 반영 확인
- 미리보기 토글 클릭 → 우측 pane 숨김 → 다시 토글 → 입력한 제목 그대로 표시 확인
- 예상 결과: AC-1, AC-4 통과

**시나리오 2 — 모바일 wizard 기본 동작**
- DevTools Responsive → iPhone 13 (390px) 에뮬레이션
- step 인디케이터 "1/3" 표시 확인
- 다음 → 내용 작성 step → 제목, 본문 입력 → 다음 → 발행 설정 step
- 이전 → 내용 작성으로 돌아갔을 때 제목·본문 보존 확인
- 예상 결과: AC-2, AC-3 통과

**시나리오 3 — product 타입 wizard 4단계**
- 모바일에뮬레이션, 작가 계정 로그인
- step 1에서 "상품 포스트" 선택 → 다음
- step 2 내용 작성 → 다음
- step 3 "상품 정보" step 표시 확인 (4단계 인디케이터)
- 예상 결과: OQ-4 분기 로직 동작

**시나리오 4 — autosave 인디케이터 (5개 통합 지점 #1)**
- 데스크탑: 제목 입력 → 2초 대기 → sticky header에 "저장됨 · N초 전" 표시
- 모바일: wizard 각 step 상단에 동일 표시 확인
- 예상 결과: AC-5 통과

**시나리오 5 — DraftRestoreDialog (5개 통합 지점 #2)**
- 임시저장 버튼 클릭 → 다른 페이지 이동 → `/posts/new` 재진입
- DraftRestoreDialog 표시 확인 (데스크탑·모바일 양쪽)
- 이어쓰기 선택 → 기존 입력 복원 확인
- 예상 결과: AC-9 통과

**시나리오 6 — 멀티탭 경고 (5개 통합 지점 #3)**
- 같은 계정으로 두 탭에서 `/posts/new` 접속
- 첫 번째 탭에서 내용 입력 → 두 번째 탭에서 경고 배너 표시 확인
- 경고 배너 ✕ 클릭 → 닫힘 확인
- 예상 결과: AC-10 통과

**시나리오 7 — role-gating (5개 통합 지점 #4, #5)**
- 비작가 계정으로 `/posts/new?type=product` 직접 URL 입력
- type이 자동으로 "general"로 변경되는지 확인
- "상품 포스트" 탭 비활성 + 인라인 안내 표시 확인
- 예상 결과: AC-6 통과

**시나리오 8 — 5 locale 레이아웃 검증**
- DevTools Responsive + iPhone 13
- ko → en → ja → zh → es 순서로 언어 전환
- 각 locale에서 wizard step 인디케이터 라벨 잘림 없음 확인
- 특히 ja: "商品情報", zh: "发布设置" 등 긴 라벨 확인
- 예상 결과: AC-7 통과

### 12.2 DevTools Responsive 모드 활용 가이드

1. Chrome DevTools → Toggle Device Toolbar (Ctrl+Shift+M)
2. 프리셋: iPhone 13(390px), iPad Mini(768px), Desktop(1280px)
3. 768px 정확히 테스트: Custom width 767px(wizard), 768px(2-pane) 비교
4. 언어 전환: 사이드바 하단 언어 선택 → 각 locale 확인

---

## 13. New Open Questions for Design Phase (OQ-D-N) — ✅ Resolved (2026-04-30)

사용자가 권장 default 일괄 채택: **OQ-D-1 = A / OQ-D-2 = B / OQ-D-3 = B / OQ-D-4 = A / OQ-D-5 = B**

Design 문서 작성 중 추가로 발견된 모호점·trade-off (모두 결정 완료).

### OQ-D-1. PreviewPane 패널 헤더 — "미리보기" 레이블 표시 여부

**문제**: PreviewPane 상단에 "미리보기" 레이블(h2 또는 div)을 표시할지, 아니면 내용 바로 표시할지.

| 옵션 | 설명 |
|------|------|
| A (레이블 있음) | `<h2 class="text-xs text-text-muted">미리보기</h2>` 상단 표시 — 영역 역할 명확 |
| B (레이블 없음) | PostPreviewCard만 표시 — 더 깔끔한 디자인 |

**권장: A** — 스크린 리더용 section 레이블(`aria-label`)은 어차피 필요하므로, 시각적으로도 표시하는 것이 사용성 향상.

### OQ-D-2. wizard 하단 버튼 영역 배경 처리

**문제**: 하단 sticky 버튼 영역 배경이 투명하면 콘텐츠가 겹쳐 보임.

| 옵션 | 설명 |
|------|------|
| A | `bg-background/90 backdrop-blur-sm` — 반투명 블러 배경 |
| B | `bg-background border-t border-border` — 불투명 단색 배경 |

**권장: B** — 불투명 배경이 콘텐츠 겹침을 완전히 방지. 반투명은 시각적으로 깔끔하나 저사양 기기에서 backdrop-blur 성능 영향 가능.

### OQ-D-3. EditorWorkspace sticky header — 모바일에서 사용 여부

**문제**: 모바일 wizard에서 sticky header(제목 h1 + AutosaveIndicator + 임시저장/등록 버튼)가 필요한가? 이를 유지하면 wizard 상단에 header + WizardStepIndicator + AutosaveIndicator가 3개 레이어가 됨.

| 옵션 | 설명 |
|------|------|
| A (sticky header 유지) | wizard에서도 상단에 "등록" 버튼과 임시저장 버튼 항상 표시 |
| B (wizard는 하단 버튼만) | 마지막 step(publish)에서만 "등록" 버튼 표시. 임시저장은 모든 step 하단에 tertiary 버튼으로 |

**권장: B** — wizard의 단계별 흐름에 집중. "등록" 버튼을 마지막 step에만 표시하면 사용자가 모든 단계를 거치도록 유도 가능. 임시저장은 하단 버튼 영역에 small secondary 버튼으로 배치.

### OQ-D-4. 데스크탑 2-pane에서 isPreviewVisible 기본값

**문제**: 데스크탑 진입 시 미리보기가 기본으로 표시될지(true), 숨김 상태일지(false).

| 옵션 | 설명 |
|------|------|
| A (기본 표시) | 첫 방문 시부터 2-pane 표시. 에디터 폭이 좁아질 수 있음 |
| B (기본 숨김) | 처음에는 편집 폼 전체 너비. 사용자가 필요할 때 토글 |

**권장: A** — 이 PDCA의 핵심 목표가 "데스크탑 실시간 미리보기"이므로, 기본으로 표시하는 것이 의도에 맞음. 불편하면 사용자가 숨길 수 있음.

### OQ-D-5. 단일 PR vs 단계별 다중 PR (Do 단계 커밋 전략)

**문제**: §4.3의 6단계 추출 순서를 하나의 큰 PR로 낼지, 각 Step마다 PR을 낼지.

| 옵션 | 설명 |
|------|------|
| A (단일 PR) | 6 step 전체 완료 후 하나로. 리뷰 비용 높음. 회귀 위험 단일 점검 |
| B (단계별 PR) | Step 1~2 PR → 회귀 확인 → Step 3~4 PR → ... 단계적 |

**권장: B** — hooks 추출(Step 1)과 UI 신규 작성(Step 2)을 별도 PR로 분리하면 회귀 감지 포인트가 명확해짐. Step 3~5는 하나의 PR로 묶을 수 있음.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-30 | Initial draft — page.tsx 803줄 전체 분석, 5개 통합 지점 라인 번호 확인, 컴포넌트 트리 + 점진 추출 순서 + i18n 키 + 접근성 전체 설계. OQ-D 5개 신규 surface | itpe-ince (Claude Sonnet 4.6 + bkit frontend-architect agent) |
| 0.2 | 2026-04-30 | OQ-D 5개 모두 Resolved — 사용자가 권장 default 일괄 채택 (D-1 A / D-2 B / D-3 B / D-4 A / D-5 B). Do 단계 진입 준비 완료. 3개 PR 분할 전략(Step 1-2 / Step 3-5 / Step 6) 확정 | itpe-ince (Claude Opus 4.7) |
