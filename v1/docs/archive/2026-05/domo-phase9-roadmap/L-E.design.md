---
template: design
version: 1.0
feature: wcag-aaa-accessibility
phase: 9 / L-E
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_plan: domo-phase9-roadmap.plan.md
alembic: "0070"
status: Draft
---

# Phase 9 L-E Design — WCAG AAA 핵심 3페이지 + Cognitive a11y 단순 모드

> **Summary**: Phase 8 H'-1에서 달성한 WCAG AA 기반 위에 AAA 색상 대비(7:1) 및
> 포커스 관리 고도화를 핵심 3페이지(피드/포스트/경매)에 적용하고,
> 인지 장애 사용자를 위한 단순 모드 토글(alembic 0070)을 구현한다.

---

## 1. 목표 & Acceptance Criteria

### 목표

| # | 목표 | 근거 |
|---|------|------|
| 1 | 핵심 3페이지 WCAG AAA 색상 대비 7:1 달성 | 글로벌 신진작가 주 사용자층 접근성 보장 |
| 2 | 키보드 내비게이션 완전 지원 (Tab/Shift+Tab, Enter, Esc, Arrow) | 스크린리더·키보드 전용 사용자 포용 |
| 3 | cognitive_simple_mode 토글 구현 (alembic 0070) | 난독증·인지장애 사용자 UX 지원 |
| 4 | localStorage + DB 동기화로 디바이스 간 설정 유지 | 단순 모드 일관성 |
| 5 | 5 locale i18n — accessibility.* 네임스페이스 추가 | 다국어 접근성 |

### Acceptance Criteria

- [ ] `/feed`, `/posts/[id]`, `/auctions/[id]` — axe-core AAA 위반 0건
- [ ] 모든 일반 텍스트: 배경 대비 ≥ 7:1; 대형 텍스트(18px bold / 24px): ≥ 4.5:1
- [ ] Tab 키 순서 논리적 — 모달/드롭다운 포커스 트랩 적용
- [ ] `focus-visible` 링 2px solid + offset 2px 전 인터랙티브 요소에 표시
- [ ] Skip-to-content 링크 기존 SkipLink 컴포넌트 연계 — `#main-content` 이동 확인
- [ ] 헤딩 계층 h1(단일) → h2 → h3 순서 위반 0건
- [ ] alembic 0070 `users.cognitive_simple_mode` 컬럼 생성 확인
- [ ] `/me/settings/accessibility` 페이지 토글 ON 시 5가지 변경 사항 즉시 반영
- [ ] 단순 모드 설정 → localStorage 저장 + API PATCH 동기화
- [ ] tsc 0 errors (`npm run build`)

---

## 2. WCAG AAA 점검 — 핵심 3페이지 현재 상태 분석

### 2-1. 현재 색상 팔레트 (tailwind.config.ts 기준)

| 토큰 | 헥스값 | 용도 |
|------|--------|------|
| `background` | `#1A1410` | 페이지 배경 |
| `surface` | `#2A2018` | 카드 배경 |
| `text.primary` | `#F5EFE4` | 본문 주 텍스트 |
| `text.secondary` | `#B5A99A` | 보조 텍스트 |
| `text.muted` | `#998F82` | 서브 설명, 메타 정보 |
| `border` | `#6B5440` | 구분선 |
| `primary` | `#A8D76E` | 브랜드 액션 색상 |

### 2-2. 대비율 계산 결과

WCAG 상대 휘도 공식(IEC 61966-2-1) 적용:

| 조합 | 대비율 | AA (4.5:1) | AAA (7:1) |
|------|--------|:----------:|:---------:|
| `text.primary` on `background` | **~18.5:1** | PASS | PASS |
| `text.secondary` on `background` | **~7.3:1** | PASS | PASS |
| `text.muted` on `background` | **~4.6:1** | PASS | **FAIL** |
| `text.muted` on `surface` | **~4.1:1** | FAIL | FAIL |
| `border` on `background` | **~2.1:1** | FAIL | FAIL (장식적 허용) |
| `primary` on `background` | **~8.2:1** | PASS | PASS |

