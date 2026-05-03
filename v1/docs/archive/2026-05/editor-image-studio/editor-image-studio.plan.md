---
template: plan
version: 1.0
feature: editor-image-studio
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
parent_pdca: editor-media-studio (#6 split — OQ-6=B 사용자 결정)
---

# editor-image-studio Planning Document

> **Summary**: 포스트 에디터에 **이미지 에디터(회전·크롭·모자이크·워터마크)**를 도입한다. `POST /v1/media/{id}/transform` 엔드포인트(이미지 한정) + `media_assets.crop_meta jsonb` 컬럼(비파괴 편집 메타) + `SortableMediaCard` "편집" 버튼 진입점 + `ImageEditor` 모달 + Konva 라이브러리.
>
> **Status**: Draft v1.0
> **Sub-PDCA**: #6-image (Critical Path) — split from `editor-media-studio` per OQ-6=B
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)
> **Sister PDCA**: [editor-video-studio.plan.md](./editor-video-studio.plan.md) (영상 trim/썸네일 + 메이킹 모달, ffmpeg 인프라 결정 후 진입)

---

## 0. Split Decision (사용자 결정 2026-05-03)

**OQ-6 = B 채택**: 원래 `editor-media-studio` (XL 2주+, 7개 기능)을 두 PDCA로 분할:
- **본 PDCA `editor-image-studio` (M ~5-7일)** — 이미지 4기능, Pillow + Konva, **즉시 시작 가능** (외부 인프라 의존성 0)
- 자매 PDCA `editor-video-studio` (L ~7-10일) — 영상 trim/썸네일 + 메이킹 모달, **OQ-2 ffmpeg 인프라 결정 필요**

분할 근거:
- 이미지/영상 의존성이 완전히 다름 (Pillow vs ffmpeg). 한쪽 인프라 협의가 다른 쪽 작업을 차단하면 안 됨
- 사용자 검증 surface가 분리되어 회귀 위험 ↓
- 단일 14일 PDCA는 PDCA 사이클 자체의 효용성 떨어짐

---

## 1. Overview

### 1.1 What

| 영역 | 현재 | 목표 |
|------|------|------|
| 이미지 편집 | 없음 (업로드 후 raw 저장) | **회전 (90°/180°/270°), 크롭 (자유 + 1:1/4:3/16:9 preset), 모자이크 (드래그 영역), 워터마크 (텍스트 + 시그니처 이미지)** |
| 비파괴 편집 메타 | 없음 | `media_assets.crop_meta jsonb` — 편집 가역성 |
| 진입 UX | 없음 (업로드만) | `SortableMediaCard` "편집" 버튼 → `ImageEditor` 모달 |

영상·메이킹 모달은 본 PDCA scope 외 → `editor-video-studio` 후속.

### 1.2 Why (Roadmap §1.B-2 verbatim)

> **이미지 에디터**: 회전, 크롭, 모자이크, 워터마크

작가가 업로드한 이미지를 별도 도구 없이 플랫폼 내에서 편집 가능 → 작품 완성도 향상 + 작가 친화. 워터마크는 도용 방지(작가 시그니처) 목적.

### 1.3 Background

**기존 인프라 (재사용 가능)**:
- [v1/backend/app/services/media_processing.py](../../../backend/app/services/media_processing.py) — Pillow 기반 이미지 처리 (EXIF 제거 + 3 썸네일 + JPEG quality=85). **본 PDCA에서 transform 함수 추가 확장**
- [v1/backend/app/services/storage/](../../../backend/app/services/storage/) — local/s3 어댑터 (변환 결과물 저장 위치)
- [v1/backend/app/api/media.py](../../../backend/app/api/media.py) `PATCH /v1/media/{id}` — #4에서 추가, 현재 caption만. **본 PDCA에서 transform 엔드포인트 추가**
- [SortableMediaCard.tsx](../../../frontend/src/components/post-editor/SortableMediaCard.tsx) — 카드 컴포넌트, "편집" 버튼 진입점 추가 위치
- [useDraftAutosave](../../../frontend/src/lib/hooks/useDraftAutosave.ts) — DraftState shape에 `crop_meta` 통합 검토

**신규 도입**:
- 이미지 편집 라이브러리 (OQ-1 — Konva 권장)
- `media_assets.crop_meta` jsonb 컬럼 + alembic 0037
- `POST /v1/media/{id}/transform` 엔드포인트 (이미지 한정 — 영상은 자매 PDCA에서 추가)

