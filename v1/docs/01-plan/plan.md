# Domo 프로토타입 Plan (v1)

> **목적**: 고객과 커뮤니케이션하기 위한 프로토타입
> **작성일**: 2026-04-11
> **기준 문서**: `docs/v1_answer.md`, `docs/v2_answer.md`
> **방법론**: PDCA (Plan → Do → Check → Act)

---

## 1. 프로젝트 개요

### 1.1 프로젝트명
**Domo** — 글로벌 신진 미술 작가를 위한 SNS · 후원 · 경매 플랫폼

### 1.2 목표
고객과의 커뮤니케이션을 위한 **동작 가능한 프로토타입** 개발. 완성도보다 **주요 플로우 시연**이 우선.

### 1.3 범위 원칙
- **빠른 반복 > 완벽**: 프로토타입 → 피드백 → 수정 사이클
- **시연 가능한 핵심 플로우 우선**: 회원가입 → 작품 업로드 → 후원 → 경매
- **프로덕션 수준의 견고성은 나중에**: 보안, 성능 튜닝, 엣지 케이스 최소화
- **가짜 데이터 활용**: 초기 시드 데이터는 더미로 채움

---

## 2. MVP 범위 (확정)

### 2.1 핵심 기능 (7개)

| 순번 | 기능 | 우선순위 | 설명 |
|------|------|----------|------|
| F1 | 작가 가입/심사 시스템 | P0 | 일반 유저 자유 가입 + 작가 승인 심사 |
| F2 | 일반 피드 (SNS 포스트) | P0 | 인스타그램 스타일 피드 + 장르/추천/검색 |
| F3 | 작품 업로드 (사진) | P0 | 일반 포스트 / 상품 포스트 2종 분리 |
| F4 | 작품 업로드 (영상/타임랩스) | P1 | 50MB 일반 / 외부 임베드 지원 |
| F5 | 블루버드 일회성 후원 | P0 | 1블루버드 = 1,000원, 익명 옵션 |
| F6 | 블루버드 정기 후원 | P1 | 월 구독, 즉시 해지 + 다음 달부터 환불 |
| F7 | 경매 시스템 | P0 | 영국식 오름경매 + 즉시 구매 병행 |

### 2.2 관리자 어드민 (Top 3)

| 순번 | 기능 | 우선순위 |
|------|------|----------|
| A1 | 작가 승인 페이지 | P0 |
| A2 | 콘텐츠 신고 처리 | P0 |
| A3 | 매출 대시보드 | P1 |

### 2.3 지원 기능 (기반 인프라)

- SNS 로그인 (Google, Apple, Kakao 중 선택)
- Stripe 결제 연동
- 다국어 지원 (한국어, 영어 — 2개만)
- 이미지 업로드 & CDN 서빙
- 알림 시스템 (웹 푸시 via Firebase)

### 2.4 프로토타입 제외 항목

- 작가 인덱스/랭킹 (2차)
- 개인화 추천 알고리즘 (2차, 초기는 인기순)
- 커뮤니티/그룹 (2차)
- 1:1 DM (2차)
- 자동 번역/통역 (2차)
- 지역별 큐레이션 (2차)
- 모바일 앱 (웹 반응형 완료 후)
- 자동 번역 (수동 번역 지원만)

---

## 3. 기술 스택

### 3.1 확정 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| Frontend | Next.js 15 (App Router) + TypeScript | React 19 |
| Styling | Tailwind CSS + shadcn/ui | 빠른 UI 구축 |
| Backend | FastAPI (Python 3.12+) | |
| DB | PostgreSQL 16 | 메인 데이터 저장소 |
| Cache | Redis 7 | 세션, 추천 캐시, 경매 실시간 |
| Auth | SNS OAuth (Google/Kakao) + JWT | |
| Push | Firebase Cloud Messaging | 웹 푸시 |
| Payment | Stripe | 후원, 경매 결제 |
| Storage | 서버 로컬 (MVP) → S3 호환 (추후) | 프로토타입은 로컬 |
| Infra | Docker Compose on `100.75.139.86` | |
| CI/CD | GitHub Actions → 서버 자동 배포 | |
| Domain | `*.tuzigroup.com` | 서브도메인 분리 |

### 3.2 서브도메인 전략

| 서브도메인 | 용도 |
|------------|------|
| `domo.tuzigroup.com` | 메인 웹 (프론트) |
| `api.domo.tuzigroup.com` | 백엔드 API |
| `admin.domo.tuzigroup.com` | 관리자 페이지 |
| `cdn.domo.tuzigroup.com` | 이미지/영상 CDN (추후) |

---

## 4. 아키텍처 개요

```
[사용자] → [Next.js Frontend]
              ↓ (REST API)
          [FastAPI Backend]
         ↓      ↓         ↓
   [PostgreSQL] [Redis] [Stripe API]
         ↓
   [Firebase FCM] → [사용자 웹 푸시]
```

### 4.1 주요 모듈

| 모듈 | 책임 |
|------|------|
| `auth` | SNS 로그인, JWT 발급, 역할 관리 (Artist/Collector/Admin) |
| `users` | 프로필, 작가 심사, 팔로우 |
| `posts` | 일반 포스트 / 상품 포스트 (사진/영상) |
| `sponsorships` | 블루버드 후원 (일회성/정기) |
| `auctions` | 경매 생성, 입찰, 낙찰, 미결제 처리 |
| `payments` | Stripe 연동, 정산 |
| `notifications` | 알림 생성, FCM 전송 |
| `admin` | 작가 승인, 신고 처리, 대시보드 |

