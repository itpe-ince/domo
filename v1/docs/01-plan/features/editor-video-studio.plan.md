---
template: plan
version: 1.0
feature: editor-video-studio
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
parent_pdca: editor-media-studio (#6 split — OQ-6=B 사용자 결정)
---

# editor-video-studio Planning Document

> **Summary**: 포스트 에디터에 **영상 에디터(trim·썸네일 선택)**와 **메이킹 영상 전용 모달(`MakingVideoModal`)**을 도입한다. `POST /v1/media/{id}/transform` 엔드포인트의 영상 분기 + ffmpeg 인프라 결정 + `media_assets.transform_meta jsonb` (또는 `editor-image-studio`에서 만든 `crop_meta` 확장) + `SortableMediaCard` 영상 카드 "편집" 버튼 + `is_making_video` 토글 → 모달 진입.
>
> **Status**: Draft v1.0
> **Sub-PDCA**: #6-video (Critical Path) — split from `editor-media-studio` per OQ-6=B
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)
> **Sister PDCA**: [editor-image-studio.plan.md](./editor-image-studio.plan.md) (이미지 편집, 즉시 시작 가능 — 본 PDCA와 독립)
> **Blocker**: **OQ-2 ffmpeg 인프라 결정 필요** — 사용자 결정 + 운영 영향 협의 후 design 진입 권장

---

## 0. Split Decision (사용자 결정 2026-05-03)

OQ-6 = B 채택으로 원래 `editor-media-studio`(XL 2주+, 7기능)를 두 PDCA로 분할:
- 자매 PDCA `editor-image-studio` (M ~5-8일) — Pillow + Konva, 즉시 시작
- **본 PDCA `editor-video-studio` (L ~7-10일)** — 영상 trim/썸네일 + 메이킹 모달, **OQ-2 ffmpeg 인프라 결정 필요**

본 PDCA는 자매 image PDCA와 **독립 진행 가능**. design 진입 시점은 OQ-2 결정 + 인프라 협의 완료 후.

---

## 1. Overview

### 1.1 What

| 영역 | 현재 | 목표 |
|------|------|------|
| 영상 편집 | 없음 (업로드 후 raw 저장, 처리 0) | **trim (start/end)**, **썸네일 프레임 선택** |
| 메이킹 영상 | `is_making_video` boolean 토글만 | 전용 **`MakingVideoModal`** — 영상 업로드 + 영상 에디터 통합 |
| 영상 처리 인프라 | 없음 (ffmpeg 미설치) | OQ-2 결정에 따라 클라이언트 ffmpeg.wasm / 서버 ffmpeg / 외부 서비스 |

이미지 편집은 본 PDCA scope 외 → 자매 `editor-image-studio` 참조.

### 1.2 Why (Roadmap §1.A + §1.B-2 verbatim)

> **A. 메이킹 영상 토글**:
> - 메이킹 영상 올리는 **별도 모달** 구성. 해당 모달을 통해 메이킹 영상 제작 및 편집
> - **사후 토글**을 선택하면, 메이킹 영상 제작 편집 모달이 열림
>
> **B-2 (영상 부분)**:
> - **영상 에디터**: 영상 잘라내기, 썸네일 선택

작가의 작품 제작 과정(메이킹 영상)은 도용 방지·진정성 증명에 핵심 가치. 별도 모달로 명확한 UX. 영상 trim은 업로드 후 불필요 부분(시작 자투리 등) 제거 + 첫 화면(썸네일)을 작가가 선택 가능하게 함.

### 1.3 Background

**기존 인프라**:
- [v1/backend/app/services/media_processing.py](../../../backend/app/services/media_processing.py) — **이미지 전용**. 영상 처리 전무
- [v1/backend/app/api/media.py](../../../backend/app/api/media.py) `upload_media()` — "Video: store raw" 분기에서 처리 0
- [v1/backend/app/services/storage/](../../../backend/app/services/storage/) — local/s3 어댑터 (변환 결과물 저장 위치)
- `MediaAsset.duration_sec` 컬럼 존재 (현재 일부만 채워짐)
- [SortableMediaCard.tsx](../../../frontend/src/components/post-editor/SortableMediaCard.tsx) — 영상 카드도 표시 (preview ▶ 아이콘). "편집" 버튼 진입점은 자매 PDCA(image)에서 추가될 예정 — 본 PDCA는 그 위에 영상 분기 추가
- `is_making_video` 컬럼 (`MediaAsset.is_making_video`, `MediaAssetIn.is_making_video`) — 이미 존재

