# Design — Settings Unification

> **Status**: 구현 완료 (retroactive design)
> **Plan**: `v1/docs/01-plan/features/settings-unification.plan.md`
> **Created**: 2026-05-11
> **Project Level**: Dynamic

---

## 1. Overview

`/me/*`와 `/me/settings/*`에 8개 페이지로 파편화된 설정성 기능을 `/me/settings` 단일 Hub + 6 카테고리 sub-page 구조로 통합. 기존 6개 페이지 삭제, 링크 5개 파일 갱신, i18n 5 locale 70 entries 추가.

---

## 2. Component Architecture

### 2.1 페이지 구조

```
src/app/me/settings/
├── page.tsx                  ← Hub (신규, 6 카테고리 카드 그리드)
├── profile/page.tsx          ← bio 이동 (자기소개 다국어 5 locale)
├── display/page.tsx          ← preferences 이동 (locale, currency)
├── accessibility/page.tsx    ← 유지 (대비/폰트)
├── notifications/page.tsx    ← notifications/preferences + newsletter 섹션 통합
├── privacy/page.tsx          ← 유지 (PostHog 옵트아웃)
└── account/page.tsx          ← account + sponsor-validity 섹션 통합
```

### 2.2 Hub Page Layout

```
┌────────────────────────────────────────────┐
│  ← 설정                                     │
│  프로필, 알림, 개인정보 등을 한 곳에서 관리  │
├────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 👤 프로필 │ │ 🎨 표시  │ │ ♿ 접근성│  │
│  │ 자기소개... │ │ 언어/통화│ │ 대비/폰트│  │
│  │         → │ │       → │ │       → │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 🔔 알림   │ │ 🔒 개인  │ │ 👤 계정  │  │
│  │ 채널/뉴스 │ │ 추적 거부│ │ 인증/내보│  │
│  │         → │ │       → │ │       → │  │
│  └──────────┘ └──────────┘ └──────────┘  │
└────────────────────────────────────────────┘
```

### 2.3 반응형 Breakpoint

| Viewport | 그리드 |
|----------|--------|
| Mobile (< 768px) | 1열 |
| Tablet (768~1024px) | 2열 |
| Desktop (≥ 1024px) | 3열 |