### 1.4 Related Documents

- 부모 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §1.B-2 + §2 row #6 + §4 row #6
- 자매 PDCA: [editor-video-studio.plan.md](./editor-video-studio.plan.md)
- #4 archive: [editor-media-ux/](../../archive/2026-05/editor-media-ux/) — `useMediaUploadQueue`/`MediaPreviewList`/`SortableMediaCard`/`PATCH /v1/media/{id}`/`_check_auction_media_lock` 패턴 재사용

---

## 2. Scope

### 2.1 In Scope

#### 이미지 에디터 (ImageEditor 모달)
- [ ] **회전**: 90°/180°/270° 버튼. 캔버스 즉시 반영
- [ ] **크롭**: 자유 비율 + preset(1:1, 4:3, 16:9, original). 모바일 touch 지원 (OQ-7=A)
- [ ] **모자이크**: 드래그로 영역 선택, 픽셀 크기 조정 (강도 10/20/40px)
- [ ] **워터마크**: 텍스트 입력 + 시그니처 이미지 (OQ-5=C). 위치 드래그 조정 (좌상/우상/좌하/우하/중앙 + 자유)
- [ ] **저장 / 취소**: "저장" → transform API 호출 → 카드 갱신 + draft autosave trigger. "취소" → 변경 무시 + 모달 닫음
- [ ] **재진입 시 이전 편집 상태 복원** (OQ-3=A 비파괴 채택 시): `crop_meta`에서 회복하여 모달 열 때 동일 상태 노출

#### 백엔드 (이미지 한정)
- [ ] **`media_assets.crop_meta jsonb` 컬럼** — alembic `0037_media_crop_meta.py` (additive, default NULL)
- [ ] **`POST /v1/media/{id}/transform` 엔드포인트** (이미지 한정) — 권한 검증(소유자 + auction lock OQ-8=C) → Pillow 처리 → 결과물 저장 → `MediaAsset.url`/`thumbnail_url`/`thumb_*_url`/`crop_meta` 갱신 → 응답
- [ ] **`media_processing.py` 확장**: `process_image_transform(image_bytes, ops)` 신규 함수 — 회전 + 크롭 + 모자이크 + 워터마크 처리. EXIF 재제거 + 썸네일 재생성
- [ ] **`MediaTransformRequest` schema**: ops 배열 정의 (rotate / crop / mosaic / watermark) + crop_meta 직렬화 형태
- [ ] **rate limit**: `media_transform` scope (5/min/user — 이미지 처리는 비싸므로 caption보다 엄격)
- [ ] **error codes**: `MEDIA_NOT_OWNER` (403), `MEDIA_NOT_FOUND` (404), `AUCTION_ACTIVE_MEDIA_LOCKED` (409, OQ-8=C), `MEDIA_TRANSFORM_FAILED` (500), `MEDIA_TRANSFORM_TOO_LARGE` (413, 이미지 ≥ 20MB 차단)
- [ ] **structured audit log**: `media.transform.applied` event — user_id/media_id/post_id/ops summary

