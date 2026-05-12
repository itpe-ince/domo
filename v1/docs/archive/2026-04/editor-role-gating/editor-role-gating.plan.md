---
template: plan
version: 1.2
feature: editor-role-gating
date: 2026-04-29
author: itpe-ince (Claude Sonnet 4.6 + bkit product-manager agent)
project: domo
project_version: v1
status: Approved (Plan) — Design 진입 가능
parent_roadmap: editor-revamp-roadmap
decisions_resolved: 2026-04-29
---

# editor-role-gating Planning Document

> **Summary**: 작가 권한(role="artist" 또는 "admin")이 없는 사용자가 상품 포스트 type을 선택 자체를 할 수 없도록 UI 차원에서 차단하고, 백엔드 방어선도 검증·명시하여 submit 시점 에러를 완전히 없앤다.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-04-29
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

현재 `/posts/new` 에디터에서 일반 사용자도 "상품 포스트" 타입 버튼을 자유롭게 클릭할 수 있으며, 차단은 submit 버튼을 누른 시점에만 이루어진다. 이로 인해 사용자가 가격·매체·제작연도 등 상품 전용 필드를 모두 입력한 뒤에야 차단 메시지를 보게 되는 UX 문제가 발생한다.

본 PDCA는 type 선택 UI 자체에서 권한 게이팅을 적용하여 오류 노출 시점을 앞당기고, 비작가 사용자에게 "작가 신청" 경로를 즉시 안내함으로써 학습 효과와 전환 동선을 개선한다. 백엔드의 403 방어선은 이미 존재하므로 검증·문서화하고 방어 심층화(defense in depth)를 명시한다.

### 1.2 Background

- **마스터 로드맵**: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md) §2 Phase 1 — Foundation, #1 항목
- **로드맵 요구사항 원본 (§1 B-1)**: "작가가 아닌 경우에는 상품 포스트 불가 여야 함"
- **현재 구현 위치**: [v1/frontend/src/app/posts/new/page.tsx](../../../frontend/src/app/posts/new/page.tsx)
  - Line 156: `if (type === "product" && me?.role !== "artist" && me?.role !== "admin")` — submit 시 차단
  - Line 259: 선택 후 경고 메시지 표시 (차단 아님)
  - Line 248–258: type 선택 토글 버튼 (인라인 JSX, 별도 컴포넌트 미분리)