**신규 도입**:
- ffmpeg 인프라 (OQ-2)
- `media_assets.transform_meta jsonb` 또는 `crop_meta` 확장 (자매 PDCA에서 만든 컬럼 재사용 가능)
- `MakingVideoModal.tsx` 컴포넌트
- `VideoEditor.tsx` 컴포넌트
- 영상 transform — `POST /v1/media/{id}/transform` 영상 분기

### 1.4 Related Documents

- 부모 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §1.A + §1.B-2 + §2 row #6
- 자매 PDCA: [editor-image-studio.plan.md](./editor-image-studio.plan.md) — `crop_meta` jsonb 컬럼 + transform endpoint 인프라 선행
- #4 archive: [editor-media-ux/](../../archive/2026-05/editor-media-ux/) — `useMediaUploadQueue`/`is_making_video` 패턴

---

## 2. Scope

### 2.1 In Scope

#### 영상 에디터 (VideoEditor 모달)
- [ ] **Trim (start/end)**: 영상 시작·끝 지점 설정. 타임라인 슬라이더 UI (이중 핸들 또는 양 끝 마커)
- [ ] **썸네일 프레임 선택**: 영상의 임의 시점에서 정지 화면 캡처 → 썸네일로 사용. 슬라이더에서 시점 선택 + "이 프레임을 썸네일로" 버튼

#### 메이킹 영상 모달 (MakingVideoModal)
- [ ] **진입점**: `is_making_video` 사후 토글 → 모달 자동 오픈 (roadmap §1.A 명시)
- [ ] **모달 내부**: 영상 업로드(새 업로드 또는 기존 영상 선택) + `VideoEditor` 통합 (OQ-4=A 권장)
- [ ] **`is_making_video=true` 자동 설정**: 모달 경유 업로드/선택 영상에 자동 부여. 기존 `POST /v1/media/upload`의 `is_making_video` form field 활용

#### 백엔드 (영상 한정)
- [ ] **영상 처리 인프라 — OQ-2 결정에 따라**:
  - **B (서버 ffmpeg, 권장)**: Docker 이미지에 `ffmpeg` 설치 + Celery/RQ 큐 도입 (OQ-V-1) + 동기 처리는 timeout 30s
  - A (클라이언트 ffmpeg.wasm): ~25MB 다운, 모바일 영향 큼 — 비추천
  - C (Cloudflare Stream 등): 외부 비용 + 월 사용량 모니터링 — 단순하지만 외부 의존
- [ ] **`POST /v1/media/{id}/transform` 엔드포인트 영상 분기** — 자매 PDCA(image)에서 만든 엔드포인트에 ops `trim` / `set_thumbnail` 추가
- [ ] **영상 transform 처리 함수**: `process_video_transform(media_id, ops)` — ffmpeg 호출 (OQ-2=B 시 subprocess 또는 ffmpeg-python). trim 후 새 파일 + 썸네일 추출 후 `thumbnail_url` 갱신
- [ ] **rate limit `media_transform_video` scope** (3/min/user — 영상은 더 비싸므로 image transform보다 엄격)
- [ ] **error codes**: `MEDIA_VIDEO_TRANSFORM_FAILED`, `MEDIA_VIDEO_TRANSFORM_TIMEOUT` (30s 초과), `MEDIA_VIDEO_TOO_LONG` (영상 길이 ≥ 5분 차단)
- [ ] **structured audit log**: `media.video.transform.applied`

#### 프런트엔드 (영상 한정)
- [ ] **`VideoEditor.tsx` 모달** — 타임라인 + 비디오 미리보기 + trim 핸들 + 썸네일 시점 선택
- [ ] **`MakingVideoModal.tsx` 모달** — 영상 업로드(`useMediaUploadQueue` 재사용) + `VideoEditor` 통합
- [ ] **`SortableMediaCard.tsx` 영상 카드 "편집" 버튼**: `media.type === "video"` 카드에 표시 → `VideoEditor` 모달 오픈
- [ ] **`is_making_video` 토글**: 카드에서 토글 → `MakingVideoModal` 자동 오픈 (체크박스 → 모달)
- [ ] **`MediaTransformRequest` 영상 ops 확장** — `{type: "trim", start_sec, end_sec}` / `{type: "set_thumbnail", at_sec}` 추가
- [ ] **i18n 5 locale `post.editor.media.studio.video.*` + `making.*`** — trim/썸네일/모달 라벨 약 15-20 키 × 5 locale
- [ ] **draft autosave 통합**: 영상 transform_meta가 `CreatePostMedia.transform_meta`로 직렬화 (caption 패턴 동일)