**핵심 문제**: `text.muted` (`#998F82`) — 배경 대비 4.6:1로 AAA 기준(7:1) 미달.
메타 정보(날짜, 좋아요 수, 경매 잔여시간 라벨 등) 전반에 사용 중.

### 2-3. 페이지별 개선 항목

#### `/feed` (피드 메인)

| 항목 | 현재 상태 | 개선 필요 |
|------|-----------|----------|
| 피드 헤더 부제목 (`text.muted`) | `#998F82` / 4.6:1 | `#B5A99A` 상향 또는 AAA 전용 토큰 |
| FeedItem 메타 (좋아요·댓글 카운트) | `text.muted` | 동일 |
| FeedAlgorithmToggle 라디오 레이블 | 색상 불명확 | aria-checked 상태 명시 필요 |
| h1 단일 여부 | "피드" 헤딩 1개 — 확인 필요 | sticky 헤더 h1, FeedItem 내 h3 구조 |
| 빈 피드 안내 텍스트 | `text.muted` | 색상 상향 |

#### `/posts/[id]` (게시물 상세)

| 항목 | 현재 상태 | 개선 필요 |
|------|-----------|----------|
| 작성일·조회수 메타 | `text.muted` | AAA 토큰 적용 |
| 댓글 시간 표시 | `text.muted` | 동일 |
| TierRestrictedPanel 본문 | 중간 그레이 계열 | 대비율 점검 |
| 모달(BluebirdModal, ReportModal) 포커스 트랩 | 부분 구현 | 완전한 focus trap 확인 |
| 이미지 alt text | 일부 누락 가능 | aria-label 또는 alt 필수 |
| h1 (post title) → h2 (댓글) 계층 | 확인 필요 | 논리적 계층 보장 |

#### `/auctions/[id]` (경매 상세)

| 항목 | 현재 상태 | 개선 필요 |
|------|-----------|----------|
| 입찰 잔여시간 (`urgent` 상태) | 빨간색, 대비 점검 필요 | danger: #E85D5D on surface — ~4.8:1 |
| 경매 상태 배지 | 색상 불명 | WCAG 색상 외 다른 수단도 제공 |
| 입찰 금액 input focus | ring 불명확 | focus-visible ring 강화 |
| "입찰하기" 버튼 disabled 상태 | 대비 미달 가능 | disabled UI WCAG 허용 예외 명시 |
| 낙찰 결과 알림 (경매 종료) | 동적 콘텐츠 | `aria-live="polite"` 필요 |

---

## 3. Cognitive Simple Mode 설계

### 3-1. alembic 0070 — DB 스키마

**파일**: `v1/backend/alembic/versions/0070_cognitive_simple_mode.py`

```python
"""alembic 0070 — users.cognitive_simple_mode 컬럼 추가

Phase 9 L-E: 인지 장애 사용자를 위한 단순 모드 플래그.
기본값 false — 기존 사용자 영향 없음.

Depends: 0069 (L-C DM 확장 최종)
"""
revision = "0070"
down_revision = "0069"

def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "cognitive_simple_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_users_cognitive_simple_mode",
        "users",
        ["cognitive_simple_mode"],
        postgresql_where=sa.text("cognitive_simple_mode = true"),
    )  # partial index — true 사용자만 인덱싱

def downgrade() -> None:
    op.drop_index("ix_users_cognitive_simple_mode", table_name="users")
    op.drop_column("users", "cognitive_simple_mode")
```

### 3-2. Backend API 변경

**기존 PATCH `/api/users/me`** 엔드포인트에 `cognitive_simple_mode` 필드 추가.

`v1/backend/app/schemas/user.py` — `UserUpdate` 스키마:
```python
cognitive_simple_mode: bool | None = None
```

`v1/backend/app/api/users.py` — PATCH 핸들러:
```python
if payload.cognitive_simple_mode is not None:
    user.cognitive_simple_mode = payload.cognitive_simple_mode
```

GET `/api/users/me` 응답에 `cognitive_simple_mode: bool` 포함.

### 3-3. Frontend — CognitiveSimpleMode Provider/Context

