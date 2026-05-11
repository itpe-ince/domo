# Plan — Settings Unification

> **Status**: 구현 완료 (retroactive plan — PDCA cycle 정상 진입)
> **Created**: 2026-05-11
> **Owner**: itpe-ince
> **Project Level**: Dynamic

---

## 1. Summary

`/me/*`와 `/me/settings/*`에 8개 페이지로 파편화된 설정성 기능을 `/me/settings` 단일 Hub + 6 카테고리 카드 구조로 통합. 기존 URL 제거 + 링크 일괄 갱신.

---

## 2. Context

### 2.1 파편화 현황 (Before)

| 위치 | 페이지 | 줄 수 | 내용 |
|------|-------|:----:|------|
| `/me/account` | account/page.tsx | 328 | 계정/인증/데이터 내보내기 |
| `/me/bio` | bio/page.tsx | 169 | 자기소개 다국어 |
| `/me/newsletter` | newsletter/page.tsx | — | 뉴스레터 구독 |
| `/me/notifications/preferences` | preferences/page.tsx | 274 | 알림 채널/카테고리 |
| `/me/settings/preferences` | preferences/page.tsx | 34 | 표시 (locale, currency) |
| `/me/settings/accessibility` | accessibility/page.tsx | 63 | 대비/폰트 |
| `/me/settings/privacy` | privacy/page.tsx | 135 | PostHog 옵트아웃 |
| `/me/settings/sponsor-validity` | sponsor-validity/page.tsx | — | 후원 유효기간 |

### 2.2 문제점

- 8개 페이지가 `/me/*`(탑레벨 4개) + `/me/settings/*`(서브 4개) 두 위치에 분산
- 일관된 네비게이션 부재 → 사용자가 "어디서 변경하지?" 혼란
- 일부 항목 중복 (newsletter는 알림 일종인데 `/me/newsletter`로 별도)
- sponsor-validity는 account 컨텍스트인데 settings 하위에 위치 (불일치)

---

## 3. Goals

### 3.1 Primary (Must)

| # | 목표 | 측정 |
|:-:|------|------|
| G-1 | 8개 → 6개 카테고리로 재구성 | Hub 페이지 1개 + sub-page 6개 |
| G-2 | 단일 진입점 `/me/settings` | 모든 설정 1-click 접근 가능 |
| G-3 | 기존 URL 완전 제거 | grep으로 잔존 0건 |
| G-4 | 회귀 0 | backend 787 passed 유지, tsc 0 error |

### 3.2 Secondary (Should)

| # | 목표 | 측정 |
|:-:|------|------|
| G-5 | mobile/tablet/desktop 반응형 | 카드 그리드 1/2/3열 |
| G-6 | 접근성 (aria-label, 키보드 nav) | 모든 카드 tab 가능 |
| G-7 | 5 locale i18n (ko/en/ja/zh/es) | 신규 70 entries (14 keys × 5) |

---

## 4. Scope

### 4.1 In Scope

- `/me/settings/page.tsx` Hub 페이지 신규
- 6 카테고리 sub-page 생성/이동/통합:
  1. `profile` ← bio 이동
  2. `display` ← preferences 이동
  3. `accessibility` 유지
  4. `notifications` ← notifications/preferences + newsletter 섹션 통합
  5. `privacy` 유지
  6. `account` ← account + sponsor-validity 섹션 통합
- 기존 6개 페이지 삭제 (account, bio, newsletter, notifications/preferences, settings/preferences, settings/sponsor-validity)
- 링크 업데이트 (Sidebar, MobileTabBar, patronage, legal/privacy 등)
- i18n 5 locale 신규 70 entries

### 4.2 Out of Scope

- 기존 페이지 내부 로직 변경 (이동/이름 변경만)
- 백엔드 API 변경 (frontend-only)
- 신규 설정 항목 추가
- 디자인 시스템 토큰 변경

---

## 5. Approach

### 5.1 UI 구조

```
/me/settings  (Hub)
├── 프로필 (profile)
├── 표시 (display)
├── 접근성 (accessibility)
├── 알림 (notifications)
├── 개인정보 (privacy)
└── 계정 (account)
```

Hub Layout: 카드 그리드 (mobile 1열 / tablet 2열 / desktop 3열). 각 카드 = 아이콘 + 제목 + 1줄 설명 + 화살표.

### 5.2 URL 매핑

| 기존 | 신규 |
|------|------|
| `/me/account` | `/me/settings/account` |
| `/me/bio` | `/me/settings/profile` |
| `/me/newsletter` | `/me/settings/notifications` (섹션 통합) |
| `/me/notifications/preferences` | `/me/settings/notifications` |
| `/me/settings/preferences` | `/me/settings/display` |
| `/me/settings/sponsor-validity` | `/me/settings/account` (섹션 통합) |
| `/me/settings/accessibility` | (유지) |
| `/me/settings/privacy` | (유지) |

---

## 6. Open Questions (Resolved)

| # | 질문 | 결정 | 사유 |
|:-:|------|------|------|
| OQ-1 | 통합 범위 | **8개 전체** | 사용자 혼란 최소화 |
| OQ-2 | UI 방식 | **Hub + 카테고리 카드** | 점진적 탐색 + 모바일 친화 |
| OQ-3 | 기존 URL 처리 | **제거** | clean URL + 기술부채 정리 |
| OQ-4 | GitHub OAuth | **제거 유지** | 일반 고객 GitHub 사용 미미 |
| OQ-5 | CognitiveSimpleMode | **제거 유지** | 사용 빈도 적음 |

---

## 7. KPI

| KPI | 목표 | 실측 |
|-----|:----:|:----:|
| Hub 페이지 | 1개 신규 | ✅ 1개 |
| Sub-pages | 6개 | ✅ 6개 |
| 기존 URL 잔존 | 0 | ✅ 0건 (grep 확인) |
| i18n 신규 keys | 14 keys × 5 locales = 70 | ✅ 70 entries |
| frontend tsc error | 0 | ✅ 0 |
| backend 회귀 | 0 | ✅ 780 passed |
| 링크 업데이트 파일 | ≥ 4 | ✅ 5 (Sidebar/MobileTabBar/patronage/legal+1) |

---

## 8. Risks

| Risk | Impact | Mitigation |
|------|:------:|------------|
| 외부 북마크 깨짐 | 중 | clean URL이므로 일회성 영향 — 사용자 재발견 가능 |
| Sidebar/Tab 잘못된 항목 활성화 | 낮음 | `/me/settings/*` prefix 매칭 |
| i18n 키 누락 locale | 낮음 | 5 locale 일괄 추가 |

---

## 9. Implementation (이미 완료)

| 작업 | 상태 |
|------|:----:|
| Hub 페이지 (`/me/settings/page.tsx`) | ✅ |
| profile/display/notifications/account sub-page | ✅ |
| 기존 6 페이지 삭제 | ✅ |
| 링크 업데이트 (5 파일) | ✅ |
| i18n 70 entries | ✅ |
| 회귀 검증 (pytest 780 + tsc 0) | ✅ |

---

## 10. Sub-PDCAs

단일 sub-PDCA — 별도 분할 없음 (frontend-architect agent 1회 위임).

---

## 11. Phase 14 Carry-over

없음 — 본 작업은 self-contained.

---

## 12. Next Phase

`/pdca design settings-unification` → 이미 구현 완료된 사항을 design 문서로 정리 → `/pdca analyze` → gap-detector → `/pdca report` → `/pdca archive`.

---

## Version History

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 1.0 | 2026-05-11 | 초기 plan (retroactive — 구현 완료 후 작성) | itpe-ince |
