# Domo 프로토타입 Design (v1)

> **작성일**: 2026-04-11
> **기반 문서**: `01-plan/plan.md`, `01-plan/design-direction.md`
> **단계**: PDCA Design Phase
> **목적**: MVP 7개 기능 + 3개 관리자 기능의 데이터 모델, API 스펙, 화면 설계

---

## 목차

1. [개요](#1-개요)
2. [데이터 모델](#2-데이터-모델)
3. [API 설계](#3-api-설계)
4. [화면 설계](#4-화면-설계)
5. [상태 전이 다이어그램](#5-상태-전이-다이어그램)
6. [주요 비즈니스 로직](#6-주요-비즈니스-로직)
7. [보안 및 권한](#7-보안-및-권한)
8. [알림 시스템](#8-알림-시스템)
9. [구현 우선순위](#9-구현-우선순위)
10. [열린 이슈 → 결정 사항](#10-열린-이슈--결정-사항)
11. [Design Tokens (두쫀쿠 테마)](#11-design-tokens-두쫀쿠-테마)
12. [시연 시나리오](#12-시연-시나리오-고객-커뮤니케이션용)

---

## 1. 개요

### 1.1 시스템 구성

```
┌─────────────────────────────────────────────────┐
│           domo.tuzigroup.com (Web)              │
│           Next.js 15 + TypeScript               │
└──────────────────┬──────────────────────────────┘
                   │ REST API (JWT Bearer)
┌──────────────────▼──────────────────────────────┐
│         api.domo.tuzigroup.com (API)            │
│              FastAPI + Python 3.12              │
└──┬───────────┬──────────┬──────────┬────────────┘
   │           │          │          │
   ▼           ▼          ▼          ▼
┌──────┐  ┌─────────┐  ┌────────┐  ┌──────────┐
│ PG   │  │ Redis   │  │ Stripe │  │ Firebase │
│ 16   │  │ 7       │  │ API    │  │ FCM      │
└──────┘  └─────────┘  └────────┘  └──────────┘
```

### 1.2 주요 도메인

| 도메인 | 책임 |
|--------|------|
| Identity | 회원가입, 로그인, 작가 심사, 프로필 |
| Content | 일반 포스트, 상품 포스트, 미디어 업로드 |
| Social | 팔로우, 좋아요, 댓글 |
| Sponsorship | 블루버드 후원 (일회성/정기) |
| Commerce | 경매, 즉시 구매, 주문, 결제 |
| Moderation | 신고, 경고, 이의 제기, 디지털 아트 판독 |
| Admin | 작가 승인, 신고 처리, 대시보드 |

---

## 2. 데이터 모델

### 2.1 ERD 개요

```
User ─┬── ArtistApplication (심사 신청 기록)
      ├── ArtistProfile (승인 후 작가 메타)
      │
      ├── Post ─────┬──── MediaAsset
      │             ├──── Like
      │             ├──── Comment
      │             └──── ProductPost ─┬── Auction ── Bid
      │                                └── Order ── Payment
      │
      ├── Sponsorship (as Sponsor)
      ├── Subscription (as Sponsor)
      ├── Follow (follower/followee)
      ├── Notification
      ├── Report (as Reporter)
      └── Warning
```

### 2.2 테이블 상세 스키마

#### users
```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           VARCHAR(255) UNIQUE NOT NULL,
  role            VARCHAR(20) NOT NULL DEFAULT 'user',
    -- 'user' | 'artist' | 'admin'
  status          VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active' | 'suspended' | 'deleted'
  sns_provider    VARCHAR(20),
    -- 'google' | 'kakao' | 'apple'
  sns_id          VARCHAR(255),
  display_name    VARCHAR(100) NOT NULL,
  avatar_url      TEXT,
  bio             TEXT,
  country_code    VARCHAR(2),
  language        VARCHAR(10) DEFAULT 'ko',
  birth_date      DATE,
  is_minor        BOOLEAN DEFAULT FALSE,
  guardian_id     UUID REFERENCES users(id),
  warning_count   INT DEFAULT 0,
  gdpr_consent_at TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_role_status ON users(role, status);
CREATE UNIQUE INDEX idx_users_sns ON users(sns_provider, sns_id);
```

#### artist_applications
```sql
CREATE TABLE artist_applications (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  portfolio_urls  TEXT[],
  school          VARCHAR(200),
  intro_video_url TEXT,
  sample_images   TEXT[],
  statement       TEXT,
  status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'approved' | 'rejected'
  reviewed_by     UUID REFERENCES users(id),
  review_note     TEXT,
  reviewed_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_artist_apps_status ON artist_applications(status, created_at);
```

#### artist_profiles
```sql
-- 작가 승인 후 생성되는 메타 정보. users 테이블의 공통 프로필과 분리.
CREATE TABLE artist_profiles (
  user_id          UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  application_id   UUID REFERENCES artist_applications(id),
  verified_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  verified_by      UUID REFERENCES users(id),
  school           VARCHAR(200),
  intro_video_url  TEXT,
  portfolio_urls   TEXT[],
  statement        TEXT,
  badge_level      VARCHAR(20) DEFAULT 'emerging',
    -- 'emerging' | 'featured' | 'popular' | 'master' (2차 인덱스 시스템에서 갱신)
  payout_country   VARCHAR(2),
  payout_account   JSONB,
    -- 프로토타입에서는 참조용 JSON, 실제 정산 연동은 2차
  guardian_consent BOOLEAN DEFAULT FALSE,
    -- 미성년 작가의 경우 보호자 동의 여부
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
```

#### posts
```sql
CREATE TABLE posts (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id       UUID NOT NULL REFERENCES users(id),
  type            VARCHAR(20) NOT NULL,
    -- 'general' | 'product'
  title           VARCHAR(200),
  content         TEXT,
  genre           VARCHAR(50),
    -- 'painting' | 'photography' | 'sculpture' | ...
  tags            TEXT[],
  language        VARCHAR(10) DEFAULT 'ko',
  like_count      INT DEFAULT 0,
  comment_count   INT DEFAULT 0,
  view_count      INT DEFAULT 0,
  bluebird_count  INT DEFAULT 0,
  status          VARCHAR(20) DEFAULT 'pending_review',
    -- 'draft' | 'pending_review' | 'published' | 'hidden' | 'deleted'
    -- 업로드 직후 이미지 포함 포스트는 pending_review로 시작하여
    -- 디지털 아트 판독 통과 시 published로 전환됨.
    -- 텍스트 전용 일반 포스트는 바로 published 가능 (application 레이어에서 처리).
  digital_art_check VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'approved' | 'rejected' | 'not_required'
    -- not_required: 텍스트 전용 포스트 등 판독 불필요
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_posts_author ON posts(author_id, created_at DESC);
CREATE INDEX idx_posts_feed ON posts(status, type, created_at DESC);
CREATE INDEX idx_posts_genre ON posts(genre, status, created_at DESC);
```

#### media_assets
```sql
CREATE TABLE media_assets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id         UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  type            VARCHAR(20) NOT NULL,
    -- 'image' | 'video' | 'external_embed'
  url             TEXT NOT NULL,
  thumbnail_url   TEXT,
  width           INT,
  height          INT,
  duration_sec    INT,
  size_bytes      BIGINT,
  external_source VARCHAR(20),
    -- 'youtube' | 'vimeo'
  external_id     VARCHAR(100),
  order_index     INT DEFAULT 0,
  is_making_video BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_media_post ON media_assets(post_id, order_index);
```

#### product_posts
```sql
CREATE TABLE product_posts (
  post_id         UUID PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  is_auction      BOOLEAN DEFAULT FALSE,
  is_buy_now      BOOLEAN DEFAULT FALSE,
  buy_now_price   DECIMAL(12, 2),
  currency        VARCHAR(3) DEFAULT 'KRW',
  dimensions      VARCHAR(100),
  medium          VARCHAR(100),
  year            INT,
  is_sold         BOOLEAN DEFAULT FALSE
);
```

#### auctions
```sql
CREATE TABLE auctions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_post_id UUID NOT NULL REFERENCES product_posts(post_id),
  start_price     DECIMAL(12, 2) NOT NULL,
  min_increment   DECIMAL(12, 2) DEFAULT 1000,
  current_price   DECIMAL(12, 2) NOT NULL,
  current_winner  UUID REFERENCES users(id),
  start_at        TIMESTAMPTZ NOT NULL,
  end_at          TIMESTAMPTZ NOT NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    -- 'scheduled' | 'active' | 'ended' | 'cancelled' | 'settled'
  bid_count       INT DEFAULT 0,
  payment_deadline TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_auctions_status ON auctions(status, end_at);
```

#### bids
```sql
CREATE TABLE bids (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  auction_id      UUID NOT NULL REFERENCES auctions(id),
  bidder_id       UUID NOT NULL REFERENCES users(id),
  amount          DECIMAL(12, 2) NOT NULL,
  status          VARCHAR(20) DEFAULT 'active',
    -- 'active' | 'outbid' | 'won' | 'cancelled'
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_bids_auction ON bids(auction_id, amount DESC);
```

#### orders
```sql
CREATE TABLE orders (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  buyer_id        UUID NOT NULL REFERENCES users(id),
  seller_id       UUID NOT NULL REFERENCES users(id),
  product_post_id UUID NOT NULL REFERENCES product_posts(post_id),
  source          VARCHAR(20) NOT NULL,
    -- 'auction' | 'buy_now'
  auction_id      UUID REFERENCES auctions(id),
  amount          DECIMAL(12, 2) NOT NULL,
  currency        VARCHAR(3) DEFAULT 'KRW',
  platform_fee    DECIMAL(12, 2) DEFAULT 0,
  status          VARCHAR(30) NOT NULL DEFAULT 'pending_payment',
    -- 'pending_payment' | 'paid' | 'cancelled' | 'expired' | 'refunded'
  stripe_payment_intent_id VARCHAR(100),
  payment_due_at  TIMESTAMPTZ,
  paid_at         TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_orders_buyer ON orders(buyer_id, created_at DESC);
CREATE INDEX idx_orders_seller ON orders(seller_id, created_at DESC);
```

#### sponsorships
```sql
CREATE TABLE sponsorships (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sponsor_id      UUID NOT NULL REFERENCES users(id),
  artist_id       UUID NOT NULL REFERENCES users(id),
  post_id         UUID REFERENCES posts(id),
  bluebird_count  INT NOT NULL,
  amount          DECIMAL(12, 2) NOT NULL,
  currency        VARCHAR(3) DEFAULT 'KRW',
  is_anonymous    BOOLEAN DEFAULT FALSE,
  visibility      VARCHAR(20) DEFAULT 'public',
    -- 'public' | 'artist_only' | 'private'
  message         TEXT,
  stripe_payment_intent_id VARCHAR(100),
  status          VARCHAR(20) DEFAULT 'completed',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sponsorship_artist ON sponsorships(artist_id, created_at DESC);
```

#### subscriptions (정기 후원)
```sql
CREATE TABLE subscriptions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sponsor_id      UUID NOT NULL REFERENCES users(id),
  artist_id       UUID NOT NULL REFERENCES users(id),
  monthly_bluebird INT NOT NULL,
  monthly_amount  DECIMAL(12, 2) NOT NULL,
  currency        VARCHAR(3) DEFAULT 'KRW',
  stripe_subscription_id VARCHAR(100),
  status          VARCHAR(20) DEFAULT 'active',
    -- 'active' | 'cancelled' | 'past_due'
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
    -- TRUE: 해지 요청됨, current_period_end까지만 active 유지
    -- current_period_end 경과 시 status='cancelled'로 전이 (webhook 또는 cron)
  current_period_end TIMESTAMPTZ,
  cancelled_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### follows
```sql
CREATE TABLE follows (
  follower_id     UUID NOT NULL REFERENCES users(id),
  followee_id     UUID NOT NULL REFERENCES users(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (follower_id, followee_id)
);
CREATE INDEX idx_follows_followee ON follows(followee_id);
```

#### likes
```sql
CREATE TABLE likes (
  user_id         UUID NOT NULL REFERENCES users(id),
  post_id         UUID NOT NULL REFERENCES posts(id),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (user_id, post_id)
);
```

#### comments
```sql
CREATE TABLE comments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id         UUID NOT NULL REFERENCES posts(id),
  author_id       UUID NOT NULL REFERENCES users(id),
  parent_id       UUID REFERENCES comments(id),
  content         TEXT NOT NULL,
  status          VARCHAR(20) DEFAULT 'visible',
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_comments_post ON comments(post_id, created_at);
```

#### reports
```sql
CREATE TABLE reports (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reporter_id     UUID NOT NULL REFERENCES users(id),
  target_type     VARCHAR(20) NOT NULL,
    -- 'post' | 'comment' | 'user'
  target_id       UUID NOT NULL,
  reason          VARCHAR(50) NOT NULL,
  description     TEXT,
  status          VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'resolved' | 'rejected'
  handled_by      UUID REFERENCES users(id),
  handled_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### warnings (3진 아웃)
```sql
CREATE TABLE warnings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  reason          TEXT NOT NULL,
  report_id       UUID REFERENCES reports(id),
  issued_by       UUID REFERENCES users(id),
  is_active       BOOLEAN DEFAULT TRUE,
  appealed        BOOLEAN DEFAULT FALSE,
  appeal_note     TEXT,
  cancelled_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### notifications
```sql
CREATE TABLE notifications (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id),
  type            VARCHAR(50) NOT NULL,
    -- 'sponsorship' | 'bid' | 'auction_won' | 'follow' | 'comment' | 'warning' | ...
  title           VARCHAR(200),
  body            TEXT,
  link            TEXT,
  is_read         BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

#### system_settings
```sql
CREATE TABLE system_settings (
  key             VARCHAR(100) PRIMARY KEY,
  value           JSONB NOT NULL,
  updated_by      UUID REFERENCES users(id),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
-- 예시 키:
-- 'bluebird_unit_price' = {"amount": 1000, "currency": "KRW"}
-- 'platform_fee_auction' = {"percent": 10}
-- 'platform_fee_sponsorship' = {"percent": 5}
-- 'auction_payment_deadline_days' = {"days": 3}
-- 'warning_threshold' = {"count": 3}
```

---

## 3. API 설계

### 3.1 공통 사항

- **Base URL**: `https://api.domo.tuzigroup.com/v1`
- **인증**: `Authorization: Bearer {JWT}`

#### 성공 응답 포맷 (단일)
```json
{
  "data": { ... }
}
```

#### 성공 응답 포맷 (목록 + 페이지네이션)
```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "base64_encoded_cursor",
    "has_more": true
  }
}
```

#### 에러 응답 포맷
```json
{
  "error": {
    "code": "INSUFFICIENT_BID",
    "message": "Bid amount must be higher than current price + min increment",
    "details": { "current_price": 420000, "min_increment": 10000 }
  }
}
```

#### 표준 에러 코드

| HTTP | 코드 | 설명 |
|------|------|------|
| 400 | `VALIDATION_ERROR` | 요청 본문/쿼리 검증 실패 |
| 400 | `INVALID_REQUEST` | 일반적인 잘못된 요청 |
| 401 | `UNAUTHORIZED` | JWT 없음/만료 |
| 403 | `FORBIDDEN` | 권한 부족 |
| 403 | `ACCOUNT_SUSPENDED` | 경고 누적으로 정지된 계정 |
| 404 | `NOT_FOUND` | 리소스 없음 |
| 409 | `CONFLICT` | 중복 생성 등 충돌 |
| 409 | `INSUFFICIENT_BID` | 입찰가가 current_price + min_increment 미만 |
| 409 | `AUCTION_CLOSED` | 종료된 경매 |
| 409 | `AUCTION_NOT_STARTED` | 시작 전 경매 |
| 409 | `SELF_BID_FORBIDDEN` | 자기 작품 입찰 시도 |
| 409 | `ALREADY_PURCHASED` | 이미 판매된 상품 |
| 422 | `DIGITAL_ART_PENDING` | 판독 대기 중 포스트 노출 시도 |
| 429 | `RATE_LIMITED` | API 호출 한도 초과 |
| 500 | `INTERNAL_ERROR` | 서버 내부 오류 |
| 502 | `STRIPE_ERROR` | Stripe API 실패 |

- **페이지네이션**: 커서 기반
  - 요청: `?cursor=<base64>&limit=20`
  - 응답: 위 "성공 응답 포맷 (목록)" 참조
  - 기본 limit: 20, 최대 100

### 3.2 엔드포인트 목록

#### Auth
| Method | Path | 설명 |
|--------|------|------|
| POST | `/auth/sns/{provider}` | SNS 로그인 (google/kakao/apple) |
| POST | `/auth/refresh` | 토큰 갱신 |
| POST | `/auth/logout` | 로그아웃 |
| GET  | `/auth/me` | 내 정보 조회 |

#### Users & Artists
| Method | Path | 설명 |
|--------|------|------|
| GET  | `/users/{id}` | 유저 프로필 조회 |
| PATCH| `/users/me` | 내 프로필 수정 |
| POST | `/artists/apply` | 작가 심사 신청 |
| GET  | `/artists/apply/me` | 내 심사 상태 |
| POST | `/users/{id}/follow` | 팔로우 |
| DELETE | `/users/{id}/follow` | 언팔로우 |
| GET  | `/users/{id}/followers` | 팔로워 목록 |
| GET  | `/users/{id}/following` | 팔로잉 목록 |

#### Posts
| Method | Path | 설명 |
|--------|------|------|
| GET  | `/posts/feed` | 개인화 피드 (팔로우 70% + 트렌딩 30% 혼합, auth 필요) |
| GET  | `/posts/feed?following_only=true` | 팔로잉 전용 피드 (팔로우한 작가의 포스트만, auth 필요) |
| GET  | `/posts/explore` | 탐색 (장르/인기순, 공개) |
| GET  | `/posts/search?q=` | 검색 |
| POST | `/posts` | 포스트 작성 (general/product) |
| GET  | `/posts/{id}` | 포스트 상세 |
| PATCH| `/posts/{id}` | 포스트 수정 |
| DELETE | `/posts/{id}` | 포스트 삭제 |
| POST | `/posts/{id}/like` | 좋아요 |
| DELETE | `/posts/{id}/like` | 좋아요 취소 |
| GET  | `/posts/{id}/comments` | 댓글 목록 |
| POST | `/posts/{id}/comments` | 댓글 작성 |

#### Media Upload
| Method | Path | 설명 |
|--------|------|------|
| POST | `/media/upload` | 이미지/영상 업로드 (multipart) |
| POST | `/media/external` | YouTube/Vimeo 임베드 등록 |

#### Sponsorship (Bluebird)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/sponsorships` | 일회성 후원 생성 (블루버드 수량) |
| GET  | `/sponsorships/mine` | 내 후원 이력 |
| GET  | `/users/{id}/sponsorships` | 작가 받은 후원 (공개 범위 적용) |
| POST | `/subscriptions` | 정기 후원 시작 |
| DELETE | `/subscriptions/{id}` | 정기 후원 해지 |
| GET  | `/subscriptions/mine` | 내 정기 후원 목록 |

#### Auctions & Orders
| Method | Path | 설명 |
|--------|------|------|
| POST | `/auctions` | 경매 생성 (상품 포스트 기반) |
| GET  | `/auctions` | 경매 목록 |
| GET  | `/auctions/{id}` | 경매 상세 |
| POST | `/auctions/{id}/bids` | 입찰 |
| GET  | `/auctions/{id}/bids` | 입찰 내역 |
| POST | `/products/{postId}/buy-now` | 즉시 구매 |
| GET  | `/orders/mine` | 내 주문 목록 |
| POST | `/orders/{id}/pay` | 결제 (Stripe Payment Intent 생성) |
| POST | `/orders/{id}/cancel` | 주문 취소 |

#### Notifications
| Method | Path | 설명 |
|--------|------|------|
| GET  | `/notifications` | 내 알림 목록 |
| GET  | `/notifications/unread-count` | 읽지 않은 알림 개수 |
| PATCH| `/notifications/{id}/read` | 단건 읽음 처리 |
| POST | `/notifications/read-all` | 전체 읽음 처리 |
| POST | `/notifications/fcm-token` | FCM 토큰 등록 |
| DELETE | `/notifications/fcm-token` | FCM 토큰 해제 (로그아웃) |

#### Reports & Moderation
| Method | Path | 설명 |
|--------|------|------|
| POST | `/reports` | 신고 생성 |
| GET  | `/warnings/mine` | 내 경고 목록 |
| POST | `/warnings/{id}/appeal` | 경고 이의 제기 |

#### Search Filters (탐색/검색 보강)
검색 및 탐색 API는 다음 쿼리 파라미터를 공통 지원:
- `q`: 키워드
- `genre`: 장르 (`painting`, `photography`, `sculpture` 등)
- `type`: 포스트 타입 (`general`, `product`)
- `price_min`, `price_max`: 가격대 (currency 기준)
- `currency`: KRW | USD
- `is_auction`: true/false
- `sort`: `latest` | `popular` | `ending_soon` (경매)

#### Admin
| Method | Path | 설명 |
|--------|------|------|
| GET  | `/admin/artists/applications` | 심사 대기 목록 |
| POST | `/admin/artists/applications/{id}/approve` | 승인 (users.role=artist 전환 + artist_profiles 생성) |
| POST | `/admin/artists/applications/{id}/reject` | 거절 |
| GET  | `/admin/reports` | 신고 대기 목록 |
| POST | `/admin/reports/{id}/resolve` | 신고 처리 + 경고 발급 |
| GET  | `/admin/appeals` | 경고 이의 제기 목록 (appealed=true) |
| POST | `/admin/warnings/{id}/cancel` | 경고 취소 (이의 제기 승인) |
| POST | `/admin/warnings/{id}/reject-appeal` | 이의 제기 거절 |
| GET  | `/admin/posts/digital-art-queue` | 디지털 아트 판독 대기 |
| POST | `/admin/posts/{id}/digital-art-verdict` | 판독 결과 입력 (approve/reject) |
| GET  | `/admin/dashboard/revenue` | 매출 대시보드 |
| GET  | `/admin/dashboard/stats` | 사용자/콘텐츠 통계 |
| GET  | `/admin/settings` | 시스템 설정 조회 |
| PATCH| `/admin/settings/{key}` | 시스템 설정 수정 |

#### Webhooks
| Method | Path | 설명 |
|--------|------|------|
| POST | `/webhooks/stripe` | Stripe 이벤트 수신 (결제/구독/환불) |

### 3.3 주요 요청/응답 예시

#### 포스트 작성 (상품 포스트)

```http
POST /v1/posts
Content-Type: application/json

{
  "type": "product",
  "title": "Sunrise in Lima",
  "content": "...",
  "genre": "painting",
  "tags": ["oil", "landscape"],
  "media_ids": ["uuid1", "uuid2"],
  "product": {
    "is_auction": true,
    "is_buy_now": false,
    "dimensions": "50x70cm",
    "medium": "Oil on canvas",
    "year": 2026
  },
  "auction": {
    "start_price": 300000,
    "min_increment": 10000,
    "start_at": "2026-04-12T00:00:00Z",
    "end_at": "2026-04-19T00:00:00Z"
  }
}
```

#### 블루버드 후원

```http
POST /v1/sponsorships

{
  "artist_id": "uuid",
  "post_id": "uuid",
  "bluebird_count": 12,
  "is_anonymous": false,
  "visibility": "public",
  "message": "Love your work!"
}
```

응답:
```json
{
  "success": true,
  "data": {
    "sponsorship_id": "uuid",
    "amount": 12000,
    "currency": "KRW",
    "stripe_client_secret": "pi_xxx_secret_xxx"
  }
}
```

---

## 4. 화면 설계

### 4.1 화면 목록 (23개)

**공개 화면**
1. 랜딩 페이지
2. 로그인 (SNS)
3. 회원가입 완료 (온보딩 설문: 관심 장르, 언어, FCM 토큰 등록)

**피드 & 탐색**
4. 홈 피드 (팔로우 70% + 트렌딩 30% 혼합, 비로그인 시 공개 피드)
5. 팔로잉 피드 (팔로우한 작가의 포스트 전용, 로그인 필요)
6. 탐색 (장르/인기, 비로그인도 접근 가능)
7. 검색 결과 (필터: 장르/가격/경매 상태)
8. 알림 센터 (읽지 않음 카운트 + 전체 읽음)

**프로필**
8. 유저 프로필
9. 작가 프로필 (작가 전용 필드: 학교, 소개 영상, 뱃지)
10. 프로필 편집
11. 작가 심사 신청

**콘텐츠**
12. 포스트 상세
13. 포스트 작성/편집 (외부 임베드 YouTube/Vimeo URL 입력 포함)
14. 작품 상세 (상품 포스트: 즉시 구매 + 경매 입찰 조건부 표시)

**거래**
15. 경매 상세 (실시간 입찰, 2초 폴링)
16. 블루버드 후원 모달
17. 정기 후원 관리 (해지 시 당월 말까지 유지 안내)
18. 주문 내역 / 결제

**관리자**
19. 어드민 대시보드 (매출 + 통계)
20. 작가 승인 페이지
21. 신고/이의 제기 처리 페이지 (탭 구조)
22. 디지털 아트 판독 큐
23. 시스템 설정 페이지 (블루버드 단가, 수수료율, 미결제 기한 등)

### 4.2 주요 화면 와이어프레임 (텍스트)

#### 홈 피드 (데스크톱, X 스타일 3컬럼)

```
┌───────────────────────────────────────────────────────────────┐
│ [Logo Domo]                                          [프로필] │
├──────────┬─────────────────────────────────┬──────────────────┤
│          │                                 │                  │
│ ▢ 홈     │  [피드 아이템 1]                │ 트렌딩 작품       │
│ ▢ 팔로잉 │  ┌─────────────────────┐        │ ┌──────────────┐ │
│ ▢ 탐색   │  │  [작품 이미지]       │        │ │ @artist_lima │ │
│ ▢ 알림   │  │                     │        │ │ ♥ 234 🕊56   │ │
│ ▢ 프로필 │  │                     │        │ └──────────────┘ │
│          │  │                     │        │                  │
│ ─────    │  └─────────────────────┘        │ 추천 작가         │
│          │  @artist_lima · 2h              │ ┌──────────────┐ │
│ [+ 작성] │  ♥ 234  💬 12  🕊 56블루버드    │ │ @maria_rio   │ │
│          │                                 │ │ ✓ Artist     │ │
│          │  [피드 아이템 2]                │ └──────────────┘ │
│          │  ...                            │                  │
└──────────┴─────────────────────────────────┴──────────────────┘
```

**사이드바 메뉴 (로그인 상태별)**:
- 비로그인: 홈(추천) · 탐색 · [로그인] 버튼
- 로그인: 홈(혼합) · 팔로잉 · 탐색 · 알림(뱃지) · 프로필 · [+ 작성]
- Admin 추가: 대시보드 · 작가 승인 · 모더레이션 · 시스템 설정

**반응형 브레이크포인트**:
- `sm` (<768px): 좌측 사이드바 숨김, 하단 `MobileTabBar` 표시 + 우하단 FAB(+)
- `md` (768~1280px): 아이콘 전용 사이드바 (w-80px), 우측 레일 숨김
- `xl` (>1280px): 풀 사이드바 (w-260px, 로고+레이블) + 우측 레일 (w-340px)

#### 홈 피드 (모바일, 하단 탭바)

```
┌─────────────────────────────┐
│ 추천                        │ ← sticky header
│ 팔로우한 작가와 인기 작품... │
├─────────────────────────────┤
│                             │
│  [피드 아이템 1]            │
│  ┌───────────────────────┐  │
│  │   [작품 이미지]        │  │
│  │                       │  │
│  │                       │  │
│  └───────────────────────┘  │
│  @artist_lima · 2h          │
│  ♥ 234  💬 12  🕊 56        │
│                             │
│  [피드 아이템 2]            │
│  ...                        │
│                             │
│                      ┌───┐  │
│                      │ + │  │ ← FAB (logged-in)
│                      └───┘  │
├─────────────────────────────┤
│ 🏠   👥   🔍   🔔   👤     │ ← 하단 탭바 (로그인)
└─────────────────────────────┘
   홈  팔로잉 탐색 알림 프로필

비로그인 시 하단 탭바:
│ 🏠         🔍         👤   │
   홈         탐색      로그인
```

**모바일 FAB(+) 탭 시 작성 메뉴 팝오버**:
```
  ┌──────────────────────┐
  │ 🎨 작품 등록          │ → /posts/new?type=product
  │    판매·경매·블루버드 │
  ├──────────────────────┤
  │ ✏️ 일반 포스트        │ → /posts/new?type=general
  │    작업 과정·생각     │
  └──────────────────────┘
```

데스크탑 사이드바의 `+ 작성` 버튼도 동일한 `CreateMenu` 팝오버를 사용 (align="top", side="left").

#### 작품 상세 (TikTok 스타일 몰입형)

> CTA 버튼은 **조건부 렌더링**:
> - `product_posts.is_buy_now = TRUE` → "즉시 구매" 버튼 표시
> - `product_posts.is_auction = TRUE` → "경매 입찰" 버튼 표시
> - 둘 다 TRUE → 두 버튼 모두 표시 (즉시 구매 우선 노출)
> - 블루버드 후원은 모든 상품 포스트에서 항상 표시

```
┌─────────────────────────────────────┐
│  ←                        ⋯         │
│                                      │
│  [작품 이미지 풀스크린 - swipe로    │
│   다음 이미지]                       │
│                                      │
│  ━━━━━━━━━━━━━━━━━━━━━ 페이드 그라데이션
│  @artist_lima · 🎖 Verified          │
│  "Sunrise in Lima"                   │
│  Oil on canvas · 50x70cm · 2026      │
│                                      │
│  ♥ 234    💬 12    ↗ 공유             │
│  ┌─────────────────────────────────┐ │
│  │  🕊 블루버드 후원               │ │  ← 항상 표시
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │  💳 즉시 구매 (₩500,000)         │ │  ← is_buy_now일 때만
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │  🔨 경매 입찰 (₩420,000)         │ │  ← is_auction일 때만
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

#### 경매 상세

```
┌─────────────────────────────────────────┐
│ [작품 이미지]     │  경매 정보             │
│                  │  ─────                  │
│                  │  현재 입찰가             │
│                  │  ₩ 420,000              │
│                  │                          │
│                  │  남은 시간               │
│                  │  02:15:33                │  ← 카운트다운 (10초 이하 펄스)
│                  │                          │
│                  │  입찰 수: 14             │
│                  │  입찰자: @collector_jp  │
│                  │                          │
│                  │  ┌────────────────────┐ │
│                  │  │ ₩ 430,000          │ │
│                  │  └────────────────────┘ │
│                  │  [입찰하기]              │  ← Primary
│                  │                          │
│                  │  [입찰 내역 ▼]          │
└─────────────────────────────────────────┘
```

#### 블루버드 후원 모달

```
┌────────────────────────────┐
│  🕊  블루버드 후원          │
│  ────────────────────────  │
│                             │
│  @artist_lima에게          │
│                             │
│  블루버드 수량              │
│  [ - ] [  5  ] [ + ]        │
│  = ₩ 5,000                 │
│                             │
│  메시지 (선택)              │
│  ┌────────────────────┐    │
│  │                    │    │
│  └────────────────────┘    │
│                             │
│  공개 범위                  │
│  ○ 전체 공개               │
│  ◉ 작가에게만              │
│  ○ 비공개                  │
│                             │
│  □ 익명 후원               │
│                             │
│  ┌────────────────────┐    │
│  │  🕊 후원하기        │    │  ← Primary
│  └────────────────────┘    │
└────────────────────────────┘
```

#### 관리자 작가 승인 페이지

```
┌─────────────────────────────────────────────────┐
│ [Admin Domo]                            관리자  │
├─────────────────────────────────────────────────┤
│ ┃ 작가 승인 대기 (12)  │  신고 (3)  │  매출    │
│ ┃                                                │
│ ┃ ┌─────────────────────────────────────────┐  │
│ ┃ │ @newartist1 · Peru                      │  │
│ ┃ │ 신청일 2026-04-10                       │  │
│ ┃ │                                         │  │
│ ┃ │ [포트폴리오 썸네일 4장]                 │  │
│ ┃ │                                         │  │
│ ┃ │ School: Lima Art Academy                │  │
│ ┃ │ Statement: "...."                        │  │
│ ┃ │                                         │  │
│ ┃ │ [승인] [거절] [상세 보기]              │  │
│ ┃ └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 5. 상태 전이 다이어그램

### 5.1 작가 심사 신청

```
[pending] ──(admin approve)──> [approved] ──> user.role = 'artist'
   │
   └──(admin reject)──> [rejected] ──> 재신청 가능
```

### 5.2 경매

```
[scheduled] ──(start_at)──> [active] ──(end_at, no bid)──> [ended]
                              │                               │
                              │                               └── 종료 처리
                              │
                              └──(end_at, has bid)──> [ended]
                                                         │
                                                         ▼
                                                    주문 생성
                                                         │
                                                         ▼
                                                  [pending_payment]
```

### 5.3 주문 (경매 낙찰 후)

```
[pending_payment]
      │
      ├──(낙찰자 결제)──> [paid] ──> 작가 알림
      │
      └──(payment_due_at 초과)──> [expired]
                                      │
                                      ├── 차순위 입찰자 존재?
                                      │      ├── YES → 새 order 생성 [pending_payment]
                                      │      └── NO  → 경매 재등록 또는 종료
                                      │
                                      └── 낙찰자 경고 +1
```

### 5.4 정기 후원 해지

```
[active] ──(cancel)──> current_period_end까지 [active] 유지
                              │
                              └──(next billing)──> [cancelled] + 환불 안 함
```

### 5.5 경고 (3진 아웃)

```
warning_count: 0 → 1 → 2 → 3
                            │
                            └──> status = 'suspended'
                                    │
                                    └──(이의 제기 승인)──> warning_count -1, 재활성화
```

### 5.6 이의 제기 플로우

```
[경고 발급] ──(유저 이의 제기)──> warnings.appealed = TRUE
                                         │
                                         └── 관리자 /admin/appeals 큐에 진입
                                                │
                                                ├──(승인)──> warning.cancelled_at 기록,
                                                │              warning.is_active=FALSE,
                                                │              user.warning_count -1,
                                                │              suspended였다면 재활성화
                                                │
                                                └──(거절)──> appealed 유지, is_active 유지,
                                                              유저에게 거절 알림
```

### 5.7 디지털 아트 판독 플로우

```
[포스트 업로드 (미디어 포함)]
        │
        ▼
posts.status = 'pending_review'
posts.digital_art_check = 'pending'
        │
        ├── 텍스트 전용 포스트 → digital_art_check = 'not_required',
        │                         status = 'published' (즉시)
        │
        └── 이미지/영상 포스트 → /admin/posts/digital-art-queue 진입
                                       │
                                       ├──(관리자 approve)──>
                                       │     digital_art_check = 'approved',
                                       │     status = 'published',
                                       │     작성자에게 알림
                                       │
                                       └──(관리자 reject)──>
                                             digital_art_check = 'rejected',
                                             status = 'hidden',
                                             작성자에게 사유 알림
```

### 5.8 정기 후원 해지 플로우

```
[active, cancel_at_period_end=FALSE]
        │
        │ 유저 해지 요청
        ▼
cancel_at_period_end = TRUE
cancelled_at = now()
status 는 여전히 'active' (current_period_end까지 서비스 유지)
        │
        │ Stripe webhook: customer.subscription.deleted 또는
        │ cron: current_period_end 경과
        ▼
status = 'cancelled'
        │ (당월분 환불 없음, 다음 달부터 과금 중단)
```

---

## 6. 주요 비즈니스 로직

### 6.1 블루버드 금액 계산

```python
def calculate_sponsorship_amount(bluebird_count: int) -> dict:
    unit_price = get_system_setting("bluebird_unit_price")
    # {"amount": 1000, "currency": "KRW"}
    return {
        "amount": bluebird_count * unit_price["amount"],
        "currency": unit_price["currency"],
    }
```

### 6.2 경매 입찰 검증 (동시성 제어 포함)

```python
def place_bid(auction_id, bidder_id, amount):
    # SELECT ... FOR UPDATE 로 행 레벨 락 (낙관적 락 대체)
    with transaction() as tx:
        auction = tx.execute(
            "SELECT * FROM auctions WHERE id=:id FOR UPDATE",
            id=auction_id,
        ).one()

        # 상태 검증
        if auction.status != "active":
            raise ApiError("AUCTION_CLOSED")
        if now() < auction.start_at:
            raise ApiError("AUCTION_NOT_STARTED")
        if now() >= auction.end_at:
            raise ApiError("AUCTION_CLOSED")

        # 권한 검증
        user = get_user(bidder_id)
        if user.warning_count >= 3 or user.status == "suspended":
            raise ApiError("ACCOUNT_SUSPENDED")
        if bidder_id == auction.product.author_id:
            raise ApiError("SELF_BID_FORBIDDEN")

        # 금액 검증
        min_required = auction.current_price + auction.min_increment
        if amount < min_required:
            raise ApiError("INSUFFICIENT_BID", details={
                "current_price": auction.current_price,
                "min_increment": auction.min_increment,
            })

        # 이전 1위 입찰 -> outbid
        previous_winner = auction.current_winner
        tx.execute(
            "UPDATE bids SET status='outbid' "
            "WHERE auction_id=:aid AND status='active'",
            aid=auction_id,
        )
        # 새 입찰 생성
        tx.execute(
            "INSERT INTO bids(auction_id, bidder_id, amount, status) "
            "VALUES(:aid, :bid, :amt, 'active')",
            aid=auction_id, bid=bidder_id, amt=amount,
        )
        # 경매 current_price/winner/bid_count 갱신
        tx.execute(
            "UPDATE auctions SET current_price=:p, current_winner=:w, "
            "bid_count=bid_count+1 WHERE id=:id",
            p=amount, w=bidder_id, id=auction_id,
        )

    # 트랜잭션 커밋 후 알림
    if previous_winner and previous_winner != bidder_id:
        send_notification(previous_winner, "bid_outbid")
    send_notification(auction.product.author_id, "bid_placed")
    # 프로토타입: 2초 폴링 방식 사용 (WebSocket은 2차)
    invalidate_auction_cache(auction_id)
```

### 6.3 경매 종료 & 주문 생성

```python
def finalize_auction(auction_id):
    auction = get_auction(auction_id)
    if auction.end_at > now():
        return

    top_bid = get_top_bid(auction_id)
    if not top_bid:
        update_auction_status(auction_id, "ended")
        return

    payment_deadline_days = get_system_setting("auction_payment_deadline_days")["days"]
    order = create_order(
        buyer_id=top_bid.bidder_id,
        seller_id=auction.product.author_id,
        source="auction",
        auction_id=auction_id,
        amount=top_bid.amount,
        payment_due_at=now() + timedelta(days=payment_deadline_days),
    )
    update_auction_status(auction_id, "ended")
    send_notification(top_bid.bidder_id, "auction_won", order_id=order.id)
```

### 6.4 미결제 처리 (Cron, 5분 간격)

**정책 요약**:
1. 결제 기한(`system_settings.auction_payment_deadline_days`, 기본 3일) 초과 시 주문 만료
2. 낙찰자에게 경고 +1 발급
3. 차순위 입찰자에게 낙찰 이전 (Second Chance Offer)
4. 연쇄 미결제는 **최대 2회**까지만 차순위 이전, 초과 시 재경매 제안
5. 차순위 낙찰자의 결제 기한도 동일하게 3일 부여

```python
MAX_SECOND_CHANCE_ROUNDS = 2  # 시스템 설정으로 노출 가능

def process_expired_orders():
    expired_orders = query(
        "SELECT * FROM orders "
        "WHERE status='pending_payment' AND payment_due_at < NOW()"
    )
    for order in expired_orders:
        with transaction() as tx:
            # 1. 현 주문 expired 처리
            tx.execute(
                "UPDATE orders SET status='expired' WHERE id=:id",
                id=order.id,
            )
            # 2. 낙찰자 경고 발급
            issue_warning(order.buyer_id, reason="auction_unpaid",
                          related_order_id=order.id)

            if order.source != "auction":
                continue

            auction = tx.execute(
                "SELECT * FROM auctions WHERE id=:id FOR UPDATE",
                id=order.auction_id,
            ).one()

            # 3. 차순위 이전 라운드 카운트 체크
            second_chance_count = count(
                "SELECT COUNT(*) FROM orders "
                "WHERE auction_id=:aid AND status='expired'",
                aid=order.auction_id,
            )
            if second_chance_count > MAX_SECOND_CHANCE_ROUNDS:
                # 한도 초과 → 재경매 제안
                tx.execute(
                    "UPDATE auctions SET status='ended', "
                    "current_winner=NULL WHERE id=:id",
                    id=auction.id,
                )
                notify_seller_for_relist(order.seller_id, auction.id)
                continue

            # 4. 차순위 입찰자 조회 (기존 expired 낙찰자 제외)
            expired_bidders = query(
                "SELECT buyer_id FROM orders "
                "WHERE auction_id=:aid AND status='expired'",
                aid=auction.id,
            )
            next_bid = query_one(
                "SELECT * FROM bids "
                "WHERE auction_id=:aid "
                "AND bidder_id NOT IN :excluded "
                "ORDER BY amount DESC LIMIT 1",
                aid=auction.id,
                excluded=[b.buyer_id for b in expired_bidders],
            )

            if not next_bid:
                # 차순위 없음 → 재경매 제안
                tx.execute(
                    "UPDATE auctions SET status='ended', "
                    "current_winner=NULL WHERE id=:id",
                    id=auction.id,
                )
                notify_seller_for_relist(order.seller_id, auction.id)
                continue

            # 5. 차순위에게 낙찰 이전 (신규 주문 생성)
            deadline_days = get_system_setting(
                "auction_payment_deadline_days"
            )["days"]
            new_order = create_order(
                buyer_id=next_bid.bidder_id,
                seller_id=order.seller_id,
                source="auction",
                auction_id=auction.id,
                amount=next_bid.amount,
                payment_due_at=now() + timedelta(days=deadline_days),
            )
            # 6. 경매 current_winner/price 갱신
            tx.execute(
                "UPDATE auctions SET current_winner=:w, "
                "current_price=:p WHERE id=:id",
                w=next_bid.bidder_id, p=next_bid.amount, id=auction.id,
            )

        send_notification(next_bid.bidder_id, "second_chance_offer",
                          order_id=new_order.id)
```

### 6.5 경고 누적 & 정지

```python
def issue_warning(user_id, reason, report_id=None):
    create_warning(user_id, reason, report_id)
    user = get_user(user_id)
    new_count = user.warning_count + 1
    update_user(user_id, warning_count=new_count)

    threshold = get_system_setting("warning_threshold")["count"]
    if new_count >= threshold:
        update_user(user_id, status="suspended")
        send_notification(user_id, "account_suspended")
```

### 6.6 정기 후원 해지

```python
def cancel_subscription(subscription_id, user_id):
    sub = get_subscription(subscription_id)
    if sub.sponsor_id != user_id:
        raise ApiError("FORBIDDEN")

    # Stripe에서 current period 말까지 유지
    stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    # 로컬 상태: status는 active 유지, cancel_at_period_end 플래그만 ON
    update_subscription(
        subscription_id,
        cancel_at_period_end=True,
        cancelled_at=now(),
    )
    # 현재 주기까지는 서비스 유지, 다음 결제 건너뜀
    # Stripe webhook(customer.subscription.deleted) 수신 시
    # status='cancelled'로 전이 (당월분 환불 없음)
```

### 6.7 피드 알고리즘 (프로토타입 단순 버전)

**`GET /posts/feed` — 홈 피드 (혼합)**

```python
def build_home_feed(user_id, cursor, limit=20, following_only=False):
    following_ids = get_following_ids(user_id)

    if following_only:
        # 팔로잉 전용 피드 (사이드바 "팔로잉" 메뉴에서 호출)
        return query_posts_by_authors(
            following_ids, cursor, limit=limit,
            status="published",
        )

    # 기본: 팔로우 70% + 트렌딩 30% 혼합 (사이드바 "홈" 메뉴)
    follow_limit = max(1, int(limit * 0.7))
    trending_limit = limit - follow_limit

    follow_posts = query_posts_by_authors(
        following_ids, cursor, limit=follow_limit,
        status="published",  # 판독 대기 제외
    )
    trending_posts = query_trending_posts(
        exclude_ids=[p.id for p in follow_posts],
        limit=trending_limit,
        status="published",
    )
    return interleave(follow_posts, trending_posts)
```

**비로그인 사용자의 홈 피드**: 프론트엔드는 `/posts/explore`를 호출하여
공개 포스트를 최신순으로 표시. (추후 `/posts/feed`를 auth 선택으로
전환하여 비로그인도 트렌딩 가중치를 받을 수 있도록 개선 예정.)

**트렌딩 스코어 공식 (프로토타입)**:
```
score = like_count * 0.4 + bluebird_count * 0.4 + recency_score * 0.2
recency_score = 1.0 - min(age_hours / 168, 1.0)  # 7일 기준
```

### 6.8 작가 승인 후 역할 전이 정책

```python
def approve_artist_application(application_id, admin_id):
    app = get_application(application_id)
    with transaction() as tx:
        tx.execute(
            "UPDATE artist_applications SET status='approved', "
            "reviewed_by=:a, reviewed_at=NOW() WHERE id=:id",
            a=admin_id, id=application_id,
        )
        tx.execute(
            "UPDATE users SET role='artist' WHERE id=:uid",
            uid=app.user_id,
        )
        # artist_profiles 생성
        tx.execute("""
            INSERT INTO artist_profiles(
                user_id, application_id, verified_by,
                school, intro_video_url, portfolio_urls, statement
            ) VALUES (:uid, :aid, :vb, :sc, :iv, :pu, :st)
        """, uid=app.user_id, aid=app.id, vb=admin_id,
            sc=app.school, iv=app.intro_video_url,
            pu=app.portfolio_urls, st=app.statement)

    # JWT 전이 정책: 기존 access token은 만료(최대 1시간)까지 유효.
    # 다음 /auth/refresh 호출 시 새 role이 반영된 토큰 발급.
    # 즉시 반영이 필요한 경우 refresh_tokens 테이블에서 기존 토큰 무효화.
    # 프로토타입에서는 "다음 로그인 또는 토큰 갱신 시 반영"으로 충분.
    send_notification(app.user_id, "artist_approved")
```

### 6.9 미성년자 정책 (프로토타입 범위)

프로토타입은 **정책 안내 UI + 데이터 수집**만 구현하고, 실제 제어는 2차 출시로 유보합니다.

```python
# 회원가입 온보딩 시 생년월일 수집
def complete_onboarding(user_id, birth_date, ...):
    age = calculate_age(birth_date)
    is_minor = age < get_minor_threshold_for_country(country_code)
    # 국가별 기준:
    #   KR: 14, US(COPPA): 13, EU(GDPR-K): 16 기본
    update_user(user_id, birth_date=birth_date, is_minor=is_minor)

    if is_minor:
        # 프로토타입: 안내 배너만 표시
        # 2차: 보호자 연동 플로우 (email invite 등)
        show_minor_consent_notice(user_id)

# 미성년 작가 승인 시 UI 경고
def approve_artist_application(..., app):
    user = get_user(app.user_id)
    if user.is_minor and not artist_profile.guardian_consent:
        # 프로토타입: 경고 로그만, 승인 차단 안 함
        log_warning("Minor artist approved without guardian consent")
```

**2차 출시 확장 예정 규칙** (프로토타입 제외):
- 미성년자 경매 입찰 금액 상한
- 보호자 명의 정산 계좌 필수
- 보호자 이메일 연동 및 동의 확인 플로우
- 결제 수단 제한

### 6.10 댓글 정책

프로토타입은 **1뎁스 댓글만** 지원합니다. `comments.parent_id`는 스키마에 존재하지만 항상 NULL로 저장하며, 2차 출시에서 대댓글 UI를 활성화할 때 사용합니다.

---

## 7. 보안 및 권한

### 7.1 역할 (Role)

| 역할 | 권한 |
|------|------|
| guest | 공개 콘텐츠 조회만 |
| user | 피드 조회, 좋아요, 댓글, 후원, 경매 입찰, 즉시 구매, 팔로우 |
| artist | user 권한 + 포스트 작성, 상품 등록, 경매 생성 |
| admin | 모든 권한 + 어드민 페이지 |

### 7.2 권한 체크 엔드포인트 매트릭스

**기본 규칙**:
- 모든 `/v1/**` 엔드포인트는 **인증 필수 (user 이상)** 이 기본값
- 예외: 아래 "공개 엔드포인트" 목록 (JWT 없이 접근 가능)
- `/v1/admin/**` 는 **admin 전용**
- 상품 포스트 작성 및 경매 생성은 **artist 이상**
- 계정이 `suspended` 또는 `warning_count >= 3`이면 모든 쓰기 작업 `ACCOUNT_SUSPENDED` 에러

#### 공개 엔드포인트 (guest 접근 가능)

| 엔드포인트 | 설명 |
|------------|------|
| POST /auth/sns/{provider} | 로그인 |
| POST /auth/refresh | 토큰 갱신 |
| GET /posts/explore | 탐색 (공개 포스트만) |
| GET /posts/search | 검색 |
| GET /posts/{id} | 공개 포스트 상세 |
| GET /users/{id} | 공개 프로필 |
| GET /auctions | 경매 목록 |
| GET /auctions/{id} | 경매 상세 |
| POST /webhooks/stripe | Stripe webhook (서명 검증) |

#### 역할별 쓰기 권한 요약

| 엔드포인트 | guest | user | artist | admin |
|------------|:-----:|:----:|:------:|:-----:|
| POST /posts (type=general) | ❌ | ✅ | ✅ | ✅ |
| POST /posts (type=product) | ❌ | ❌ | ✅ | ✅ |
| POST /media/upload | ❌ | ✅ | ✅ | ✅ |
| POST /sponsorships | ❌ | ✅ | ✅ | ✅ |
| POST /subscriptions | ❌ | ✅ | ✅ | ✅ |
| DELETE /subscriptions/{id} | ❌ | ✅(본인) | ✅(본인) | ✅ |
| POST /auctions | ❌ | ❌ | ✅ | ✅ |
| POST /auctions/{id}/bids | ❌ | ✅ | ✅ | ✅ |
| POST /products/{postId}/buy-now | ❌ | ✅ | ✅ | ✅ |
| POST /orders/{id}/pay | ❌ | ✅(본인) | ✅(본인) | ✅ |
| POST /reports | ❌ | ✅ | ✅ | ✅ |
| POST /warnings/{id}/appeal | ❌ | ✅(본인) | ✅(본인) | ✅ |
| GET /notifications | ❌ | ✅(본인) | ✅(본인) | ✅ |
| POST /artists/apply | ❌ | ✅ | ❌ | ❌ |
| GET /admin/** | ❌ | ❌ | ❌ | ✅ |
| PATCH /admin/settings/{key} | ❌ | ❌ | ❌ | ✅ |

### 7.3 JWT 구조

```json
{
  "sub": "user_uuid",
  "role": "artist",
  "status": "active",
  "iat": 1234567890,
  "exp": 1234567890
}
```

- Access Token: 1시간
- Refresh Token: 30일 (httpOnly 쿠키)

### 7.4 GDPR 대응

- `/users/me` DELETE → soft delete + 30일 후 hard delete
- `/users/me/export` → 개인 데이터 JSON 다운로드
- 쿠키 배너 (프론트)
- 개인정보 처리방침 페이지

---

## 8. 알림 시스템

### 8.1 알림 유형

| 타입 | 트리거 | 수신자 |
|------|--------|--------|
| sponsorship_received | 블루버드 후원 받음 | 작가 |
| bid_placed | 내 경매에 입찰 | 작가 |
| bid_outbid | 내 입찰이 밀림 | 이전 1위 |
| auction_won | 낙찰 성공 | 낙찰자 |
| auction_ending_soon | 경매 10분 남음 | 관심 경매 참여자 |
| artist_approved | 작가 승인 | 신청자 |
| artist_rejected | 작가 거절 | 신청자 |
| follow | 새 팔로워 | 팔로우 대상 |
| comment | 내 포스트에 댓글 | 작성자 |
| warning_issued | 경고 발급 | 해당 유저 |
| account_suspended | 계정 정지 | 해당 유저 |

### 8.2 전달 채널

- **인앱 알림**: DB `notifications` 테이블 + Redis 캐시
- **웹 푸시**: Firebase Cloud Messaging
- **이메일**: 중요 알림만 (경고, 계정 정지, 결제 영수증)

---

## 9. 구현 우선순위

### Phase 0 — 기반 (Week 1~2)
1. Docker Compose 세팅 (PostgreSQL, Redis, Backend, Frontend)
2. GitHub Actions 배포 파이프라인
3. Next.js + Tailwind + shadcn/ui 초기화
4. FastAPI 프로젝트 구조 및 ORM (SQLAlchemy) 세팅
5. users, notifications 테이블 마이그레이션
6. SNS 로그인 (Google 1개 먼저)
7. JWT 발급 및 `/auth/me`

### Phase 1 — 핵심 컨텐츠 (Week 3~6)
1. posts, media_assets, product_posts, comments, likes, follows 테이블
2. 포스트 CRUD API + 미디어 업로드
3. 홈 피드 / 탐색 / 검색 API
4. 작가 심사 신청/승인 (artist_applications + admin API)
5. 홈 피드, 프로필, 포스트 상세 화면
6. 관리자 작가 승인 페이지 (A1)

### Phase 2 — 거래 (Week 7~10)
1. sponsorships, subscriptions 테이블 및 API
2. Stripe Payment Intent / Subscription 연동
3. 블루버드 후원 모달 UI
4. auctions, bids, orders 테이블 및 API
5. 경매 상세 화면 (실시간 폴링 또는 WebSocket)
6. 미결제 처리 Scheduled Task
7. Stripe Webhook 처리

### Phase 3 — 보완 & 시연 (Week 11~12)
1. 영상 업로드 (F4), 외부 임베드 (YouTube/Vimeo)
2. 정기 후원 해지 UX + Stripe webhook 처리
3. reports, warnings 테이블 및 관리자 신고 처리 + 이의 제기 (A2)
4. 디지털 아트 판독 큐 UI
5. 매출 대시보드 (A3)
6. system_settings 관리 UI
7. 더미 시드 데이터 (작가 50명, 포스트 200개, 경매 10개)
8. 시연 시나리오 작성 (§12 참조)

---

## 10. 열린 이슈 → 결정 사항

| 항목 | 결정 | 근거 |
|------|------|------|
| 실시간 입찰 | **2초 폴링 채택** (WebSocket은 2차) | 프로토타입 시연 리스크 최소화 |
| 미디어 스토리지 | Phase 0~3은 서버 로컬, S3 호환(Minio) 전환은 2차 | 프로토타입 단순성 |
| Stripe Tax | MVP 미연동, 고정 수수료만 | 법적 검토 2차로 유보 |
| 다국어 i18n | **next-intl 채택** | Next.js App Router 공식 지원 |
| 추천 알고리즘 | 단순 가중치(팔로우 70% + 트렌딩 30%), ML은 2차 | §6.7 참조 |
| 작가 인덱스 점수 | 2차 출시로 유보, 프로토타입은 badge_level 필드만 제공 | MVP 범위 외 |
| SNS 로그인 | Phase 0는 Google만, Phase 1에 Kakao/Apple 추가 | Google 계정 확산도 |
| 통화 | 프로토타입 KRW 단일, USD는 2차 | Stripe 설정 단순화 |

---

## 11. Design Tokens (두쫀쿠 테마)

> 출처: `01-plan/design-direction.md`. 본 섹션은 Design 문서 내 단일 소스로 흡수한 요약이며, 구현 시 Tailwind config의 기준입니다.

### 11.1 Color Tokens

| Token | Hex | 용도 |
|-------|-----|------|
| `background` | `#1A1410` | 메인 배경 (다크 초콜릿) |
| `surface.DEFAULT` | `#2A2018` | 카드, 모달, 네비게이션 |
| `surface.hover` | `#352821` | 인터랙션 호버 |
| `border` | `#3D2F24` | 구분선 |
| `primary.DEFAULT` | `#A8D76E` | 피스타치오 그린 (버튼, 뱃지, 블루버드) |
| `primary.hover` | `#BDE284` | 버튼 호버 |
| `primary.muted` | `#5E7A3E` | 비활성 |
| `text.primary` | `#F5EFE4` | 본문 (크림) |
| `text.secondary` | `#B5A99A` | 보조 |
| `text.muted` | `#7A6F60` | placeholder |
| `danger` | `#E85D5D` | 경고/제재 |
| `warning` | `#F0B14A` | 주의 |
| `success` | `#A8D76E` | 성공 (primary 통일) |

> WCAG AA 대비비 4.5:1 검증은 구현 시 자동화 도구(axe, Lighthouse)로 확인.

### 11.2 Typography

- **폰트**: Pretendard (한글) + Inter (영문/숫자, tabular-nums)
- **타입 스케일**: 12 / 14 / 16 / 20 / 24 / 32 / 48 px (px/line-height 쌍은 design-direction.md §3.2 참조)

### 11.3 Spacing & Radius

- spacing: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px`
- radius: `sm=4 / md=8 / lg=12 / xl=16 / full=9999`

### 11.4 컴포넌트 스타일 규칙

- Primary 버튼: `bg-primary text-background rounded-full px-5 py-2.5`
- Secondary 버튼: `bg-surface border border-primary text-text-primary`
- 카드: `bg-surface border border-border rounded-xl hover:bg-surface-hover`
- 뱃지: `bg-primary text-background text-xs px-2 py-0.5 rounded-full`

### 11.5 모션

- 기본 전환: `200~300ms ease-out`
- 경매 카운트다운 마지막 10초: `animate-pulse`
- 블루버드 후원 성공: 피스타치오 파티클 이펙트 (선택적)

### 11.6 다크 모드

- 프로토타입은 **다크 모드 단일**. 라이트 모드 미지원.
- Tailwind 기본 `dark:` 프리픽스 없이 루트 테마에 적용.

---

## 12. 시연 시나리오 (고객 커뮤니케이션용)

프로토타입 시연 시 사용할 5개 핵심 시나리오입니다. 더미 시드 데이터는 이 시나리오를 기준으로 준비합니다.

### 시나리오 1: 신진 작가 가입 및 승인
**배역**: Maria (페루 리마 미대생, 24세)
**흐름**:
1. Google 로그인 → 온보딩 (국가 페루, 관심 장르 회화)
2. 작가 심사 신청 (포트폴리오 4장, 학교명, 소개 영상 URL, 자기소개)
3. [관리자 전환] 승인 페이지에서 Maria 신청 검토 → 승인
4. Maria 계정 재접속 → `role=artist`로 전환 확인
5. 작가 프로필 화면에 뱃지 표시

### 시나리오 2: 작품 업로드 및 피드 노출
**배역**: Maria (작가)
**흐름**:
1. 포스트 작성 → 상품 포스트 선택
2. 이미지 3장 업로드 ("Sunrise in Lima" 유화 50x70cm)
3. 가격/경매 설정: 즉시 구매 ₩500,000 + 경매 시작가 ₩300,000, 7일간
4. 저장 → `pending_review` 상태
5. [관리자] 디지털 아트 판독 큐에서 승인 → `published`
6. 피드에 노출 확인

### 시나리오 3: 블루버드 후원
**배역**: Alex (일본 도쿄 컬렉터, user 역할)
**흐름**:
1. 홈 피드에서 Maria의 작품 발견 → 좋아요, 댓글
2. Maria 프로필 진입 → 팔로우
3. 블루버드 후원 버튼 클릭 → 모달 오픈
4. 12 블루버드 선택 (₩12,000), 메시지 "Love your work!", 공개 범위 전체
5. Stripe 결제 완료
6. Maria 프로필의 "받은 후원"에 노출
7. Maria에게 실시간 알림 전송 (sponsorship_received)

### 시나리오 4: 경매 입찰 및 낙찰 후 결제
**배역**: Chen (대만 컬렉터), Sato (일본 컬렉터) — 두 명 동시 시연
**흐름**:
1. Maria의 경매 상세 진입 (카운트다운 표시)
2. Chen 입찰 ₩310,000 → 1위
3. Sato 입찰 ₩320,000 → 1위, Chen에게 outbid 알림
4. Chen 재입찰 ₩340,000 → 1위
5. 경매 종료 (시연용으로 관리자가 `end_at`을 앞당김)
6. Chen 낙찰, 주문 생성, 결제 기한 3일
7. Chen 결제 완료 → Maria에게 매출 알림

### 시나리오 5: 신고 → 경고 → 이의 제기
**배역**: 불량 유저 Bob (부적절 댓글 작성)
**흐름**:
1. Alex가 Bob의 댓글을 신고 (reason: "abusive")
2. [관리자] 신고 처리 페이지에서 검토 → 경고 발급
3. Bob 알림 수신, 프로필에 경고 스티커 표시
4. Bob이 이의 제기 글 등록 ("오해입니다")
5. [관리자] 이의 제기 탭에서 검토 → 경고 취소
6. Bob 계정 정상화, `warning_count` -1

### 시연 환경 준비 체크리스트

- [ ] 시드 유저: 일반 유저 10명, 작가 50명 (국가별 분산), 관리자 2명
- [ ] 시드 포스트: 일반 포스트 100개, 상품 포스트 100개 (모두 published 상태)
- [ ] 활성 경매: 10개 (다양한 남은 시간)
- [ ] 블루버드 후원 이력: 각 작가당 평균 5~20건
- [ ] 신고 케이스: 3~5건 (pending 상태)
- [ ] Stripe 테스트 카드 준비 (`4242 4242 4242 4242`)
- [ ] 관리자 계정 접속 URL 및 비밀번호 문서화

---

## 부록: 용어 사전

| 용어 | 정의 |
|------|------|
| 블루버드 | 플랫폼의 후원 단위. 1 블루버드 = 기본 1,000원 |
| 작가(Artist) | 심사 승인을 받은 유저. 상품 포스트 업로드 가능 |
| 일반 포스트 | SNS 성격의 게시물 (판매/경매 없음) |
| 상품 포스트 | 판매/경매 가능한 작품 게시물 |
| 경고(Warning) | 신고 처리 결과 발급되는 제재 단위. 3회 누적 시 계정 정지 |
| 관리자(Admin) | 작가 승인, 신고 처리, 시스템 설정 권한을 가진 내부 운영자 |
