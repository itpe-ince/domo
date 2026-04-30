---
template: plan
version: 1.2
feature: editor-draft-autosave
date: 2026-04-30
author: itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent)
project: domo
project_version: v1
status: Approved (Plan) — Design 진입 가능
parent_roadmap: editor-revamp-roadmap
oq_resolved: 2026-04-30
---

# editor-draft-autosave Planning Document

> **Summary**: 글 작성 중 페이지 이탈 또는 새로고침으로 인한 입력 데이터 손실을 방지하는 자동 저장 및 임시저장 기능
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-04-30
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

신진 작가 사용자가 긴 글/작품 설명 작성 중 실수로 페이지를 이탈하거나 새로고침할 때 모든 입력 내용이 사라지는 문제를 해결한다. localStorage 기반 자동저장(오프라인 안전망)과 서버 Draft 저장(멀티 디바이스 동기화) 두 계층을 조합하여 작가 친화적인 작성 환경을 제공한다.

### 1.2 Background

현재 `/posts/new/page.tsx`는 474줄 단일 컴포넌트로 18개 폼 상태를 관리한다 (type, title, content, genre, tags, media, embeds, scheduledAt, locationName, locationLat, locationLng, isAuction, isBuyNow, buyNowPrice, dimensions, medium, year, isMakingVideo, applicationStatus 등). 현재 자동저장/복원 로직이 전혀 없어 아래 상황에서 모든 입력이 유실된다:

- 브라우저 새로고침 (가장 흔한 사고)
- 탭 실수 종료 또는 배터리 방전
- 모바일 → 데스크탑 전환 (다른 기기로 이어 쓰기 불가)
- 뒤로가기 버튼 또는 다른 링크 클릭

작가 사용자는 작품 설명, 제작 과정, 가격 근거 등 콘텐츠를 작성할 때 일반 SNS 포스트보다 훨씬 긴 시간을 투자한다. 입력 손실은 플랫폼 이탈 원인 중 가장 강력한 요인이다.

**Backend 선행 조사 결과 (2026-04-30):**

`Post.status` 컬럼이 이미 `'draft'` 값을 지원한다:

```python
# v1/backend/app/models/post.py:43-44
status: Mapped[str] = mapped_column(String(20), default="pending_review")
# 'draft' | 'pending_review' | 'published' | 'hidden' | 'deleted'
```

DB 마이그레이션 없이 draft 저장 로직 구현 가능. 단, Draft 전용 API 엔드포인트 신규 구현은 필요하다.

### 1.3 Related Documents

| 구분 | 경로 | 설명 |
|------|------|------|
| 부모 로드맵 | [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) | 전체 에디터 개편 11개 sub-PDCA 인덱스 |
| 선행 PDCA 아카이브 | [docs/archive/2026-04/editor-role-gating/](../../archive/2026-04/editor-role-gating/) | #1 성공 사례 (Match Rate 98%) — lessons learned 포함 |
| Post 모델 | [backend/app/models/post.py](../../../backend/app/models/post.py) | `Post.status` draft 지원 확인 (L43-44) |
| 에디터 페이지 | [frontend/src/app/posts/new/page.tsx](../../../frontend/src/app/posts/new/page.tsx) | 현재 폼 상태 18개 관리 컴포넌트 |

---

## 2. Problem Statement

### 2.1 현재 페인포인트

| 상황 | 결과 | 발생 빈도 추정 |
|------|------|---------------|
| 브라우저 새로고침 (Ctrl+R, F5) | 전체 입력 손실 | 매우 높음 — 실수로 자주 발생 |
| 탭/브라우저 닫기 | 전체 입력 손실 | 높음 — 실수 또는 배터리 방전 |
| 뒤로가기 버튼 | 전체 입력 손실 | 높음 — 링크 오클릭 시 |
| 모바일 → 데스크탑 전환 | 이어 쓰기 불가 | 중간 — 작가는 이동 중 초안 작성 빈번 |
| 장시간 작성 중 세션 만료 | 전체 입력 손실 (제출 실패) | 낮음 — 그러나 가장 치명적 |

### 2.2 사용자 영향

신진 작가 사용자는 작품 설명 + 제작 과정 + 판매 조건을 함께 작성하는 경우 평균 작성 시간이 일반 SNS 포스트 대비 3~5배 길다. 입력 손실은 단순 불편이 아니라 **플랫폼 신뢰도 타격** 및 **재방문율 감소**로 직결된다.

---

## 2. Scope

### 2.1 In Scope

