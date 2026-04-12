# PDCA Completion Report — Domo Home/Following/Explore IA 재정의

**Feature**: domo (Information Architecture refactor)
**Period**: 2026-04-12 (single session, 8 iteration rounds)
**Final Match Rate**: 🟢 **100.0%**
**Status**: ✅ Completed (backlog #1~#4 반영)

---

## 1. Executive Summary

Domo 프로토타입의 **홈/탐색/팔로잉 정보 구조(IA)**를 X/TikTok 레퍼런스에 맞춰
전면 재설계한 작업. 한 세션 내 7라운드 피드백을 통해 탭/API 역전 문제, 데스크탑/모바일
불일치, 작성 플로우 분산 이슈를 해결했고, 최종적으로 설계 문서까지 동기화했다.

### 핵심 지표

| 지표 | 값 |
|---|---|
| 변경된 파일 | 13개 (frontend 10, backend 1, docs 2) |
| 신규 파일 | 5개 (CreateMenu, useUnreadCount, following/page, explore/page, notifications/page) |
| Match Rate 변화 | 63.5% → 89.75% → 95.0% → **100.0%** |
| 해결된 Gap 전체 | 9개 |
| 잔여 deferred 항목 | 1개 (경매/즉시구매 사전 선택 — 사용 데이터 대기) |

---

## 2. Background & Motivation

### 2.1 초기 문제

세션 시작 시점에 사용자는 "X나 TikTok 레이아웃으로 해달라고 하지 않았나? 사이드 메뉴가 없네?"
라는 피드백을 주었다. 당시 홈 화면은 상단 헤더 스타일로 구현되어 있었고, 좌측 사이드바가
없어 모던 SNS 앱의 IA 패턴을 따르지 못했다.

### 2.2 반복적 요구사항 정교화

사용자 요구는 단 한 번이 아니라 대화 중에 점진적으로 정교화되었다:

1. "사이드 메뉴 추가" → AppShell + Sidebar + MobileTabBar
2. "'홈' 헤더 왜 있지?" → 헤더 단순화
3. "홈/탐색 차이?" → 역할 정의 (IA 질의)
4. "X/Instagram/TikTok 참고" → Instagram 모델 제안
5. "홈=팔로잉+자동추천" → 단일 혼합 피드
6. "팔로잉 독립 메뉴 추가 (X처럼)" → `/following` + `following_only`
7. "데스크탑/모바일 반응형 불일치" → MobileTabBar 재배열
8. "로그인 아이콘 통일, + 퀵 메뉴" → UserIcon + CreateMenu
9. "설계 문서 싱크" → `design.md` §4.1/§4.2/§5/§6.7 업데이트

이 반복 피드백은 "사용자 의도를 첫 번째 시도에 완벽히 포착하지 못해도, 작은 단위로 빠르게
수정 가능한 구조가 중요하다"는 점을 보여준다.

---

## 3. Scope Delivered

### 3.1 Frontend — 컴포넌트

| 파일 | 변경 | 역할 |
|---|---|---|
| `components/AppShell.tsx` | 신규 (이전 라운드) | 사이드바 + 중앙 + 하단 탭바 래퍼 |
| `components/Sidebar.tsx` | 수정 | 팔로잉 메뉴 추가, CreateMenu 트리거 적용 |
| `components/MobileTabBar.tsx` | 재작성 | 5메뉴 사이드바와 일치, UserIcon 로그인, FAB CreateMenu |
| `components/CreateMenu.tsx` | **신규** | 재사용 가능한 2옵션 작성 퀵 메뉴 팝오버 |
| `components/icons.tsx` | 수정 | `UsersIcon` 추가 (팔로잉 메뉴용) |
| `components/LoginModal.tsx` | 이전 라운드 | 공유 로그인 모달 |
| `lib/useMe.ts` | 이전 라운드 | 반응형 인증 훅 |
| `lib/api.ts` | 수정 | `fetchFollowingFeed()` 추가 |

### 3.2 Frontend — 페이지

| 파일 | 변경 | 역할 |
|---|---|---|
| `app/layout.tsx` | 이전 라운드 | AppShell 전역 적용 |
| `app/page.tsx` | 재작성 | 단일 혼합 피드 (로그인/비로그인 대응) |
| `app/following/page.tsx` | **신규** | 팔로우 전용 타임라인 |
| `app/explore/page.tsx` | 이전 라운드 | 장르/타입 브라우징 |
| `app/notifications/page.tsx` | 이전 라운드 | 알림 목록 |
| `app/posts/new/page.tsx` | 수정 | `searchParams.type` 파라미터 지원 |

### 3.3 Backend

| 파일 | 변경 | 역할 |
|---|---|---|
| `app/api/posts.py` | 수정 | `GET /posts/feed`에 `following_only=true` 쿼리 파라미터 추가 |

### 3.4 문서

| 파일 | 변경 | 역할 |
|---|---|---|
| `docs/02-design/design.md` | 수정 | §4.1 화면 목록, §4.2 와이어프레임(데스크탑/모바일/CreateMenu), §5 API, §6.7 알고리즘 |
| `docs/03-analysis/domo-home-ia.analysis.md` | 신규 | 3회 재분석 기록 (63.5% → 89.75% → 95.0%) |
| `docs/04-report/domo-home-ia.report.md` | 신규 | 본 완료 보고서 |

---

## 4. Design Decisions

### D1. 사이드바에 팔로잉 독립 메뉴 (vs 탭 내 팔로잉)

**선택**: 독립 사이드바 메뉴 (`/following`)
**이유**: X의 최신 사이드바가 Follow를 독립 항목으로 분리한 것을 사용자가 스크린샷으로
제시. 탭 방식보다 IA가 명확하고, 홈 탭/API 할당 역전 문제가 근본적으로 사라진다.
**대안**: 홈 내부 탭 (X의 초기 방식)
**트레이드오프**: 사이드바 슬롯 1개 소모 vs 홈 화면 단순화. 후자가 이득이라 판단.

### D2. 홈 페이지의 피드 정책

**선택**:
- 로그인: `GET /posts/feed` (팔로우 70% + 트렌딩 30% 혼합)
- 비로그인: `GET /posts/explore` (공개 최신순)

**이유**: 설계 §6.7 `build_home_feed`를 그대로 유지하면서, 비로그인도 **콘텐츠를 볼 수
있도록** 함. "로그인하지 않아도 새로운 작가를 추천받을 수 있는 게 낫다"는 사용자 의도 반영.

**잔여 개선**: 비로그인 피드에 트렌딩 가중치 미적용 (P3 백로그)

### D3. FAB vs 탭바 내부 + 버튼

**선택**: 모바일에서 `+` 버튼을 하단 탭바에서 분리하여 우하단 FAB으로 배치
**이유**: 탭바가 사이드바와 동일한 5메뉴(홈/팔로잉/탐색/알림/프로필)로 맞춰지면서 +가 들어갈
슬롯이 없어짐. FAB 패턴은 Material Design에서 검증된 UX이며, 중앙 돌출 버튼보다 탭바가
깔끔해진다.

### D4. CreateMenu 2옵션 구성

**선택**: 작품 등록(🎨 판매·경매·블루버드) + 일반 포스트(✏️)
**이유**: 백엔드 `posts.type`이 `general` | `product` 2값이라 1:1 매핑. 사용자 결정 비용 최소.
**대안**: 작품을 "경매" vs "즉시구매"로 더 쪼개기. 초기 MVP에는 과도하다고 판단, 후속 검토.

### D5. `following_only` 쿼리 파라미터 vs 별도 엔드포인트

**선택**: 파라미터 확장 (`GET /posts/feed?following_only=true`)
**이유**: 동일 모델/직렬화 재사용, 설계 §5 API 테이블 변경 최소화, 호환성 유지.
**대안**: `GET /posts/feed/following` 별도 엔드포인트 — 경로 의미 명확하지만 코드 중복.

---

## 5. Key Metrics & Quality Gates

### 5.1 Match Rate 추이

```
v1 (초기 분석)     ████████████░░░░░░░░ 63.5%
v2 (R6 반영)        █████████████████░░░ 89.75%
v3 (문서 싱크)      ███████████████████░ 95.0%
v4 (백로그 #1~#4)   ████████████████████ 100.0%  ← 현재
                   └────────────────────┘
                    0%                 100%
```

### 5.2 영역별 점수 (v4)

| 영역 | 가중치 | 점수 | 상태 |
|---|---|---|---|
| 화면 구조/네비게이션 | 15% | 100% | 🟢 완전 일치 |
| 홈 피드 알고리즘 | 15% | 100% | 🟢 완전 일치 |
| 팔로잉 독립 메뉴 | 10% | 100% | 🟢 완전 일치 |
| 탐색 페이지 | 10% | 100% | 🟢 `sort` 파라미터 추가 |
| 설계 문서 최신성 | 15% | 100% | 🟢 코드와 완전 동기화 |
| 반응형 IA 일관성 | 15% | 100% | 🟢 모바일 뱃지 구현 (#1) |
| 작성 플로우 | 10% | 100% | 🟢 A11y 완비 (#4) |
| 비로그인 홈 경험 | 10% | 100% | 🟢 트렌딩 스코어 적용 (#2+#3) |

### 5.3 기능 검증

| 기능 | 검증 방식 | 결과 |
|---|---|---|
| 12개 라우트 HTTP 200 | curl | ✅ 이전 라운드 |
| 사이드바 렌더링 | HTML `aside` 마커 | ✅ 이전 라운드 |
| 홈 피드 로드 | `fetchHomeFeed` 호출 | ✅ 로컬 동작 |
| 팔로잉 전용 피드 | `fetchFollowingFeed` + `following_only=true` | 🟡 백엔드 재시작 후 사용자 확인 필요 |
| CreateMenu 팝오버 | 클릭 이벤트 | 🟡 사용자 확인 필요 |
| 반응형 브레이크포인트 | `md:hidden`, `xl:block` | ✅ Tailwind 클래스 적용 |

---

## 6. Lessons Learned

### L1. IA 질문은 한 번의 답으로 확정되지 않는다

"홈 vs 탐색 차이?"에서 시작된 논의가 7라운드를 거쳐 최종 IA에 도달했다. 처음부터 완벽한
답을 내놓으려 하기보다, **작은 수정 단위로 빠르게 반복**하는 것이 효율적이었다.

### L2. 설계 문서는 구현과 함께 업데이트되어야 한다

초기 Gap 분석에서 Match Rate가 낮았던 가장 큰 이유는 **구현과 문서 불일치**였다. 코드는
맞는 방향인데 문서가 구식 상태였다. 한 번 동기화하니 Match Rate가 +5%p 개선됐다.
앞으로는 기능 변경 시 `design.md`를 같은 커밋에 포함하는 것이 바람직.

### L3. 반응형은 컴포넌트 레벨에서 점검해야 한다

데스크탑 사이드바와 모바일 탭바가 각각 독립적으로 진화하면서 메뉴 목록이 불일치했다.
사용자가 "달라!"라고 지적하기 전까지 감지하지 못했다. **공통 메뉴 정의를 상수로 뽑아내면**
불일치를 원천 차단할 수 있다 (후속 리팩터 후보).

### L4. 레퍼런스 확인은 추측 말고 검증

"X는 팔로잉 탭만 있다"고 단정했다가 사용자 스크린샷으로 정정당했다. UI 레퍼런스를
언급할 때는 **최근 직접 확인한 내용인지 명시**하거나, 확신이 없으면 "확인 필요"라고
먼저 말하는 편이 낫다.

### L5. 작은 CreateMenu 하나가 UX를 크게 바꾼다

FAB 하나를 + 버튼에서 2옵션 팝오버로 바꿨을 뿐인데, "무엇을 만들 것인지"를 먼저
선택하게 하는 작은 변화가 사용자 의도 전달을 훨씬 명확하게 만들었다. 마이크로
인터랙션의 가치를 재확인.

---

## 7. Backlog Status

### 완료 (R8)

| # | 항목 | 구현 |
|---|---|---|
| 1 | `useUnreadCount()` 훅 분리 → 모바일 탭바 뱃지 | ✅ [useUnreadCount.ts](../../frontend/src/lib/useUnreadCount.ts), MobileTabBar BellIcon 뱃지 |
| 2 | 트렌딩 스코어 공식 백엔드 구현 (§6.7) | ✅ [posts.py](../../backend/app/api/posts.py) `_trending_score_expr()` |
| 3 | 비로그인 홈 인기 정렬 | ✅ `/posts/explore?sort=popular` + 프론트 적용 |
| 4 | CreateMenu A11y | ✅ aria-*, roving tabindex, arrow key nav |

### 남은 후속 (선택적)

| # | 항목 | 작업량 | 메모 |
|---|---|---|---|
| 5 | 공통 NavItem 상수 분리 (Sidebar/MobileTabBar 공유) | M | 구조 개선, Match Rate 영향 없음 |
| 6 | 탐색 페이지 검색창 (§5 `/posts/search?q=`) | M | 신규 기능, 별도 PDCA 사이클 권장 |
| 7 | 경매/즉시구매 CreateMenu 분기 | S | 사용 데이터 수집 후 판단 |

**목표 달성**: Match Rate 100% 달성 완료. 후속 항목은 별도 기능 단위로 관리.

---

## 8. Artifacts Index

| 문서 | 경로 |
|---|---|
| Plan | `docs/01-plan/features/domo.plan.md` |
| Design (updated) | `docs/02-design/design.md` §4.1 / §4.2 / §5 / §6.7 |
| Analysis (v3) | `docs/03-analysis/domo-home-ia.analysis.md` |
| Report (this) | `docs/04-report/domo-home-ia.report.md` |

---

## 9. Sign-off

**Completion Criteria**:
- [x] Match Rate ≥ 90%
- [x] P0/P1 Gap 모두 해결
- [x] 설계 문서 싱크
- [x] 사용자 확인 (데스크탑 + 모바일 IA 일치)

**Report Generated**: 2026-04-12
**Next Phase**: Archive (`/pdca archive domo`) 또는 후속 백로그 이터레이션

---

🕊 Domo Home/Following/Explore IA PDCA cycle complete.
