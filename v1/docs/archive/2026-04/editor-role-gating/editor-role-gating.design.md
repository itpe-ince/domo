---
template: design
version: 1.0
feature: editor-role-gating
date: 2026-04-29
author: itpe-ince (Claude Sonnet 4.6 + bkit frontend-architect agent)
project: domo
project_version: v1
status: Approved (Design) — Do 진입 가능
parent_plan: editor-role-gating.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
oq_resolved: 2026-04-29
---

# editor-role-gating Design Document

> **Summary**: 비작가 사용자가 상품 포스트 type을 선택하는 시점에 UI 차원에서 차단하고, 작가 신청 CTA를 인라인으로 노출한다. 백엔드 403 방어선은 이미 완전히 구현되어 있으므로 테스트 추가만 진행한다.

---

## 1. Architecture Overview

### 변경 영역 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│  /posts/new (page.tsx)                                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  useMe() → { me, loading }                               │   │
│  │  me.role: "user" | "artist" | "admin"                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  [NEW] PostTypeSelector                                  │   │
│  │  ├── props: value, onChange, userRole, disabled          │   │
│  │  ├── canCreateProduct = role === "artist" || "admin"     │   │
│  │  ├── [일반 포스트] 버튼 — 항상 활성                         │   │
│  │  └── [상품 포스트] 버튼                                     │   │
│  │       ├── canCreateProduct=true  → 클릭 가능               │   │
│  │       └── canCreateProduct=false → disabled + 인라인 안내  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
│                            ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  handleSubmit() Line 156 — role 검증 유지 (defense in depth) │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                             │
                    API call (type=product)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  POST /v1/posts (posts.py Line 200)                              │
│  └── role 검증 (Line 207): role not in ("artist","admin") → 403 │
│      [이미 구현 완료 — 변경 없음]                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 흐름

```
[useMe()] → me: ApiUser | null
  │
  ├── me == null (비로그인): PostTypeSelector disabled=true 전체
  │   → 클릭 시 LoginModal 트리거 (기존 동작, page.tsx에서 처리)
  │
  ├── me.loading == true: PostTypeSelector disabled=true 전체
  │   → type 선택 UI는 스켈레톤 없이 단순 비활성 처리
  │
  └── me != null:
      canCreateProduct = me.role === "artist" || me.role === "admin"
        ├── true:  product 버튼 활성, 기존 동작 유지
        └── false: product 버튼 disabled
                   버튼 하단 인라인 안내 렌더링
                   "작가 등록 후 작성 가능합니다" + "/artists/apply" 링크
```

---

## 2. Component Specification — `PostTypeSelector.tsx`

**파일 위치**: `v1/frontend/src/components/post-editor/PostTypeSelector.tsx`

### Props 인터페이스

```typescript
export type PostType = "general" | "product";

interface PostTypeSelectorProps {
  value: PostType;
  onChange: (value: PostType) => void;
  userRole: "user" | "artist" | "admin" | undefined;
  disabled?: boolean; // uploading/submitting 중 전체 비활성
}
```

**설계 근거**: `me` 객체 전체를 받지 않고 `userRole` 스칼라만 받는다. 이유:
- 컴포넌트의 단일 책임 — type 선택 + role 게이팅만 담당
- 테스트 작성 편의 (role 값만 주입하면 됨)
- `ApiUser` 타입 의존을 컴포넌트 외부로 격리
- `MediaToolbar`의 prop 패턴과 동일한 방식 (`disabled?: boolean` 스칼라 전달)

### 내부 상태

없음. **Controlled component** — 모든 상태는 `page.tsx`가 소유한다.

### 렌더 구조 (JSX 트리)

```
<div>                                    ← wrapper
  <div.pill-container>                   ← bg-surface rounded-full p-1 border border-border w-fit
    <button>[일반 포스트]</button>         ← 항상 활성
    <button>[상품 포스트]</button>         ← canCreateProduct에 따라 활성/비활성
  </div>
  {!canCreateProduct && (
    <p role="note">                      ← 인라인 안내 (비활성일 때만)
      작가 등록 후 작성 가능합니다{" "}
      <Link href="/artists/apply">작가 신청</Link>
    </p>
  )}
</div>
```

