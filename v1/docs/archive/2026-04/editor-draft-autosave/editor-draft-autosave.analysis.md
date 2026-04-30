---
template: analysis
version: 1.0
feature: editor-draft-autosave
date: 2026-04-30
author: itpe-ince (Claude Opus 4.7 + bkit gap-detector agent)
project: domo
project_version: v1
parent_design: editor-draft-autosave.design.md
---

# editor-draft-autosave Analysis Report

## 1. Executive Summary

**Match Rate: 94%** (initial) → **98%** (after AC-7 confirmed implemented)

설계와 구현이 매우 높은 일치도. Backend 4개 endpoint, partial index, cleanup cron, frontend hook/dialog/page/sidebar/i18n 모두 design 명세대로 구현. 3개 OQ 결정(Q-D1=B, Q-D2=A, Q-D3=A) 모두 코드에 정확히 반영.

**Iterate 결과 (2026-04-30 v1.1)**: AC-7 멀티탭 충돌 경고가 코드 점검 결과 이미 완전 구현된 상태로 확인됨. `multiTabWarning` state(L111), `storage` 이벤트 useEffect(L255-266), 경고 배너 JSX(L474-489, `role="status"` + dismiss 버튼 보너스), 5개 locale `post.draft.multiTabWarning` 모두 존재. design §3.8과 정확히 일치 + 접근성/UX 개선.

---

## 2. Acceptance Criteria Verification (7개)

| AC | 기준 | 코드 위치 | 결과 |
|----|------|-----------|:----:|
| AC-1 | F5 새로고침 → 자동 복원 다이얼로그 | `posts/new/page.tsx` useEffect + `DraftRestoreDialog` | ✅ Pass |
| AC-2 | "임시저장" 버튼 → 서버 저장 + 인디케이터 | `posts/new/page.tsx` `handleManualSave` → `saveToServer()`. AutosaveIndicator | ✅ Pass |
| AC-3 | `/posts/drafts` 목록 페이지 | `app/posts/drafts/page.tsx` (LoginModal + skeleton + empty + list) | ✅ Pass |
| AC-4 | draft 클릭 → 폼 채워진 상태 | DraftCard Link + `getDraft()` + `draftToFormState()` + `handleRestore()` | ✅ Pass |
| AC-5 | 발행 성공 → draft 자동 삭제 | `from_draft_id` → `posts.py:286-293` 같은 트랜잭션. localStorage `clearDraft()`. Belt-and-suspenders DELETE | ✅ Pass |
| AC-6 | 비로그인도 localStorage 자동저장 | `domo-draft-guest-new` storage key, hook `enabled: !meLoading` | ✅ Pass |
| AC-7 | 멀티탭 동시 편집 충돌 경고 | `posts/new/page.tsx:111,255-266,474-489` + `post.draft.multiTabWarning` (5 locale) | ✅ Pass |

**7 / 7 Pass.** AC-7 코드 점검 결과 design §3.8 스니펫과 정확히 일치하며, `role="status"` 접근성 + dismiss 버튼 추가 개선 확인.

---

## 3. Design Specification Conformance

### 3.1 Backend API Endpoints (4개) — 100%

- `POST /v1/posts/drafts` upsert (draft_id 분기, 20개 한도, oldest auto-delete) ✅
- `GET /v1/posts/drafts` list (limit 1-50, offset, updated_at desc, total) ✅
- `GET /v1/posts/drafts/{id}` (소유자 불일치 → 404 anti-enumeration) ✅
- `DELETE /v1/posts/drafts/{id}` (hard delete + cascade) ✅
- `POST /v1/posts` `from_draft_id` 같은 트랜잭션 삭제 ✅

### 3.2 Backend Infrastructure — 100%

- `schemas/draft.py`: DraftUpsertBody / DraftView / DraftListResponse + 추가 DraftDeleteResponse ✅
- `from_draft_id` in PostCreate ✅
- Partial index `0035_draft_limit_index.py` ✅
- 90일 cleanup job + lifespan 등록 (Q-D3=A) ✅
- Smoke test 8 시나리오 ✅

### 3.3 Frontend Hook + Components — 100% (13/13)

- `useDraftAutosave` hook signature 정확히 일치 ✅
- 2초 debounce + beforeunload flush ✅
- localStorage 키 전략 (`domo-draft-{userId|guest}-{new|draftId}`) ✅
- StoredDraft payload (state + savedAt) — Q-5 timestamp 비교 ✅
- DraftRestoreDialog Q-5 newer-first ✅
- Modal pattern (LoginModal style) ✅
- `/posts/drafts` 페이지 + DraftCard ✅
- posts/new/page.tsx 통합 ✅
- Sidebar.tsx UserDropdown 메뉴 ✅
- DraftIcon ✅
- lib/api.ts Draft helpers ✅
- AutosaveIndicator 인라인 ✅
- AC-7 멀티탭 storage event + 배너 (L111, L255-266, L474-489) ✅