- [x] FR-1: localStorage 기반 폼 상태 자동저장 (debounced)
- [x] FR-2: 페이지 재진입 시 자동 복원 확인 다이얼로그
- [x] FR-3: 명시적 "임시저장" 버튼 (서버 draft 저장)
- [x] FR-4: 본인 draft 목록 페이지 (`/posts/drafts`)
- [x] FR-5: 발행 시 draft 자동 삭제 (서버 + localStorage)
- [x] FR-6: 멀티 디바이스 동기화 (서버 draft 활용)
- [x] Draft 전용 백엔드 API 엔드포인트 신규 구현
- [x] `useDraftAutosave` 훅 신규 구현

### 2.2 Out of Scope

- 협업 편집 (실시간 다중 사용자 동시 편집) — 별도 PDCA
- 버전 히스토리 (변경 이력 저장 및 되돌리기) — 별도 PDCA
- 멀티 디바이스 동시 편집 충돌 해결 UI — 별도 PDCA (AC-7에서 토스트 경고만)
- Draft 미디어 파일 재업로드 처리 — 미디어는 이미 URL 형태로 저장되므로 URL만 draft에 포함

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | 요구사항 | 우선순위 | MoSCoW |
|----|----------|----------|--------|
| FR-1 | localStorage에 폼 상태 자동저장 — debounced (1~3초 간격), 사용자 입력 멈춤 감지 | High | Must |
| FR-2 | 페이지 재진입 시 자동 복원 확인 다이얼로그 ("이전에 작성 중인 글이 있습니다. 복원하시겠습니까?") — 거부 시 localStorage clear | High | Must |
| FR-3 | 명시적 "임시저장" 버튼 — 클릭 시 서버에 `Post.status='draft'`로 저장 + 토스트 노출 | High | Must |
| FR-4 | 본인 draft 목록 페이지 (`/posts/drafts`) — draft 조회/이어쓰기/삭제 | Medium | Should |
| FR-5 | 발행(publish) 성공 시 해당 draft 자동 삭제 — 서버 + localStorage 동시 | High | Must |
| FR-6 | 멀티 디바이스 동기화 — 다른 기기에서 저장한 서버 draft도 동일 사용자로 조회 가능 | Medium | Should |

### 3.2 Non-Functional Requirements

| ID | 카테고리 | 기준 | 측정 방법 |
|----|----------|------|-----------|
| NFR-1 | 가용성 | localStorage 자동저장은 네트워크 없이도 동작 (오프라인 안전망) | 네트워크 차단 상태 수동 테스트 |
| NFR-2 | UX 피드백 | 자동저장 인디케이터 상시 노출 ("저장됨 · 5초 전" 형식) | 시각 확인 |
| NFR-3 | 데이터 안전 | localStorage 키 충돌 방지 — `domo-draft-{userId}-new` 형식으로 사용자별 격리 | 다중 사용자 수동 테스트 |
| NFR-4 | 서버 부하 | 서버 draft는 사용자당 최대 20개 제한 — 초과 시 가장 오래된 draft 자동 삭제 경고 | API 응답 검증 |
| NFR-5 | 성능 | 자동저장 debounce로 keystore 이벤트당 즉시 저장 방지 — localStorage 쓰기 1~3초 간격 | 브라우저 DevTools Storage 모니터링 |

---

## 4. Solution Sketch

### 4.1 Frontend 아키텍처

**신규 훅: `useDraftAutosave`**

```
lib/hooks/useDraftAutosave.ts
  - 입력: formState (18개 필드), userId, draftId (선택)
  - 출력: { savedAt, isDirty, saveDraft, restoreDraft, clearDraft }
  - localStorage debounced write (1~3초)
  - 마운트 시 localStorage 복원 여부 확인
  - 명시적 saveDraft() 호출 시 서버 API 호출
```

**신규 페이지: `/posts/drafts`**

```
app/posts/drafts/page.tsx
  - 본인 draft 목록 (카드 형태)
  - 이어쓰기: /posts/new?draft={id}
  - 삭제: 개별 삭제 버튼
```

**수정 파일: `/posts/new/page.tsx`**

```
- useDraftAutosave 훅 통합
- 복원 확인 다이얼로그 (페이지 진입 시)
- "임시저장" 버튼 추가
- draft 모드 진입 (?draft={id}) 시 폼 채우기
- 발행 성공 후 draft 삭제 호출
```

### 4.2 Backend API 설계

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| `POST` | `/v1/posts/drafts` | Draft 생성 또는 업데이트 (upsert) | 필수 |
| `GET` | `/v1/posts/drafts` | 본인 draft 목록 (최신순) | 필수 |
| `GET` | `/v1/posts/drafts/{id}` | 특정 draft 상세 조회 (이어쓰기) | 필수 |
| `DELETE` | `/v1/posts/drafts/{id}` | Draft 삭제 | 필수 |

Draft 검증 규칙: `title`, `content` 빈 값 허용 (발행 시 검증과 분리).

### 4.3 저장 계층 전략