### 전체 구현 코드

```typescript
"use client";

import Link from "next/link";

export type PostType = "general" | "product";

interface PostTypeSelectorProps {
  value: PostType;
  onChange: (value: PostType) => void;
  userRole: "user" | "artist" | "admin" | undefined;
  disabled?: boolean;
}

export function PostTypeSelector({
  value,
  onChange,
  userRole,
  disabled = false,
}: PostTypeSelectorProps) {
  const canCreateProduct = userRole === "artist" || userRole === "admin";

  const baseBtnCls =
    "px-5 py-2 rounded-full text-sm transition-colors";
  const activeCls = "bg-primary text-background";
  const inactiveCls = "text-text-secondary";
  const disabledProductCls =
    "border-border text-text-muted bg-surface-hover/30 opacity-60 cursor-not-allowed";

  return (
    <div className="space-y-1.5">
      <div className="flex bg-surface rounded-full p-1 border border-border w-fit">
        {/* 일반 포스트 */}
        <button
          type="button"
          onClick={() => !disabled && onChange("general")}
          disabled={disabled}
          className={`${baseBtnCls} ${
            value === "general" ? activeCls : inactiveCls
          }`}
        >
          일반 포스트
        </button>

        {/* 상품 포스트 */}
        <button
          type="button"
          onClick={() => {
            if (disabled || !canCreateProduct) return;
            onChange("product");
          }}
          disabled={disabled || !canCreateProduct}
          aria-disabled={!canCreateProduct || disabled}
          title={
            !canCreateProduct
              ? "작가 등록 후 작성 가능합니다"
              : undefined
          }
          className={`${baseBtnCls} ${
            !canCreateProduct
              ? disabledProductCls
              : value === "product"
              ? activeCls
              : inactiveCls
          }`}
        >
          상품 포스트
        </button>
      </div>

      {/* 인라인 안내 (비작가일 때만) */}
      {!canCreateProduct && userRole !== undefined && (
        <p role="note" className="text-xs text-text-muted pl-1">
          작가 등록 후 작성 가능합니다.{" "}
          <Link
            href="/artists/apply"
            className="text-primary underline underline-offset-2 hover:opacity-80"
          >
            작가 신청
          </Link>
        </p>
      )}
    </div>
  );
}
```

**렌더 조건 상세**:

| userRole | canCreateProduct | 안내 텍스트 노출 |
|----------|-----------------|----------------|
| undefined (로딩 중) | false | 미노출 (userRole 조건) |
| "user" | false | 노출 |
| "artist" | true | 미노출 |
| "admin" | true | 미노출 |

### 접근성 (a11y)

| 항목 | 구현 | 이유 |
|------|------|------|
| `disabled` HTML 속성 | 사용 | 네이티브 포커스/이벤트 차단 |
| `aria-disabled="true"` | 추가 | `disabled`는 포커스를 잃어 스크린 리더가 읽지 못할 수 있음 — 병행 명시 |
| `title` 속성 | 비작가 시 안내 문구 | 툴팁 대체 텍스트 |
| `role="note"` | 인라인 안내 `<p>` | 보조 설명임을 스크린 리더에 명시 |
| `cursor-not-allowed` | Tailwind 클래스 | 시각적 차단 신호 |

### Tailwind 클래스 패턴

| 상태 | 클래스 |
|------|--------|
| 활성(선택됨) | `bg-primary text-background` |
| 비활성(선택 안 됨) | `text-text-secondary` |
| 상품 비활성 (비작가) | `border-border text-text-muted bg-surface-hover/30 opacity-60 cursor-not-allowed` |
| 전체 disabled | `disabled:opacity-30` (기존 `MediaToolbar.tsx` 패턴 동일) |

---

## 3. Page Integration — `posts/new/page.tsx`

### 기존 인라인 JSX 제거 범위

**Line 236–263** (아래 블록 전체를 `PostTypeSelector` 컴포넌트로 교체):