- **백엔드**: [v1/backend/app/api/posts.py Line 207](../../../backend/app/api/posts.py#L207) — `POST /v1/posts`에 role 검증 이미 존재 (403 반환)
- **작가 신청 페이지**: [v1/frontend/src/app/artists/apply/](../../../frontend/src/app/artists/apply/)

### 1.3 Related Documents

- 마스터 로드맵: [editor-revamp-roadmap.plan.md](./editor-revamp-roadmap.plan.md)
- 백엔드 posts API: [v1/backend/app/api/posts.py](../../../backend/app/api/posts.py)
- 프런트 에디터 페이지: [v1/frontend/src/app/posts/new/page.tsx](../../../frontend/src/app/posts/new/page.tsx)
- 작가 신청 페이지: [v1/frontend/src/app/artists/apply/page.tsx](../../../frontend/src/app/artists/apply/page.tsx)

---

## 2. Problem Statement

### 현재 코드의 3가지 문제점

**P-1. 잘못된 기대 형성 (type 선택 단계에서 차단 없음)**

type 선택 버튼(Line 248–258)에는 권한 검사가 전혀 없다. 비작가 사용자가 "상품 포스트" 버튼을 클릭하면 즉시 상품 필드(장르, 크기, 매체, 연도, 가격)가 표시된다. 사용자는 자신이 작성할 수 있다고 오해한 채 시간을 투자하게 된다.

**P-2. 차단 시점 지연 → 시간 낭비 및 UX 답답함**

실제 차단은 submit 버튼 클릭 시점(Line 156)에서야 발생한다. 상품 폼 필드를 모두 입력하고 제출을 시도해야만 "상품 포스트는 작가 권한이 필요합니다" 에러를 본다. 입력 시간이 전부 손실되며, 작가 신청으로 이어지는 동선이 없다.

**P-3. 백엔드 방어선 문서화 부재 + 캐시 stale 리스크**

백엔드 `POST /v1/posts`에 role 검증(Line 207)이 이미 존재하나, 이 사실이 plan/design 문서에 명시되지 않아 "frontend만 있고 backend는 없다"고 오해할 수 있다. 또한 사용자가 작가 승인을 받아 role이 변경된 직후, frontend가 캐시된 me 데이터를 사용하면 product 옵션이 여전히 잠긴 채로 보이는 역방향 문제가 생길 수 있다.

### 사용자 영향

| 대상 | 현재 경험 | 개선 후 경험 |
|------|-----------|-------------|
| 비작가 일반 사용자 | 상품 필드 입력 후 submit 시 에러 | type 선택 시점에 잠금 표시 + 작가 신청 CTA 즉시 노출 |
| 신규 승인된 작가 | 역할 변경 후 즉시 반영 여부 불명확 | role 갱신 후 안내 메시지 또는 자동 반영으로 즉시 사용 가능 |
| 기존 작가 (role="artist") | 정상 동작 | 변경 없음 (회귀 없어야 함) |
| 관리자 (role="admin") | 정상 동작 | 변경 없음 |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | 요구사항 | 우선순위 | 상태 |
|----|----------|----------|------|
| FR-1 | type 선택 UI에서 product 옵션은 role="artist" 또는 role="admin"인 경우에만 클릭 가능하다 | Must | Pending |
| FR-2 | 비작가 사용자에게는 product 옵션이 비활성(disabled) 상태로 노출되며, 잠금 아이콘 또는 "작가 전용" 표시를 함께 보여준다 | Must | Pending |
| FR-3 | 비활성 product 옵션에 hover 또는 클릭 시, "작가만 작성할 수 있습니다" 안내 문구와 "작가 신청하기" 링크(`/artists/apply`)가 즉시 노출된다 | Must | Pending |
| FR-4 | 백엔드 `POST /v1/posts` 엔드포인트는 role 기반 검증(403)을 유지한다 (현재 구현 보존 및 테스트 추가) | Must | 이미 구현됨 — 테스트 필요 |
| FR-5 | 작가 신청 승인 후 role이 갱신된 경우, 새로고침 또는 역할 변경 감지를 통해 product 옵션이 활성화된다 | Should | Pending |
| FR-6 | 비로그인 사용자는 기존대로 LoginModal을 트리거한다 (현재 동작 유지) | Must | 현재 구현됨 — 회귀 방지 |

### 3.2 Non-Functional Requirements

| 분류 | 기준 | 측정 방법 |
|------|------|-----------|
| UX 성능 | 기존 작가 사용자(role="artist")의 product 작성 진입~submit 완료 시간이 현재 대비 1초 이상 증가하지 않는다 | 수동 E2E 타이밍 측정 |
| 가용성 | product 옵션 비활성 처리가 JS 에러 없이 동작한다 (disabled 상태에서 클릭 이벤트 방어) | 브라우저 콘솔 확인 |
| 보안 | frontend 권한 검사 우회(직접 API 호출)를 backend 403으로 차단한다 | curl 테스트 |
| 접근성 | 비활성 버튼에 `aria-disabled="true"` 및 `title` 속성으로 스크린 리더 안내 제공 | 수동 확인 |

---

## 4. Out of Scope

본 PDCA에서 제외하는 항목 (향후 별도 PDCA 또는 로드맵 항목으로 처리):

- 작가 신청 페이지(`/artists/apply`) 자체의 UX 개선 또는 기능 추가
- 관리자가 사용자 role을 변경하는 admin UI 개선
- role 변경 실시간 감지를 위한 WebSocket 또는 Server-Sent Events 도입
- 작가 승인 알림(push/이메일) 시스템
- role 기반 기능 차단의 일반화(미들웨어/HOC 추상화) — 이번엔 이 페이지만
- type 선택 컴포넌트의 별도 파일 분리(단, 분리가 구현에 자연스럽다면 허용)
- 드래프트 자동저장, 반응형 리디자인 등 로드맵의 다른 항목

---

## 5. Solution Sketch

### 5.1 변경 영역

| 영역 | 현재 상태 | 변경 방향 |
|------|-----------|-----------|
| Frontend — type 선택 토글 | `page.tsx` 내 인라인 버튼 2개 (일반/상품) | product 버튼에 role 조건 추가: 비작가면 `disabled`/`aria-disabled`, hover 시 툴팁/인라인 안내 + "작가 신청" 링크 |
| Frontend — submit 차단 | Line 156: submit 시 role 체크 후 `setError` | 유지 (방어선 이중화). 단, FR-1 적용 후 실제로 도달하지 않아야 함 |
| Frontend — 경고 메시지 | Line 259: type=product 선택 후 경고 텍스트 표시 | FR-3의 인라인 안내로 교체 또는 보완 |
| Backend — `POST /v1/posts` | Line 207: role 검증 + 403 | 현재 구현 보존. 통합 테스트 케이스 추가 |

### 5.2 Frontend 구현 접근

type 선택 버튼 영역(현재 Line 237–263)에서 다음 로직을 추가한다:

```
isArtist = me?.role === "artist" || me?.role === "admin"

[일반 포스트 버튼] — 변경 없음

[상품 포스트 버튼]
  - isArtist == true:  현재와 동일하게 클릭 가능, 활성 스타일
  - isArtist == false: 
      disabled (pointer-events-none + opacity 처리)
      aria-disabled="true"
      잠금 아이콘 (자물쇠 svg 또는 text)
      hover 또는 클릭 시 → 인라인 안내 표시
        "작가만 작성할 수 있습니다.  [작가 신청하기 →]"
        링크: /artists/apply
```

role 갱신 감지는 `useMe()` 훅이 반환하는 `me` 객체가 갱신되면 자동 반영된다. 별도 구현 불필요. 단, 승인 직후 페이지 새로고침 없이 반영되는지는 `useMe()`의 캐시 전략에 따라 다르며 Open Question Q-3에서 결정한다.

### 5.3 Backend 검증

`app/api/posts.py` Line 207의 기존 코드를 보존하고, 다음 테스트를 추가한다:

- role="user"인 토큰으로 `POST /v1/posts` (type="product") → 403 확인
- role="artist"인 토큰으로 동일 요청 → 201 확인

---

## 6. Acceptance Criteria

테스트 가능한 완료 조건:

| ID | 조건 | 방법 |
|----|------|------|
| AC-1 | role="user"인 사용자가 `/posts/new`에 진입하면 "상품 포스트" 버튼이 비활성 상태로 렌더링된다 | 브라우저 수동 확인 + DOM `aria-disabled` 확인 |
| AC-2 | 비활성 "상품 포스트" 버튼에 마우스를 올리거나 클릭하면 "작가만 작성할 수 있습니다" 안내와 `/artists/apply` 링크가 노출된다 | 브라우저 수동 확인 |
| AC-3 | role="artist"인 사용자는 "상품 포스트" 버튼을 정상 클릭할 수 있고, 상품 필드(장르/크기/매체/연도/가격)가 정상 표시된다 | 브라우저 수동 확인 (회귀 테스트) |
| AC-4 | role="admin"인 사용자도 role="artist"와 동일하게 정상 동작한다 | 브라우저 수동 확인 |
| AC-5 | role="user" 사용자가 `curl -X POST /v1/posts -H "Authorization: Bearer <user_token>" -d '{"type":"product",...}'`를 직접 호출하면 HTTP 403을 반환한다 | curl 테스트 |
| AC-6 | 비로그인 상태에서 `/posts/new` 진입 시 LoginModal이 기존대로 표시된다 (회귀 없음) | 브라우저 수동 확인 |
| AC-7 | 기존 role="artist" 사용자가 상품 포스트를 작성하고 제출하는 전체 흐름이 정상 완료된다 (회귀 없음) | E2E 수동 테스트 |

---

## 7. Risks & Mitigations

| ID | 리스크 | 영향 | 발생 가능성 | 대응 |
|----|--------|------|-------------|------|
| R-1 | role="artist" 기존 사용자에게 product 옵션이 잘못 비활성화되는 회귀 | 높음 (작가가 상품 포스트 못 씀) | 낮음 | AC-3/AC-4/AC-7로 작가 계정 회귀 테스트 필수. PR 전 작가 계정으로 직접 확인 |
| R-2 | 작가 신청 페이지(`/artists/apply`)가 미완성이거나 에러 상태여서 CTA 클릭 시 막다른 길이 됨 | 중간 (UX 단절) | 중간 | 구현 전 `/artists/apply` 페이지 동작 확인 필수. 문제 있으면 링크 임시 비활성화 또는 별도 안내로 대체 |
| R-3 | `me` 데이터 캐시 stale로 인해 작가 승인 직후 product 옵션이 여전히 잠긴 채로 보임 | 낮음 (신규 작가의 첫 1회 경험) | 중간 | Q-3에서 결정. 최소한 새로고침 안내 문구 제공 |
| R-4 | 인라인 안내 UI가 좁은 모바일 화면에서 레이아웃을 깸 | 낮음 | 중간 | 모바일 뷰포트에서 확인. 툴팁보다 아래 인라인 텍스트 방식이 안전 |

---

## 8. Dependencies

### 8.1 선행 의존성

없음. 이 PDCA는 Phase 1의 첫 항목이므로 선행 sub-PDCA가 없다.

### 8.2 후행 의존성

- 본 PDCA 완료 후 → **#2 editor-draft-autosave** 진입 가능 (로드맵 §3 Critical Path: 1 → 2 → 3)
- 본 PDCA의 type 선택 컴포넌트 구조가 #3 `editor-responsive-redesign`의 type 선택 UI 재설계에 기반이 됨

### 8.3 외부 의존성

| 의존 항목 | 상태 | 비고 |
|-----------|------|------|
| `useMe()` 훅의 `me.role` 제공 | 현재 동작 중 | `page.tsx` Line 45에서 사용 중 |
| `/artists/apply` 페이지 | 존재 확인 필요 | 구현 전 동작 확인 필수 (R-2) |
| 백엔드 `POST /v1/posts` 403 | 이미 구현됨 | `posts.py` Line 207 보존 |

---

## 9. Estimated Effort

**총 규모: XS (반나절, 약 4.5~5.5시간)**

| PDCA 단계 | 내용 | 예상 시간 |
|-----------|------|-----------|
| Design | type 선택 UI 변경 스펙 확정, Open Questions 해소 | 1h |
| Do | frontend 버튼 비활성 처리 + 안내 UI + 링크. backend 테스트 추가 | 2h |
| Check | 수동 E2E (AC-1~7), curl 테스트 (AC-5), `/artists/apply` 동작 확인 | 1h |
| Act | 회귀 수정 (있다면) | 0~1h |
| Report | 완료 보고서 작성 | 0.5h |

---

## 10. Open Questions — RESOLVED

사용자 확인 완료 (2026-04-29). 모든 Open Question 해결.

### Q-1. type 선택 컴포넌트 분리 → **결정: 별도 컴포넌트 분리 (B)**

- 신규 파일: `v1/frontend/src/components/post-editor/PostTypeSelector.tsx`
- `page.tsx` Line 237–263의 인라인 JSX를 추출
- #3 responsive-redesign 때 재사용 + #2 draft-autosave 시 type 자동 복원 로직 깔끔
- **근거**: 구조 정리 + 후속 PDCA 작업 비용 절감

### Q-2. 비활성 상품 옵션 안내 UI → **결정: 인라인 텍스트 + 클릭 차단 (A 변형)**

- 비작가 사용자에게 product 버튼은:
  - 버튼 자체는 시각적으로 비활성 처리 (opacity-60, cursor-not-allowed)
  - **클릭은 완전히 차단** (disabled 또는 onClick guard)
  - 버튼 바로 **아래 인라인 안내 텍스트** 항상 표시: "작가 등록 후 작성 가능합니다 → [작가 신청](/artists/apply)"
- 모바일/데스크탑 동일 동작 (툴팁 의존성 없음)
- **근거**: 가장 단순하고 명확. 모바일에서도 동일 UX 제공.

### Q-3. 작가 승인 후 role 반영 방식 → **결정: 알림 시스템 연동 (C)**

**중요한 발견 — 인프라 대부분 이미 존재:**

- ✅ Backend: [api/admin/users.py:97-99](../../../backend/app/api/admin/users.py#L97-L99) 의 `approve_application` 핸들러는 승인 시 이미 `Notification` 레코드를 자동 생성한다
- ✅ Backend: [api/admin/users.py:71](../../../backend/app/api/admin/users.py#L71) 의 `revoke_user_tokens(reason="admin_role_change")` 호출로 사용자의 모든 기존 토큰을 즉시 무효화 → **자동 로그아웃 강제**
- ✅ Frontend: [lib/useMe.ts:50](../../../frontend/src/lib/useMe.ts#L50) 의 `AUTH_CHANGED_EVENT` 리스너로 토큰 변경 자동 감지 → 다음 요청 시 401 → 로그인 모달

**구현 흐름:**

```
[관리자] 작가 신청 승인 클릭
   ↓
[backend] User.role = "artist" 업데이트
   ↓
[backend] revoke_user_tokens() — 기존 토큰 모두 무효화
   ↓
[backend] Notification 생성 ("축하합니다, 작가가 되셨습니다") — 이미 존재
   ↓
[frontend] 다음 API 호출 시 401 응답
   ↓
[frontend] AUTH_CHANGED_EVENT 발생 → useMe() me=null
   ↓
[frontend] LoginModal 자동 노출
   ↓
[사용자] 재로그인 → 신규 토큰 발급 (role=artist 반영)
   ↓
[사용자] 알림 페이지에서 "축하" 메시지 확인 → 에디터 진입 시 product 옵션 활성화
```

**이번 PDCA에서 추가 작업:**

- (선택) 알림 메시지 텍스트 검토 — 현재 `Notification.message` 내용 확인 후 필요 시 개선
- (선택) 알림 클릭 시 에디터로 deep link — `/posts/new?type=product` 자동 선택
- 본 PDCA 핵심 작업과 직접 연관 없음 → **별도 sub-task로 분리** (또는 이번 PDCA 내 nice-to-have 로 포함)

**Scope 영향:**

- 당초 "scope 초과"로 표기했으나 실제로는 인프라 대부분 존재 → XS 유지 가능
- 알림 메시지/딥링크 검증/개선만 추가 — 추가 0.5h 예상


---

## 11. Architecture Considerations

### 11.1 Project Level

Dynamic 레벨 유지 (기존 v1 구조: Next.js App Router + FastAPI + Tailwind). 이번 변경은 새 레이어를 추가하지 않는다.

### 11.2 Key Decisions

| 결정 항목 | 현재 | 이번 변경 |
|-----------|------|-----------|
| role 판별 위치 | frontend submit + backend | frontend type 선택 + frontend submit + backend |
| 컴포넌트 구조 | 인라인 | Q-1 답변에 따라 결정 |
| 안내 UI 방식 | submit 후 에러 메시지 | Q-2 답변에 따라 결정 |

### 11.3 변경 파일 범위 (예상)

```
변경:
  v1/frontend/src/app/posts/new/page.tsx   (또는 신규 컴포넌트로 분리)

추가 (Q-1 선택 시):
  v1/frontend/src/components/post-editor/PostTypeSelector.tsx

테스트 추가:
  v1/backend/tests/test_posts.py           (role 기반 403 케이스)
```

---

## 12. Convention Prerequisites

### 12.1 기존 컨벤션 확인

- [x] Next.js App Router (현재 page.tsx 사용 중)
- [x] Tailwind CSS 스타일링
- [x] TypeScript strict 모드
- [x] `useMe()` 훅으로 인증 사용자 정보 접근
- [x] `useI18n()` 훅으로 다국어 처리

### 12.2 이번 PDCA에서 확인/정의할 컨벤션

| 항목 | 현재 상태 | 정의 필요 |
|------|-----------|-----------|
| 비활성 버튼 패턴 | 프로젝트 내 통일 패턴 미확인 | Tailwind `disabled:opacity-50 cursor-not-allowed` 또는 `aria-disabled` 패턴 확인 |
| 권한 표시 아이콘 | 미정의 | 자물쇠(🔒) 아이콘 또는 텍스트 전용 |

### 12.3 환경 변수

신규 환경 변수 없음. 기존 인증 토큰 시스템 그대로 사용.

---

## 13. Next Steps

1. [x] Open Questions Q-1, Q-2, Q-3에 대한 사용자 결정 수렴 (2026-04-29 완료)
2. [ ] `/artists/apply` 페이지 동작 상태 확인 (R-2 대응) — Design 단계에서 검증
3. [ ] `/pdca design editor-role-gating` 진행 (frontend-architect 에이전트 위임)
4. [ ] Design → Do → Check → Act → Report → Archive 표준 사이클 완료 후 #2 draft-autosave 진입

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft — 현재 코드 분석 기반, 3개 문제점 구체화, 6개 FR + AC-7 + Q-3 포함 | itpe-ince / Claude Sonnet 4.6 + bkit product-manager |
| 0.2 | 2026-04-29 | Open Questions 모두 RESOLVED. Q-3 알림 시스템 활용 — 인프라 대부분 이미 존재 확인 (`Notification` 모델 + `revoke_user_tokens` + `AUTH_CHANGED_EVENT`). Status: Draft → Approved (Plan) | itpe-ince / Claude Opus 4.7 |
| 0.3 | 2026-04-29 | Design 단계 OQ-1=B (pending 사용자 별도 안내), OQ-2=A (현재 `/profile` deep link 유지) 결정. 사용자 알림 UX 우려는 #12 `notifications-ux-audit` 신규 sub-PDCA로 분리 (Phase 3) | itpe-ince / Claude Opus 4.7 |
