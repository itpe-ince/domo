---
template: plan
version: 1.2
feature: editor-media-ux
sub-pdca: "#4"
date: 2026-05-01
author: itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent)
project: domo
project_version: v1
status: Draft
parent_roadmap: editor-revamp-roadmap
kind: sub-pdca
size: M (3-4일)
---

# editor-media-ux Planning Document

> **Summary**: `MediaPreviewList`에 드래그 순서 변경(dnd-kit)·파일별 업로드 진행률·이미지 캡션 입력을 추가하고, 백엔드에 `media_assets.caption` 컬럼 + `PATCH /v1/media/{id}` 엔드포인트를 도입한다. #1-#3에서 확립한 5개 통합 지점 회귀 0을 유지하면서 Phase 2 미디어 UX 인프라 기반을 구축한다.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-01
> **Sub-PDCA**: #4 (Critical Path: #1 ✅ → #2 ✅ → #3 ✅ → **#4 ⏭️** → #6 → #8 → #10)
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)
> **Status**: Draft

---

## 1. Overview

### 1.1 무엇을 (What)

현재 [`v1/frontend/src/components/post-editor/MediaPreviewList.tsx`](../../../frontend/src/components/post-editor/MediaPreviewList.tsx)(70줄)는 단순 3-열 그리드 + 삭제 버튼 조합이다. 이 컴포넌트를 다음 세 방향으로 확장한다:

1. **드래그 순서 변경** (`@dnd-kit/core` + `@dnd-kit/sortable`): 미디어 카드를 드래그로 재배열. 데스크탑 마우스 + 모바일 터치 양쪽 지원 (dnd-kit 기본 제공).
2. **파일별 업로드 진행률**: 다중 파일 선택 시 각 파일의 업로드 상태(대기/업로드 중/완료/실패)를 카드 위에 표시. 현재 `handleFiles`의 `for...of` 순차 업로드를 병렬 업로드로 전환.
3. **이미지 캡션**: 각 미디어 카드 아래 캡션 텍스트 입력. 클라이언트 상태 + DraftState에 저장, 발행 시 `POST /v1/posts` body의 `media[].caption`으로 전달 → 백엔드가 `media_assets.caption` 컬럼에 저장.

백엔드에서는 `media_assets` 테이블에 `caption text NULL` 컬럼을 추가하는 Alembic 마이그레이션(`0036_media_caption.py`)과 `PATCH /v1/media/{id}` 엔드포인트를 신규 도입한다.

### 1.2 왜 (Why)

부모 로드맵 §1.B-1, §1.B-2 요구사항 원본:

> **B-1 (입력 흐름)**: "미디어 순서 조절 드래그로 변경 가능해야 함", "여러 파일 업로드 시 각 파일별 진행률 표시 필요"
>
> **B-2 (콘텐츠 풍부도)**: "이미지에 캡션/설명 등록 가능해야 함 — 갤러리 카탈로그 스타일"

### 1.3 배경 (Background)

**현재 `MediaPreviewList`의 한계:**

| 기능 | 현재 상태 | 이 PDCA 후 |
|------|----------|-----------|
| 드래그 순서 변경 | 없음 | dnd-kit 기반 drag-to-reorder |
| 업로드 진행률 표시 | 전체 "업로드 중..." 텍스트만 (`uploading` boolean 1개) | 파일별 progress (대기/업로드 중/완료/실패) |
| 캡션 입력 | 없음 | 카드 아래 inline textarea |
| 업로드 방식 | `for...of` 순차 (`handleFiles` in `page.tsx`) | 병렬 (`Promise.all` + 개별 진행률 추적) |