```tsx
// 제거 대상 (Line 236–263)
{/* Post type toggle */}
<div className="flex bg-surface rounded-full p-1 border border-border w-fit">
  <button
    onClick={() => setType("general")}
    className={...}
  >
    일반 포스트
  </button>
  <button
    onClick={() => setType("product")}
    className={...}
  >
    상품 포스트
  </button>
</div>
{type === "product" && me.role !== "artist" && me.role !== "admin" && (
  <p className="text-warning text-xs">
    상품 포스트는 작가 권한이 필요합니다.
  </p>
)}
```

### 신규 컴포넌트 사용 코드

**import 추가**:
```typescript
import { PostTypeSelector } from "@/components/post-editor/PostTypeSelector";
import type { PostType } from "@/components/post-editor/PostTypeSelector";
```

**state 타입 업데이트** (Line 62 근방, 현재 `"general" | "product"` 문자열 리터럴):
```typescript
// 변경 전
const [type, setType] = useState<"general" | "product">("general");

// 변경 후
const [type, setType] = useState<PostType>("general");
```

**JSX 교체** (Line 236–263 위치):
```tsx
<PostTypeSelector
  value={type}
  onChange={setType}
  userRole={me?.role}
  disabled={uploading || submitting}
/>
```

**`uploading` 상태**: `page.tsx`에 이미 `submitting` 상태가 존재한다. 파일 업로드 중 비활성이 필요하다면 `uploading` 상태를 `disabled`에 OR 조건으로 전달한다. 현재 `MediaToolbar`는 `disabled` prop 없이 사용되므로, 해당 state가 없다면 `submitting`만 사용한다.

### submit 시점 검증 유지 (Line 154–159)

```typescript
// 이 블록은 그대로 유지 — defense in depth
if (type === "product" && me?.role !== "artist" && me?.role !== "admin") {
  setError("상품 포스트는 작가만 작성할 수 있습니다.");
  return;
}
```

**유지 이유**: `PostTypeSelector`의 disabled 처리는 클릭 차단이지만, 직접 state 조작(개발자 도구, 미래 버그)에 의한 우회를 방어한다. 정상 사용 경로에서는 도달하지 않는다.

---

## 4. Backend Verification — `api/posts.py`

### 사전 조사 결과

**결론: role guard 이미 완전히 구현됨 — 코드 변경 없음**

`v1/backend/app/api/posts.py` Line 206–210:

```python
# 현재 구현 (변경 없음)
if body.type == "product" and user.role not in ("artist", "admin"):
    raise ApiError(
        "FORBIDDEN", "Only artists can create product posts", http_status=403
    )
```

- `get_current_user` 의존성으로 인증 필수
- `body.type == "product"` 조건 정확히 매칭
- `user.role not in ("artist", "admin")` — artist, admin 모두 허용
- `http_status=403` — 표준 Forbidden 응답

### 에러 응답 형식 (project envelope)

`ApiError` 클래스가 생성하는 응답 형식:

```json
{
  "detail": {
    "code": "FORBIDDEN",
    "message": "Only artists can create product posts"
  }
}
```

FastAPI의 `HTTPException` 래퍼를 통해 HTTP 403으로 반환된다. 프런트엔드 `ApiClientError` 처리 시 이 구조로 파싱된다.

---

## 5. Test Specification

### 백엔드 테스트 파일 생성

**파일 위치**: `v1/backend/tests/test_posts.py`

현재 프로젝트에 `v1/backend/tests/` 디렉토리가 존재하지 않으므로 신규 생성이 필요하다.

**테스트 인프라 확인 사항** (Do 단계에서 확인):
- `conftest.py` 위치 및 DB fixture 패턴
- FastAPI `TestClient` 또는 `AsyncClient` 사용 여부
- 테스트 DB 설정 방식 (SQLite in-memory vs. PostgreSQL test DB)

### 테스트 케이스 스펙

