# Analysis — settings-unification

> **Analysis Type**: Gap Analysis (Design vs Implementation, retroactive)
> **Project**: domo (v1)
> **Analyst**: itpe-ince (Claude Code, bkit-gap-detector)
> **Date**: 2026-05-11
> **Plan**: `v1/docs/01-plan/features/settings-unification.plan.md`
> **Design**: `v1/docs/02-design/features/settings-unification.design.md`

---

## 1. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Page Structure (Hub + 6 sub-pages) | 100% | ✅ |
| URL Routing (6 deletions + 2 retentions) | 100% | ✅ |
| Link Update Coverage (5+ files) | 100% | ✅ |
| i18n Coverage (70 entries × 5 locales) | 100% | ✅ |
| Residual URL Cleanliness | 100% | ✅ |
| Responsive Grid (1/2/3-col) | 100% | ✅ |
| Accessibility Pattern | 95% | ✅ (semantic variation) |
| Regression (tsc 0 / backend 780) | 100% | ✅ |
| **Overall Match Rate** | **99%** | ✅ |

---

## 2. Detailed Verification

### 2.1 Hub Page (`src/app/me/settings/page.tsx`)

| Design | 구현 | 상태 |
|---|---|:--:|
| Hub at `/me/settings` | `SettingsHubPage()` line 34 | ✅ |
| 6 categories | `CATEGORIES` const lines 21–32 | ✅ |
| Responsive 1/2/3-col | `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` line 51 | ✅ |
| Title/Subtitle i18n | `t("settings.hub.title")` / `subtitle` | ✅ |
| `aria-label` on cards | line 61 | ✅ |
| Keyboard nav | Next.js `<Link>` → `<a>` | ✅ |

### 2.2 Sub-pages (6개 모두 확인)

| Sub-page | 파일 | 이전 경로 명시 |
|---|---|:--:|
| profile | `profile/page.tsx` | "이전 경로: /me/bio" ✅ |
| display | `display/page.tsx` | "이전 경로: /me/settings/preferences" ✅ |
| accessibility | `accessibility/page.tsx` | (유지) ✅ |
| notifications | `notifications/page.tsx` | "이전 경로: /me/notifications/preferences + /me/newsletter" ✅ |
| privacy | `privacy/page.tsx` | (유지) ✅ |
| account | `account/page.tsx` | "이전 경로: /me/account + /me/settings/sponsor-validity" ✅ |

### 2.3 Deleted Directories (6개 모두 absent)

- `me/account/` ✅
- `me/bio/` ✅
- `me/newsletter/` ✅
- `me/notifications/preferences/` ✅
- `me/settings/preferences/` ✅
- `me/settings/sponsor-validity/` ✅

### 2.4 Link Updates

| 파일 | 변경 위치 | 상태 |
|---|---|:--:|
| `Sidebar.tsx` | line 129, 361 | ✅ |
| `MobileTabBar.tsx` | line 84 | ✅ |
| `me/patronage/page.tsx` | line 108 | ✅ |
| `legal/privacy/page.tsx` | line 98 | ✅ |
| `me/settings/accessibility/page.tsx` | breadcrumb line 21 | ✅ |
| `me/settings/privacy/page.tsx` | breadcrumb line 68 | ✅ |

### 2.5 i18n (70 entries × 5 locales)

`settings.hub` 트리 모든 locale 파일 line 1829 동일 위치 확인:

```
settings.hub
├── title (1)
├── subtitle (1)
└── category × 6 × {title, description} = 12
   = 14 keys total × 5 locales = 70 entries
```

### 2.6 Residual Cleanliness

`grep "href=.*deprecated"` on frontend src: **0건**.

추가 grep 발견 6 파일은 모두 정당:
- 4 sub-page `"이전 경로:"` 주석 — 마이그레이션 문서화 의도
- `lib/api.ts` — 백엔드 API 경로 (design §4.2 "backend 무영향" 명시)
- `PreferencesCard.tsx:6` JSDoc — **C-3 hot-fixed (`/me/settings/display` 갱신 완료)**

### 2.7 Regression

| Metric | Target | Actual |
|---|:--:|:--:|
| frontend tsc | 0 error | 0 ✅ |
| backend pytest | 회귀 0 | 780 passed ✅ |

---

## 3. Differences Found

### 3.1 🔴 Missing (Design O, Implementation X)

없음.

### 3.2 🟡 Added (Design X, Implementation O)

없음.

### 3.3 🔵 Changed (Design ≠ Implementation)

| # | 항목 | Design | 구현 | 영향 |
|:-:|---|---|---|:--:|
| C-1 | Hub icons | 🎨 display, 👤 account | 🌐 display, ⚙️ account | 낮음 — 의미 명확성 ↑ |
| C-2 | 시맨틱 구조 | `<nav>` + `<h2>` 카드별 | `role="list"` + `role="listitem"` + `<h1>` 페이지 | 낮음 — WCAG 동등 |
| C-3 | PreferencesCard JSDoc | display 경로 | preferences 경로 (stale) | 사소 — **hot-fix 완료** |

---

## 4. Match Rate Calculation

| 컴포넌트 | 가중치 | 점수 |
|---|:--:|:--:|
| Hub structure | 25% | 100% |
| URL routing | 20% | 100% |
| Link updates | 15% | 100% |
| i18n | 15% | 100% |
| Residual cleanliness | 10% | 100% |
| Responsive + Accessibility | 10% | 95% |
| Regression | 5% | 100% |
| **Weighted Total** | **100%** | **99.5%** |

**Final Match Rate: 99% (≥ 90% 충족)**

---

## 5. Recommended Actions

### 5.1 Immediate

- [x] `PreferencesCard.tsx:6` JSDoc `/me/settings/preferences` → `/me/settings/display` (완료)

### 5.2 Documentation Updates

- Design §2.2 ASCII diagram icons 갱신 (🌐 display, ⚙️ account) — trivial
- Design §6 Accessibility: `role="list"`/`role="listitem"` substitution 명시 — trivial

### 5.3 Approved As-Is

- 구조/라우팅/i18n/회귀 모든 핵심 요구사항: 100%
- 아이콘 선택 차이는 implementation discretion 범위

---

## 6. 결론

```
settings-unification Match Rate: 99% (≥ 90%)

✅ 회귀 0 + tsc 0 + 8 페이지 통합 + 70 i18n
✅ design-impl 일치도 거의 완벽
🔵 3개 minor (1개 hot-fix 완료, 2개는 design 문서 갱신만 권장)

권고: /pdca report settings-unification 진행 가능
```

---

## Version History

| 버전 | 날짜 | 변경 | 작성자 |
|------|:----:|------|--------|
| 0.1 | 2026-05-11 | 초기 분석. Match Rate 99% (4 minor → 1 hot-fix 적용). | itpe-ince |