#### 프런트엔드 (이미지 한정)
- [ ] **신규 의존성**: `konva` + `react-konva` (~50-60KB gzip 추정 — 측정 후 결정)
- [ ] **`ImageEditor.tsx` 모달** — Konva Stage + 4개 도구 패널(회전/크롭/모자이크/워터마크) + 저장/취소
- [ ] **`SortableMediaCard.tsx` 편집 버튼**: 이미지 타입 카드에만 표시 (`media.type === "image"`). 클릭 → ImageEditor 모달 오픈
- [ ] **`crop_meta` 클라이언트 통합**: `CreatePostMedia`에 `crop_meta?: CropMeta` 옵션 필드 추가. DraftState 자동 통합 (#4 caption 패턴과 동일)
- [ ] **`patchMediaTransform(id, ops)` API client** — `lib/api.ts` 신규 함수
- [ ] **i18n 5 locale `post.editor.media.studio.image.*` 신규 키** — 회전/크롭/모자이크/워터마크 라벨, 비율 preset, 저장/취소 버튼, transform error 메시지 등 ~15-20 키 × 5 locale
- [ ] **draft autosave 통합**: 모달에서 변경된 `crop_meta`가 즉시 저장되지 않고 "저장" 클릭 시에만 `formState.media`에 반영 (모달 cancel 시 변경 폐기) → autosave는 자동
- [ ] **a11y**: 모달 focus trap (Escape 닫음, Tab 순환), 키보드 회전 (R키 등 단축키 — OQ로 surface 가능), `prefers-reduced-motion` 시 transition 비활성

### 2.2 Out of Scope

| 항목 | 분리된 PDCA |
|------|-------------|
| 영상 trim, 썸네일 선택 | `editor-video-studio` (자매 PDCA) |
| 메이킹 영상 모달 | `editor-video-studio` |
| ffmpeg 인프라 결정 | `editor-video-studio` |
| 이미지 자동 보정 (Auto enhance/밝기/대비/채도) | 후속 PDCA |
| Instagram-style preset filter | 후속 |
| 다중 미디어 일괄 편집 | 후속 |
| AI 배경 제거 / 업스케일 | 후속 |
| GIF 편집 | 후속 (현재 GIF는 이미지로 처리되나 transform 시 Pillow가 첫 프레임만 처리할 가능성 — design에서 결정) |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | `media_assets.caption` 옆에 `crop_meta jsonb NULL` 컬럼 추가 (alembic 0037 additive) | High |
| FR-02 | `POST /v1/media/{id}/transform` 엔드포인트 — 이미지 transform 4종(rotate/crop/mosaic/watermark) | High |
| FR-03 | 권한: 소유자만 + active auction 시 차단 (OQ-8=C, `_check_auction_media_lock` 재사용) | High |
| FR-04 | `media_processing.py`에 `process_image_transform(bytes, ops)` 신규 함수 + 썸네일 재생성 | High |
| FR-05 | rate limit `media_transform` scope (5/min/user) | High |
| FR-06 | `ImageEditor` 모달 — Konva 기반, 4 도구 (회전/크롭/모자이크/워터마크) | High |
| FR-07 | `SortableMediaCard` 이미지 카드에 "편집" 버튼 (hover/focus 시 표시, mobile 항상) | High |
| FR-08 | `crop_meta` DraftState 자동 통합 (caption 패턴 동일) — autosave 회귀 0 | High |
| FR-09 | 워터마크 — 텍스트 + 시그니처 이미지 둘 다 (OQ-5=C). 위치 드래그 + 5 preset 위치 | Medium |
| FR-10 | 모자이크 — 픽셀 크기 3 단계(10/20/40px). 영역 자유 드래그 | Medium |
| FR-11 | 5 통합 지점 회귀 0 (autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) | High |
| FR-12 | 5 locale i18n `post.editor.media.studio.image.*` 누락 0 | High |
| FR-13 | 비파괴 편집(OQ-3=A) — `crop_meta`에서 모달 재진입 시 이전 상태 복원 | Medium |
| FR-14 | 모바일 touch 크롭/모자이크/워터마크 위치 조정 (OQ-7=A) | Medium |
| FR-15 | a11y — 모달 focus trap + Escape + Tab + `prefers-reduced-motion` | Medium |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| Performance | 이미지 ≤ 10MB transform < 3초 (Pillow). ≥ 20MB는 413 거부 |
| 회귀 | TS 0 에러, 5 통합 지점 + #4 미디어 흐름 동작 동일 |
| Bundle | Konva + react-konva 추가 < 80KB gzip (실측 후 결정) |
| Accessibility | WCAG AA — 모달 focus trap, ARIA, prefers-reduced-motion |
| Security | OWASP A01 — 소유자 검증. EXIF 재제거(GPS 등 메타 누설 방지) |

---

## 4. Open Questions — ✅ Resolved (2026-05-03, 사용자 권장 default 일괄 채택)

| OQ | 질문 | A | B | C | 결정 |
|----|------|---|---|---|:----:|
| OQ-1 | 이미지 편집 라이브러리 | `react-image-crop` | `Konva` + `react-konva` | `cropper.js` | **✅ B (Konva + react-konva)** |
| OQ-3 | 비파괴 vs 파괴적 편집 | `crop_meta jsonb` 보존 | 새 파일 생성 | — | **✅ A (crop_meta 보존)** |
| OQ-5 | 워터마크 소스 | 텍스트만 | 시그니처만 | 둘 다 | **✅ C (둘 다)** |
| OQ-7 | 모바일 지원 | 데스크탑+모바일 동시 | 데스크탑 우선 | — | **✅ A (모바일 동시)** |
| OQ-8 | transform API 권한 | 소유자만 | draft 상태만 | `_check_auction_media_lock` 동일 | **✅ C (auction lock 적용)** |
| OQ-9 | GIF transform | 첫 프레임만 정적 변환 | 편집 버튼 비활성 | 모든 프레임 | **✅ B (편집 비활성, 후속 PDCA)** |

자매 PDCA `editor-video-studio` OQ는 본 PDCA scope 외 — 별도 협의.

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 |
|----|------|------|
| AC-1 | 이미지 카드 "편집" 버튼 클릭 → ImageEditor 모달 오픈 | 수동 |
| AC-2 | 회전 90° → 캔버스 즉시 반영 → 저장 → 카드 썸네일 갱신 | 수동 |
| AC-3 | 크롭 자유 + 1:1 preset → 저장 → DB caption + crop_meta 갱신 + URL 새 파일 | curl + DB |
| AC-4 | 모자이크 영역 드래그 → 저장 → 픽셀 처리된 결과물 표시 | 수동 |
| AC-5 | 워터마크 텍스트 + 위치 드래그 → 저장 | 수동 |
| AC-6 | 워터마크 시그니처 이미지 (작가 프로필) → 저장 | 수동 |
| AC-7 | 모달 재진입 → crop_meta 기반 이전 상태 복원 (비파괴 OQ-3=A) | 수동 |
| AC-8 | active auction 미디어 transform → 409 AUCTION_ACTIVE_MEDIA_LOCKED | curl |
| AC-9 | 비소유자 transform → 403 MEDIA_NOT_OWNER | curl |
| AC-10 | 21MB 이미지 transform → 413 MEDIA_TRANSFORM_TOO_LARGE | curl |
| AC-11 | 5 locale 신규 키 모두 표시 | 수동 |
| AC-12 | 5 통합 지점 회귀 0 | 수동 체크리스트 |
| AC-13 | 모바일 touch 크롭/모자이크 동작 | 실기기/DevTools |
| AC-14 | TypeScript 0 에러, ruff 0 에러 (alembic 제외) | CI |
| AC-15 | 모달 focus trap + Escape + prefers-reduced-motion | 수동 |

---

## 6. Risks

| Risk | Impact | 완화 |
|------|:---:|------|
| Konva + react-konva 번들 크기 (~50-60KB gzip 추정) | Medium | 측정 후 임계 80KB 이하 유지. dynamic import 검토 |
| `crop_meta` jsonb 스키마 진화 비용 | Medium | design에서 엄격 정의 (회전 도/크롭 4점/모자이크 영역 배열/워터마크 객체) + 버전 필드 |
| 큰 이미지(≥ 20MB) 메모리 폭증 | Medium | 413 차단 + 클라이언트 사전 필터 |
| 모바일 touch 크롭 UX 복잡도 | Medium | Konva 자체 지원. design에서 touch event 명세 |
| 5 통합 지점 회귀 — 특히 useDraftAutosave (DraftState에 crop_meta 추가) | High | `crop_meta?` optional + 기존 draft fallback (caption 패턴 재사용) |
| Pillow 워터마크 시그니처 이미지 합성 — 알파 채널/투명도 처리 | Low | design에서 RGBA 합성 패턴 명세 |
| EXIF 재제거 누락 (워터마크 추가 후 메타 잔존) | High | `process_image_transform` 끝에 `ImageOps.exif_transpose` + EXIF strip 명시 |

---

## 7. Architecture Considerations

### 7.1 Project Level
Dynamic 유지.

### 7.2 Key Decisions

| Decision | Selected | Rationale |
|----------|---------|-----------|
| 이미지 편집 라이브러리 | **Konva + react-konva** (OQ-1=B) | 4기능 단일 라이브러리. 캔버스 기반 모자이크/워터마크 자연 |
| 처리 위치 | **서버 Pillow** | 기존 `media_processing.py` 자연 확장. 클라이언트는 Konva canvas로 미리보기만 |
| 비파괴 메타 | **`crop_meta jsonb`** (OQ-3=A) | 편집 가역, 원본 보존, 추후 재편집 |
| 결과물 저장 | 신규 파일 생성 + 기존 `url`/`thumbnail_url`/`thumb_*_url` 갱신 | 원본은 별도 보존 (storage_key에 `_original` suffix 또는 별도 컬럼 — design 결정) |

### 7.3 신규 의존성
- `konva` (~40KB gzip 추정)
- `react-konva` (~10KB gzip 추정)
- 합산 ~50KB — 임계 80KB 이하

---

## 8. Convention Prerequisites

- 신규 컴포넌트 위치: `v1/frontend/src/components/post-editor/studio/ImageEditor.tsx` + 하위 도구 컴포넌트
- 신규 i18n prefix: `post.editor.media.studio.image.*`
- 신규 환경변수: 없음 (Pillow는 이미 설치됨)
- 신규 alembic: `0037_media_crop_meta.py`
- 신규 rate_limit scope: `media_transform`
- 신규 error codes: `MEDIA_TRANSFORM_FAILED`, `MEDIA_TRANSFORM_TOO_LARGE`

---

## 9. Phased Delivery

### Step 1 — Backend (M, ~2일)
1. alembic `0037_media_crop_meta.py` (additive)
2. `MediaAsset.crop_meta` 모델 + `MediaAssetIn.crop_meta?` schema
3. `MediaTransformRequest` schema (ops 배열) + `MediaTransformResponse`
4. `process_image_transform(image_bytes, ops)` 함수 (Pillow) + EXIF 재제거 + 썸네일 재생성
5. `POST /v1/media/{id}/transform` 엔드포인트 (권한 5단계 + auction lock + storage 저장)
6. `core/rate_limit.py` `media_transform` scope
7. error codes 4종
8. structured audit log

**Step 1 회귀 체크**: 기존 PATCH /v1/media/{id} (caption) 정상, 기존 POST /v1/media/upload 정상

### Step 2 — Frontend 기본 (M, ~2일)
1. `npm install konva react-konva`
2. `lib/api.ts` `MediaTransformRequest`/`patchMediaTransform()` API client
3. `CreatePostMedia.crop_meta?` + `DraftState` 자동 통합 (caption 패턴)
4. `SortableMediaCard.tsx` 이미지 카드에 "편집" 버튼
5. `ImageEditor.tsx` 모달 골격 + Konva Stage

**Step 2 회귀 체크**: 5 통합 지점 + 기존 caption/drag-reorder/upload 정상

### Step 3 — Frontend 도구 (L, ~3일)
1. 회전 도구 (단순)
2. 크롭 도구 + 비율 preset
3. 모자이크 도구 (드래그 영역 + 픽셀 강도)
4. 워터마크 도구 (텍스트 + 시그니처 이미지 + 위치 드래그)
5. 저장/취소 + 비파괴 재진입 복원

### Step 4 — i18n + 회귀 (S, ~1일)
1. 5 locale `post.editor.media.studio.image.*` 약 15-20 키 × 5 locale = 75-100 entries
2. 5 통합 지점 + 모바일 viewport + a11y 매뉴얼 검증

총 예상: **M~L (5-8일)**, OQ-6=B 분할 효과로 가시성 ↑

---

## 10. Next Steps

1. [ ] 본 plan + OQ 6개 사용자 결정
2. [ ] `/pdca design editor-image-studio` (`bkit:bkend-expert` + `bkit:frontend-architect` 병렬 위임)
3. [ ] design 후 `/pdca do` Step 1-4 순차

자매 PDCA `editor-video-studio`는 본 PDCA와 **독립 진행 가능** (의존성 0). ffmpeg 인프라 결정 시점에 시작.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-03 | Initial draft from `editor-media-studio` split (OQ-6=B 사용자 결정). 이미지 한정 — 회전/크롭/모자이크/워터마크 + Konva + Pillow + crop_meta jsonb + transform endpoint. OQ 6개 (영상 OQ-2/OQ-4는 자매 PDCA로 이동) | itpe-ince (Claude Opus 4.7) |
| 1.1 | 2026-05-03 | OQ 6개 모두 Resolved — 사용자 권장 default 일괄 채택 (B/A/C/A/C/B). Design 단계 진입 준비 완료 — bkit:bkend-expert + bkit:frontend-architect 병렬 위임 | itpe-ince (Claude Opus 4.7) |