---

## 5. 데이터 모델 (핵심 엔티티 요약)

> 상세 스키마는 `02-design/schema.md`에서 구체화

| 엔티티 | 주요 필드 |
|--------|-----------|
| User | id, email, role, status, sns_provider, profile |
| ArtistApplication | user_id, portfolio, school, status, reviewed_by |
| Post | id, author_id, type(general/product), media, content |
| ProductPost | post_id, price, is_auction, is_buy_now |
| Sponsorship | id, sponsor_id, artist_id, amount, type, is_anonymous |
| Subscription | id, sponsor_id, artist_id, monthly_amount, status |
| Auction | id, product_post_id, start_price, end_time, current_bid |
| Bid | id, auction_id, bidder_id, amount, created_at |
| Order | id, buyer_id, product_id, status, payment_intent_id |
| Report | id, reporter_id, target_type, target_id, reason, status |
| Warning | id, user_id, reason, issued_by, active |

---

## 6. 개발 단계 (3개월 로드맵)

### Phase 0: 기반 구축 (Week 1~2)
- 프로젝트 초기화 (Next.js + FastAPI + PostgreSQL Docker Compose)
- GitHub → 서버 자동 배포 파이프라인
- SNS 로그인 연동
- 기본 DB 스키마 생성
- 관리자 계정 시드

### Phase 1: 핵심 플로우 (Week 3~6)
- 작가 가입/심사 (F1) + 관리자 승인 (A1)
- 일반 피드 (F2) + 사진 업로드 (F3)
- 프로필 페이지
- 팔로우 시스템

### Phase 2: 거래 기능 (Week 7~10)
- 블루버드 일회성 후원 (F5) + Stripe 연동
- 경매 시스템 (F7) + 입찰 로직
- 즉시 구매
- 주문/결제 플로우

### Phase 3: 보완 & 시연 준비 (Week 11~12)
- 영상 업로드 (F4)
- 정기 후원 (F6)
- 관리자 신고 처리 (A2) + 매출 대시보드 (A3)
- 더미 시드 데이터 대량 주입
- 프로토타입 시연 시나리오 작성

---

## 7. 인력 및 예산

### 7.1 개발 인력 (예상)
| 역할 | 인원 | 기간 |
|------|------|------|
| PM / 기획 | 1 | 3개월 |
| 프론트엔드 (Next.js) | 1~2 | 3개월 |
| 백엔드 (FastAPI) | 1 | 3개월 |
| 디자인 | 0.5 | 1~2개월 |
| 총합 | 3.5~4.5 FTE | |

### 7.2 예산 (고객 답변 기준 1~3억)
- 개발 인건비, 인프라, 외부 서비스(Stripe, Firebase) 수수료 포함
- **월 운영비**: 100~500만원 범위

### 7.3 운영 인력 (고객측)
- 작가 심사 1명
- 콘텐츠 모더레이션 1명
- 고객 지원(CS) 1명
- 결제/정산 1명

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 3개월 일정 타이트 | 높음 | Phase 단위로 우선순위 조정, 비핵심 기능 제외 |
| Stripe 글로벌 결제 복잡도 | 중간 | MVP는 단일 통화(USD/KRW) 고정, 다통화는 2차 |
| 타겟 시장 불일치 | 중간 | 프로토타입 시연 시 고객과 재논의 |
| 디지털 아트 관리자 수동 판독 부담 | 낮음 | 관리자 검토 큐 UI 제공 |
| 경매 실시간성 | 중간 | Redis + WebSocket(Socket.IO) 또는 폴링 |
| 법적 컴플라이언스(GDPR, 세금) | 중간 | 프로토타입은 정책 페이지만, 실제 연동은 2차 |

---

## 9. 다음 단계

1. 본 Plan 문서 리뷰 및 확정
2. `/pdca design domo` — 데이터 모델, API 스펙, 화면 설계
3. Phase 0 착수 — 프로젝트 초기화

---

## 10. 부록: 확정된 정책 요약

### 후원 (블루버드)
- 1 블루버드 = 1,000원 (시스템 설정 변경 가능)
- 익명 후원 가능
- 리워드: 뱃지, 작가 메시지
- 공개 범위: 전체/작가만/비공개
- 정기 후원 해지: 즉시 해지, 당월까지 유지, 다음 달부터 환불

### 경매
- 영국식 오름경매 + 즉시 구매 병행
- 작가가 기간/최소입찰가 설정
- 낙찰 후 미결제: 3일 결제 기한 → 차순위 이전 → 재경매 → 경고 누적
- 배송 분쟁: 플랫폼 미개입

### 제재
- 3진 아웃 경고 시스템
- 이의 제기 가능 (관리자 판단)

### 컴플라이언스
- GDPR 정책 적용
- 미성년자: 국제 법규 준수 (GDPR-K, COPPA, 한국 14세)
- 세금: Stripe Tax 등 자동화 도구 연동 권장
- 디지털 아트: 시스템 관리자 수동 판독