```
[사용자 입력]
     │
     ├─ debounce 1~3초 ──▶ [localStorage] ◀── 복원 확인 다이얼로그 (페이지 재진입)
     │                       (오프라인 안전망)
     │
     └─ 명시적 버튼 클릭 ──▶ [서버 draft API] ──▶ [/posts/drafts 목록]
                              (멀티 디바이스 동기화)
```

localStorage vs 서버 draft 충돌 해결: timestamp 비교 → 더 최신 우선.

---

## 5. Requirements (Functional + Non-Functional) — 상세

*§3에서 정의. 이 섹션은 Open Questions 해소 후 확정.*

---

## 6. Acceptance Criteria

| ID | 기준 | 검증 방법 |
|----|------|-----------|
| AC-1 | 글 작성 중 페이지 새로고침 → 자동 복원 다이얼로그 표시 ("이전 작성 내용이 있습니다. 복원하시겠습니까?") | 수동 테스트: 입력 후 F5 |
| AC-2 | "임시저장" 버튼 클릭 → 서버에 `Post.status='draft'`로 저장 + 성공 토스트 노출 | API 응답 확인 + UI 토스트 확인 |
| AC-3 | `/posts/drafts` 페이지에서 본인 draft 목록 확인 가능 (빈 상태 / 1개 이상 상태) | 수동 테스트 |
| AC-4 | Draft 카드 클릭 → `/posts/new?draft={id}` 진입, 폼이 draft 데이터로 채워진 상태 | 수동 테스트: 모든 저장 필드 확인 |
| AC-5 | 발행(submit) 성공 시 draft 자동 삭제 — 서버 draft 삭제 + localStorage clear | API 응답 확인 + localStorage 검사 |
| AC-6 | 비로그인 사용자도 localStorage 자동저장 동작 (로그인 후 서버 draft 활용 가능) | 비로그인 상태 수동 테스트 |
| AC-7 | 멀티탭 동시 편집 시 충돌 경고 토스트 노출 (마지막 저장 우선, 강제 덮어쓰기 없음) | 멀티탭 수동 테스트 |

---

## 7. Risks & Mitigations

| ID | 리스크 | 영향도 | 발생 가능성 | 대응 방안 |
|----|--------|--------|-------------|-----------|
| R-1 | localStorage 용량 한계 (5MB) | Low | Low | 미디어는 URL만 저장, 텍스트 100KB 이내로 가정. 초과 시 콘솔 경고 + 서버 draft 저장 유도 |
| R-2 | 복원 다이얼로그 거부 시 데이터 영구 삭제 | Medium | Medium | 다이얼로그에 "삭제" 레이블 명시 + 삭제 전 한 번 더 확인 (단계: 거부 → "정말 삭제하시겠습니까?") |
| R-3 | 서버 draft 무한 누적 | Medium | Medium | NFR-4: 사용자당 최대 20개 + 90일 미수정 자동 만료 cron job |
| R-4 | 자동저장 debounce 충돌 (빠른 연속 타이핑) | Low | Low | onBlur, 명시 저장 버튼 클릭 시 즉시 flush. debounce cancel on unmount |
| R-5 | 기존 `POST /v1/posts` 와 draft API 중복 로직 | Medium | Medium | Draft API는 별도 `/v1/posts/drafts` 라우터로 분리. 검증 규칙도 분리 (빈 값 허용) |

---

## 8. Dependencies

