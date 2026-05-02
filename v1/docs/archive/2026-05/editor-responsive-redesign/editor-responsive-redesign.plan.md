---
template: plan
version: 1.2
feature: editor-responsive-redesign
sub-pdca: "#3"
date: 2026-04-30
author: itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent)
project: domo
project_version: v1
status: Draft
parent_roadmap: editor-revamp-roadmap
kind: sub-pdca
size: L (1주)
---

# editor-responsive-redesign Planning Document

> **Summary**: 현재 단일 폼으로 구성된 포스트 에디터(`/posts/new`)를 데스크탑 2-pane 레이아웃(작성 + 미리보기)과 모바일 단계형 풀스크린 wizard로 분리하고, 803줄로 비대해진 page.tsx를 컴포넌트 단위로 분해한다. DB·API 변경 없는 순수 프런트엔드 개편.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-04-30
> **Sub-PDCA**: #3 (Critical Path: #1 ✅ → #2 ✅ → **#3 ⏭️** → #4 → #6 → #8 → #10)
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)
> **Status**: Draft

---

## 1. Overview

### 1.1 무엇을 (What)

[`v1/frontend/src/app/posts/new/page.tsx`](../../../frontend/src/app/posts/new/page.tsx) (현재 803줄)를 다음 두 가지 방향으로 개편한다:

1. **반응형 레이아웃 분리**: 데스크탑에서는 좌측 편집 폼 + 우측 실시간 미리보기의 2-pane 구조, 모바일에서는 타입 → 미디어/내용 → 발행 설정 순서의 단계형 풀스크린 wizard
2. **page.tsx 컴포넌트 분해**: 803줄 단일 파일을 역할 단위 컴포넌트(`EditorWorkspace`, `PreviewPane`, `EditorMobileWizard` 등 후보)로 분리하여 유지보수성 확보

### 1.2 왜 (Why)

부모 로드맵 §1.B-1, §1.C 요구사항 원본:

> **B-1 (입력 흐름)**: "모바일과 데스크탑 에디터 영역의 디자인 분리 필요"
>
> **C (화면 UI 개선)**: "우선 에디터만 개선 필요 / 에디터에서 선택한 발행 옵션, 작가 기능에 대한 시스템적인 대응 필요"

### 1.3 배경 (Background)

현재 `/posts/new/page.tsx`는 803줄 단일 컴포넌트로 다음 기능을 모두 포함하고 있다:

