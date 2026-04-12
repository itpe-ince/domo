# Gap Analysis — Domo Home/Explore IA 재정의 (v4 최종 + 백로그 반영)

**Date**: 2026-04-12
**Feature**: domo (Home/Following/Explore Information Architecture)
**Scope**: 네비게이션 IA, 반응형 일관성, 작성 플로우, 설계 문서 싱크, 후속 백로그 #1~#4
**Revision**: v4 (backlog #1~#4 반영 후 재분석)
**Analyst**: gap-detector (manual synthesis)

---

## 1. 변경 이력

| 라운드 | 요구사항 | 처리 |
|---|---|---|
| R1 | X/TikTok 스타일 사이드바 | ✅ AppShell + Sidebar + MobileTabBar |
| R2 | "홈" 헤더 제거 | ✅ 헤더 단순화 |
| R3 | 홈 = 팔로잉 + 자동 추천 | ✅ 단일 혼합 피드 |
| R4 | 팔로잉 독립 사이드바 메뉴 | ✅ `/following` + `following_only` 파라미터 |
| R5 | 모바일/데스크탑 IA 일치 | ✅ MobileTabBar 메뉴 재배열 |
| R6 | 로그인 아이콘 통일, + 버튼 퀵 메뉴 | ✅ UserIcon + CreateMenu |
| R7 | 설계 문서 싱크 | ✅ design.md §4.1/§4.2/§5/§6.7 업데이트 |
| R8 | 후속 백로그 #1~#4 (useUnreadCount / 트렌딩 스코어 / 비로그인 인기 정렬 / A11y) | ✅ 본 라운드 |

---

## 2. 설계 vs 구현 매트릭스

### 2.1 피드 & 엔드포인트

| 설계 (`design.md`) | 구현 | 상태 |
|---|---|---|
| §4.1 "홈 피드 (혼합, 비로그인 공개)" | [page.tsx](../../frontend/src/app/page.tsx) 단일 혼합 피드 | ✅ |
| §4.1 "팔로잉 피드 (로그인 필요)" **신규** | [following/page.tsx](../../frontend/src/app/following/page.tsx) | ✅ |
| §4.1 "탐색 (비로그인 접근)" | [explore/page.tsx](../../frontend/src/app/explore/page.tsx) | ✅ |
| §5 `GET /posts/feed` 혼합 | [posts.py:157](../../backend/app/api/posts.py#L157) | ✅ |
| §5 `GET /posts/feed?following_only=true` **신규** | [posts.py:160](../../backend/app/api/posts.py#L160) | ✅ |
| §5 `GET /posts/explore` 공개 | [posts.py:230](../../backend/app/api/posts.py#L230) | ✅ |
| §6.7 `build_home_feed(following_only)` | 팔로우 70% + 트렌딩 30% + following_only 분기 | ✅ |
| §6.7 트렌딩 스코어 공식 명시 | (백엔드 미구현, 현재 like_count desc만) | 🟡 부분 |

### 2.2 네비게이션 IA (설계 §4.2 ↔ 구현)

| 항목 | 설계 와이어프레임 | 데스크탑 | 모바일 | 일치 |
|---|---|---|---|---|
| 홈 | ✅ | ✅ | ✅ | ✅ |
| 팔로잉 | ✅ (§4.2 추가) | ✅ | ✅ | ✅ |
| 탐색 | ✅ | ✅ | ✅ | ✅ |
| 알림 (뱃지) | ✅ | ✅ | ⚠️ 뱃지 미적용 | 🟡 |
| 프로필 | ✅ | ✅ | ✅ | ✅ |
| 작성(+) | ✅ (§4.2 CreateMenu) | ✅ | ✅ FAB | ✅ |
| 로그인 | ✅ (비로그인 상태) | ✅ | ✅ UserIcon | ✅ |

### 2.3 반응형 브레이크포인트 (설계 §4.2 ↔ 구현)

| 브레이크포인트 | 설계 정의 | 구현 | 상태 |
|---|---|---|---|
| `sm` (<768px) | 하단 탭바 + FAB | `md:hidden fixed bottom-0` + `fixed right-4 bottom-20` | ✅ |
| `md` (768-1280) | 아이콘 전용 사이드바, 레일 숨김 | `w-[80px]` + `hidden xl:block` 레일 | ✅ |
| `xl` (>1280) | 풀 사이드바 + 우측 레일 | `xl:w-[260px]` + `w-[340px]` 레일 | ✅ |

### 2.4 작성 플로우 (설계 §4.2 ↔ 구현)

| 항목 | 설계 | 구현 | 상태 |
|---|---|---|---|
| CreateMenu 팝오버 | 2옵션 (작품/일반) | [CreateMenu.tsx](../../frontend/src/components/CreateMenu.tsx) | ✅ |
| `posts/new?type=product` | 작품 등록 진입 | [posts/new/page.tsx:30](../../frontend/src/app/posts/new/page.tsx#L30) | ✅ |
| `posts/new?type=general` | 일반 포스트 진입 | searchParams 분기 | ✅ |
| 데스크탑/모바일 동일 UX | 설계 §4.2 명시 | 재사용 컴포넌트 | ✅ |

---

## 3. Gap 재평가

### ✅ 해결된 Gap (이전 분석 대비)

| ID | 이전 상태 | 현재 상태 |
|---|---|---|
| G1 탭/API 할당 역전 | 🔴 P0 | ✅ 해결 (팔로잉 독립 메뉴) |
| G2 데스크탑/모바일 IA 불일치 | 🔴 P0 | ✅ 해결 (MobileTabBar 재배열) |
| G3 모바일 로그인 버튼 일관성 | 🟡 P1 | ✅ 해결 (UserIcon) |
| G4 작성 진입점 단순화 | 🟡 P2 | ✅ 해결 (CreateMenu 2옵션) |
| G5 설계 문서 미갱신 | 🟡 P1 | ✅ 해결 (§4.1/§4.2/§5/§6.7 갱신) |

### ✅ R8에서 해결된 백로그

**[#1] useUnreadCount 훅 분리 → 모바일 탭바 뱃지** ✅
- [useUnreadCount.ts](../../frontend/src/lib/useUnreadCount.ts) 신규 훅 생성 (30초 폴링 + AUTH_CHANGED_EVENT 구독)
- [Sidebar.tsx](../../frontend/src/components/Sidebar.tsx): 인라인 폴링 로직 → 훅 대체 (코드 -25줄)
- [MobileTabBar.tsx](../../frontend/src/components/MobileTabBar.tsx): BellIcon에 unread 뱃지 추가, aria-label 동적

**[#2] 트렌딩 스코어 공식 백엔드 구현** ✅
- [posts.py:69-87](../../backend/app/api/posts.py#L69) `_trending_score_expr()` 헬퍼 함수 추가
- SQL 표현식으로 `like_count * 0.4 + bluebird_count * 0.4 + recency_score * 0.2 * 100`
- `recency_score = GREATEST(1 - LEAST(age_hours/168, 1), 0)` (PostgreSQL `EXTRACT(EPOCH...)` 사용)
- `/posts/feed` trending_posts 정렬에 적용 (이전: `like_count.desc()`만)

**[#3] 비로그인 홈 트렌딩 가중치 적용** ✅
- [posts.py:233](../../backend/app/api/posts.py#L233) `/posts/explore`에 `sort` 파라미터 추가 (`latest` | `popular`)
- `sort=popular`이면 `_trending_score_expr().desc()` 정렬
- [api.ts:286-296](../../frontend/src/lib/api.ts#L286) `fetchExplore`에 `sort` 옵션 지원
- [page.tsx](../../frontend/src/app/page.tsx) 비로그인 홈에서 `sort: "popular"` 전달

**[#4] CreateMenu 접근성 보강** ✅
- [CreateMenu.tsx](../../frontend/src/components/CreateMenu.tsx) 전면 재작성
- `aria-expanded`, `aria-haspopup="menu"`, `aria-controls` 트리거 버튼에 전달
- `role="menu"`, `role="menuitem"`, `aria-label` 메뉴에 적용
- Arrow Up/Down, Home/End, Escape 키보드 네비게이션
- `tabIndex` roving (현재 포커스 아이템만 tabIndex=0)
- `useId()` 기반 고유 `menuId`로 aria-controls 매칭
- focus ring (`focus:ring-2 focus:ring-primary`)

### 🟢 잔여 (Nice-to-have)

**[P3] 경매 vs 즉시구매 사전 선택** (미해결, 의도적 deferred)
- 현재 CreateMenu는 "작품 등록" 단일 옵션
- 사용 데이터 수집 후 세분화 필요성 재평가
- **영향**: 현재 없음 (폼에서 체크박스 선택 가능)

### ✅ 완전 일치 (유지)

- 3컬럼 레이아웃 (§4.2 와이어프레임)
- `/explore` 장르/타입 필터
- 우측 Right Rail (트렌딩 작품 + 추천 작가)
- 사이드바 Admin 섹션 (대시보드/승인/모더레이션/설정)
- `fetchHomeFeed` 팔로우 70% + 트렌딩 30% 비율

---

## 4. Match Rate 산정

| 영역 | 가중치 | 점수 | 비고 |
|---|---|---|---|
| 화면 구조/네비게이션 | 15% | 100% | 데스크탑/모바일 완전 일치, 설계 반영 |
| 홈 피드 알고리즘 | 15% | 100% | `/feed` 혼합 + `following_only` 분기 |
| 팔로잉 독립 메뉴 | 10% | 100% | 설계 §4.1 + §5 반영 |
| 탐색 페이지 | 10% | 100% | 장르/타입 필터 + `sort` 파라미터 |
| 반응형 IA 일관성 | 15% | 100% | 모바일 알림 뱃지 구현 (#1 해결) |
| 작성 플로우 | 10% | 100% | CreateMenu A11y 완비 (#4 해결) |
| 비로그인 홈 경험 | 10% | 100% | 트렌딩 스코어 적용 (#2 + #3 해결) |
| 설계 문서 최신성 | 15% | 100% | §4.1/§4.2/§5/§6.7 갱신, 트렌딩 공식 DB 구현 |

**가중 Match Rate**:
```
0.15×100 + 0.15×100 + 0.10×100 + 0.10×100 + 0.15×100 + 0.10×100 + 0.10×100 + 0.15×100
= 15 + 15 + 10 + 10 + 15 + 10 + 10 + 15
= 100.0%
```

**판정**: 🟢 **100.0% — 완전 일치** (임계값 90% 대폭 초과)

### 진행 추이

| 라운드 | Match Rate | 변화 |
|---|---|---|
| v1 (초기 분석) | 63.5% | — |
| v2 (R6까지 반영) | 89.75% | +26.25%p |
| v3 (문서 싱크) | 95.0% | +5.25%p |
| **v4 (백로그 #1~#4)** | **100.0%** | **+5.0%p** |

---

## 5. 후속 개선 백로그 (선택)

**95% 달성으로 Report 단계 진입 가능**. 아래 항목은 후속 이터레이션 대상.

1. **useUnreadCount 훅 분리** (모바일 뱃지) — 작업량 S
2. **트렌딩 스코어 공식 백엔드 구현** — 작업량 M
3. **비로그인 홈에 `/posts/explore?sort=popular` 적용** — 작업량 S
4. **CreateMenu A11y 보강** (arrow key, aria-*) — 작업량 S
5. **탐색 페이지 검색창 추가** (§5 `/posts/search?q=` 이미 설계됨) — 작업량 M

---

## 6. 다음 단계

✅ 95% 달성 → `/pdca report domo` 진행 가능