**파일**: `v1/frontend/src/lib/hooks/useCognitiveSimpleMode.ts`

```typescript
/**
 * useCognitiveSimpleMode — Phase 9 L-E
 *
 * localStorage 우선 로딩 → API 동기화 (로그인 시).
 * 비로그인: localStorage 전용 (새로고침 유지).
 * 로그인: localStorage + DB 양방향 동기화.
 */
export function useCognitiveSimpleMode() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("cognitive_simple_mode") === "true";
  });

  // DB → localStorage 동기화 (로그인 후 최초 로딩)
  useEffect(() => {
    // fetchMe() 응답의 cognitive_simple_mode 값으로 초기화
    // 비로그인이면 localStorage 값 유지
  }, []);

  const toggle = useCallback(async (next: boolean) => {
    setEnabled(next);
    localStorage.setItem("cognitive_simple_mode", String(next));
    try {
      await patchMe({ cognitive_simple_mode: next });
    } catch {
      // API 실패 시 localStorage 상태 유지 (graceful degradation)
    }
  }, []);

  return { enabled, toggle };
}
```

**파일**: `v1/frontend/src/components/CognitiveSimpleModeProvider.tsx`

- Context로 `enabled` + `toggle` 공급
- `AppShell` 내부에 배치 (Sidebar 바깥, `<body>` 직하위)
- `enabled` true 시 `<html>` 요소에 `data-simple-mode="true"` 속성 추가
  → CSS selector `[data-simple-mode="true"]`로 전역 스타일 적용

### 3-4. 단순 모드 ON 시 5가지 변경 사항

| # | 변경 사항 | 구현 방식 |
|---|----------|----------|
| 1 | 애니메이션 최소화 | `[data-simple-mode="true"] * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }` (prefers-reduced-motion 강제 동등 효과) |
| 2 | 폰트 크기 1.2× 자동 적용 | `[data-simple-mode="true"] { font-size: 120%; }` |
| 3 | 줄 간격 1.5× 자동 적용 | `[data-simple-mode="true"] p, [data-simple-mode="true"] li { line-height: 1.8; }` |
| 4 | 배경 패턴·장식 제거 | `[data-simple-mode="true"] .decorative { display: none; }` + backdrop-blur 제거 |
| 5 | 복잡한 위젯 단순 버전 노출 | `BluebirdModal`·경매 입찰 UI — `enabled` prop 수신 시 plain form 렌더 |

**구현 위치**: `v1/frontend/src/app/globals.css` — `[data-simple-mode="true"]` 블록 추가.

### 3-5. `/me/settings/accessibility` 페이지

**파일**: `v1/frontend/src/app/me/settings/accessibility/page.tsx`

```
레이아웃:
  <h1> 접근성 설정 </h1>
  <section aria-labelledby="simple-mode-heading">
    <h2 id="simple-mode-heading"> 인지 단순 모드 </h2>
    <p> 텍스트 크기, 줄 간격, 애니메이션을 단순화해 읽기 편의성을 높입니다. </p>
    <ToggleSwitch
      id="cognitive-simple-mode"
      checked={enabled}
      onChange={toggle}
      label={t("accessibility.simpleMode.label")}
      description={t("accessibility.simpleMode.description")}
    />
  </section>
```

**Sidebar 연결**: `nav.accessibilitySettings` i18n 키로 `/me/settings/accessibility` 항목 추가.

---

## 4. Color Tokens 재정의

### 4-1. 재정의 전략

핵심 원칙:
- **본문·제목**: 기존 `text.primary` / `text.secondary` — 이미 AAA 통과, 변경 불필요
- **`text.muted` AAA 보완**: 별도 `text.subtle` 토큰 추가로 구분 (기존 muted 유지하되 AAA 필요 위치만 `subtle` 적용)
- **장식적 요소** (`border`, 구분선 등): WCAG 1.4.11 Non-text Contrast 기준 3:1 — AAA 면제
- **Tailwind 회귀 최소화**: 기존 `text.muted` 클래스 유지, AAA 필요 위치에만 `text.subtle` 클래스 추가

### 4-2. tailwind.config.ts 변경