### 2.2 Out of Scope

| 항목 | 분리된 PDCA |
|------|-------------|
| 이미지 편집 (회전/크롭/모자이크/워터마크) | `editor-image-studio` (자매 PDCA) |
| 영상 중간 컷 편집 (여러 구간 cut) | 후속 PDCA — trim(start/end)만 |
| 컬러 그레이딩, 텍스트 오버레이 (영상) | 후속 |
| 음악/효과음 추가 | 후속 |
| 영상 회전/리사이즈 | 후속 |
| 영상 자동 transcode (HLS/DASH) | 후속 (현재는 mp4 raw 유지) |
| 4K/8K 영상 지원 | 후속 (현재 1080p 권장) |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | OQ-2 결정에 따라 ffmpeg 인프라 도입 (B 권장: 서버 ffmpeg + 동기 처리 timeout 30s) | High |
| FR-02 | `POST /v1/media/{id}/transform` 영상 분기 — `trim` / `set_thumbnail` ops | High |
| FR-03 | 권한: 소유자만 + active auction 차단 (자매 PDCA `_check_auction_media_lock` 재사용) | High |
| FR-04 | rate limit `media_transform_video` (3/min/user) | High |
| FR-05 | 영상 길이 ≥ 5분 또는 size ≥ 50MB 거부 | High |
| FR-06 | timeout 30s 초과 시 `MEDIA_VIDEO_TRANSFORM_TIMEOUT` 응답 | High |
| FR-07 | `VideoEditor` 모달 — 타임라인 + trim + 썸네일 시점 선택 | High |
| FR-08 | `MakingVideoModal` — `is_making_video` 토글 → 자동 오픈, 영상 업로드 + 영상 에디터 통합 | High |
| FR-09 | `SortableMediaCard` 영상 카드 "편집" 버튼 (자매 PDCA에서 만든 진입점에 영상 분기 추가) | High |
| FR-10 | 5 통합 지점 회귀 0 | High |
| FR-11 | 5 locale i18n 누락 0 | High |
| FR-12 | 모바일 영상 trim UX (touch 핸들 드래그) | Medium |
| FR-13 | a11y — 모달 focus trap + 키보드 trim 슬라이더 (Arrow keys) | Medium |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| Performance | 영상 ≤ 50MB / ≤ 5분 trim < 30초 (서버 ffmpeg). timeout 시 명시 응답 |
| 인프라 | OQ-2=B 시 Docker 이미지 +200MB 추정 (ffmpeg). 협의 필수 |
| 회귀 | TS 0 에러, 자매 image PDCA 인프라(crop_meta + transform endpoint) 동작 동일 |
| Bundle | 클라이언트 ffmpeg.wasm 미도입 (OQ-2=B 채택 시). HTML5 `<video>` 태그만 사용 |
| Accessibility | WCAG AA — 키보드 슬라이더, ARIA |

---

## 4. Open Questions (사용자 확정 필요)

본 PDCA에는 인프라 영향 큰 OQ가 우선. **OQ-2가 가장 중요** — 결정 전 design 진입 비추천.