```python
# v1/backend/tests/test_posts.py

import pytest

# ─── test_create_product_post_as_user ────────────────────────────────────
# role="user" 사용자가 type="product" 포스트 생성 시도 → 403 반환
def test_create_product_post_as_user(client, user_token):
    """
    Given: role="user" 인증 토큰
    When:  POST /v1/posts (type="product")
    Then:  HTTP 403
           body.detail.code == "FORBIDDEN"
    """
    response = client.post(
        "/v1/posts",
        json={
            "type": "product",
            "title": "Test Product",
            "content": "content",
            "media": [],
            "product": {
                "is_auction": False,
                "is_buy_now": True,
                "buy_now_price": 100.0,
                "currency": "USD",
            },
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


# ─── test_create_product_post_as_artist ──────────────────────────────────
# role="artist" 사용자가 type="product" 포스트 생성 시도 → 200 반환
def test_create_product_post_as_artist(client, artist_token):
    """
    Given: role="artist" 인증 토큰
    When:  POST /v1/posts (type="product")
    Then:  HTTP 200
           body.data.type == "product"
    """
    response = client.post(
        "/v1/posts",
        json={
            "type": "product",
            "title": "Artist Product",
            "content": "artist content",
            "media": [],
            "product": {
                "is_auction": False,
                "is_buy_now": True,
                "buy_now_price": 150.0,
                "currency": "USD",
            },
        },
        headers={"Authorization": f"Bearer {artist_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["type"] == "product"


# ─── test_create_general_post_as_user ────────────────────────────────────
# role="user" 사용자가 type="general" 포스트 생성 → 200 (제한 없음)
def test_create_general_post_as_user(client, user_token):
    """
    Given: role="user" 인증 토큰
    When:  POST /v1/posts (type="general")
    Then:  HTTP 200
           일반 포스트 type은 role 제한 없음
    """
    response = client.post(
        "/v1/posts",
        json={
            "type": "general",
            "title": "General Post",
            "content": "anyone can post",
            "media": [],
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["type"] == "general"
```

### 프런트엔드 컴포넌트 테스트

현재 프로젝트에 컴포넌트 테스트 인프라(Jest, Vitest, Testing Library)가 확인되지 않으므로 **이번 PDCA 범위에서 제외**한다. Do 단계에서 `package.json`을 확인하여 인프라가 존재하면 추가 작성을 권장한다.

---

## 6. i18n Keys

### 추가 키 스펙

**파일**: `v1/frontend/src/i18n/ko.json`, `en.json`, `ja.json`, `zh.json`, `es.json`

`post` 네임스페이스에 2개 키 추가:

```json
// ko.json (현재 "post" 섹션 Line 97~120에 추가)
"post": {
  // ... 기존 키 유지 ...
  "type.product.disabledHint": "작가 등록 후 작성 가능합니다.",
  "type.product.applyLink": "작가 신청"
}
```

```json
// en.json
"type.product.disabledHint": "Available after artist registration.",
"type.product.applyLink": "Apply as artist"

// ja.json
"type.product.disabledHint": "アーティスト登録後に作成できます。",
"type.product.applyLink": "アーティスト申請"

// zh.json
"type.product.disabledHint": "成為藝術家後即可創作。",
"type.product.applyLink": "申請成為藝術家"

// es.json
"type.product.disabledHint": "Disponible después del registro de artista.",
"type.product.applyLink": "Solicitar como artista"
```

### i18n 적용 방식

현재 `page.tsx`에서 `useI18n()` 훅을 사용하나, `PostTypeSelector`는 독립 컴포넌트이므로 내부에서 직접 `useI18n()` 훅을 호출한다:

```typescript
import { useI18n } from "@/i18n";

// PostTypeSelector 내부
const { t } = useI18n();

// 사용
<p role="note">
  {t("post.type.product.disabledHint")}{" "}
  <Link href="/artists/apply">{t("post.type.product.applyLink")}</Link>
</p>
```

**MVP 단순화**: i18n 인프라 연동이 복잡하다면 한국어 하드코딩으로 시작하고, Act 단계에서 i18n 키로 교체한다. 프로젝트 우선 언어는 한국어이므로 허용 가능.

---