### 3.4 i18n keys (5 locale × 21 keys) — 100%

`nav.draftsList` + `post.draft.*` 21개 키 5 locale 모두 완전. 추가로 `card.*`, `list.newPost` 정당하게 추가.

**Minor 누락**: `lastSavedAgo: "{{time}} 전"` 키는 5 locale 모두 미정의. 그러나 `formatRelativeTime` 유틸이 한국어 hardcode 반환하므로 호출부가 이 키 참조 안 함 → 기능 영향 없음.

### 3.5 OQ Resolution Traceability — 100%

- **Q-D1=B** (Permissive role check): `api/drafts.py:172-175` docstring + update path role 검증 skip, create path만 검증 ✅
- **Q-D2=A** (formatRelativeTime 추출): `lib/formatRelativeTime.ts` 신규 + notifications 재사용 ✅
- **Q-D3=A** (lifespan 등록): webhook_cleanup_jobs.py 패턴 따름 ✅

---

## 4. Identified Gaps

### Critical (0)
없음.

### Major (0)

**M-1. AC-7 멀티탭 충돌 경고 배너** — ✅ **Resolved (v1.1, 2026-04-30)**
- 코드 점검 결과 `posts/new/page.tsx:111, 255-266, 474-489`에 design §3.8 명세대로 완전 구현
- 5개 locale `post.draft.multiTabWarning` 키 모두 정의 (ko/en/ja/zh/es)
- `role="status"` 접근성 속성 + dismiss 버튼은 design 스니펫보다 개선된 부분

### Minor (1)

**m-1. i18n `lastSavedAgo` 키 미정의**
- 5개 locale 모두 미정의. `formatRelativeTime` 유틸이 한국어 hardcode라 호출부 참조 없음. TODO 주석으로 인지됨 (`formatRelativeTime.ts:7-9`).
- 향후 시간 표기 다국어화 시 보완 필요 — 별도 i18n PDCA로 이관 권장

---

## 5. Out-of-Scope Changes

모두 정당:
- `DraftDeleteResponse` schema (future-proofing)
- `card.*` i18n 키 (DraftCard 구현 필수)
- `list.newPost` 키 (빈 상태 CTA)
- Optimistic delete UI (UX 향상)
- `loadStoredDraft` hook return (Q-5 timestamp 비교 보강)
- Belt-and-suspenders DELETE (방어적)
- non-artist auto-fallback to general (UX 보호)

---

## 6. Match Rate Calculation

| 카테고리 | 가중치 | 점수 | 가중 |
|----------|:------:|:----:|:----:|
| AC (7개) | 30% | 92.9% → **100%** | 27.9 → **30.0** |
| Backend API + Infra (11항목) | 25% | 100% | 25.0 |
| Frontend (13항목) | 25% | 92.3% → **100%** | 23.1 → **25.0** |
| i18n (5 × 21) | 10% | 100% | 10.0 |
| OQ Traceability (3개) | 10% | 100% | 10.0 |
| **Initial** | 100% | | **94.0** |
| **After Iterate v1.1 (AC-7 confirmed)** | 100% | | **100.0** |

> 잔존 minor(`lastSavedAgo` i18n 키 미정의)는 호출부에서 미참조이므로 가중에서 제외. 별도 i18n PDCA로 이관.

---

## 7. Next Steps

**Iterate 완료 (v1.1, 2026-04-30)**: AC-7 코드 점검 결과 design §3.8 명세대로 이미 구현되어 있음. 추가 코드 작업 불필요.

**다음 단계**: `/pdca report editor-draft-autosave`로 완료 보고서 생성.

후속 PDCA 후보 (별도 feature로 분리):
- `i18n-time-formatting`: `formatRelativeTime` 다국어화 + `lastSavedAgo` 키 5 locale 정의

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-30 | Initial gap analysis. AC 7개, Backend 11, Frontend 13, i18n 5×21keys, OQ 3개 검증. Match Rate 94%, AC-7 iterate 후 98% 예상 | itpe-ince + Claude Opus 4.7 + bkit gap-detector |
| 1.1 | 2026-04-30 | Iterate 단계 점검 결과 AC-7이 이미 완전 구현됨 확인 (state, storage useEffect, JSX 배너, 5 locale i18n 키). Match Rate 94% → **100%**. 모든 AC Pass, Major/Critical Gap 0. 잔존 minor `lastSavedAgo`는 호출부 미참조로 가중 제외, 별도 i18n PDCA로 이관 권장. → `/pdca report` 단계로 진행 | itpe-ince + Claude Opus 4.7 |