| OQ | 질문 | A | B | C | D | 권장 default |
|----|------|---|---|---|---|:-:|
| **OQ-2 (최우선)** | **영상 처리 위치** | 클라이언트 `ffmpeg.wasm` (~25MB 다운) | **서버 `ffmpeg`** (Docker + 큐 인프라) | Cloudflare Stream 등 외부 서비스 | 영상 trim/썸네일 미지원 (UI 마커만) | **B (서버 ffmpeg)** — 자체 통제 + 비용 명확. 단 운영 협의 필수 |
| OQ-V-1 | OQ-2=B 채택 시 **처리 큐** | 동기 (FastAPI request 내 30s timeout) | Celery + Redis 큐 | RQ + Redis 큐 | — | A (MVP 단순, 30s 초과 시 거부). B/C는 후속 PDCA |
| OQ-4 | **메이킹 영상 모달 구조** | **`MakingVideoModal` 독립** (체크박스→모달) | 일반 영상 흐름과 동일, `is_making_video` 플래그만 | — | — | A (UX 명확 + roadmap §1.A 명시) |
| OQ-V-2 | **영상 길이/크기 제한** | 1분 / 20MB | **5분 / 50MB** | 10분 / 100MB | — | B (작가 메이킹 영상 평균 1-3분 가정) |
| OQ-V-3 | **trim 결과 저장 방식** | 새 파일 생성 + 기존 url 교체 | `transform_meta` jsonb 보존 (재생 시 클라이언트 trim — 비파괴) | — | — | A (서버 처리 결과물이라 새 파일이 자연. 비파괴는 이미지에만 적용) |
| OQ-V-4 | **썸네일 프레임 추출 방식** | 클라이언트 canvas 캡처 → 업로드 | 서버 ffmpeg `-ss` + `-vframes 1` | — | — | B (서버 일관, 화질 안정) |
| OQ-7 | **모바일 지원** | 데스크탑+모바일 동시 | 데스크탑 우선 | — | — | A (#3 responsive 정신) |
| OQ-8 | **transform API 권한** | 소유자만 | draft 상태만 | **`_check_auction_media_lock` 동일** | — | C (caption + image studio 정책 일관) |

> 이미지 OQ(라이브러리/비파괴 등)는 자매 PDCA에서 처리됨.

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 |
|----|------|------|
| AC-1 | 영상 카드 "편집" 버튼 → VideoEditor 모달 오픈 | 수동 |
| AC-2 | trim start/end 슬라이더 → 저장 → 새 영상 파일 + DB url 갱신 | curl + 다운로드 검증 |
| AC-3 | 썸네일 시점 선택 → 저장 → DB `thumbnail_url` 갱신 | curl + DB |
| AC-4 | `is_making_video` 토글 → MakingVideoModal 자동 오픈 | 수동 |
| AC-5 | 모달에서 영상 업로드 + trim → 저장 → `is_making_video=true` | 수동 + DB |
| AC-6 | active auction 영상 transform → 409 | curl |
| AC-7 | 비소유자 transform → 403 | curl |
| AC-8 | 51MB 영상 → 413 또는 검증 거부 | curl |
| AC-9 | 6분 영상 → 413 `MEDIA_VIDEO_TOO_LONG` | curl |
| AC-10 | 30초+ 처리 → 504 `MEDIA_VIDEO_TRANSFORM_TIMEOUT` | curl + ffmpeg slow input |
| AC-11 | 5 locale 신규 키 모두 표시 | 수동 |
| AC-12 | 5 통합 지점 회귀 0 | 수동 체크리스트 |
| AC-13 | 모바일 touch trim 핸들 동작 | 실기기 |
| AC-14 | TypeScript 0 에러 | CI |

---

## 6. Risks

| Risk | Impact | 완화 |
|------|:---:|------|
| **ffmpeg 인프라 운영 영향** (Docker 이미지 +200MB, 큐 추가 시 Redis 인프라) | High | OQ-2 결정 + 인프라 협의 design 단계 의무. MVP는 동기 처리(OQ-V-1=A) timeout 30s |
| 30초 timeout 부족 (긴 영상) | Medium | OQ-V-2=B(5분/50MB) 제한 + 향후 큐 도입 |
| 클라이언트 영상 미리보기 메모리 (HTML5 video) | Low | 브라우저 native — preload="metadata" |
| 메이킹 영상 모달과 일반 미디어 흐름 동기화 | Medium | OQ-4=A 독립 모달 — 흐름 분리. design에서 state 명세 |
| 5 통합 지점 회귀 (특히 useDraftAutosave — transform_meta가 DraftState 진입) | High | `transform_meta?` optional + 자매 PDCA의 crop_meta 패턴 재사용 |
| ffmpeg 보안 (악성 영상 입력 시 RCE 가능성) | High | 입력 size/길이 사전 검증 + 컨테이너 격리 + ffmpeg 최신 버전 + 신뢰할 수 있는 source mp4만 |
| 자매 PDCA(image)와 동일 `media_assets.crop_meta` 컬럼 사용 시 schema 충돌 | Medium | design에서 결정 — 단일 jsonb 컬럼 (image+video 모두 포함) vs 별도 컬럼 (`crop_meta` + `video_transform_meta`) |

---

## 7. Architecture Considerations

### 7.1 Project Level
Dynamic 유지.

### 7.2 Key Decisions

| Decision | Selected (권장) | Rationale |
|----------|---------|-----------|
| 영상 처리 위치 | **서버 ffmpeg** (OQ-2=B) | 자체 통제. 클라이언트 ffmpeg.wasm은 모바일 영향 큼 |
| 처리 큐 | **동기 처리 + 30s timeout** (OQ-V-1=A, MVP) | 단순. Celery/RQ는 후속 |
| trim 저장 | **새 파일 생성** (OQ-V-3=A) | 서버 처리 결과물 |
| 썸네일 추출 | **서버 ffmpeg `-ss` + `-vframes 1`** (OQ-V-4=B) | 화질 안정 |
| 메이킹 모달 | **독립 컴포넌트** (OQ-4=A) | UX 명확 |

### 7.3 인프라 영향

OQ-2=B 채택 시:
- **Docker 이미지**: `apt install ffmpeg` 또는 multi-stage build로 ~200MB 추가
- **메모리**: ffmpeg 처리 중 50MB 영상 → 약 200-300MB RAM 사용
- **CPU**: 컨테이너 CPU limit 협의 필요
- **배포 파이프라인**: 변경 없음 (Dockerfile만 수정)
- **운영 비용**: 미미 (자체 호스팅)

---

## 8. Convention Prerequisites

- 신규 컴포넌트 위치: `v1/frontend/src/components/post-editor/studio/{VideoEditor,MakingVideoModal}.tsx`
- 신규 i18n prefix: `post.editor.media.studio.video.*` + `post.editor.media.studio.making.*`
- 신규 환경변수: `FFMPEG_PATH=/usr/bin/ffmpeg` (or auto-detect), `MEDIA_VIDEO_TRANSFORM_TIMEOUT_SEC=30`, `MEDIA_VIDEO_MAX_DURATION_SEC=300`, `MEDIA_VIDEO_MAX_SIZE_MB=50`
- 신규 alembic: `0038_media_video_transform_meta.py` (또는 자매 PDCA의 0037에서 통합 jsonb 결정)
- 신규 rate_limit scope: `media_transform_video`
- 신규 error codes: 4종

---

## 9. Phased Delivery

### Step 1 — 인프라 협의 (의존성 — 사용자/운영 결정)
- OQ-2=B 채택 시 Dockerfile에 ffmpeg 설치 PR
- 환경변수 4개 추가 + `.env.example` 갱신
- ffmpeg-python 또는 subprocess 패턴 결정 (design)

### Step 2 — Backend (M, ~2-3일)
1. Dockerfile ffmpeg 설치 + 빌드 검증
2. `process_video_transform(media_id, ops)` 함수 (subprocess 또는 ffmpeg-python)
3. `MediaTransformRequest`에 영상 ops 추가 (`trim` / `set_thumbnail`)
4. transform 엔드포인트 영상 분기 (자매 PDCA에서 만든 endpoint 확장)
5. rate limit + error codes
6. 영상 길이/크기 사전 검증
7. structured audit log

**Step 2 회귀 체크**: 자매 PDCA 이미지 transform 정상

### Step 3 — Frontend VideoEditor (L, ~3일)
1. `VideoEditor.tsx` 모달 — 타임라인 + trim + 썸네일 시점
2. `SortableMediaCard.tsx` 영상 카드 "편집" 버튼 (자매 PDCA에서 만든 진입점에 영상 분기)
3. `lib/api.ts` `MediaTransformRequest` 영상 ops 추가
4. `CreatePostMedia.transform_meta?` (영상용) 또는 자매 PDCA의 crop_meta 확장 — design 결정

### Step 4 — Frontend MakingVideoModal (M, ~1.5일)
1. `MakingVideoModal.tsx` — `useMediaUploadQueue` 재사용 + `VideoEditor` 통합
2. `is_making_video` 토글 → 모달 자동 오픈 로직 (`SortableMediaCard` 또는 외부)

### Step 5 — i18n + 회귀 (S, ~1일)
1. 5 locale `post.editor.media.studio.video.*` + `making.*` (~30 키 × 5 locale)
2. 5 통합 지점 + 모바일 + a11y 매뉴얼

총 예상: **L (7-10일)** + 인프라 협의 시간

---

## 10. Next Steps

1. [ ] **OQ-2 사용자 결정 + ffmpeg 인프라 운영 협의** (가장 우선)
2. [ ] OQ-V-1~4 + OQ-7/OQ-8 결정
3. [ ] 자매 PDCA `editor-image-studio` 진행 상황 확인 — `crop_meta` 컬럼/transform endpoint 인프라 우선 도입 권장
4. [ ] `/pdca design editor-video-studio` (`bkit:bkend-expert` ffmpeg 인프라 + `bkit:frontend-architect` VideoEditor UX 병렬)
5. [ ] design 후 `/pdca do` Step 1-5

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-03 | Initial draft from `editor-media-studio` split (OQ-6=B 사용자 결정). 영상 trim/썸네일 + 메이킹 모달 + ffmpeg 인프라. OQ 8개 (OQ-2 영상 인프라 가장 중요). 자매 PDCA `editor-image-studio`와 독립 진행 가능 | itpe-ince (Claude Opus 4.7) |