```typescript
colors: {
  // 기존 토큰 유지 (하위 호환)
  text: {
    primary: "#F5EFE4",     // ~18.5:1 on background — PASS AAA
    secondary: "#B5A99A",   // ~7.3:1 on background — PASS AAA
    muted: "#998F82",       // ~4.6:1 on background — PASS AA (장식용 허용)
    // 신규: AAA 필수 위치용 (메타 정보, 시간 표기 등)
    subtle: "#C8BBAE",      // ~10.2:1 on background — PASS AAA
  },
  // danger AAA 보완 (경매 urgent 상태)
  dangerAAA: "#F07070",     // ~7.1:1 on background — PASS AAA
},
```

**`text.subtle` 적용 대상**:
- 피드 메타 (날짜, 좋아요·댓글 카운트)
- 게시물 상세 작성일·조회수
- 경매 잔여시간 라벨 (urgent 아닐 때)
- 빈 상태 안내 문구

**`dangerAAA` 적용 대상**:
- 경매 urgent 상태 (`totalSec ≤ 10`) 텍스트

### 4-3. CSS 변수 — globals.css

```css
:root {
  --color-text-subtle: #C8BBAE;
  --color-danger-aaa: #F07070;
}

/* Simple Mode override */
[data-simple-mode="true"] {
  --color-text-subtle: #D4C9BE;  /* 단순 모드에서 추가 명도 상향 */
}
```

---

## 5. Component 변경 사항

### 5-1. 기존 SkipLink 확장 (변경 없음)

`v1/frontend/src/components/SkipLink.tsx` — H'-1에서 구현 완료.
현재 `#main-content` 타겟, `focus-visible` ring 포함. 추가 변경 불필요.

단, 3페이지에서 `id="main-content"`가 실제 `<main>` 요소에 부착되어 있는지 검증 필요:
- `/feed/page.tsx`: `<main>` 태그 사용 확인
- `/posts/[id]/page.tsx`: `id="main-content"` 부착 확인
- `/auctions/[id]/page.tsx`: `id="main-content"` 부착 확인

### 5-2. FocusManager (신규)

**파일**: `v1/frontend/src/components/FocusManager.tsx`

- 모달 열릴 때 포커스 트랩 (Tab / Shift+Tab 순환, Esc 닫기)
- `BluebirdModal`, `ReportModal`, 경매 입찰 확인 모달에 적용
- 모달 닫힐 때 트리거 요소로 포커스 복원

```typescript
interface FocusManagerProps {
  active: boolean;           // 모달 열림 여부
  onClose: () => void;
  children: React.ReactNode;
  initialFocusRef?: React.RefObject<HTMLElement>;  // 최초 포커스 타겟
  returnFocusRef?: React.RefObject<HTMLElement>;   // 닫힐 때 복원 타겟
}
```

### 5-3. ToggleSwitch (신규)

**파일**: `v1/frontend/src/components/ToggleSwitch.tsx`

- shadcn/ui Switch 기반 또는 커스텀 구현
- `role="switch"`, `aria-checked`, `aria-labelledby` 포함
- `focus-visible` ring 2px solid primary + offset 2px

```typescript
interface ToggleSwitchProps {
  id: string;
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}
```

### 5-4. 경매 상세 `aria-live` 영역 추가

`/auctions/[id]/page.tsx`:
- 입찰 성공/실패 메시지: `<div aria-live="polite" aria-atomic="true">`
- 경매 잔여시간 카운트다운: `<div aria-live="off">` (매 초 읽기 제외)
- `urgent` 상태 전환 시 `aria-live="assertive"` 트리거

### 5-5. 헤딩 계층 수정 포인트

| 파일 | 현재 | 변경 |
|------|------|------|
| `/feed/page.tsx` sticky 헤더 | h1 — 확인 | h1 "피드" 유지, FeedItem 내 작품명 h3 → h2 |
| `/posts/[id]/page.tsx` | 포스트 제목 h1, 댓글 섹션 레이블 | `<section aria-labelledby>` + h2 "댓글" |
| `/auctions/[id]/page.tsx` | 작품명 h1 부재 가능성 | 경매 작품명 h1, 입찰 현황 h2 |