Tailwind: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`.

---

## 3. URL Routing

### 3.1 매핑 테이블

| 기존 URL | 신규 URL | 처리 |
|----------|----------|------|
| `/me/account` | `/me/settings/account` | 이동 + sponsor-validity 섹션 추가 |
| `/me/bio` | `/me/settings/profile` | 이동 |
| `/me/newsletter` | `/me/settings/notifications` | 통합 (newsletter 섹션) |
| `/me/notifications/preferences` | `/me/settings/notifications` | 이동 |
| `/me/settings/preferences` | `/me/settings/display` | 이름 변경 |
| `/me/settings/sponsor-validity` | `/me/settings/account` | 통합 (sponsor-validity 섹션) |
| `/me/settings/accessibility` | (유지) | — |
| `/me/settings/privacy` | (유지) | — |

### 3.2 삭제 파일

```
src/app/me/account/                       (디렉터리 전체)
src/app/me/bio/                           (디렉터리 전체)
src/app/me/newsletter/                    (디렉터리 전체)
src/app/me/notifications/preferences/     (디렉터리)
src/app/me/settings/preferences/          (디렉터리)
src/app/me/settings/sponsor-validity/     (디렉터리)
```

`/me/notifications/` 자체는 알림 inbox용도로 유지 가능 (preferences 서브만 제거).

---

## 4. Data Flow

### 4.1 인증/권한

각 sub-page는 기존 인증 패턴 유지:
- `tokenStore.get()` 체크 → 없으면 `router.replace("/login")`
- `fetchMe()` 호출 → role 검증 (필요 시)
- `useMe()` hook 활용 (보유 컴포넌트)

### 4.2 백엔드 API (변경 없음)

| Sub-page | 호출 API | 변경 |
|---------|---------|:----:|
| profile | `PATCH /me/bio`, `POST /me/bio/translate` | ❌ 없음 |
| display | `PATCH /me/preferences` | ❌ 없음 |
| accessibility | localStorage 기반 (서버 호출 없음) | ❌ 없음 |
| notifications | `PATCH /me/notifications`, `PATCH /me/newsletter` | ❌ 없음 |
| privacy | localStorage + PostHog opt-out | ❌ 없음 |
| account | `POST /auth/logout`, `GET /me/export`, `PATCH /me/sponsor-validity` | ❌ 없음 |

**Frontend-only refactor — backend 무영향**.

---

## 5. i18n Schema

### 5.1 신규 키 (14 keys × 5 locales = 70 entries)

```json
{
  "settings": {
    "hub": {
      "title": "설정",
      "subtitle": "프로필, 알림, 개인정보 등을 한 곳에서 관리합니다",
      "category": {
        "profile": {
          "title": "프로필",
          "description": "자기소개와 다국어 번역"
        },
        "display": {
          "title": "표시",
          "description": "언어와 통화 설정"
        },
        "accessibility": {
          "title": "접근성",
          "description": "대비, 폰트 크기"
        },
        "notifications": {
          "title": "알림",
          "description": "이메일·푸시 알림과 뉴스레터"
        },
        "privacy": {
          "title": "개인정보",
          "description": "데이터 수집 및 추적 옵션"
        },
        "account": {
          "title": "계정",
          "description": "인증, 데이터 내보내기, 후원 유효기간"
        }
      }
    }
  }
}
```

### 5.2 5 Locales

| Locale | 파일 |
|--------|------|
| ko (Korean) | `src/i18n/ko.json` |
| en (English) | `src/i18n/en.json` |
| ja (Japanese) | `src/i18n/ja.json` |
| zh (Chinese) | `src/i18n/zh.json` |
| es (Spanish) | `src/i18n/es.json` |

기존 sub-page 키 (`bio.*`, `preferences.*`, `accessibility.*`, `privacy.*`, 등) 변경 없음.

---

## 6. Accessibility

| 항목 | 구현 |
|------|------|
| aria-label | Hub 카드 각각 `aria-label={t("settings.hub.category.X.title")}` |
| 키보드 네비게이션 | 카드 `<a>` 태그 → tab 순회 + Enter 활성화 |
| 화면 낭독기 | semantic HTML (`<nav>` + `<a>` + `<h2>`) |
| 색상 대비 | 기존 디자인 토큰 사용 (WCAG AA 충족) |
| 폰트 크기 | rem 단위 (사용자 설정 존중) |

---

## 7. Link Update Map

| 파일 | 변경 횟수 | 변경 내용 |
|------|:--:|----------|
| `src/components/Sidebar.tsx` | 2 | `/me/account` → `/me/settings`, accessibility 별도 항목 제거 |
| `src/components/MobileTabBar.tsx` | 1 | `/me/settings/preferences` → `/me/settings` |
| `src/app/me/patronage/page.tsx` | 1 | `/me/account` → `/me/settings/account` |
| `src/app/legal/privacy/page.tsx` | 1 | `/me/account` → `/me/settings/account` |
| `src/app/me/settings/accessibility/page.tsx` | 1 | breadcrumb `/me/account` → `/me/settings` |
| `src/app/me/settings/privacy/page.tsx` | 1 | breadcrumb → `/me/settings` |

---

## 8. Testing

### 8.1 Frontend

- `npx tsc --noEmit` → 0 error
- 시각적 확인: Hub 카드 그리드 (mobile/tablet/desktop)
- 기존 URL 잔존 grep: `href="/me/account"`, `href="/me/bio"`, `href="/me/newsletter"`, `href="/me/notifications/preferences"`, `href="/me/settings/preferences"`, `href="/me/settings/sponsor-validity"` → 0건

### 8.2 Backend

- `pytest tests/` → 회귀 0 (backend 무변경)
- 787 → 780 차이는 별도 이슈 (GitHub OAuth tests 의도적 제거)

### 8.3 e2e (수동)

- 로그인 → `/me/settings` 진입 → 각 카드 클릭 → sub-page 정상 진입
- Sidebar → 설정 클릭 → Hub 진입
- 모바일 탭바 → 설정 아이콘 → Hub 진입

---

## 9. Migration / Rollout

| 단계 | 내용 |
|------|------|
| 1 | Hub 페이지 + 4 신규 sub-page 작성 |
| 2 | 2개 기존 sub-page (accessibility, privacy) breadcrumb 갱신 |
| 3 | 6개 기존 페이지 삭제 |
| 4 | 5개 파일 링크 갱신 |
| 5 | i18n 70 entries 추가 |
| 6 | tsc + 회귀 검증 |

**Rollback 전략**: git revert로 즉시 복원 가능 (frontend-only, DB 마이그레이션 없음).

---

## 10. Risks

| Risk | Impact | Mitigation |
|------|:--:|------|
| 외부 북마크 깨짐 | 중 | clean URL 우선 — 일회성 영향 |
| Sidebar prefix 매칭 오류 | 낮음 | `/me/settings/*` prefix `startsWith` 또는 정확 일치 사용 |
| i18n 키 누락 locale | 낮음 | 5 locale 일괄 추가 검증 |

---

## 11. Out-of-Scope

- 기존 페이지 내부 로직 변경 (이동/이름 변경만)
- 백엔드 API 변경
- 신규 설정 항목 추가
- 디자인 시스템 토큰 변경
- 모바일 native 앱 (별도 로드맵)

---

## 12. Version History

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 1.0 | 2026-05-11 | 초기 design (retroactive — 구현 후 정리) | itpe-ince |