| 종류 | 항목 | 상태 |
|------|------|------|
| 선행 PDCA | `editor-role-gating` (#1) — PostTypeSelector 컴포넌트 공유 가능 | 완료 (아카이브 됨) |
| 후행 PDCA | `editor-responsive-redesign` (#3) — 자동저장 UI 인디케이터 위치 결정에 영향 | 대기 중 |
| 내부 인프라 | `Post.status` 컬럼 (draft 지원 확인됨) | 준비됨 |
| 외부 의존 | 없음 — localStorage + 자체 API | — |

---

## 9. Estimated Effort

| Phase | 작업 | 예상 시간 |
|-------|------|-----------|
| Plan | 요구사항 정의 + Open Questions 해소 | 0.5d |
| Design | API 스펙 + 컴포넌트 설계 + localStorage 스키마 | 0.5d |
| Do — Frontend | `useDraftAutosave` 훅, 복원 다이얼로그, 임시저장 버튼, `/posts/new` 통합 | 1.0d |
| Do — Backend | `/v1/posts/drafts` API 4개 엔드포인트, 검증 규칙 분리 | 0.5d |
| Do — Pages | `/posts/drafts` 목록 페이지 | 0.5d |
| Check | Gap analysis (gap-detector) | 0.3d |
| Act | 이터레이션 (필요 시) | 0~0.3d |
| Report + Archive | 완료 보고 + 아카이브 | 0.2d |
| **합계** | | **M (2~3일)** |

---

## 10. Open Questions — RESOLVED (2026-04-30)

사용자 결정 완료. 5개 모두 권장 default 채택.

| ID | 질문 | 결정 | 영향 |
|----|------|------|------|
| **Q-1** | 명시적 "임시저장" 버튼 vs 자동저장만 | **둘 다 제공** | localStorage 자동저장 + 서버 draft API + 명시 버튼 |
| **Q-2** | Drafts 목록 페이지 진입 경로 | **에디터 내 버튼 + 사용자 메뉴 (Sidebar dropdown)** | UserDropdown에 "임시저장 목록" 메뉴, 에디터 헤더에 "불러오기" 버튼 |
| **Q-3** | 자동저장 주기 | **입력 멈춤 2초 후 debounce** | `useDraftAutosave` hook에 `debounceMs: 2000` 옵션 |
| **Q-4** | 발행 성공 시 draft 삭제 | **자동 삭제 (확인 없음)** | `handleSubmit` 성공 후 `clearDraft(localStorage + server)` |
| **Q-5** | localStorage vs 서버 draft 충돌 | **더 최신 timestamp 우선** | 복원 시 둘의 `updated_at` 비교, 더 최신 것 노출 + 다른 것 옵션으로 보존 |

### 결정 영향 요약 (Design 단계 입력)

- **신규 컴포넌트**: `useDraftAutosave` hook, `DraftRestoreDialog`, `/posts/drafts` page, UserMenu 항목
- **신규 API 4개**: `POST/GET/DELETE /v1/posts/drafts`, `GET /v1/posts/drafts/{id}`
- **기존 수정**: `posts/new/page.tsx` (autosave 통합), `Sidebar.tsx` (사용자 메뉴 항목 추가)
- **DB 마이그레이션**: 0개 (Post.status enum이 이미 'draft' 지원)

---

## 11. Architecture Considerations

### 11.1 Project Level Selection

| Level | 특성 | 선택 |
|-------|------|:----:|
| Starter | 단순 구조 | ☐ |
| **Dynamic** | Feature-based, BaaS 통합, fullstack | **X** |
| Enterprise | 엄격한 레이어 분리, DI | ☐ |

기존 프로젝트 레벨 유지 (Dynamic). 변경 없음.

### 11.2 Key Architectural Decisions

| 결정 사항 | 선택 | 근거 |
|-----------|------|------|
| 저장 전략 | localStorage-first + 서버 보조 | 네트워크 없이도 안전망 보장 |
| Debounce 방식 | `useEffect` + `setTimeout` / 또는 `useDebouncedCallback` | 기존 프로젝트 패턴 확인 후 결정 |
| Draft API 라우터 | `/v1/posts/drafts` 별도 라우터 (기존 `/v1/posts`와 분리) | 검증 규칙 충돌 방지 |
| localStorage 키 | `domo-draft-{userId}-new` | 사용자별 격리. `domo-*` prefix 기존 컨벤션 준수 |

### 11.3 변경 파일 범위 (예상)

```
신규 파일:
  frontend/src/lib/hooks/useDraftAutosave.ts
  frontend/src/app/posts/drafts/page.tsx
  backend/app/api/routes/posts_drafts.py  (또는 posts.py 내 drafts 섹션)

수정 파일:
  frontend/src/app/posts/new/page.tsx     (훅 통합 + 복원 로직 + draft 모드)
  frontend/src/lib/api.ts                 (draft API 함수 추가)
  backend/app/api/routes/posts.py         (발행 시 draft 삭제 트리거)
  backend/app/api/router.py               (drafts 라우터 등록)
```

---

## 12. Convention Prerequisites

### 12.1 확인이 필요한 기존 컨벤션

| 컨벤션 | 현재 상태 | 확인 방법 |
|--------|-----------|-----------|
| localStorage 키 네이밍 | `domo-*` prefix 사용 확인됨 (`tokenStore`, `useRecentSearches`) | 코드 grep |
| useEffect debounce 패턴 | 기존 훅에서 패턴 확인 필요 | `lib/hooks/` 탐색 |
| Toast 시스템 | 존재 여부 확인 필요 — 없으면 별도 설치 또는 구현 | `components/` 탐색 |
| API 클라이언트 패턴 | `lib/api.ts` 기존 패턴 확인 | 직접 탐색 |

### 12.2 Environment Variables

이 PDCA에서 신규 환경 변수 필요 없음. 기존 API_URL 사용.

---

## 13. Next Steps

1. **Open Questions 5개 사용자 확인** (Q-1 ~ Q-5) — Design 진입 전 필수
2. `/pdca design editor-draft-autosave` (frontend-architect agent 위임 권장)
3. Design → Do → Check → Act → Report → Archive 표준 사이클
4. 완료 후 #3 `editor-responsive-redesign` 진입

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-30 | Initial draft | itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent) |
