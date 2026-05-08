# user-system-guide Gap 분석 보고서

> v1 가이드(`user-system-guide.ko.md`) vs. 실제 소스 검증 결과  
> 검증 기준: alembic head 0083, frontend `feature/editor-improve` 브랜치 (2026-05-08)

---

## 요약 카운트

| 상태 | 건수 |
|------|------|
| ✅ 일치 | 31 |
| ⚠️ 정정 필요 | 14 |
| ❌ 소스 미존재 (제거) | 9 |
| ➕ 소스에 있으나 가이드 누락 | 8 |

---

## Gap 상세 테이블

| 섹션 | 항목 | 가이드 주장 | 실제 소스 | 상태 | 처리 |
|------|------|------------|----------|------|------|
| 2.1 | 회원가입 방법 | 이메일+비번 / Google / GitHub / 매직링크 4가지 | `auth.py` L37: `/auth/sns/google` 1종만. GitHub OAuth 없음. 매직링크는 admin invite용 전용 (`admin/users.py` L270) | ⚠️ | Google 소셜 로그인만 명시. GitHub·매직링크 제거 |
| 2.2 | 로그인 방법 | 이메일+비번, 소셜(Google/GitHub), 매직링크 | Google ID token 방식만 구현됨. `/me/account`에 `loginWithMockEmail` 개발용 mock 존재 — 프로덕션 방식 아님 | ⚠️ | Google 로그인만 명시. 이메일+비번 로그인 엔드포인트도 미구현 확인 |
| 2.3 | 프로필 페이지 경로 | `/me` | Sidebar에 `/me` 직접 링크 없음. 프로필은 `/users/{id}`. 계정 설정은 `/me/account` | ⚠️ | 경로 정정: 계정 설정은 `/me/account`, 공개 프로필은 `/users/{id}` |
| 3.1 | 미디어 파일 크기 | 최대 10MB/파일, 영상 100MB | i18n `ko.json` L329: `"tooLarge": "파일 크기 초과 (50MB 이하)"`. backend `media.py`에서 50MB 제한 적용 | ⚠️ | 50MB로 정정 (이미지·영상 공통) |
| 3.1 | 공개 범위 옵션 | public / followers_only / subscribers_only / private 4종 | `series.py` L13: `Visibility = Literal["public", "followers_only", "unlisted"]`. `subscribers_only`, `private` 미존재 | ⚠️ | `unlisted` (링크 공유)로 교체. `subscribers_only`·`private` 제거 |
| 3.1 | 티어 우선 공개 | 가이드에 없음 | `ko.json` L451-471: `tierRelease` — subscriber/sponsor/follower 대상, 1h/6h/24h/3d/7d 기간 선택 | ➕ | v2에 추가 |
| 3.1 | 예약 발행 | 가이드에 없음 | `ko.json` L414-481: `schedulePicker` — 5분 이후 최대 1년 이내 예약 발행 지원 | ➕ | v2에 추가 |
| 3.1 | 임시저장 | 가이드에 없음 | `/posts/drafts` page 존재. `ko.json` L257-284: 자동 임시저장 + 멀티탭 경고 | ➕ | v2에 추가 |
| 3.2 | AI 캡션 재생성 제한 | "일 3회 제한" | `rate_limit.py`에 `ai_caption_regenerate` 키 없음. 실제 제한 미확인 | ❌ | 재생성 가능 사실만 명시, 횟수 제한 삭제 |
| 3.3 | 시리즈 생성 경로 | `/me/series` | `/me/series` page.tsx 없음. `series.py` API만 존재. 에디터 내 SeriesCreateModal로 생성 | ⚠️ | `/me/series` 경로 제거. 에디터 내 생성 방법으로 정정 |
| 3.4 | 도슨트 작성 경로 | `/posts/[id]/edit` | `/posts/[id]/edit/page.tsx` 존재 ✅. 하지만 도슨트 전용 UI는 DocentSection 컴포넌트 — 에디터 별도 섹션에 있음 | ✅ | 유지 |
| 4.1 | 티어 금액 | "₩1,000~₩50,000" | `tier_benefits.py` 스키마 / `TierBenefitsPanel.tsx` — 금액은 작가가 자유롭게 설정. 특정 고정 금액 없음 | ⚠️ | 고정 금액 표 제거. "작가가 자유 설정" 명시 |
| 4.2 | 자동 갱신 알림 "만료 30일 전" | "만료 30일 전 사이드바 배너" | `useExpiryBanner.ts` L15: `COOLDOWN_MS = 7 * 24 * 60 * 60 * 1000`. `windowDays` 기본값 7 — 7일 이내만 배너 표시 | ⚠️ | 30일 → 7일로 정정 |
| 4.3 | 후원 관리 경로 `/me/sponsorships` | ✅ page 존재 | `sponsorships/page.tsx` ✅ | ✅ | 유지 |
| 4.3 | 결제 이력 다운로드 | "PDF / CSV 다운로드" | `SponsorshipHistory.tsx` 존재하나 PDF/CSV export UI 미확인. backend에 `GET /settlements/mine` 있음 (JSON 응답) | ❌ | PDF/CSV 언급 제거 |
| 4.4 | 정산 알림 "Slack" | "정산 임계값 도달 시 Slack 알림" | backend에 Slack webhook 없음. 이메일/푸시만 있음 | ❌ | Slack 언급 제거 |
| 5.1 | AI 가격 추천 | "Phase 11 예정" | 소스 미존재 — 예정 기능 | ❌ | v2에서 삭제 (사용자 가이드에 불필요) |
| 5.3 | 자동 알림 타이밍 | "1시간/6시간/24시간 전" | `auctions.py` — 알림 로직은 bid_outbid/bid_placed/auction_ended_won/no_winner 이벤트 기반. 시간 기반 사전 알림 cron 미확인 | ⚠️ | "입찰 아웃팅·경매 종료 시 즉시 알림"으로 정정 |
| 5.4 | 낙찰 후 24시간 결제 | "Stripe Checkout 링크, 24시간 이내" | `auctions.py` — 낙찰 처리 로직 있으나 24시간 제한 명시 없음. Stripe Checkout은 `payments.py`에 setup-intent만 | ⚠️ | 24시간 언급 제거. "Stripe 결제 링크 발송" 수준으로 정정 |
| 6.1 | 피드 알고리즘 종류 | "default/v1/v2 3가지" | `posts.py` L1107: `pattern="^(default|v1|v2|auto)$"` — 4가지 (default/v1/v2/auto) | ⚠️ | `auto` 추가. 단, UI 토글(`FeedAlgorithmToggle`)은 `default`/`v1` 2종만 노출 — 사용자 직접 선택은 2종 |
| 6.1 | v2 ML 피드 UI | "feed.tsx에서 사용자 선택 가능" | `feed/page.tsx` L111: `showToggle = Boolean(me) && flagEnabled` — PostHog feature flag `feed-algorithm-v2` 활성 시에만 토글 노출 | ⚠️ | "기능 플래그 활성 시 맞춤 추천 토글 표시" 명시 |
| 6.2 | 컬렉션 경로 | `/explore/collections` | `/explore/collections/page.tsx` ✅, `/explore/collections/[id]/page.tsx` ✅ | ✅ | 유지 |
| 6.5 | `/me/settings/curation` | "AI 컬렉션 노출 제외 토글" | 해당 page.tsx 없음. 해당 API endpoint 없음 | ❌ | FAQ Q5 항목 제거 또는 "미구현" 명시 |
| 7.1 | DM rate limit | "5 msg/min/대화" | `rate_limit.py`에 1:1 DM 전용 rate limit 키 없음. 그룹 DM (`group_msg_send`)은 L125에 5/min 존재 | ⚠️ | 1:1 DM rate limit 언급 제거. 그룹 DM 5/min만 명시 |
| 7.4 | WebSocket 경로 | `WS /ws/dm?token={jwt}` | `websocket_dm.py` L48: `@router.websocket("/ws/dm")` ✅ | ✅ | 유지 |
| 7.4 | "3초 폴링 fallback" | WS 미연결 시 3초 폴링 | `useConversations.ts` L16: 10초 폴링 (`POLL_INTERVAL_MS = 10_000`). WS fallback 아닌 기본 polling | ⚠️ | 3초 → 10초로 정정. "폴링 기반 기본 동작" 명시 |
| 8.1 | 알림 설정 경로 | `/me/settings/notifications` | 실제 경로는 `/me/notifications/preferences` (`page.tsx` L4 주석 확인) | ⚠️ | 경로 정정 |
| 8.2 | 이메일 빈도 | "weekly/biweekly" | `me_devices.py` L65: `pattern="^(weekly|biweekly|monthly|never)$"` — monthly·never 2종 추가 | ⚠️ | 4가지 옵션(주간/격주/월간/수신안함)으로 정정 |
| 9.1 | 접근성 설정 경로 | `/me/settings/accessibility` | `/me/settings/accessibility/page.tsx` ✅ | ✅ | 유지 |
| 9.3 | WCAG AAA | "핵심 3페이지 AAA 준수" | `accessibility/page.tsx` — 포커스 링 2px, skip-link, SkipLink 컴포넌트 존재. AAA(7:1)는 목표치. 실제 전수 감사 결과 미확인 | ⚠️ | "AA 이상 목표" 수준으로 표현 완화 |
| 10.1 | 2FA/WebAuthn 일반 사용자 적용 | "관리자/작가(선택): 2FA TOTP + WebAuthn" | `auth.py` L151: passkey_count 조회가 admin role 전용 분기 안에 있음. 일반 사용자 2FA UI 없음 | ⚠️ | "현재 관리자 전용 2FA" 명시. 일반 사용자 WebAuthn 언급 제거 |
| 10.3 | 세션 관리 경로 | `/me/security` | `/me/security` page.tsx 없음. 세션 관리는 `/me/account` 내부에서 처리 | ⚠️ | `/me/account`로 경로 정정 |
| 10.4 | GDPR 데이터 경로 | `/me/privacy/export`, `/me/privacy/delete` | `me/account/page.tsx` — `exportMyData()`, `requestAccountDeletion()` 함수 사용. 실제 UI 경로는 `/me/account` | ⚠️ | `/me/account` 내 기능으로 정정 |
| 11.1 | 오프라인 지원 | "서비스 워커, 일부 기능" | `manifest.json` ✅ (standalone PWA 설정). 그러나 sw.js / next-pwa 등 서비스 워커 파일 없음 (`/public/`에 없음) | ⚠️ | "홈 화면 추가 지원 (standalone)" 수준으로 표현. 오프라인 지원 언급 제거 |
| 11.2 | 키보드 단축키 표 | `g h`, `g f`, `g e`, `g m`, `g p`, `n`, `/`, `Esc`, `j/k`, `l`, `b`, `?` 12개 | FocusManager.tsx: Esc + Tab trap만 구현. ImageEditor.tsx: `1/2/3/4` 도구 전환 hotkey. 전역 네비게이션 단축키(`g h`, `j/k` 등) 코드 없음 | ❌ | 전역 네비게이션 단축키 표 완전 제거. 구현된 단축키만 기재 |
| 12 FAQ | Q5 `/me/settings/curation` | 해당 경로로 안내 | 해당 page 없음 | ❌ | Q5 제거 |
| - | 커뮤니티 기능 | 가이드에 없음 | `/communities/page.tsx`, `/communities/[id]/page.tsx`, `communities.py` API 존재 | ➕ | v2에 추가 |
| - | 온보딩 마법사 | 가이드에 없음 | `/onboarding/page.tsx`, `OnboardingWizard.tsx`, Sidebar 내 첫 세션 표시 | ➕ | v2에 추가 |
| - | 스토리 허브 | 가이드에 없음 | `/stories/page.tsx`, Sidebar `nav.stories` | ➕ | v2에 추가 |
| - | 작가 신청 | 가이드에 없음 | `/artists/apply/page.tsx`, `artists.py` `/apply` endpoint | ➕ | v2에 추가 |
| - | 주문 이력 | 가이드에 없음 | `/orders/page.tsx` 존재 | ➕ | v2에 추가 |
| - | 작가 인터뷰 | 가이드에 없음 | `/me/interviews/page.tsx`, `/users/[id]/interviews/[locale]/page.tsx` | ➕ | v2에 추가 |