## 7. Notification Integration (Q-3 검증)

### 이미 동작하는 흐름 (코드 확인 완료)

| 단계 | 파일 / 위치 | 상태 |
|------|------------|------|
| 관리자 승인 → role 업데이트 | `api/admin/users.py` `approve_application()` | 구현됨 |
| 토큰 무효화 | `api/admin/users.py` Line 71: `revoke_user_tokens(reason="admin_role_change")` | 구현됨 |
| Notification 생성 | `api/admin/users.py` Line 97–105: `type="artist_approved"`, `title="작가 승인 완료"` | 구현됨 |
| 알림 메시지 텍스트 | `body="축하합니다! 작가 심사가 승인되었습니다."` | 구현됨 |
| 알림 링크 | `link="/profile"` | 구현됨 — `/posts/new?type=product` deep link는 nice-to-have |
| Frontend 토큰 갱신 감지 | `useMe.ts` Line 47–49: `AUTH_CHANGED_EVENT` listener | 구현됨 |

### 현재 알림 메시지 평가

- `title`: "작가 승인 완료" — 명확함, 변경 불요
- `body`: "축하합니다! 작가 심사가 승인되었습니다." — 적절함, 변경 불요
- `link`: "/profile" — 프로필로 이동. `/posts/new?type=product`로 변경하면 에디터 직행 가능 (nice-to-have, 이번 PDCA 범위 외)

### 이번 PDCA 추가 작업: 없음

기존 알림 메시지 텍스트가 충분하므로 fixture 업데이트 불필요. 알림 → 에디터 deep link는 Open Question으로 등록.

---

## 8. Edge Cases

| 케이스 | 처리 방식 | 근거 |
|--------|-----------|------|
| `me` 로딩 중 (`loading=true`) | `disabled={true}` 전체 → type 선택 버튼 모두 비활성 | `userRole=undefined` → `canCreateProduct=false` → product 버튼 비활성. 인라인 안내는 `userRole !== undefined` 조건으로 미노출 |
| 비로그인 (`me=null`) | `page.tsx`의 기존 `LoginModal` 로직이 처리 — `PostTypeSelector`까지 도달하지 않음 | Line 234: `{me && (` 블록 내에 PostTypeSelector 위치 |
| `role="admin"` | `canCreateProduct=true` → product 옵션 활성 | artist와 동일 처리 |
| 작가 신청 진행 중 (`status="pending"`) | 이번 PDCA scope 외. 현재는 "user" role이므로 product 비활성 처리됨 | Open Question으로 등록 |
| 좁은 모바일 화면 | 인라인 텍스트 방식이므로 레이아웃 안전. pill 컨테이너는 `w-fit`으로 내용에 맞게 조정됨 | 툴팁 불사용 결정 (Q-2)의 근거 |
| 작가 승인 직후 (role 갱신 전) | 기존 토큰 만료 → 401 → `AUTH_CHANGED_EVENT` → `useMe()` 갱신 → 재로그인 → 신규 토큰 | 자동 처리됨 (§7 참조) |

---

## 9. Migration & Rollout

- **무중단 배포 가능**: UI 개선 + 기존 검증 유지. 기존 artist 사용자에게 회귀 없음
- **Feature flag 불요**: 새 동작(비활성 처리)이 기존보다 더 안전하고, 기존 작가에게는 동일한 UX 제공
- **롤백 가능**: `PostTypeSelector` 교체 전 인라인 JSX로 되돌리면 원상 복구됨

---

## 10. Implementation Order

1. **(사전) `/artists/apply` 페이지 동작 상태 확인**
   - 파일: `v1/frontend/src/app/artists/apply/page.tsx` 존재 확인 완료
   - 실제 폼 제출 흐름 수동 확인 (R-2 대응)

2. **`PostTypeSelector.tsx` 신규 작성**
   - 파일: `v1/frontend/src/components/post-editor/PostTypeSelector.tsx`
   - i18n 키 추가 (5개 locale 파일)

