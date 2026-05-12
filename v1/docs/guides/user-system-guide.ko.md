# Domo 사용자 가이드 v2

> 신진 작가와 미술학도를 위한 글로벌 SNS · 후원 · 경매 플랫폼

본 문서는 일반 사용자(작가, 컬렉터, 팬)가 Domo를 사용하는 방법을 설명합니다.
관리자 운영 가이드는 [admin-system-guide.ko.md](./admin-system-guide.ko.md)를 참고하세요.

- 대상: 일반 사용자
- 언어: 한국어 (서비스는 ko/en/ja/zh/es 5개 언어 지원)
- 검증 기준: alembic head 0083, frontend feature/editor-improve 브랜치 (2026-05-08)

---

## 목차

1. [Domo 소개](#1-domo-소개)
2. [시작하기 — 회원가입 · 로그인](#2-시작하기--회원가입--로그인)
3. [프로필 관리](#3-프로필-관리)
4. [작품 게시 — 포스트 · 시리즈 · AI 캡션 · 도슨트](#4-작품-게시--포스트--시리즈--ai-캡션--도슨트)
5. [작가 후원 — Blue Bird 시스템](#5-작가-후원--blue-bird-시스템)
6. [경매 — 입찰 · 알림 · 결제](#6-경매--입찰--알림--결제)
7. [작가 발견 — 피드 · 컬렉션 · Featured Artist · 커뮤니티](#7-작가-발견--피드--컬렉션--featured-artist--커뮤니티)
8. [메시징 — DM · 그룹 채팅 · 첨부](#8-메시징--dm--그룹-채팅--첨부)
9. [알림 · 이메일 다이제스트 · 만료 배너](#9-알림--이메일-다이제스트--만료-배너)
10. [환경 설정 — 통화 · 언어 · 단순 모드](#10-환경-설정--통화--언어--단순-모드)
11. [보안 · 개인정보](#11-보안--개인정보)
12. [모바일 PWA · 키보드 단축키](#12-모바일-pwa--키보드-단축키)
13. [자주 묻는 질문 (FAQ)](#13-자주-묻는-질문-faq)
14. [가이드 검증 메타정보](#14-가이드-검증-메타정보)

---

## 1. Domo 소개

Domo(Domo Lounge)는 갤러리 입점이 어려운 신진 작가, 미술학도,
동남아·라틴아메리카·동유럽 지역 작가를 위한
**SNS + 블로그 + 작품 쇼케이스 + 후원(Blue Bird) + 경매**를 통합한 플랫폼입니다.

### 핵심 가치

- **Blue Bird 후원**: 진입 장벽이 낮은 마이크로 패트로니지 — 작가가 직접 티어와 금액을 설정
- **글로벌 작가 인덱스**: 거래·참여 활동 기반 신진 작가 자동 랭킹
- **AI 보조 큐레이션**: AI 캡션·도슨트·자동 컬렉션으로 작가 정체성 강화
- **다국어 자동 번역**: 한국어로 작성하면 5개 언어(ko/en/ja/zh/es)로 자동 노출

### 주요 사용자

- **작가**: 작품 게시, 후원 모집, 경매 출품, 시리즈 관리
- **컬렉터**: 작가 발견, 후원, 경매 입찰, 작품 수집
- **팬**: 작가 팔로우, 댓글, 공유, 알림 수신

🔗 관련 소스: `/v1/frontend/src/app/page.tsx`, `/v1/frontend/src/components/Sidebar.tsx`

---

## 2. 시작하기 — 회원가입 · 로그인

### 2.1 회원가입

현재 **Google 계정**을 통한 소셜 로그인으로 가입합니다.

**가입 흐름**:
1. 로그인 버튼 클릭 → LoginModal 표시
2. "Google로 계속하기" → Google OAuth 인증
3. 최초 가입 시 온보딩 마법사(OnboardingWizard)로 프로필 초기 설정

**온보딩 마법사**:
- 첫 로그인 후 자동으로 시작됩니다
- 표시 이름, 자기소개, 관심 장르 등 기본 프로필 설정
- 완료 후 사이드바에서 언제든 재시작 가능

**미성년자 보호**:
- 18세 미만 사용자는 보호자 동의 확인 후 이용 가능 (`/guardian/consent/{token}`)

### 2.2 로그인

- Google 계정으로 1클릭 로그인
- 토큰 만료: Access 1시간, Refresh 7일 자동 갱신
- 여러 기기에서 동시 로그인 가능 — 세션은 `/me/account`에서 관리

🔗 관련 소스:
- `/v1/frontend/src/components/LoginModal.tsx`
- `/v1/frontend/src/components/onboarding/OnboardingWizard.tsx`
- `/v1/frontend/src/app/onboarding/page.tsx`
- `/v1/backend/app/api/auth.py`

---

## 3. 프로필 관리

### 3.1 공개 프로필 (`/users/{userId}`)

다른 사용자가 볼 수 있는 프로필 페이지:
- 아바타, 표시 이름, 자기소개
- 게시한 작품 목록
- 시리즈 목록 (`/users/{userId}/series`)
- 작가 인터뷰 (작가 신청 승인 후, `/users/{userId}/interviews/{locale}`)
- 프레스 킷 (`/users/{userId}/press-kit`)
- 타임라인 (`/users/{userId}/timeline`)
- Blue Bird 후원 버튼

### 3.2 계정 설정 (`/me/account`)

로그인 후 본인 계정을 관리합니다:
- 프로필 정보 수정
- 데이터 내보내기 (JSON)
- 계정 삭제 (30일 유예 후 영구 삭제, 취소 가능)
- 법적 동의 이력 확인

### 3.3 자기소개 다국어 관리 (`/me/bio`)

- 5개 언어(ko/en/ja/zh/es)로 자기소개 개별 작성 가능
- "AI 번역 적용" 버튼: 한국어 원문 → 나머지 4개 언어 자동 번역 (`POST /me/bio/translate`)
- 번역 결과를 직접 수정하여 저장 가능

### 3.4 작가 신청 (`/artists/apply`)

일반 사용자는 작가 신청을 통해 상품 포스트 작성, 경매 출품, 후원 수령 권한을 얻습니다:
- 포트폴리오 정보 입력
- 미술 학교 인증(선택): 재학 이메일로 인증
- 관리자 심사 후 승인 (보통 1-3일)

🔗 관련 소스:
- `/v1/frontend/src/app/users/[id]/page.tsx`
- `/v1/frontend/src/app/me/account/page.tsx`
- `/v1/frontend/src/app/me/bio/page.tsx`
- `/v1/frontend/src/app/artists/apply/page.tsx`
- `/v1/backend/app/api/me_bio.py`
- `/v1/backend/app/api/artists.py`

---

## 4. 작품 게시 — 포스트 · 시리즈 · AI 캡션 · 도슨트

### 4.1 포스트 작성 (`/posts/new`)

**기본 입력**:
- 제목, 본문
- 미디어 업로드: 이미지(JPG/PNG/WebP/AVIF) · 영상 · GIF
  - 최대 **50MB**/파일
  - Presigned URL 직접 업로드 (서버 경유 없음)
  - 멀티파일 업로드 지원
- 장르 태그 (회화·디지털·조각·사진 등)
- 위치 (선택)

**공개 범위**:

| 옵션 | 설명 |
|------|------|
| `public` (전체 공개) | 누구나 열람 |
| `followers_only` (팔로워만) | 나를 팔로우하는 사람만 |
| `unlisted` (링크 공유) | URL을 아는 사람만 (피드에 노출 안 됨) |

**고급 옵션**:
- 댓글 허용/비허용 (비허용 시 기존 댓글 보존)
- 시리즈에 추가
- 예약 발행 (5분 이후 ~ 1년 이내 일시 지정)
- 이미지 편집 (Konva 기반 인라인 에디터 — 회전, 크롭, 모자이크, 워터마크)
- 워터마크 / 시그니처 적용

**티어 우선 공개** (작가 전용):
- 특정 구독자/후원자/팔로워 대상으로 먼저 공개 후, 설정 기간(1h/6h/24h/3d/7d) 경과 후 전체 공개 전환

**임시저장**:
- 작성 중 자동으로 임시저장 (`/posts/drafts`에서 목록 확인)
- 재접속 시 이어쓰기 또는 새로 작성 선택 가능
- 멀티탭 경고: 다른 탭에서 편집 중이면 알림 표시

### 4.2 AI 캡션 자동 생성

작품 업로드 후 AI가 한국어 캡션을 자동 생성하고 5개 언어로 번역합니다:

- 자동 적용 위치: `<img alt="...">` 자동 채움 → 접근성 + SEO 개선
- 수동 오버라이드: 작가가 직접 캡션 작성 시 AI 캡션보다 우선 적용 (`caption_override`)
- 재생성: 작가 요청 시 재생성 가능
- LLM 미가용 시: 빈 alt로 graceful 처리

### 4.3 시리즈

작품을 주제별로 묶어 일관된 컬렉션으로 노출합니다:

- 시리즈 생성: 포스트 작성 에디터 내 "시리즈 추가" → 새 시리즈 생성 또는 기존 선택
- 드래그 앤 드롭으로 순서 변경 (dnd-kit)
- 시리즈 전용 페이지: `/users/{userId}/series`
- 시리즈 표지 이미지 자동 또는 수동 지정

### 4.4 AI 도슨트 (작품 해설)

작가 직접 해설(`artist_docent_text`)과 AI 보조 해설(`ai_docent_text`)이 함께 제공됩니다:

**작가 직접 작성**:
- `/posts/{id}/edit`에서 도슨트 텍스트 입력
- 작품 의도, 영감, 기법 등 자유롭게 서술

**AI 도슨트 생성**:
- "AI 도슨트 생성" 버튼 클릭 → LLM이 작품·작가 bio·시리즈 컨텍스트 분석 → 큐레이터 톤 해설 생성
- 5개 언어 자동 번역 (translation cache 재사용으로 비용 절감)
- **opt-out 토글**: AI 도슨트 비활성화 가능 (`ai_docent_opted_out`)

**노출 우선순위**:
1. 작가 도슨트가 있으면 우선 표시
2. AI 도슨트는 "AI 도슨트 보기" 토글로 펼침
3. opt-out=true 시 AI 섹션 비노출

🔗 관련 소스:
- `/v1/frontend/src/components/post-editor/EditorWorkspace.tsx`
- `/v1/frontend/src/components/post-editor/PublishDrawer.tsx`
- `/v1/frontend/src/components/post-editor/ImageEditor.tsx`
- `/v1/frontend/src/components/DocentSection.tsx`
- `/v1/frontend/src/app/posts/new/page.tsx`
- `/v1/frontend/src/app/posts/drafts/page.tsx`
- `/v1/backend/app/api/posts.py`
- `/v1/backend/alembic/versions/0078_ai_artwork_caption.py`
- `/v1/backend/alembic/versions/0079_llm_docent.py`

---

## 5. 작가 후원 — Blue Bird 시스템

Domo의 핵심 기능. 갤러리 없이도 작가가 직접 후원을 받는 마이크로 패트로니지.

### 5.1 후원 시작

작가 프로필 또는 작품 상세에서 "Blue Bird 후원" 버튼을 클릭합니다:

**티어 선택**:
- 작가가 직접 설정한 금액과 메시지가 표시됩니다
- 각 티어별 보상: 후원자 전용 작품 열람, 시리즈 우선 알림 등 (작가가 `/me/tier-benefits`에서 설정)

**다중 통화 지원**:
- KRW · USD · JPY · EUR 등 복수 통화 자동 환산
- Open Exchange Rates 기반 환율 갱신 (Redis 5분 캐시)
- 결제는 Stripe 처리

### 5.2 결제 · 자동 갱신

**Stripe SetupIntent** 기반 카드 등록:
- PCI-DSS 준수 (Domo 서버는 카드 정보 저장 안 함)
- 익월 자동 갱신 (구독 모델)
- 자동 갱신 ON/OFF 토글 가능

### 5.3 후원 관리 (`/me/sponsorships`)

내가 후원 중인 작가 목록 + 만료일 + 자동 갱신 상태를 확인합니다:
- 만료 임박 배너 (7일 이내)
- 갱신 / 일시 정지 / 해지 버튼

### 5.4 구독 목록 (`/subscriptions`)

구독 내역과 상태를 확인하는 별도 페이지입니다.

### 5.5 작가 페이지 — 후원 받기 (`/me/patronage`)

작가는 후원 통계와 정산 내역을 확인합니다 (작가 계정 전용):
- 누적 후원자 수, 월간 활성 후원자
- Stripe Connect 정산 자동화 (KYC 승인 후)

### 5.6 후원 혜택 설정 (`/me/tier-benefits`)

작가가 각 티어별 보상 내용을 직접 설정합니다 (작가 계정 전용).

🔗 관련 소스:
- `/v1/frontend/src/components/BluebirdModal.tsx`
- `/v1/frontend/src/components/sponsorships/`
- `/v1/frontend/src/app/me/sponsorships/page.tsx`
- `/v1/frontend/src/app/me/patronage/page.tsx`
- `/v1/frontend/src/app/me/tier-benefits/page.tsx`
- `/v1/frontend/src/app/subscriptions/page.tsx`
- `/v1/backend/app/api/payments.py`

---

## 6. 경매 — 입찰 · 알림 · 결제

작가가 작품을 경매로 출품하면, 컬렉터가 입찰합니다.

### 6.1 경매 출품 (작가)

`/posts/new` → 상품 포스트 → "경매로 판매" 옵션:
- 시작가 (reserve_price)
- 최소 입찰 단위 (min_increment)
- 종료 일시
- 즉시 구매가 (선택)

### 6.2 입찰 (컬렉터)

`/auctions/{id}` 경매 상세 페이지:
- 현재 최고가, 입찰 횟수, 종료까지 남은 시간 (실시간)
- AuctionCountdown 컴포넌트로 카운트다운 표시
- 입찰 버튼 → 카드 등록(Stripe) + 입찰 확정
- 입찰 시 KYC 인증 필수

**알림**:
- 내 입찰이 밀렸을 때: "입찰이 밀렸습니다" 즉시 알림
- 작가에게: 새 입찰 발생 시 즉시 알림
- 경매 종료 후 낙찰자·작가에게 자동 알림

### 6.3 낙찰 · 결제

- 낙찰 후 결제 링크(Stripe) 발송
- 결제 완료 후 작가에게 정산 (Stripe Connect)
- 낙찰자에게 작품 다운로드 / 배송 안내 (작가 처리)

### 6.4 경매 공유 카드

작가는 활성 경매의 공유 카드(PNG 이미지)를 자동 생성하여 SNS에 공유할 수 있습니다 (`POST /auctions/{id}/share-card`).

### 6.5 주문 이력 (`/orders`)

낙찰 완료 내역과 결제 상태를 확인합니다.

🔗 관련 소스:
- `/v1/frontend/src/app/auctions/[id]/page.tsx`
- `/v1/frontend/src/app/orders/page.tsx`
- `/v1/frontend/src/components/AuctionCountdown.tsx`
- `/v1/frontend/src/components/AuctionShareCard.tsx`
- `/v1/backend/app/api/auctions.py`

---

## 7. 작가 발견 — 피드 · 컬렉션 · Featured Artist · 커뮤니티

Domo는 작가 발견을 위한 다양한 채널을 제공합니다.

### 7.1 피드 (`/feed`)

로그인 사용자는 팔로우 작가와 추천 작품을 혼합한 피드를 봅니다.

**알고리즘**:

| Algo | 설명 |
|------|------|
| `default` (최신순) | 시간순 + 트렌딩 혼합 |
| `v1` (맞춤 추천) | 팔로우 가중치 + engagement 기반 개인화 |
| `v2` | ML 협업 필터링 (Matrix Factorization) |
| `auto` | A/B 테스트 — v1/v2 자동 배분 |

**사용자 UI**: 로그인 상태 + PostHog feature flag `feed-algorithm-v2` 활성 시 "최신순 / 맞춤 추천" 토글 표시.

**Cold start**: 상호작용 5건 미만 시 시간순으로 fallback.

**추천 이유**: 각 포스트에 "팔로잉", "인기", "비슷한 장르" 라벨 표시.

### 7.2 팔로잉 피드 (`/following`)

팔로우한 작가의 최신 작품만 표시됩니다. 로그인 필요.

### 7.3 탐색 (`/explore`)

다양한 필터로 작품과 작가를 발견합니다:
- 탭: 인기 / 최신 / 지역 / 장르 / 판매·경매
- 지역 필터: 동남아시아, 남미, 동유럽, 동아시아, 북미, 서유럽
- 장르 필터: 수채화, 유화, 디지털, 조각, 혼합매체

### 7.4 검색 (`/search`)

작가, 작품, 포스트를 통합 검색합니다:
- 탭: 전체 / 작가 / 작품 / 포스트
- 필터: 가격 범위, 지역, 활성 상태
- 정렬: 관련도 / 최신순 / 인기순
- 최근 검색 기록 저장 (로그인 시)

### 7.5 AI 큐레이션 컬렉션 (`/explore/collections`)

주 1회(월요일 09:00 UTC) AI가 작품 임베딩 클러스터링으로 주제별 컬렉션을 자동 생성합니다:
- 예: "이번 주 신진 페인터", "디지털 아트 신예"
- 5개 언어 자동 번역 (제목/설명)
- 컬렉션 상세: `/explore/collections/{id}`

### 7.6 Featured Artist

홈 / 탐색 페이지 상단에 추천 작가를 노출합니다:
- 수동 큐레이션(관리자) 또는 AI 자동 추천 후 관리자 검수·발행
- 선정 기준: artist_index 상위권, engagement 활성, 다양성 반영

### 7.7 신진작가 인덱스 (`/artists/index`)

거래·참여 활동 기반으로 신진 작가를 자동 랭킹합니다. 로그인 없이도 열람 가능.

### 7.8 커뮤니티 (`/communities`)

주제별 공개 커뮤니티에서 포스트를 공유하고 댓글을 나눌 수 있습니다:
- 커뮤니티 목록 조회 및 가입 (`/communities/{id}`)
- 커뮤니티 포스트 작성 및 댓글
- 관리자(생성자)만 참여자 관리 가능

### 7.9 스토리 허브 (`/stories`)

작가 인터뷰, 제작 과정, 영감 이야기 등 장문 콘텐츠를 읽을 수 있는 허브입니다.

🔗 관련 소스:
- `/v1/frontend/src/app/feed/page.tsx`
- `/v1/frontend/src/app/explore/`
- `/v1/frontend/src/app/search/page.tsx`
- `/v1/frontend/src/app/explore/collections/`
- `/v1/frontend/src/app/artists/index/page.tsx`
- `/v1/frontend/src/app/communities/`
- `/v1/frontend/src/app/stories/page.tsx`
- `/v1/frontend/src/components/feed/FeedAlgorithmToggle.tsx`
- `/v1/backend/app/api/posts.py` (feed endpoint)
- `/v1/backend/app/api/ai_collections.py`
- `/v1/backend/app/api/communities.py`

---

## 8. 메시징 — DM · 그룹 채팅 · 첨부

### 8.1 1:1 DM (`/me/messages`)

사이드바 "메시지" 또는 작가 프로필의 "메시지" 버튼으로 대화를 시작합니다:
- 텍스트 메시지 (HTML escape 처리)
- 읽음 표시
- 차단 / 신고 기능
- 메시지 수정: 발송 후 5분 이내 가능

### 8.2 그룹 DM

3인 이상의 그룹 대화방:
- 생성: `POST /me/messages/conversations/group` (참여자 2명 이상 지정)
- 최대 50인
- 역할: admin (생성자) / member
- admin만 참여자 추가/제거 가능
- 탈퇴 시 소프트 삭제 (메시지 히스토리 보존)
- Rate limit: **5 msg/min**/사용자/그룹

### 8.3 파일 · 이미지 첨부

- 허용 MIME: image/jpeg, image/png, image/gif, image/webp, application/pdf
- 최대 10MB
- S3 Presigned URL 발급 (15분 유효)
- 이미지는 미리보기, 파일은 다운로드 링크 제공

### 8.4 WebSocket 실시간

`WS /ws/dm?token={access_token}` — 실시간 메시지 푸시:
- 새 메시지 즉시 화면 표시
- 30초 heartbeat (pong 미응답 시 disconnect)
- 다중 인스턴스: Redis pub/sub (REDIS_URL 미설정 시 in-memory 단일 pod)
- WebSocket 미연결 시 **10초 폴링** fallback

🔗 관련 소스:
- `/v1/frontend/src/app/me/messages/page.tsx`
- `/v1/frontend/src/app/me/messages/[id]/page.tsx`
- `/v1/frontend/src/components/messaging/`
- `/v1/frontend/src/lib/hooks/useConversations.ts`
- `/v1/backend/app/api/conversations.py`
- `/v1/backend/app/api/group_conversations.py`
- `/v1/backend/app/api/websocket_dm.py`

---

## 9. 알림 · 이메일 다이제스트 · 만료 배너

### 9.1 푸시 알림

브라우저 / 모바일 푸시 알림:

**설정 경로**: `/me/notifications/preferences`

**알림 종류별 ON/OFF 토글**:
- 경매 관련 (입찰, 종료, 낙찰)
- 후원/구독 관련
- 좋아요·댓글 참여 알림
- 시스템 알림

### 9.2 이메일 다이제스트

`/me/notifications/preferences`에서 수신 주기 선택:

| 옵션 | 설명 |
|------|------|
| `weekly` | 매주 |
| `biweekly` | 격주 |
| `monthly` | 매월 |
| `never` | 수신 안 함 |

내용: 팔로우 작가 신작, 추천 작가, 본인 작품 통계(작가), 후원 만료 임박.

**수신 취소**: `/newsletter/unsubscribe` 링크 제공.

### 9.3 만료 배너 (ExpiryBanner)

후원 만료 **7일 이내**일 때 사이드바 배너가 표시됩니다:
- "N일 후 만료됩니다" 메시지 + 갱신 버튼
- "잊기" 버튼: 7일 cooldown 후 배너 재표시
- 갱신 버튼 클릭 시 즉시 연장

🔗 관련 소스:
- `/v1/frontend/src/app/me/notifications/preferences/page.tsx`
- `/v1/frontend/src/app/notifications/page.tsx`
- `/v1/frontend/src/app/newsletter/unsubscribe/page.tsx`
- `/v1/frontend/src/components/sponsorships/ExpiryBanner.tsx`
- `/v1/frontend/src/lib/hooks/useExpiryBanner.ts`
- `/v1/backend/app/api/me_devices.py`

---

## 10. 환경 설정 — 통화 · 언어 · 단순 모드

### 10.1 PreferencesCard (사이드바 하단)

로그인 여부에 관계없이 사이드바 하단의 환경설정 카드에서 즉시 변경할 수 있습니다.

**통화 (Currency)**:
- USD, KRW, JPY, EUR 등 복수 통화 선택
- localStorage에 저장, 로그인 시 서버와 동기화
- 가격 표시가 선택한 통화로 자동 환산

**언어 (Locale)**:
- ko (한국어), en (English), ja (日本語), zh (中文), es (Español)
- 즉시 적용 (전체 UI 라벨 전환)

**단순 모드**:
- 토글 ON 시:
  - 텍스트 크기 1.2배 확대
  - 줄 간격 1.8 적용
  - 애니메이션 최소화
  - 장식 요소 제거
  - 배경 블러 효과 제거
- 대상: 인지장애, 난독증, 노안 사용자

### 10.2 접근성 설정 페이지 (`/me/settings/accessibility`)

단순 모드 토글 + 포커스 모드 안내 + OS 고대비 모드 힌트를 별도 페이지에서도 관리 가능합니다.

### 10.3 개인정보·쿠키 설정 (`/me/settings/privacy`)

분석 쿠키(PostHog) 수신 동의를 개별적으로 관리합니다. GDPR Article 7 준수.

🔗 관련 소스:
- `/v1/frontend/src/components/PreferencesCard.tsx`
- `/v1/frontend/src/app/me/settings/accessibility/page.tsx`
- `/v1/frontend/src/app/me/settings/privacy/page.tsx`
- `/v1/frontend/src/components/CognitiveSimpleModeProvider.tsx`
- `/v1/backend/app/api/me_preferences.py`

---

## 11. 보안 · 개인정보

### 11.1 세션 관리 (`/me/account`)

- Access 토큰 1시간, Refresh 7일 자동 갱신
- 현재 활성 세션 목록 조회 (`GET /auth/sessions`)
- 특정 세션 또는 모든 세션 로그아웃 가능

### 11.2 KYC (신원 확인)

후원금 수령(작가) 또는 경매 입찰 시 신원 확인이 필요합니다:
- KYC 시작: `POST /kyc/start`
- 승인 후 정산 및 입찰 활성화

### 11.3 GDPR / 개인정보 (`/me/account`)

- **데이터 내보내기**: `/me/account`에서 JSON 파일 다운로드 (1일 1회 제한)
- **계정 삭제**: 30일 유예 기간 후 영구 삭제 (취소 버튼으로 철회 가능)
- **쿠키 동의 관리**: `/me/settings/privacy`에서 마케팅/분석 옵트인 관리
- **법적 문서**: `/legal/privacy`, `/legal/terms`, `/legal/cookies`

### 11.4 콘텐츠 경고 / 제한

- 경고 3회 이상 시 입찰 제한 (account suspended)
- 경고 내역 확인: `/warnings`

🔗 관련 소스:
- `/v1/frontend/src/app/me/account/page.tsx`
- `/v1/frontend/src/app/me/settings/privacy/page.tsx`
- `/v1/frontend/src/app/warnings/page.tsx`
- `/v1/backend/app/api/auth.py` (sessions)
- `/v1/backend/app/api/kyc.py`
- `/v1/backend/app/api/me.py` (export, delete)
- `/v1/backend/alembic/versions/0007_gdpr.py`

---

## 12. 모바일 PWA · 키보드 단축키

### 12.1 PWA (Progressive Web App)

- iOS Safari / Android Chrome에서 "홈 화면에 추가" → standalone 앱처럼 실행
- 앱 이름: Domo Lounge (short: Domo)
- 테마 컬러: #A8D76E (포트레이트 방향 고정)
- 아이콘: 192x192, 512x512 제공

> 현재 오프라인 지원(서비스 워커)은 구현되지 않았습니다. 홈 화면 추가 및 standalone 모드만 지원합니다.

### 12.2 키보드 단축키

현재 구현된 단축키:

| 단축키 | 동작 | 범위 |
|--------|------|------|
| `Esc` | 모달 닫기 / 팝오버 닫기 | 전체 |
| `Tab` / `Shift+Tab` | 포커스 순환 (모달 내) | 모달 포커스 트랩 |
| `1` / `2` / `3` / `4` | 이미지 에디터 도구 전환 (회전/크롭/모자이크/워터마크) | 이미지 에디터 내 |

> 전역 네비게이션 단축키(g h, n, j/k, l 등)는 현재 미구현입니다.

### 12.3 접근성 키보드 지원

- Skip-to-content 링크 (SkipLink 컴포넌트) — 메인 콘텐츠로 즉시 이동
- 모달 포커스 트랩 (FocusManager) — Tab 순환, Esc 닫기, 닫힘 시 원래 요소로 포커스 복원
- 모든 인터랙티브 요소에 2px focus-visible 링 표시

🔗 관련 소스:
- `/v1/frontend/public/manifest.json`
- `/v1/frontend/src/components/FocusManager.tsx`
- `/v1/frontend/src/components/SkipLink.tsx`
- `/v1/frontend/src/components/post-editor/ImageEditor.tsx`

---

## 13. 자주 묻는 질문 (FAQ)

**Q1. 후원금이 작가에게 언제 정산되나요?**
KYC 승인된 작가에게 Stripe Connect를 통해 자동 정산됩니다. KYC 미완료 시 정산 보류됩니다.

**Q2. AI 도슨트를 끄고 싶어요.**
`/posts/{id}/edit` 편집 페이지에서 "AI 도슨트 비활성화" 토글 ON. 기존 AI 도슨트는 숨겨지고, 본인 도슨트만 노출됩니다.

**Q3. 외국 사용자에게 작품이 어떻게 보이나요?**
자기소개(/me/bio), AI 캡션, AI 도슨트, AI 컬렉션 제목/설명은 5개 언어로 자동 번역됩니다. 포스트 본문 텍스트는 자동 번역되지 않으며 작성 언어 그대로 표시됩니다.

**Q4. 경매 종료 직전 입찰이 들어오면 어떻게 되나요?**
현재 anti-snipe 자동 연장 기능은 구현되지 않았습니다. 종료 시각 이후 새 입찰은 불가하며, 최후 최고 입찰자가 낙찰자가 됩니다.

**Q5. 후원 자동 갱신 해지는 어떻게 하나요?**
`/me/sponsorships` → 해당 작가 카드 → "자동 갱신 해지". 다음 만료일까지는 후원 유지, 이후 자동 종료됩니다.

**Q6. 메시지에 파일 첨부가 안 돼요.**
10MB 초과 또는 허용되지 않는 형식인지 확인하세요. 허용: 이미지(jpg/png/gif/webp), PDF. .exe, .zip 등은 불가.

**Q7. 단순 모드와 다크 모드를 동시에 쓸 수 있나요?**
가능합니다. 사이드바 하단 PreferencesCard에서 단순 모드 ON, 별도 다크 모드 설정을 동시에 적용할 수 있습니다.

**Q8. 작가 신청 후 얼마나 기다려야 하나요?**
관리자 심사 후 승인 또는 반려 알림을 받습니다. 통상 1-3일 소요됩니다. 신청 상태는 `/artists/apply` 페이지에서 확인 가능합니다.

**Q9. 포스트 공개 범위 "링크 공유"란 무엇인가요?**
`unlisted` 옵션입니다. 피드나 탐색에 노출되지 않고, 해당 포스트 URL을 아는 사람만 열람할 수 있습니다. SNS 공유 또는 특정 대상에게 작품을 선공개할 때 유용합니다.

**Q10. 커뮤니티를 만들 수 있나요?**
네. `/communities`에서 새 커뮤니티 생성이 가능합니다. 생성자가 admin 역할로 참여자를 관리합니다.

---

## 14. 가이드 검증 메타정보

본 v2 가이드는 아래 소스를 직접 분석하여 작성되었습니다.

| 항목 | 값 |
|------|---|
| alembic head | 0083_ai_collections |
| frontend 브랜치 | feature/editor-improve |
| 검증 일시 | 2026-05-08 |
| pages 검증 | `/v1/frontend/src/app/**/*.tsx` 54개 |
| backend API 검증 | `/v1/backend/app/api/*.py` (admin 제외) |
| i18n 검증 | `/v1/frontend/src/i18n/ko.json` |
| gap 분석 보고서 | [user-system-guide.gap-analysis.md](./user-system-guide.gap-analysis.md) |

---

## 추가 자료

- 관리자 운영 가이드: [admin-system-guide.ko.md](./admin-system-guide.ko.md)
- 운영 정책: [../operations/ml-experiments-policy.md](../operations/ml-experiments-policy.md)

문의: support@domo.example