---

## 주요 발견 사항

### 1. 회원가입·로그인 방법 과장 (⚠️ 심각)
가이드는 이메일+비밀번호, Google, GitHub, 매직링크 4가지를 기술했으나 실제 구현은 **Google OAuth 1종**뿐이다. 이메일+비밀번호 로그인 엔드포인트가 없고, GitHub OAuth는 backend에 구현 없음. 매직링크는 admin 초대 전용으로만 사용.

### 2. 포스트 공개 범위 오류 (⚠️ 심각)
가이드의 `subscribers_only`와 `private`은 스키마에 없다. 실제 값은 `public` / `followers_only` / `unlisted`(링크 공유) 3종이다. 사용자가 가이드대로 기대하면 혼란이 발생할 수 있다.

### 3. 키보드 단축키 표 전체 미구현 (❌)
가이드의 12개 전역 단축키(`g h`, `n`, `j/k`, `l`, `b` 등)는 코드베이스 어디에도 구현되지 않았다. 구현된 단축키는 모달 Esc 닫기, 이미지 에디터 `1/2/3/4` 도구 전환뿐이다.

### 4. 알림 설정·GDPR 경로 오류 (⚠️)
- 알림 설정: `/me/settings/notifications` → 실제 `/me/notifications/preferences`
- 데이터 내보내기·계정 삭제: `/me/privacy/export`, `/me/privacy/delete` → 실제 `/me/account` 내 기능
- 세션 관리: `/me/security` → 실제 `/me/account`

### 5. 만료 배너 타이밍 오류 (⚠️)
가이드는 "30일 전 배너"라고 했으나 `useExpiryBanner.ts`의 `windowDays` 기본값은 7일이다.

### 6. 이메일 다이제스트 빈도 불완전 (⚠️)
가이드는 `weekly`/`biweekly` 2종만 언급했으나 실제 API는 `weekly`/`biweekly`/`monthly`/`never` 4종을 지원한다.

### 7. 가이드 누락 기능 다수 (➕)
커뮤니티(`/communities`), 온보딩 마법사, 스토리 허브(`/stories`), 작가 신청(`/artists/apply`), 작가 인터뷰, 주문 이력(`/orders`), 임시저장, 예약 발행, 티어 우선 공개 등이 실제 구현됐으나 가이드에 없다.

---

## 검증 메타

| 항목 | 값 |
|------|---|
| alembic head | 0083_ai_collections |
| 검증 브랜치 | feature/editor-improve |
| 검증 일시 | 2026-05-08 |
| 검증 범위 | frontend pages 54개, backend API 파일 전체 (admin 제외), alembic 0001~0083 |
