---
template: plan
version: 1.0
feature: upload-retry-ui
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
parent_pdca: editor-media-ux (#4, archived 2026-05-03)
---

# upload-retry-ui Planning Document

> **Summary**: editor-media-ux(#4)에서 carry-over된 후속 — 업로드 실패한 미디어 카드에 retry 버튼을 추가해 사용자가 카드 삭제 없이 재업로드 가능하게 한다. `useMediaUploadQueue`의 `error` 상태 task를 활용. `xhr.abort()`로 진행 중 업로드 취소도 함께 도입.
>
> **Status**: Draft (carry-over from #4 R-FE-7 / Design §F-9.4)
> **Sub-PDCA**: Carry-over (not in original 11-feature roadmap)

---

## 1. Overview

### 1.1 Purpose

PDCA #4(editor-media-ux)에서 의도적 scope 외로 분류된 항목 — 업로드 실패 카드에 **retry 버튼**과 **진행 중 업로드 취소(cancel) 버튼**을 추가. 현재 사용자는 실패 카드를 삭제 후 다시 업로드해야 하며 진행 중 업로드를 멈출 수단이 없음.

### 1.2 Background

- 부모 PDCA #4의 R-FE-7 명시: "사용자는 실패 카드 삭제 후 재업로드"
- `useMediaUploadQueue`는 이미 task `error` 상태 + `result` 보존 로직을 가지고 있어 retry 도입 비용 낮음
- XHR 기반 `uploadMediaFileWithProgress`는 `xhr.abort()` 패턴으로 cancel 도입 가능 (현재 `AbortController` 미통합)
- `MediaUploadProgress`의 "{n}개 실패" 메시지는 이미 표시됨

### 1.3 Related Documents

- 부모 #4 archive: [v1/docs/archive/2026-05/editor-media-ux/](../../archive/2026-05/editor-media-ux/)
- Design §F-9.4 (retry scope 외 명시) + R-FE-7 (cosmetic 위험)

---

## 2. Scope

### 2.1 In Scope

- `useMediaUploadQueue` API 확장: `retry(taskId)` + `cancel(taskId)` 메서드
- `uploadMediaFileWithProgress`에 `signal?: AbortSignal` 파라미터 추가 (또는 별도 `XMLHttpRequest` 핸들 반환 패턴)
- `SortableMediaCard` error overlay에 **retry 버튼** + 진행 중 카드에 **cancel 버튼**
- `MediaUploadProgress`에 "{n}개 실패 — 모두 재시도" 일괄 retry 액션 (선택)
- i18n 5 locale 신규 키 (`media.retry.button`, `media.cancel.button`, `media.retry.aria`, `media.cancel.aria` 등 ~6키)

### 2.2 Out of Scope

- 자동 retry (실패 시 N초 후 자동 재시도) — 별도 검토
- 부분 chunk upload / resumable upload (S3 multipart 등)
- 발행 후 미디어 교체 (edit replace)
- 업로드 큐 영구 저장 (앱 종료 후 복원)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|:---:|
| FR-01 | error 상태 카드에 retry 버튼 표시 | High |
| FR-02 | retry 클릭 → 동일 file로 재업로드 (queue task 새로 생성 또는 status 'queued'로 reset) | High |
| FR-03 | uploading 상태 카드에 cancel(✕) 버튼 표시 + 클릭 시 `xhr.abort()` | High |
| FR-04 | cancel된 task는 큐에서 제거 (state 'cancelled' 별도 도입 검토) | Medium |
| FR-05 | MediaUploadProgress에 "{n}개 실패" 옆에 "모두 재시도" 일괄 액션 (실패 ≥ 2건일 때만) | Medium |
| FR-06 | 5 locale i18n 신규 키 누락 0 | High |
| FR-07 | 5 통합 지점 회귀 0 (autosave/DraftRestoreDialog/멀티탭/role-gating/useArtistGate) | High |

### 3.2 Non-Functional Requirements

| Category | Criteria |
|----------|----------|
| 회귀 | TypeScript 0 에러, 기존 업로드 흐름(성공) 동작 동일 |
| Accessibility | retry/cancel 버튼에 `aria-label` 명시, 키보드 포커스 가능 |
| UX | retry 후 progress overlay 정상 갱신 (0% → real %) |

---

## 4. Open Questions (사용자 확정 필요)

| ID | 질문 | A | B | 권장 default |
|----|------|---|---|:---:|
| OQ-1 | retry 시 task 처리 방식 | 동일 task `id` 유지하고 `status: 'queued'` reset | 새 `id`로 task 추가하고 기존은 큐에서 제거 | **A** (id 유지로 SortableContext 식별자 안정) |
| OQ-2 | cancel된 task UI 처리 | 큐에서 즉시 제거 (카드 사라짐) | `status: 'cancelled'`로 잔류, dismiss 버튼 | **A** (단순) |
| OQ-3 | 일괄 retry (FR-05) 도입 여부 | 도입 (실패 ≥ 2건일 때) | 미도입 (개별만) | **A** (저비용 + UX 개선) |
| OQ-4 | XHR 취소 패턴 | `AbortController` + `signal` (modern) | `xhr.abort()` 직접 핸들 노출 | **B** (XHR과 자연스러움, AbortController는 fetch 전용 패턴) |

---

## 5. Acceptance Criteria

| ID | 기준 | 검증 |
|----|------|------|
| AC-1 | error 카드 retry 버튼 클릭 → 동일 파일 재업로드 → 성공 | 수동 (Network throttle로 의도적 fail 유도) |
| AC-2 | uploading 카드 cancel(✕) 클릭 → 즉시 progress 중단 + 카드 제거 | 수동 |
| AC-3 | 5 locale 신규 키 모두 표시 (ko/en/ja/zh/es) | 수동 |
| AC-4 | 5 통합 지점 회귀 0 | 수동 체크리스트 |
| AC-5 | TypeScript 0 에러 | CI |
| AC-6 | retry 실패 시도가 무한 루프 안 됨 (기본 3회 한도 또는 사용자 명시 제어) | 수동 |
| AC-7 | accessibility — Tab/Enter로 retry/cancel 버튼 동작 | 수동 |

---

## 6. Risks

| Risk | Impact | 완화 |
|------|:---:|------|
| `xhr.abort()` 호출 시 fastapi 서버 측 부분 업로드 데이터 처리 | Medium | abort 후 서버에서 incomplete file 자동 GC 또는 재시도 시 idempotent 처리 검증 |
| retry 무한 루프 (network 영구 오류) | Medium | 기본 3회 한도 또는 사용자 명시 retry only (자동 retry 미도입) |
| 동일 task id로 retry 시 SortableContext 혼란 | Low | OQ-1=A 권장 — id 유지 + status reset |
| 5 통합 지점 회귀 | High | 본 PDCA는 hook + 카드 컴포넌트 변경만, page.tsx 비변경 |

---

## 7. Architecture Considerations

- 기존 `useMediaUploadQueue` API 확장 (메서드 2개 추가) — 외부 사용자 회귀 0
- `uploadMediaFileWithProgress`에 abort handle 노출 옵션 추가
- 컴포넌트: `SortableMediaCard` 내부 button 추가 (위치 — error overlay 안 또는 카드 하단)

---

## 8. Phased Delivery

### Phase 1 — hook 확장 (XS, ~1 시간)
- `useMediaUploadQueue.retry(taskId)` + `cancel(taskId)` 메서드
- `uploadMediaFileWithProgress`에 abort handle 옵션
- TypeScript 검증

### Phase 2 — UI (S, ~2 시간)
- `SortableMediaCard` retry 버튼 (error overlay) + cancel 버튼 (uploading)
- `MediaUploadProgress` 일괄 retry (OQ-3=A 시)
- 5 locale i18n 신규 키 6개

### Phase 3 — 회귀 검증 (XS, ~30 분)
- 5 통합 지점 체크
- 5 locale 전환
- a11y 키보드

총 예상: **~3.5 시간, S** 규모

---

## 9. Next Steps

1. [ ] 본 plan 사용자 승인
2. [ ] OQ 4개 결정
3. [ ] design 단계 생략 가능 (S 규모 + #4 패턴 명확) → `/pdca do upload-retry-ui` 직접 진입
4. [ ] Phase 1-3 순차 진행
5. [ ] `/pdca analyze` → ≥ 90% 시 report → archive

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-03 | Initial draft from #4 R-FE-7 carry-over (사용자 명시). 사용자 결정: retry 버튼 + cancel 버튼 도입. 4 OQ + 7 FR + 7 AC 명세 | itpe-ince (Claude Opus 4.7) |