- 18개 폼 상태 관리 (type, title, content, genre, tags, media, embeds, scheduledAt, locationName, locationLat, locationLng, isMakingVideo, isAuction, isBuyNow, buyNowPrice, dimensions, medium, year)
- `useDraftAutosave` 훅 통합 (#2 PDCA 완료)
- `DraftRestoreDialog`, `currentDraftId` 상태, 멀티탭 경고 (#2 완료)
- `PostTypeSelector` (role-gating 포함, #1 PDCA 완료)
- `TagAutocomplete`, `MediaToolbar`, `MediaPreviewList`, `AutosaveIndicator`, `LoginModal`
- 발행(submit) 로직, draft 삭제 연동

이 단일 파일 구조는 다음 한계를 만든다:

- **모바일 사용성 저하**: 데스크탑용 세로 스크롤 폼이 모바일에서 그대로 노출 — 각 입력 영역의 공간 활용 비효율
- **유지보수 비용 증가**: 803줄 파일에 Phase 2~4 기능(#4 미디어 UX, #5 Rich content, #7 product meta 등)이 계속 추가되면 단일 파일이 1,500줄+로 비대해질 위험
- **미리보기 부재**: 데스크탑 환경에서도 발행 전 전체 미리보기를 볼 방법이 없음

**선행 PDCA 완료 상태 (Design 단계 진입 전 확인 필수):**

| PDCA | 상태 | 영향 |
|------|------|------|
| #1 `editor-role-gating` | 완료 (아카이브) | `PostTypeSelector` 재사용 — 건드리지 않음 |
| #2 `editor-draft-autosave` | 완료 (아카이브) | `useDraftAutosave`, `DraftRestoreDialog`, `currentDraftId`, 멀티탭 경고 — 전체 보존 |

### 1.4 관련 문서

| 구분 | 경로 | 설명 |
|------|------|------|
| 부모 로드맵 | [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) | §1.B-1, §1.C 요구사항 원본, §9 D-2 순서 결정 |
| 선행 PDCA #1 | [docs/archive/2026-04/editor-role-gating/](../../archive/2026-04/editor-role-gating/) | role-gating, PostTypeSelector |
| 선행 PDCA #2 | [docs/archive/2026-04/editor-draft-autosave/](../../archive/2026-04/editor-draft-autosave/) | autosave hook, DraftRestoreDialog |
| 에디터 페이지 | [frontend/src/app/posts/new/page.tsx](../../../frontend/src/app/posts/new/page.tsx) | 현재 803줄 — 분해 대상 |
| PostTypeSelector | [frontend/src/components/post-editor/PostTypeSelector.tsx](../../../frontend/src/components/post-editor/PostTypeSelector.tsx) | #1에서 추출된 컴포넌트 — 재사용 |
| Sidebar 반응형 참고 | [frontend/src/components/Sidebar.tsx](../../../frontend/src/components/Sidebar.tsx) | 모바일 breakpoint 처리 참고 |
| Tailwind 설정 | [frontend/tailwind.config.ts](../../../frontend/tailwind.config.ts) | 기존 breakpoint 및 색상 토큰 |
| Root 레이아웃 | [frontend/src/app/layout.tsx](../../../frontend/src/app/layout.tsx) | AppShell 구조 — 2-pane과 공존 확인 |

---

## 2. Scope

### 2.1 In Scope (포함)

- [x] **데스크탑 2-pane 레이아웃**: 좌측 편집 폼(EditorWorkspace) + 우측 실시간 미리보기(PreviewPane)
- [x] **모바일 단계형 wizard**: 타입 선택 → 미디어/내용 입력 → 발행 설정의 풀스크린 단계형 UI (EditorMobileWizard)
- [x] **반응형 breakpoint 정의**: Tailwind md/lg 기준으로 레이아웃 분기 (OQ-1 결정 후 확정)
- [x] **page.tsx 컴포넌트 분해**: 803줄 단일 파일을 역할 단위로 분리 (전략은 OQ-3 결정 후 확정)
- [x] **기존 기능 전체 보존 (회귀 0)**: autosave 인디케이터, DraftRestoreDialog, currentDraftId, 멀티탭 경고, PostTypeSelector(role-gating 포함) — 모든 단계·레이아웃에서 동작 보장
- [x] **단계 간 상태 유지**: 모바일 wizard step 이동 시 입력 데이터 유실 없음
- [x] **5 locale i18n 정합**: 한/영/일/중/스페인어 — 신규 UI 키 추가 및 레이아웃 깨짐 0
- [x] **접근성**: 탭 순서, ARIA landmark, `prefers-reduced-motion` 존중

### 2.2 Out of Scope (제외 — 별도 sub-PDCA)

| 항목 | 해당 sub-PDCA |
|------|--------------|
| DB 마이그레이션 | 해당 없음 (이 PDCA에서 DB 변경 없음) |
| 신규 백엔드 API | 해당 없음 (이 PDCA에서 API 변경 없음) |
| 본문 마크다운 / 서식 에디터 | #5 `editor-rich-content` |
| 미디어 드래그 순서 변경, 파일별 진행률, 이미지 캡션 | #4 `editor-media-ux` |
| 메이킹 영상 모달, 이미지·영상 에디터 | #6 `editor-media-studio` |
| 공개 범위·댓글·시리즈·예약발행 패널 | #8 `publish-controls` |
| 작가 메타데이터 구조화 입력 (dimensions/medium/year), 협업자 태그 | #7 `editor-product-meta` |

---

## 3. Requirements

### 3.1 Functional Requirements (기능 요구사항)

| ID | 요구사항 | 우선순위 | MoSCoW |
|----|----------|----------|--------|
| FR-01 | 뷰포트 breakpoint 기준 이상(데스크탑)에서 좌측 편집 폼 + 우측 미리보기 2-pane 레이아웃 표시 | High | Must |
| FR-02 | 데스크탑 미리보기 pane이 편집 폼 변경 시 실시간 갱신 (실시간 vs 토글 방식은 OQ-2 결정) | High | Must |
| FR-03 | breakpoint 미만(모바일)에서 단계형 wizard UI — 전체 화면, 하단 네비게이션 바로 step 이동 | High | Must |
| FR-04 | 모바일 wizard 상단에 현재 step 진행률 표시 (예: Step 2/3, 또는 step 인디케이터 바) | Medium | Should |
| FR-05 | 모바일 각 step에서 "다음" 진행 전 해당 step 입력값 검증 (예: 타입 미선택 시 다음 불가) | Medium | Should |
| FR-06 | 803줄 `page.tsx`를 역할 단위 컴포넌트로 분해 — 최소 EditorWorkspace(편집 영역), PreviewPane(미리보기), EditorMobileWizard(모바일 step 컨테이너) 후보 분리 | High | Must |
| FR-07 | 기존 기능 회귀 0 — autosave 인디케이터(모든 step에서 가시), DraftRestoreDialog(진입 시 동작), currentDraftId 상태, 멀티탭 경고, PostTypeSelector(role-gating), `useDraftAutosave` 훅 동작 — 데스크탑·모바일 양쪽에서 완전 보존 | High | Must |
| FR-08 | 5 locale(ko/en/ja/zh/es) 신규 UI 문자열 누락 0, 기존 키 깨짐 0 — 특히 일본어·중국어 라벨 길이 차이로 인한 레이아웃 깨짐 검증 | High | Must |
| FR-09 | 모바일 wizard step 이동 시(앞/뒤) 입력 데이터 보존 — step 재방문 시 이전 입력값 유지 | High | Must |

### 3.2 Non-Functional Requirements (비기능 요구사항)

| ID | 카테고리 | 기준 | 측정 방법 |
|----|----------|------|-----------|
| NFR-1 | 성능 | 2-pane 레이아웃 전환 시 CLS(Cumulative Layout Shift) 발생 최소화 — 정확한 임계값은 design 단계에서 측정 | 브라우저 DevTools Lighthouse |
| NFR-2 | 성능 | 모바일 step 전환 시 UI 응답 지연 없음 — 정확한 ms 기준은 design 단계에서 정의 | 수동 테스트 |
| NFR-3 | 접근성 | 2-pane 및 wizard에서 논리적 탭 순서 유지, 편집 영역 / 미리보기 영역 ARIA landmark 적용 | Axe DevTools, 키보드 수동 테스트 |
| NFR-4 | 접근성 | `prefers-reduced-motion: reduce` 적용 시 step 전환 애니메이션 비활성화 | OS 설정 토글 후 수동 확인 |
| NFR-5 | 반응형 | 지정 breakpoint 상·하에서 레이아웃 깨짐 0 — 모든 주요 뷰포트 너비(320px~1920px) 커버 | 브라우저 DevTools Responsive |
| NFR-6 | 유지보수성 | 분해 후 page.tsx(또는 최상위 entry)가 단순 조합자 역할로 축소 — 세부 로직은 개별 컴포넌트 파일로 이동 | 코드 리뷰 |

---

## 4. Open Questions — ✅ Resolved (2026-04-30, 사용자 권장 default 일괄 채택)

| ID | 질문 | 옵션 A | 옵션 B | 옵션 C | 결정 |
|----|------|--------|--------|--------|:----:|
| OQ-1 | 반응형 breakpoint 분기 기준 | `md(768px)` 이상 2-pane, 미만 wizard (Tailwind 표준 2단) | `sm(640px)`/`md(768px)`/`lg(1024px)` 3단 분기 | `lg(1024px)` 이상 2-pane, `md` 중간 단계 별도 처리 4단 | **✅ A** |
| OQ-2 | 데스크탑 2-pane 미리보기 방식 | 라이브 자동 미리보기 (타이핑마다 갱신) | 토글 버튼으로 명시 미리보기 (기본 숨김) | 사이드 고정 + 토글 버튼으로 on/off 전환 | **✅ C** |
| OQ-3 | page.tsx 803줄 분리 전략 | 한 번에 큰 컴포넌트 3~4개로 즉시 split | 점진적 hooks-first 추출 (기존 파일 유지하며 부분 추출) | 새 폴더 `app/posts/new-v2/` 평행 개발 후 컷오버 | **✅ B** |
| OQ-4 | 모바일 wizard 단계 수 | 3단계: 타입 선택 → 내용(미디어+본문) → 발행 설정 | 4단계: 타입 선택 → 미디어 → 본문·태그 → 발행 설정 | 5단계: 타입 → 미디어 → 본문 → 상품 메타(product only) → 발행 설정 | **✅ A** (product type일 때만 4단계로 확장 — design 단계에서 분기 로직 명시) |

**확정된 결정이 Design 단계에 미치는 영향:**

- **OQ-1=A** → 데스크탑 2-pane은 Tailwind `md:grid-cols-[1fr_1fr]` 또는 `md:flex` 패턴, `< 768px`에서는 wizard. Sidebar의 분기 방식과 일관
- **OQ-2=C** → 사이드 미리보기 컨테이너 항상 마운트, `isPreviewVisible` state로 표시/숨김 토글. 숨김 시 `display:none` 또는 width 0 처리하여 데이터는 유지
- **OQ-3=B** → Do 단계: ① hooks 먼저 추출(`useDraftAutosave`는 이미 분리됨, 신규로 `usePostFormState`, `usePostMediaState`, `useArtistGate`, `useScheduleState` 등 검토) → ② JSX 영역을 `EditorWorkspace`/`PreviewPane`/`EditorMobileWizard`로 점진 이동 → ③ 매 추출 후 회귀 체크리스트 5개(autosave/draft/multi-tab/role-gating/PostTypeSelector) 즉시 검증
- **OQ-4=A** → 모바일 wizard 기본 3단계. `type === "product"` 분기 시 상품 메타 단계가 추가될 수 있으나, **#7 `editor-product-meta` PDCA에서 합치기로 확정**. 본 PDCA에서는 product 모바일 step에 메타 필드를 인라인 표시(현행 구조 유지)하거나 임시 4단계로 노출 — design 단계에서 결정

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | 뷰포트 너비 ≥ 768px(OQ-1 A 채택 시) Chrome에서 `/posts/new` 접속 → 좌측 편집 폼 + 우측 미리보기 2-pane이 나란히 표시된다 | 브라우저 DevTools Responsive → 768px 이상 수동 확인 |
| AC-2 | 뷰포트 너비 < 768px(모바일 시뮬레이터, iPhone 13 기준) → 단계형 wizard UI가 풀스크린으로 표시되고, 단계 인디케이터가 상단에 보인다 | DevTools 모바일 에뮬레이터 수동 확인 |
| AC-3 | 모바일 wizard에서 step 이동(앞/뒤) 시 이전 step에서 입력한 데이터가 유지된다 (예: 타입 선택 후 내용 입력 → 뒤로 → 앞으로 → 내용 보존) | 수동 테스트 |
| AC-4 | 데스크탑 2-pane에서 제목/내용 입력 시 미리보기 pane이 갱신된다 (OQ-2 C 채택 시: 미리보기 토글 on 상태에서) | 수동 테스트 |
| AC-5 | autosave 인디케이터("저장됨 · N초 전")가 데스크탑 2-pane 상단과 모바일 wizard 모든 step 상단에서 가시 상태 | 수동 확인 (각 step 진입 후 2초 대기) |
| AC-6 | role-gating — 비작가 사용자가 모바일 wizard 타입 선택 step에서 "상품 포스트" 탭을 선택할 수 없다 (PostTypeSelector 동작 보존) | 비작가 계정으로 수동 테스트 |
| AC-7 | 5 locale(ko/en/ja/zh/es) 전환 시 2-pane·wizard 모든 레이아웃에서 텍스트 잘림·줄바꿈 깨짐 없음 — 특히 일본어·중국어 긴 라벨 검증 | 각 locale 전환 후 전체 화면 수동 확인 |
| AC-8 | `prefers-reduced-motion: reduce` OS 설정 시 wizard step 전환 애니메이션이 비활성화된다 | macOS 손쉬운 사용 → 모션 줄이기 on 후 확인 |
| AC-9 | DraftRestoreDialog — 임시저장 데이터 있을 때 `/posts/new` 진입 시 복원 다이얼로그가 데스크탑·모바일 양쪽에서 표시된다 | 수동 테스트 (임시저장 후 재진입) |
| AC-10 | 멀티탭 경고 — 같은 사용자가 두 탭에서 `/posts/new`를 열면 경고 토스트가 모바일·데스크탑 양쪽에서 표시된다 | 멀티탭 수동 테스트 |

---

## 6. Risks & Mitigations

| ID | 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|----|--------|--------|-------------|-----------|
| R-1 | **803줄 page.tsx 분해 중 회귀 발생** — autosave, DraftRestoreDialog, currentDraftId, 멀티탭 경고, PostTypeSelector 5개 통합 지점이 컴포넌트 경계에서 끊어질 위험 | High | High | OQ-3 B(점진적 hooks-first) 채택 시 회귀 최소화. Do 단계에서 추출마다 AC-5~AC-10 즉시 검증 후 다음 추출 진행. 전체 분해 전 기능 동작 스냅샷(수동 테스트 체크리스트) 사전 작성 |
| R-2 | **모바일 wizard와 데스크탑 폼의 상태 동기화** — 동일 page에서 두 레이아웃이 공유하는 formState 관리 복잡도 | Medium | Medium | 단일 formState를 page(또는 최상위 컨테이너)에서 소유 후 props drilling. Context 도입 시 기존 useState 패턴과 혼용 위험 → Context 도입은 OQ-3 결정 후 design 단계에서 명시 |
| R-3 | **i18n 긴 라벨 깨짐** — 일본어·중국어 번체 라벨이 2-pane 미리보기 헤더나 wizard step 탭에서 넘칠 수 있음 | Medium | Medium | Design 단계에서 최장 라벨(일본어/중국어) 기준 레이아웃 설계. `truncate` / `min-w-0` 방어 클래스 사전 적용 |
| R-4 | **모바일 미디어 업로더 UX** — 현재 MediaToolbar / MediaPreviewList가 모바일 wizard 특정 step에 맞게 조정될 때 기존 업로드 흐름이 깨질 수 있음 | Medium | Low | MediaToolbar·MediaPreviewList 수정 최소화. wizard에서 해당 컴포넌트를 그대로 래핑. 깊은 수정은 #4 `editor-media-ux`로 이월 |
| R-5 | **AppShell + Sidebar 레이아웃과 2-pane 충돌** — root layout이 `<AppShell>`을 사용하며 Sidebar가 왼쪽에 고정됨. 2-pane이 전체 너비를 요구할 경우 충돌 | Medium | Medium | design 단계에서 layout.tsx → AppShell → Sidebar → main 계층 분석. 2-pane을 `main` 영역 내부에서만 구성하여 AppShell 수정 최소화 |

---

## 7. Architecture Considerations

### 7.1 Project Level

Dynamic 유지 (변경 없음) — 기존 App Router + feature-based 구조 그대로.

### 7.2 핵심 설계 방향

| 결정 사항 | 선택 | 근거 |
|-----------|------|------|
| 반응형 구현 방식 | Tailwind responsive utility (`md:`, `lg:`) 우선 | CSS-in-JS 도입 없음. 기존 Tailwind 컨벤션 유지 |
| 상태 관리 | 기존 `useState` 유지, top-level 소유 후 props 전달 | Redux/Zustand/Context 신규 도입 없음. OQ-3와 연결 |
| UI 컴포넌트 | shadcn/ui Tabs, Progress 등 기존 설치 컴포넌트 우선 재사용 | 신규 라이브러리 설치 최소화 |
| 신규 컴포넌트 위치 | `v1/frontend/src/components/post-editor/` — PostTypeSelector 옆 | 기존 post-editor 디렉토리 컨벤션 유지 |
| 애니메이션 | Tailwind transition utility + `prefers-reduced-motion` CSS 조건 | framer-motion 도입 없음 |

### 7.3 예상 신규 컴포넌트 후보 (Design 단계에서 확정)

```
v1/frontend/src/components/post-editor/
  ├── PostTypeSelector.tsx          (기존 — 유지)
  ├── EditorWorkspace.tsx           (신규 후보 — 편집 폼 컨테이너)
  ├── PreviewPane.tsx               (신규 후보 — 미리보기 pane)
  ├── EditorMobileWizard.tsx        (신규 후보 — 모바일 step 컨테이너)
  ├── WizardStepIndicator.tsx       (신규 후보 — 진행률 인디케이터)
  └── EditorLayout.tsx              (신규 후보 — 데스크탑/모바일 분기 최상위)
```

정확한 컴포넌트 명칭·분해 경계는 Design 단계에서 확정. 위는 Plan 단계 후보.

---

## 8. Convention Prerequisites

### 8.1 기존 컨벤션 유지 사항

| 컨벤션 | 현재 상태 | 이 PDCA에서 적용 방식 |
|--------|-----------|----------------------|
| Tailwind class 사용 | 전체 프런트엔드 Tailwind 전용 | 신규 레이아웃도 Tailwind 전용. CSS module / 인라인 스타일 도입 없음 |
| App Router 파일 구조 | `app/` 디렉토리 기반 | 신규 파일 추가 시 동일 구조 준수 |
| i18n 키 패턴 | `t("namespace.key")` 형식 | 신규 i18n 키 prefix: `post.editor.*` — 기존 `post.draft.*` 키와 충돌 없이 병존 |
| 컴포넌트 `"use client"` 지시문 | 클라이언트 컴포넌트에 명시 | 신규 컴포넌트 동일 적용 |
| TypeScript strict | `tsconfig.json` 기준 | 신규 컴포넌트 타입 누락 없음 |

### 8.2 신규 환경 변수

없음 — 이 PDCA는 DB·API 변경 없는 순수 프런트엔드 개편.

### 8.3 신규 i18n 키 범위

- prefix: `post.editor.*` (예: `post.editor.preview`, `post.editor.nextStep`, `post.editor.stepIndicator` 등)
- 기존 `post.draft.*` 키는 건드리지 않음
- 5 locale 파일 동시 갱신 필수: `ko.json`, `en.json`, `ja.json`, `zh.json`, `es.json`

---

## 9. Phased Delivery / Implementation Order

OQ 결정 후 확정. 아래는 OQ-3 B(점진적 hooks-first) 채택 가정 예시:

| Step | 내용 | 완료 기준 |
|------|------|-----------|
| 1 | breakpoint·grid 결정 (OQ-1, 2 해소) → Design 문서 작성 | Design 승인 |
| 2 | 데스크탑 2-pane 골격 — EditorLayout + PreviewPane 신규, page.tsx 내 2-pane 렌더 추가 | AC-1, AC-4 통과 |
| 3 | 모바일 wizard 골격 — EditorMobileWizard + WizardStepIndicator + step state machine | AC-2, AC-3, AC-8 통과 |
| 4 | 기존 page.tsx 점진 분해 — EditorWorkspace 추출 + 기존 기능 이관 | AC-5, AC-6, AC-9, AC-10 통과 |
| 5 | 5 locale i18n 갱신 | AC-7 통과 |
| 6 | 회귀 검증 — autosave / draft restore / 멀티탭 / role-gating 4개 시나리오 전체 | 모든 AC 통과 |

---

## 10. Next Steps

1. **OQ-1 ~ OQ-4 사용자 확인** — 한 번에 답변 가능 (권장 default: A, C, B, B)
2. OQ 해소 후 `/pdca design editor-responsive-redesign` — `bkit:frontend-architect` agent 위임 권장
   - 2-pane vs wizard 구조 설계, breakpoint utility 정의, 컴포넌트 tree 확정
3. 부모 로드맵 §9 D-2 결정에 따라 본 sub-PDCA 진입 (Critical Path #3)
4. Design → Do → Check → Act → Report → Archive 표준 사이클

---

## 11. Estimated Effort

| Phase | 작업 | 예상 시간 |
|-------|------|-----------|
| Plan | 요구사항 정의 + OQ 해소 | 0.5d |
| Design | 컴포넌트 tree + breakpoint + 2-pane/wizard 구조 설계 | 1.0d |
| Do — 2-pane 골격 | EditorLayout, PreviewPane 구현 | 1.0d |
| Do — 모바일 wizard | EditorMobileWizard, WizardStepIndicator, step state machine | 1.5d |
| Do — page.tsx 분해 | 기존 기능 이관 (점진적) | 1.0d |
| Do — i18n | 5 locale 갱신 | 0.5d |
| Check | Gap analysis (gap-detector) | 0.3d |
| Act | 이터레이션 (필요 시) | 0~0.5d |
| Report + Archive | 완료 보고 + 아카이브 | 0.2d |
| **합계** | | **L (약 1주)** |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-30 | Initial draft | itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent) |
| 0.2 | 2026-04-30 | OQ 4개 모두 Resolved — 사용자가 권장 default 일괄 채택 (OQ-1 A / OQ-2 C / OQ-3 B / OQ-4 A). page.tsx 줄 수 803으로 정정. Design 단계 진입 준비 완료 | itpe-ince (Claude Opus 4.7) |