**선행 PDCA 완료 상태 (#3 아카이브 확인):**

| PDCA | 상태 | 이 PDCA와의 관련 |
|------|------|----------------|
| #1 `editor-role-gating` | 완료 (아카이브) | `PostTypeSelector` — 건드리지 않음 |
| #2 `editor-draft-autosave` | 완료 (아카이브) | `DraftState` shape 변경 — caption 추가 시 회귀 검토 필수 |
| #3 `editor-responsive-redesign` | 완료 (아카이브, Match Rate 96%) | `MediaPreviewList`를 `EditorStepContent` + `EditorWorkspace` 양쪽에서 호출. 이번에 `MediaPreviewList` 대폭 변경 — 양쪽 호출부에 신규 props 추가 필요 |

**이전 PDCA들이 frontend-only였던 것과 달리, 본 PDCA는 backend 변경을 포함한다** (DB 마이그레이션 + 신규 API 엔드포인트). 검증 비용이 더 크므로 gap-detector 활용 권장.

**`CreatePostMedia` 현재 shape** ([`v1/frontend/src/lib/api.ts:1119`](../../../frontend/src/lib/api.ts)):

```typescript
export type CreatePostMedia = {
  type: "image" | "video" | "external_embed";
  url: string;
  thumbnail_url?: string | null;
  width?: number;
  height?: number;
  duration_sec?: number;
  size_bytes?: number;
  external_source?: string | null;
  external_id?: string | null;
  is_making_video?: boolean;
  // 이 PDCA에서 추가 예정 →
  // caption?: string;
};
```

**`DraftState` 현재 shape** ([`v1/frontend/src/lib/hooks/useDraftAutosave.ts:32`](../../../frontend/src/lib/hooks/useDraftAutosave.ts)):

```typescript
export type DraftState = {
  ...
  media: CreatePostMedia[];  // caption 추가 시 연쇄적으로 변경됨
  ...
};
```

**alembic 최신 마이그레이션**: `0035_draft_limit_index` (2026-04-30 완료). 다음 번호는 `0036_media_caption` 후보.

**`PATCH /v1/media/{id}` 현재 상태**: [`v1/backend/app/api/media.py`](../../../backend/app/api/media.py)에 PATCH 엔드포인트 없음. POST `/upload`, POST `/presign`, POST `/finalize`, POST `/external`, GET `/oembed`, GET `/files/{key}` 6개만 존재.

**`MediaAsset` 모델 현재 shape** ([`v1/backend/app/models/post.py:72`](../../../backend/app/models/post.py)):

```python
class MediaAsset(Base):
    __tablename__ = "media_assets"
    # ... 기존 컬럼 ...
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_making_video: Mapped[bool] = mapped_column(Boolean, default=False)
    # caption 컬럼 없음 — 이 PDCA에서 추가
```

### 1.4 관련 문서

| 구분 | 경로 | 설명 |
|------|------|------|
| 부모 로드맵 | [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) | §1.B-1, §1.B-2, §4 row #4 |
| 선행 PDCA #3 아카이브 | [archive/2026-05/editor-responsive-redesign/](../../archive/2026-05/editor-responsive-redesign/) | 5개 통합 지점 보존 패턴, 컴포넌트 tree |
| MediaPreviewList | [frontend/.../MediaPreviewList.tsx](../../../frontend/src/components/post-editor/MediaPreviewList.tsx) | 현재 70줄 — 이번 PDCA 주요 변경 대상 |
| MediaToolbar | [frontend/.../MediaToolbar.tsx](../../../frontend/src/components/post-editor/MediaToolbar.tsx) | 파일 선택 진입점 — `onImageSelect` prop |
| EditorWorkspace | [frontend/.../EditorWorkspace.tsx](../../../frontend/src/components/post-editor/EditorWorkspace.tsx) | `MediaPreviewList` 호출부 (데스크탑) |
| EditorStepContent | [frontend/.../wizard/EditorStepContent.tsx](../../../frontend/src/components/post-editor/wizard/EditorStepContent.tsx) | `MediaPreviewList` 호출부 (모바일 wizard) |
| useDraftAutosave | [frontend/.../useDraftAutosave.ts](../../../frontend/src/lib/hooks/useDraftAutosave.ts) | `DraftState` shape — caption 추가 시 검토 |
| api.ts | [frontend/src/lib/api.ts](../../../frontend/src/lib/api.ts) | `CreatePostMedia`, `uploadMediaFile` |
| MediaAsset 모델 | [backend/app/models/post.py](../../../backend/app/models/post.py) | caption 컬럼 추가 위치 (line 72-108) |
| media.py API | [backend/app/api/media.py](../../../backend/app/api/media.py) | PATCH 엔드포인트 추가 위치 |
| posts.py API | [backend/app/api/posts.py](../../../backend/app/api/posts.py) | MediaAsset 생성 시 caption pass-through (line 245-261) |
| schemas/post.py | [backend/app/schemas/post.py](../../../backend/app/schemas/post.py) | `MediaAssetIn`, `MediaAssetOut` — caption 노출 |
| package.json | [frontend/package.json](../../../frontend/package.json) | 현재 외부 라이브러리 0 — dnd-kit 추가 예정 |

---

## 2. Scope

### 2.1 In Scope (포함)

#### 백엔드 변경

- [x] **Alembic 마이그레이션**: `media_assets.caption text NULL` 컬럼 추가 (`0036_media_caption.py`)
- [x] **`MediaAsset` 모델** (`post.py`): `caption: Mapped[str | None]` 필드 추가
- [x] **`MediaAssetIn` schema** (`schemas/post.py`): `caption: str | None = None` 필드 추가
- [x] **`MediaAssetOut` schema** (`schemas/post.py`): `caption` 필드 노출 (클라이언트가 기존 미디어 caption 복원 가능)
- [x] **`posts.py` 생성 로직** (line 245-261): `MediaAsset` 생성 시 `caption=m.caption` pass-through
- [x] **`PATCH /v1/media/{id}` 엔드포인트** (`media.py`): 인증 사용자 본인 미디어의 caption 업데이트. 권한 정책(본인 소유 검증, 발행 후 수정 여부)은 OQ-6에서 결정

#### 프런트엔드 — 의존성

- [x] **`@dnd-kit/core` + `@dnd-kit/sortable`** 신규 설치: `package.json` `dependencies`에 추가. 현재 외부 라이브러리 0 프로젝트에서 첫 번째 React 전용 외부 라이브러리 도입 (trade-off §7 참조)

#### 프런트엔드 — 타입 및 상태

- [x] **`CreatePostMedia` 타입** (`api.ts`): `caption?: string` 옵션 필드 추가
- [x] **`DraftState` shape** (`useDraftAutosave.ts`): `media: CreatePostMedia[]`를 통해 caption 자동 포함 (direct 필드 변경 없음, `CreatePostMedia` 업데이트 연쇄). 기존 draft 안전 fallback 검증 필수
- [x] **`useMediaUploadQueue` hook** (신규): 다중 업로드 동시성 + 파일별 progress 상태 관리. 현재 `page.tsx`의 `handleFiles` `for...of` 순차 업로드를 이 hook으로 교체

#### 프런트엔드 — 컴포넌트

- [x] **`SortableMediaCard` 컴포넌트** (신규, `post-editor/`): dnd-kit `useSortable` hook 기반 개별 미디어 카드. drag handle + 미디어 프리뷰 + 삭제 버튼 + caption textarea + 파일별 progress overlay 포함
- [x] **`MediaUploadProgress` 컴포넌트** (신규, `post-editor/`): 다중 업로드 전체 상태를 요약 표시하는 배지형 UI (예: "3/5 업로드 완료"). 툴바 근처 또는 카드 상단에 배치 — 위치는 OQ-7에서 결정
- [x] **`MediaPreviewList` 재작성**: dnd-kit `DndContext` + `SortableContext` 래퍼로 교체. 기존 `grid grid-cols-3` 그리드는 `SortableMediaCard` 목록으로 전환. 신규 props `onReorder`, `onCaptionChange` 추가

#### 프런트엔드 — 호출부 갱신

- [x] **`EditorWorkspace.tsx`**: `MediaPreviewList` 신규 props(`onReorder`, `onCaptionChange`) 추가, `useMediaUploadQueue` hook 통합
- [x] **`EditorStepContent.tsx`** (모바일 wizard step 2): 동일하게 신규 props 추가 — dnd-kit이 모바일 터치 drag 지원하므로 추가 구현 없음

#### 프런트엔드 — i18n

- [x] **5 locale** (`ko/en/ja/zh/es`) `post.editor.media.*` prefix 신규 블록 추가:
  - `post.editor.media.caption.placeholder` — 캡션 입력 placeholder
  - `post.editor.media.dragHandle.aria` — drag handle aria-label
  - `post.editor.media.uploading.progress` — "N/M 업로드 중" 형식
  - `post.editor.media.upload.done` — 업로드 완료
  - `post.editor.media.upload.failed` — 업로드 실패
  - `post.editor.media.reorder.aria` — reorder 안내 aria
  - 추가 키는 design 단계에서 확정

### 2.2 Out of Scope (제외 — 별도 sub-PDCA)

| 항목 | 이유 / 해당 PDCA |
|------|-----------------|
| 미디어 crop, filter, 회전, 워터마크 | #6 `editor-media-studio` |
| 영상 메이킹 모달 (MakingVideoModal) | #6 `editor-media-studio` |
| 외부 임베드(oEmbed) 캡션 | 본 PDCA는 `image`/`video` type에만 caption 적용. `external_embed` 캡션은 후속 결정 필요 |
| 캡션의 마크다운 / 리치텍스트 서식 | 평문(plain text)만. 서식은 #5 `editor-rich-content` |
| 백엔드 `order_index` 일괄 업데이트 API | 프런트는 클라이언트 state 배열 순서를 신뢰. 발행 시 `POST /v1/posts` body의 `media[]` 순서대로 저장 (`order_index=idx` 기존 패턴 유지). 별도 PATCH 엔드포인트 불필요 |
| 캡션 마이그레이션 (기존 발행 포스트의 미디어) | 신규 업로드 미디어에만 적용. 기존 미디어는 `caption=null` 유지 |
| GIF 특수 처리 / 애니메이션 프리뷰 | 현행 MediaToolbar GIF 업로드 흐름 유지, 변경 없음 |
| 동영상 썸네일 선택 / 트리밍 | #6 `editor-media-studio` |

---

## 3. Requirements

### 3.1 Functional Requirements (기능 요구사항)

| ID | 요구사항 | 우선순위 | MoSCoW |
|----|----------|:--------:|--------|
| FR-01 | `media_assets.caption text NULL` 컬럼을 Alembic 마이그레이션(`0036_media_caption.py`)으로 추가. 기존 행은 `caption=NULL` | High | Must |
| FR-02 | `POST /v1/posts` 발행 시 `media[].caption` 값이 `MediaAsset.caption` 컬럼에 저장 (`posts.py` pass-through) | High | Must |
| FR-03 | `MediaAssetOut` schema에 `caption: str | None` 노출 — 클라이언트가 기존 미디어 caption 복원 가능 | High | Must |
| FR-04 | `PATCH /v1/media/{id}` 엔드포인트 신규: 인증된 소유자가 해당 미디어의 caption 업데이트 가능 | Medium | Should |
| FR-05 | `CreatePostMedia` 타입에 `caption?: string` 추가, `DraftState` 연쇄 갱신. 기존 localStorage draft에 caption 없는 경우 `caption: undefined` 안전 fallback | High | Must |
| FR-06 | `MediaPreviewList` 재작성: dnd-kit 기반 drag-to-reorder. 데스크탑 마우스 + 모바일 터치 양쪽 동작 | High | Must |
| FR-07 | 각 미디어 카드 아래 캡션 inline textarea 제공. OQ-1 결정에 따라 위치 확정 | High | Must |
| FR-08 | 다중 업로드 시 파일별 진행률 표시 (대기/업로드 중 N%/완료/실패). `useMediaUploadQueue` hook으로 병렬 업로드 전환 | High | Must |
| FR-09 | 5 통합 지점 회귀 0 보장: useDraftAutosave / DraftRestoreDialog / 멀티탭 경고 / PostTypeSelector / useArtistGate — 데스크탑·모바일 wizard 양쪽 | High | Must |
| FR-10 | 5 locale (`ko/en/ja/zh/es`) `post.editor.media.*` 키 누락 0, 기존 `post.editor.*` 키 깨짐 0 | High | Must |
| FR-11 | `@dnd-kit/core` + `@dnd-kit/sortable` `package.json` `dependencies`에 추가 | High | Must |
| FR-12 | reorder 후 순서가 `CreatePostMedia[]` 배열에 즉시 반영되어 draft 자동저장(debounce 2s) + 발행 payload에 포함 | High | Must |

### 3.2 Non-Functional Requirements (비기능 요구사항)

| ID | 카테고리 | 기준 | 측정 방법 |
|----|----------|------|-----------|
| NFR-1 | 성능 | 모바일 drag 제스처 응답 지연 체감 없음 (dnd-kit 내부 최적화 기반) — 정확한 ms 기준은 design 단계에서 정의 | 실기기 수동 테스트 |
| NFR-2 | 접근성 | drag handle에 `aria-grabbed`, `aria-roledescription="sortable"` 적용. 키보드로 Space 후 화살표 키 reorder 지원 (dnd-kit KeyboardSensor) | Axe DevTools + 키보드 수동 테스트 |
| NFR-3 | 접근성 | `prefers-reduced-motion: reduce` 시 dnd-kit drag 트랜지션 애니메이션 비활성 (dnd-kit의 `CSS.Transform` 트랜지션 조건부 제거) | OS 설정 토글 후 수동 확인 |
| NFR-4 | 회귀 | #1-#3 통합 지점 5개 회귀 0 — EditorWorkspace(데스크탑) + EditorStepContent(모바일 wizard) 양쪽에서 autosave/DraftRestoreDialog/멀티탭/PostTypeSelector/useArtistGate 전부 정상 동작 | 5개 시나리오 수동 체크리스트 |
| NFR-5 | 번들 | `@dnd-kit/core` + `@dnd-kit/sortable` 추가로 인한 번들 크기 증가 측정 — 허용 임계값은 design 단계에서 결정 | `next build` 출력 또는 `bundle-analyzer` |
| NFR-6 | 호환성 | React 18.3.x + Next.js 15.0.3 환경에서 dnd-kit 정상 동작 확인 (dnd-kit v6 기준 React 16+ 지원 공식 문서 확인) | 로컬 빌드 + 개발 서버 동작 확인 |
| NFR-7 | draft 안전성 | 기존 localStorage draft(caption 없는 구버전 `DraftState`)에서 복원 시 caption `undefined` fallback — 에러 없이 안전하게 동작 | 구버전 draft 수동 시뮬레이션 |

---

## 4. Open Questions — ✅ Resolved (2026-05-01, 사용자 권장 default 일괄 채택)

| OQ | 질문 | A | B | C | 결정 |
|----|------|---|---|---|:---:|
| OQ-1 | 캡션 입력 위치 | 각 미디어 카드 **아래 inline textarea** (항상 노출) | 카드 클릭 시 **모달** | 카드 hover 시 **floating input** | **✅ A** |
| OQ-2 | 다중 업로드 동시성 | 현행 `for...of` 순차 유지 | **병렬** `Promise.all` (전체 동시) | **청크** 병렬 (예: 3개씩) | **✅ B** |
| OQ-3 | 캡션 자동저장 시점 | **draft에만 포함** (debounce 2s — 서버 trip 최소화) / 발행 시에만 서버에 전송 | 입력마다 즉시 `PATCH /media/{id}` 호출 | 발행 시에만 일괄 | **✅ A** |
| OQ-4 | drag handle 디자인 | **dots-grip 아이콘** 카드 좌측 상단 (명시적) | 카드 전체 `grab` cursor + long-press | hover-only handle (시각적 힌트 없음) | **✅ A** |
| OQ-5 | 캡션 글자수 제한 | 제한 없음 | **280자** | 500자 | **✅ B** |
| OQ-6 | `PATCH /v1/media/{id}` 권한 정책 | **발행된 미디어도 소유자라면 caption 수정 가능** | 발행 후 수정 불가 (draft 미디어만) | design 단계로 이월 | **✅ A (단, 사용자 추가 우려: auction/product 진행 중 정책 — design 단계에서 OQ-D로 추가 검토 의무)** |
| OQ-7 | `MediaUploadProgress` 위치 | **MediaToolbar 위/아래** 고정 배지 | MediaPreviewList 상단 배너 | 별도 컴포넌트 없이 각 카드에만 표시 | **✅ A** |

**확정 결정이 design 단계에 미치는 영향**:
- OQ-1=A → `SortableMediaCard` 구조에 caption textarea가 항상 마운트. 모바일에서도 동일 UX
- OQ-2=B → `useMediaUploadQueue`는 `Promise.all`로 동시 업로드, 파일별 progress state는 Map 기반
- OQ-3=A → `DraftState`에 `media[i].caption` 포함하여 기존 autosave 흐름에 자연 통합. `PATCH /media/{id}`는 발행 후 편집 전용
- OQ-4=A → dnd-kit `PointerSensor` + `TouchSensor` 조합. `<DragHandleIcon>` 좌측 상단
- OQ-5=B → 280자 클라이언트 + 서버 검증. 백엔드 `MediaAsset.caption` 컬럼은 Text 타입이지만 schema 검증으로 280자 제한
- **OQ-6=A (조건부)** → design 단계에서 **추가 OQ-D-N**로 surface: "auction 진행 중인 product 미디어를 작가가 caption 수정하면 입찰자에게 어떤 신호를 줄 것인가? 알림? 수정 잠금?"
- OQ-7=A → `MediaUploadProgress`는 `MediaToolbar` 직후 mount

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | `media_assets` 테이블에 `caption text NULL` 컬럼이 존재하고, 기존 행은 `NULL` 유지 | `psql \d media_assets` 확인 |
| AC-2 | 이미지/영상 파일 업로드 후 caption textarea에 텍스트 입력 → 발행 → `SELECT caption FROM media_assets WHERE post_id = ?` 결과에 해당 텍스트 저장 확인 | DB 직접 조회 또는 API 응답 확인 |
| AC-3 | 미디어 3개 업로드 후 drag로 순서 변경 → 발행 → 반환된 `media[]` 배열의 `order_index`가 drag 결과와 일치 | API 응답 + 수동 테스트 |
| AC-4 | 데스크탑 마우스 drag-to-reorder 정상 동작 + 모바일 touch drag-to-reorder 정상 동작 (dnd-kit PointerSensor + TouchSensor 양쪽) | 데스크탑 Chrome + 모바일 에뮬레이터 또는 실기기 |
| AC-5 | 파일 3개 동시 선택 → 각 카드에 업로드 진행 상태(업로드 중 / 완료 / 실패) 개별 표시 | 수동 테스트 (Network throttle 3G 설정) |
| AC-6 | caption 텍스트 입력 후 2초 경과 → localStorage draft 갱신(caption 포함) → 페이지 이탈 후 재진입 → DraftRestoreDialog → 복원 시 caption 보존 | 수동 테스트 (DraftRestoreDialog 흐름) |
| AC-7 | 기존 caption 없는 localStorage draft 복원 시 에러 없이 `caption: undefined` fallback 정상 동작 | 구버전 draft JSON 수동 주입 후 복원 |
| AC-8 | 5 locale(ko/en/ja/zh/es) 전환 시 `post.editor.media.*` 키 누락 0, 기존 `post.editor.*` 키 동작 이상 0 | 각 locale 전환 후 UI 확인 |
| AC-9 | **5 통합 지점 회귀 0**: autosave 인디케이터 가시 / DraftRestoreDialog 진입 시 동작 / 멀티탭 경고 / PostTypeSelector role-gating / useArtistGate — 데스크탑 2-pane + 모바일 wizard 양쪽 | 5개 시나리오 수동 체크리스트 (#3 기준 동일) |
| AC-10 | `prefers-reduced-motion: reduce` 시 drag 트랜지션 애니메이션 비활성 | macOS 손쉬운 사용 → 모션 줄이기 on 후 확인 |

---

## 6. Risks & Mitigations

| ID | 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|----|--------|:------:|:-----------:|-----------|
| R-1 | **`DraftState` shape 변경으로 기존 localStorage draft 호환성 깨짐** — `caption` 없는 구버전 draft 복원 시 TypeScript 타입 오류 또는 UI 에러 | High | Medium | `CreatePostMedia`에 `caption?: string` 옵션 필드 추가 (required 아님). `loadLocalDraft()`에서 caption 없는 경우 `undefined` fallback 명시. AC-7로 검증 |
| R-2 | **dnd-kit 도입 — React 18 + Next.js 15 호환성 미검증** — 현재 `package.json`에 외부 React 라이브러리 0. dnd-kit v6는 React 16+ 공식 지원이나 Next.js 15 App Router + `"use client"` 환경에서 SSR hydration mismatch 가능성 | Medium | Low | do 단계 초기에 최소 샘플(카드 1개 drag) 실행 확인 후 본격 구현. SSR 비활성화 필요 시 `dynamic(() => import(...), { ssr: false })` 패턴 적용 |
| R-3 | **모바일 wizard `EditorStepContent` 컨테이너 scroll과 dnd-kit drag 충돌** — wizard step 내부가 스크롤 컨테이너인 경우 터치 drag와 scroll 제스처 충돌 가능 | Medium | Medium | dnd-kit `restrictToParentElement` modifier 적용. `TouchSensor`의 `activationConstraint: { delay: 150 }` 설정으로 스크롤과 구분. design 단계에서 확정 |
| R-4 | **`PATCH /v1/media/{id}` 권한 누락** — 소유자 외 사용자가 타인의 미디어 caption 수정 가능 | High | Low | 엔드포인트에서 `media_asset.post.author_id == current_user.id` 검증 필수. 발행 후 정책은 OQ-6 결정 준수 |
| R-5 | **다중 업로드 병렬화 시 서버 부하 / S3 동시 연결 한도** — `Promise.all`로 전체 동시 업로드 시 파일 수 많을 경우 429(Too Many Requests) 가능 | Low | Low | 현재 `rate_limit("media_upload")` 적용 중 (`media.py`). OQ-2에서 청크(C) 선택 시 리스크 완화. MVP에서는 일반적으로 파일 수 적음 — 설계 이슈 아님 |
| R-6 | **`EditorWorkspace` + `EditorStepContent` 양쪽에 신규 props 추가 시 props drilling 복잡도 증가** — 이미 `EditorWorkspace`는 40+ props | Medium | Medium | `onReorder`, `onCaptionChange` 2개만 추가. 타입 안전성 유지. Context 도입은 #3 설계 원칙(Context 신규 도입 없음) 준수 — 필요 시 design 단계에서 재논의 |
| R-7 | **5 통합 지점 회귀** — `MediaPreviewList` 대폭 변경으로 `EditorStepContent` + `EditorWorkspace` 양쪽 호출 패턴 변경 필요. 이 과정에서 autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate 연결 끊길 위험 | High | Medium | Step-by-Step 구현 순서(§9) 준수. 각 step 완료 후 5개 통합 지점 체크리스트 즉시 실행 후 다음 step 진행 |

---

## 7. Architecture Considerations

### 7.1 Project Level

Dynamic 유지 (변경 없음) — App Router + feature-based 구조 유지.

### 7.2 핵심 설계 방향

| 결정 사항 | 선택 | 근거 |
|-----------|------|------|
| 외부 라이브러리 도입 | `@dnd-kit/core` + `@dnd-kit/sortable` 도입 | custom DnD 구현 대비 trade-off: dnd-kit = 번들 ~30KB gzipped vs 커스텀 = 터치 지원·접근성·키보드 reorder 구현 비용 대폭 증가. #3 "외부 라이브러리 0" 원칙과의 trade-off이나 이 규모의 기능에서 라이브러리 도입이 타당하다고 판단 |
| 미디어 순서 상태 모델 | `CreatePostMedia[]` 배열 순서가 곧 미디어 순서. dnd-kit `arrayMove`로 reorder | 별도 `order_index` 클라이언트 상태 불필요. 발행 시 `media[0], media[1]...` 순서가 `order_index 0, 1...`로 저장 (기존 `posts.py:259` 패턴 유지) |
| 캡션 데이터 흐름 | 클라이언트 state → `CreatePostMedia.caption` → `DraftState.media[].caption` → `DraftPayload.media[].caption` → `POST /v1/posts` → `MediaAsset.caption` 저장 | 중간 단계마다 optional field. 발행 후 수정은 `PATCH /v1/media/{id}` (OQ-6 결정 후) |
| 기존 page.tsx `handleFiles` | `useMediaUploadQueue` hook으로 추출 이전 | 현재 `page.tsx`에 inline 업로드 로직 있음. hook 추출로 `EditorWorkspace` + `EditorStepContent` 양쪽에서 동일 hook 사용 가능 |
| dnd-kit SSR 처리 | `"use client"` 컴포넌트에서만 사용 — App Router 기본 제약 준수 | `MediaPreviewList` 이미 `"use client"` — 추가 처리 최소 |

### 7.3 예상 신규 컴포넌트 후보 (Design 단계에서 확정)

```
v1/frontend/src/components/post-editor/
  ├── MediaPreviewList.tsx           (기존 70줄 → 재작성 — dnd-kit DndContext + SortableContext 래퍼)
  ├── SortableMediaCard.tsx          (신규 — 개별 미디어 카드: drag handle + preview + caption + progress)
  └── MediaUploadProgress.tsx        (신규 — 전체 업로드 요약 배지)

v1/frontend/src/lib/hooks/
  └── useMediaUploadQueue.ts         (신규 — 파일별 progress 상태 + 병렬 업로드 로직)
```

### 7.4 백엔드 변경 범위

```
v1/backend/
  ├── alembic/versions/
  │   └── 0036_media_caption.py      (신규 — caption text NULL 컬럼 추가)
  ├── app/models/post.py             (MediaAsset: caption 필드 추가)
  ├── app/schemas/post.py            (MediaAssetIn/Out: caption 필드 추가)
  ├── app/api/posts.py               (line 245-261: caption pass-through)
  └── app/api/media.py               (PATCH /v1/media/{id} 신규 추가)
```

---

## 8. Convention Prerequisites

### 8.1 기존 컨벤션 유지 사항

| 컨벤션 | 현재 상태 | 이 PDCA에서 적용 방식 |
|--------|-----------|----------------------|
| Tailwind class 사용 | 전체 프런트엔드 Tailwind 전용 | 신규 컴포넌트도 Tailwind 전용. CSS module / 인라인 스타일 도입 없음 |
| `"use client"` 지시문 | 클라이언트 컴포넌트에 명시 | SortableMediaCard, MediaUploadProgress, 재작성된 MediaPreviewList 동일 적용 |
| TypeScript strict | `tsconfig.json` 기준 | caption 필드 모두 옵셔널(`?`) — 타입 누락 없음 |
| i18n 키 패턴 | `t("namespace.key")` 형식 | 신규 prefix: `post.editor.media.*` — 기존 `post.editor.*` 키와 충돌 없이 병존 |
| 신규 컴포넌트 위치 | `post-editor/` 디렉토리 | `SortableMediaCard`, `MediaUploadProgress` → `post-editor/` |
| 신규 hook 위치 | `lib/hooks/` 디렉토리 | `useMediaUploadQueue` → `lib/hooks/` |

### 8.2 신규 의존성

| 패키지 | 용도 | 추가 위치 |
|--------|------|-----------|
| `@dnd-kit/core` | DnD 핵심 컨텍스트 + 센서 | `package.json` `dependencies` |
| `@dnd-kit/sortable` | `useSortable` hook + `SortableContext` | `package.json` `dependencies` |

버전은 최신 안정 버전으로 고정 (design 단계에서 정확한 버전 명시).

### 8.3 신규 환경 변수

없음 — 백엔드 변경은 기존 DB 연결 + 인증 미들웨어 그대로 사용.

### 8.4 신규 i18n 키 범위

- prefix: `post.editor.media.*` (기존 `post.editor.preview.*`, `post.editor.wizard.*` 키와 충돌 없음)
- 정확한 키 목록은 design 단계에서 확정. 예상 후보: `caption.placeholder`, `dragHandle.aria`, `uploading.progress`, `upload.done`, `upload.failed`, `reorder.aria`
- 5 locale 파일 동시 갱신 필수: `ko.json`, `en.json`, `ja.json`, `zh.json`, `es.json`

---

## 9. Phased Delivery / Implementation Order

OQ 결정 후 확정. 아래는 OQ 권장 default(OQ-1=A, OQ-2=B, OQ-3=A, OQ-4=A, OQ-5=B, OQ-6=A, OQ-7=A) 채택 가정 예시:

| Step | 내용 | 완료 기준 |
|------|------|-----------|
| **1 (Backend — DB)** | Alembic 마이그레이션 `0036_media_caption.py` 작성 + 실행. `MediaAsset` 모델 `caption` 필드 추가. `MediaAssetIn`/`MediaAssetOut` schema 갱신. `posts.py` caption pass-through 추가. smoke test | `media_assets` 테이블에 caption 컬럼 존재, 기존 행 NULL 유지 확인 |
| **2 (Backend — API)** | `PATCH /v1/media/{id}` 엔드포인트 구현 (media.py). 소유자 검증 + caption 업데이트. OQ-6 결정 반영 | 소유자 PATCH 성공, 비소유자 403 확인 |
| **3 (Frontend — 타입 + 상태)** | `CreatePostMedia`에 `caption?` 추가 (`api.ts`). `DraftState` 연쇄 갱신 (CreatePostMedia 통해 자동 반영). 기존 draft 안전 fallback 검증 (AC-7). `DraftPayload` 연쇄 확인 | TypeScript 빌드 오류 0, 기존 draft 복원 정상 |
| **4 (Frontend — hook)** | `useMediaUploadQueue.ts` 신규 작성: 파일별 progress 상태(`idle/uploading/done/failed`) + `Promise.all` 병렬 업로드. page.tsx `handleFiles` 교체 | 파일 3개 동시 업로드 → 각 progress 상태 독립 추적 |
| **5 (Frontend — 컴포넌트)** | `SortableMediaCard.tsx` 신규 작성 (dnd-kit `useSortable`, drag handle, caption textarea, progress overlay). `MediaPreviewList.tsx` 재작성 (DndContext + SortableContext). `MediaUploadProgress.tsx` 신규 | dnd-kit drag-reorder 데스크탑 동작 |
| **6 (Frontend — 호출부)** | `EditorWorkspace.tsx` 신규 props(`onReorder`, `onCaptionChange`) 추가. `EditorStepContent.tsx` 동일. 5 통합 지점 즉시 검증 | AC-9 (5 통합 지점 회귀 0) 통과 |
| **7 (Frontend — i18n)** | 5 locale `post.editor.media.*` 신규 블록 추가 | AC-8 통과 (5 locale 누락 0) |
| **8 (QA)** | AC-1~AC-10 전체 체크. 데스크탑 + 모바일 wizard 양쪽. `prefers-reduced-motion` 확인 | 모든 AC Pass |

---

## 10. Next Steps

1. **OQ-1~OQ-7 사용자 확인** — 한 번에 답변 가능 (권장 default: A, B, A, A, B, A, A)
2. OQ 해소 후 `/pdca design editor-media-ux` — `bkit:bkend-expert` (DB/API) + `bkit:frontend-architect` (컴포넌트/dnd-kit 설계) 병렬 위임 권장
3. Design → Do → Check (gap-detector) → Act → Report → Archive 표준 사이클

---

## 11. Estimated Effort

| Phase | 작업 | 예상 시간 |
|-------|------|-----------|
| Plan | 요구사항 정의 + OQ 해소 | 0.5d |
| Design | DB 스키마 + API spec + 컴포넌트 tree + dnd-kit 설계 | 1.0d |
| Do — Step 1-2 (Backend) | 마이그레이션 + PATCH 엔드포인트 | 0.5d |
| Do — Step 3-4 (Frontend 타입/hook) | 타입 갱신 + useMediaUploadQueue | 0.5d |
| Do — Step 5-6 (Frontend 컴포넌트/호출부) | SortableMediaCard + MediaPreviewList 재작성 + 호출부 | 1.0d |
| Do — Step 7 (i18n) | 5 locale 갱신 | 0.3d |
| Check | Gap analysis (gap-detector) | 0.3d |
| Act | 이터레이션 (필요 시) | 0~0.5d |
| Report + Archive | 완료 보고 + 아카이브 | 0.2d |
| **합계** | | **M (약 3-4일)** |

---

## 12. Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-01 | 초기 draft. 소스 문서 (#3 보고서, 로드맵, 현재 코드) 검토 후 작성. backend + frontend 양쪽 변경 범위 확정. OQ 7개 권장 default 포함. | itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent) |
| 0.2 | 2026-05-01 | OQ 7개 모두 Resolved — 사용자 권장 default 일괄 채택 (A/B/A/A/B/A/A). OQ-6은 사용자 추가 우려 반영하여 design 단계에서 auction/product 진행 중 caption 수정 정책을 OQ-D-N로 surface 의무. Design 단계 진입 준비 완료 | itpe-ince (Claude Opus 4.7) |