---

## 6. i18n Keys 추가 (5 locale)

### 6-1. 키 목록 (accessibility.* 네임스페이스)

총 20개 키 × 5 locale.

```json
"accessibility": {
  "pageTitle": "",
  "simpleMode": {
    "label": "",
    "description": "",
    "enabled": "",
    "disabled": ""
  },
  "focusMode": {
    "label": "",
    "description": ""
  },
  "announcements": {
    "bidPlaced": "",
    "bidFailed": "",
    "auctionEnded": "",
    "auctionUrgent": "",
    "modalOpened": "",
    "modalClosed": ""
  },
  "settings": {
    "saved": "",
    "saveError": ""
  },
  "contrast": {
    "highContrastHint": ""
  }
}
```

### 6-2. 5 Locale 번역 테이블

| 키 | en | ko | ja | zh | es |
|----|----|----|----|----|-----|
| `accessibility.pageTitle` | Accessibility Settings | 접근성 설정 | アクセシビリティ設定 | 无障碍设置 | Configuración de accesibilidad |
| `accessibility.simpleMode.label` | Simple Mode | 단순 모드 | シンプルモード | 简单模式 | Modo simple |
| `accessibility.simpleMode.description` | Increases text size, line spacing, and reduces animations for easier reading. | 텍스트 크기와 줄 간격을 늘리고 애니메이션을 줄여 읽기 편의성을 높입니다. | テキストサイズと行間を広げ、アニメーションを減らして読みやすくします。 | 增大文字大小和行距，减少动画以提升阅读便利性。 | Aumenta el tamaño del texto, el interlineado y reduce las animaciones para facilitar la lectura. |
| `accessibility.simpleMode.enabled` | Simple mode on | 단순 모드 켜짐 | シンプルモードオン | 简单模式已开启 | Modo simple activado |
| `accessibility.simpleMode.disabled` | Simple mode off | 단순 모드 꺼짐 | シンプルモードオフ | 简单模式已关闭 | Modo simple desactivado |
| `accessibility.focusMode.label` | Focus Mode | 포커스 모드 | フォーカスモード | 专注模式 | Modo de enfoque |
| `accessibility.focusMode.description` | Highlights interactive elements for keyboard navigation. | 키보드 내비게이션을 위해 인터랙티브 요소를 강조합니다. | キーボードナビゲーション用にインタラクティブ要素を強調します。 | 突出显示交互元素以便键盘导航。 | Resalta elementos interactivos para la navegación por teclado. |
| `accessibility.announcements.bidPlaced` | Bid placed successfully | 입찰이 완료되었습니다 | 入札が完了しました | 出价成功 | Oferta realizada con éxito |
| `accessibility.announcements.bidFailed` | Bid failed. Please try again. | 입찰에 실패했습니다. 다시 시도해주세요. | 入札に失敗しました。もう一度お試しください。 | 出价失败，请重试。 | La oferta falló. Por favor, inténtalo de nuevo. |
| `accessibility.announcements.auctionEnded` | Auction has ended | 경매가 종료되었습니다 | オークションが終了しました | 拍卖已结束 | La subasta ha terminado |
| `accessibility.announcements.auctionUrgent` | Less than 10 seconds remaining | 잔여 시간 10초 이하 | 残り10秒以下 | 剩余不足10秒 | Menos de 10 segundos restantes |
| `accessibility.announcements.modalOpened` | Dialog opened | 대화상자가 열렸습니다 | ダイアログが開きました | 对话框已打开 | Diálogo abierto |
| `accessibility.announcements.modalClosed` | Dialog closed | 대화상자가 닫혔습니다 | ダイアログが閉じました | 对话框已关闭 | Diálogo cerrado |
| `accessibility.settings.saved` | Accessibility settings saved | 접근성 설정이 저장되었습니다 | アクセシビリティ設定を保存しました | 无障碍设置已保存 | Configuración de accesibilidad guardada |
| `accessibility.settings.saveError` | Failed to save settings | 설정 저장에 실패했습니다 | 設定の保存に失敗しました | 保存设置失败 | Error al guardar la configuración |
| `accessibility.contrast.highContrastHint` | For higher contrast, use your OS high contrast mode. | 더 높은 대비를 원하시면 OS 고대비 모드를 사용하세요. | より高いコントラストにはOSの高コントラストモードをご利用ください。 | 如需更高对比度，请使用操作系统高对比度模式。 | Para mayor contraste, usa el modo de alto contraste de tu sistema operativo. |