3. **`page.tsx` 변경**
   - import 추가
   - `useState<PostType>` 타입 업데이트
   - Line 236–263 인라인 JSX → `<PostTypeSelector>` 교체
   - `disabled` prop에 `submitting` 상태 전달
   - Line 154–159 submit 차단 로직 유지 (변경 없음)

4. **백엔드 테스트 추가**
   - `v1/backend/tests/` 디렉토리 생성
   - `conftest.py` fixture 패턴 확인 후 `test_posts.py` 작성
   - 3개 케이스: user→403, artist→200, general→200

5. **수동 QA (AC-1~7)**
   - role="user": product 버튼 비활성 확인, 인라인 안내 노출, "/artists/apply" 링크 동작
   - role="artist": product 버튼 활성, 상품 필드 표시, 제출 성공
   - role="admin": artist와 동일
   - 비로그인: LoginModal 트리거 (회귀 없음)

---

## 11. Open Questions (Design 단계 발견) — RESOLVED

사용자 결정 완료 (2026-04-29).

### OQ-1. 작가 신청 진행 중 (status="pending") 안내 텍스트 변형 → **결정: B (포함)**

**구현 방식:**

1. 사용자의 작가 신청 상태를 가져오기 위한 API 활용:
   - 기존 `/v1/artists/applications/mine` (또는 동등) 엔드포인트 존재 여부 확인 필요
   - 없으면 `me` 객체에 `artist_application_status?: "none" | "pending" | "approved" | "rejected"` 같은 필드 추가 검토
   - 또는 별도 hook `useArtistApplicationStatus()` 신규 작성

2. `PostTypeSelector` props 확장:
   ```ts
   interface PostTypeSelectorProps {
     value: PostType;
     onChange: (value: PostType) => void;
     userRole: ApiUser["role"] | undefined;
     applicationStatus?: "none" | "pending" | "approved" | "rejected"; // ← 추가
     disabled?: boolean;
   }
   ```

3. 인라인 안내 텍스트 분기:
   - `applicationStatus === "pending"` → "작가 심사가 진행 중입니다 (보통 1-3일)" + 신청 페이지 link 대신 disabled
   - `applicationStatus === "rejected"` → "작가 신청이 반려되었습니다 → [재신청](/artists/apply)"
   - `none` 또는 undefined → 기존 안내 ("작가 등록 후 작성 가능합니다 → [작가 신청](/artists/apply)")

4. i18n 키 추가:
   - `post.type.product.disabledHintPending` — "작가 심사가 진행 중입니다 (보통 1-3일)"
   - `post.type.product.disabledHintRejected` — "작가 신청이 반려되었습니다"
   - `post.type.product.applyAgainLink` — "재신청"

5. **사전 조사 필요**: Do 단계 시작 시 `/v1/artists/applications/mine` 또는 `me` 응답 페이로드의 application status 필드 확인. 없을 경우 백엔드 schemas/users.py 의 `MeOut` 응답에 추가하거나 별도 API 호출.

### OQ-2. 알림 클릭 시 에디터 deep link → **결정: A (현재 `/profile` 유지)**

**근거:**

- 알림 시스템 UX 자체에 대한 광범위한 우려는 신규 sub-PDCA `#12 notifications-ux-audit`로 분리 (2026-04-29 추가)
- 본 PDCA는 좁게 유지 — 알림은 이미 `/notifications` 목록 페이지에 표시되며, 사이드바 BellIcon 에 unread 카운트도 표시됨
- 본 PDCA에서는 알림 deep link 변경하지 않음
- 다중 deep link, 사용자 메뉴 알림 항목 등은 #12에서 다룸

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-29 | Initial design — 사전 조사 반영 (backend role guard 이미 완전 구현 확인, 알림 텍스트 기존 양호), PostTypeSelector 전체 스펙 작성 | itpe-ince / Claude Sonnet 4.6 + bkit frontend-architect |
| 1.1 | 2026-04-29 | OQ-1=B (pending/rejected 안내 분기), OQ-2=A (deep link 변경 안 함, #12 sub-PDCA로 분리). Status: Draft → Approved (Design) | itpe-ince / Claude Opus 4.7 |