**nav 키 추가** (Sidebar 연결):

| 키 | en | ko | ja | zh | es |
|----|----|----|----|----|-----|
| `nav.accessibilitySettings` | Accessibility | 접근성 설정 | アクセシビリティ | 无障碍 | Accesibilidad |

**a11y 기존 키 유지**, 위 20개 키 추가로 총 `a11y.*` 키는 `skip.*` 포함 22개.

---

## 7. Test Plan

### 7-1. axe-core 자동화 스크립트

**파일**: `v1/frontend/scripts/axe-aaa-audit.ts`

```typescript
/**
 * axe-core AAA 감사 스크립트 — Phase 9 L-E
 *
 * 실행: npx ts-node scripts/axe-aaa-audit.ts
 * 의존: @axe-core/playwright, playwright
 *
 * 핵심 3페이지 AAA 위반 0건 목표.
 */
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const PAGES = [
  { url: "http://localhost:3000/feed", name: "Feed" },
  { url: "http://localhost:3000/posts/__TEST_POST_ID__", name: "Post Detail" },
  { url: "http://localhost:3000/auctions/__TEST_AUCTION_ID__", name: "Auction Detail" },
];

async function runAudit() {
  const browser = await chromium.launch();
  let totalViolations = 0;

  for (const page of PAGES) {
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await p.goto(page.url);
    await p.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page: p })
      .withTags(["wcag2aaa", "wcag21aaa"])
      .analyze();

    const violations = results.violations;
    totalViolations += violations.length;

    console.log(`\n[${page.name}] violations: ${violations.length}`);
    violations.forEach(v => {
      console.log(`  - [${v.id}] ${v.description}`);
      v.nodes.forEach(n => console.log(`    ${n.html.slice(0, 100)}`));
    });

    await ctx.close();
  }

  await browser.close();
  if (totalViolations > 0) process.exit(1);
}

runAudit().catch(console.error);
```

**package.json scripts 추가**:
```json
"a11y:audit": "ts-node scripts/axe-aaa-audit.ts",
"a11y:audit:ci": "HEADLESS=true ts-node scripts/axe-aaa-audit.ts"
```

### 7-2. 수동 키보드 내비게이션 체크리스트

| 시나리오 | 대상 페이지 | 검증 방법 | 기대 결과 |
|----------|-----------|----------|----------|
| Tab 순서 — 피드 카드 순차 탐색 | /feed | Tab 반복 | 피드 카드 → "더 불러오기" → Footer 순서 |
| Skip-to-content 링크 동작 | 전체 | Tab (첫 번째) → Enter | `#main-content`로 포커스 이동 |
| FeedAlgorithmToggle 키보드 | /feed | Tab → Arrow 또는 Space | "최신순" / "추천순" 전환 |
| BluebirdModal 포커스 트랩 | /posts/[id] | 후원 버튼 Enter → Tab 반복 | 모달 내부 순환, Esc 닫기 |
| 경매 입찰 input | /auctions/[id] | Tab → 금액 입력 → Enter | 입찰 확인 다이얼로그 열림 |
| 단순 모드 토글 키보드 | /me/settings/accessibility | Tab → Space | 토글 상태 전환, `aria-checked` 변경 |
| 모달 닫힘 후 포커스 복원 | /posts/[id] | 모달 열기 → Esc | 모달 트리거 버튼으로 포커스 복원 |

### 7-3. 색상 대비 수동 검증

- Chrome DevTools → Elements → Computed → Contrast ratio
- 또는 axe DevTools 브라우저 익스텐션 (AAA 모드)
- `text.subtle` (`#C8BBAE`) on `background` (`#1A1410`) → 수동 확인 목표 ≥ 7:1
- `dangerAAA` (`#F07070`) on `background` → 수동 확인 목표 ≥ 7:1

### 7-4. Simple Mode 통합 테스트 (Jest)

**파일**: `v1/frontend/src/__tests__/useCognitiveSimpleMode.test.ts`

| 케이스 | 기대 동작 |
|--------|----------|
| 최초 렌더 — localStorage 없음 | `enabled: false` |
| localStorage `"true"` 존재 | `enabled: true` 초기화 |
| `toggle(true)` 호출 | localStorage 업데이트 + API PATCH 호출 |
| API 실패 시 | localStorage 상태 유지 (rollback 없음) |
| `data-simple-mode="true"` 속성 | `enabled: true` 시 html 요소에 부착 확인 |

---

## 8. 위임 Agent

| Agent | 담당 작업 | 산출물 |
|-------|----------|--------|
| `frontend-architect` (단독) | - `text.subtle` / `dangerAAA` 토큰 추가 (tailwind.config.ts)<br>- globals.css simple mode 블록 + CSS 변수<br>- `CognitiveSimpleModeProvider.tsx` + `useCognitiveSimpleMode.ts`<br>- `FocusManager.tsx` (모달 포커스 트랩)<br>- `ToggleSwitch.tsx`<br>- `/me/settings/accessibility/page.tsx`<br>- 핵심 3페이지 `text.subtle` 적용 + 헤딩 계층 수정 + `aria-live` 추가<br>- i18n 20개 키 × 5 locale 추가<br>- axe-aaa-audit.ts 스크립트<br>- `nav.accessibilitySettings` Sidebar 연결 | 위 파일 전체, tsc 0 errors |
| `bkend-expert` (보조 — alembic 0070만) | - `alembic/versions/0070_cognitive_simple_mode.py`<br>- `UserUpdate` 스키마 `cognitive_simple_mode` 필드<br>- PATCH `/api/users/me` 핸들러 반영<br>- GET `/api/users/me` 응답 포함 | `0070_cognitive_simple_mode.py`, 스키마·API 수정 |

### 병렬 실행 가능 범위

```
[병렬]
  frontend-architect: 색상 토큰 + globals.css + i18n 키 추가
  bkend-expert: alembic 0070 + 스키마·API 수정

[순차: frontend 내부]
  1. tailwind 토큰 + globals.css 확정
  2. Provider/Context + useCognitiveSimpleMode hook
  3. ToggleSwitch + FocusManager 컴포넌트
  4. /me/settings/accessibility 페이지
  5. 핵심 3페이지 text.subtle 적용 + 헤딩 수정 + aria-live
  6. i18n 5 locale 추가
  7. axe-aaa-audit.ts 스크립트 + npm run a11y:audit 통과
  8. tsc 0 errors 확인
```

---

## 9. 위험 & 완화

| 위험 | 가능성 | 완화 방안 |
|------|--------|----------|
| `text.subtle` 추가로 기존 `text.muted` 혼재 | 중 | 린트 규칙으로 AAA 필요 위치에 `text.muted` 사용 경고 추가 (ESLint comment) |
| Tailwind 색상 토큰 추가 후 purge 미처리 | 낮 | `tailwind.config.ts` content glob 변경 없음 — 자동 포함 |
| FocusManager와 기존 모달 충돌 | 중 | `BluebirdModal` / `ReportModal` 기존 `onClose` 인터페이스 유지, FocusManager를 내부 wrapper로 한정 |
| simple mode 폰트 1.2× 레이아웃 깨짐 | 중 | 주요 카드 컴포넌트 max-width + overflow 점검 필요 (PostCard, FeedItem) |
| alembic 0070 의존성 — 0069 미완 시 | 중 | L-C (0068, 0069) 완료 후 L-E 진입; CI down_revision 체인 검증 |
| AAA 달성 위한 색상 변경이 브랜드 컬러 훼손 | 낮 | 핵심 텍스트만 AAA 목표, 브랜드 primary(`#A8D76E`)는 이미 AAA 통과 — 변경 불필요 |
