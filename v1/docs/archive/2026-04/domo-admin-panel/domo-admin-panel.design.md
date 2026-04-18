# Design — Domo Admin Panel P1 (관리자 패널 확장)

**Feature**: domo-admin-panel
**Created**: 2026-04-14
**Phase**: Design
**Plan Reference**: [domo-admin-panel.plan.md](../../01-plan/features/domo-admin-panel.plan.md)
**Scope**: P1 항목 — 유저 관리, 학교 관리, 콘텐츠 관리, 거래 관리, 사이드바 확장

---

## 1. Data Model

### 1.1 School 테이블 (이미 생성됨)

`backend/app/models/school.py` — id, name_ko, name_en, country_code, email_domain, school_type, logo_url, status, created_at

### 1.2 신규 모델 없음

기존 모델(User, Post, Auction, Order, Sponsorship)의 조회/수정 API만 추가. 별도 테이블 불필요.

### 1.3 Alembic 마이그레이션

```
0013_schools_and_artist_fields.py
  - schools 테이블 생성
  - 초기 시드: 한국 주요 미대 10교 + 글로벌 5교
```

---

## 2. API 설계

### 2.1 유저 관리

```
GET /admin/users
  ?q=<검색어>           # display_name, email
  &role=user|artist|admin
  &status=active|suspended|deleted
  &country=KR|JP|US
  &limit=20&offset=0

GET /admin/users/{id}
  → 프로필 + 활동 요약 (포스트 수, 거래 수, 후원 수, 경고 수)

PATCH /admin/users/{id}
  body: { status?, role?, badge_level? }
  → 변경 사유 기록 + 알림 발송
```

**응답 예시** (`GET /admin/users`):
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "kim@snu.ac.kr",
      "display_name": "kim_artist",
      "role": "artist",
      "status": "active",
      "badge_level": "student",
      "country_code": "KR",
      "warning_count": 0,
      "post_count": 12,
      "created_at": "2026-01-15T..."
    }
  ],
  "pagination": { "total": 150, "offset": 0, "limit": 20 }
}
```

### 2.2 학교 관리

```
GET /admin/schools
  ?q=<학교명>
  &country=KR|JP|US
  &status=active|pending|disabled
  &limit=20&offset=0

POST /admin/schools
  body: {
    name_ko: string,
    name_en: string,
    country_code: string,
    email_domain: string,
    school_type: "university" | "art_school" | "academy" | "other",
    logo_url?: string
  }

PATCH /admin/schools/{id}
  body: { name_ko?, name_en?, email_domain?, status?, logo_url? }

GET /admin/schools/{id}/artists
  → 해당 학교 소속 작가 목록
```

### 2.3 콘텐츠 관리

```
GET /admin/posts
  ?q=<제목/내용>
  &author_id=<uuid>
  &type=general|product
  &status=published|pending_review|hidden|scheduled|deleted
  &genre=painting|drawing|...
  &sort=latest|popular
  &limit=20&offset=0

PATCH /admin/posts/{id}
  body: { status: "hidden" | "published" | "deleted" }
  → 사유 기록 + 작가에게 알림
```

### 2.4 거래 관리

```
GET /admin/auctions
  ?status=scheduled|active|ended|settled|cancelled
  &limit=20&offset=0

GET /admin/orders
  ?status=pending_payment|paid|cancelled|expired|refunded
  &source=auction|buy_now
  &limit=20&offset=0

GET /admin/settlements
  → 정산 대기 목록 (paid 상태 주문 중 작가 미정산)

POST /admin/orders/{id}/refund
  body: { reason: string }
  → 환불 처리 + 양쪽 알림
```

---

## 3. 프론트엔드 구조

### 3.1 신규 페이지

```
app/admin/
  users/page.tsx          # 유저 관리
  schools/page.tsx        # 학교 관리
  posts/page.tsx          # 콘텐츠 관리
  transactions/page.tsx   # 거래 관리 (경매 + 주문 + 정산 탭)
```

### 3.2 사이드바 Admin 메뉴 확장

```typescript
const admin: NavItem[] = [
  { href: "/admin/dashboard", label: "대시보드", Icon: DashboardIcon },
  { href: "/admin/users", label: "유저 관리", Icon: UsersIcon },
  { href: "/admin/schools", label: "학교 관리", Icon: FlagIcon },
  { href: "/admin/applications", label: "작가 심사", Icon: CheckCircleIcon },
  { href: "/admin/posts", label: "콘텐츠 관리", Icon: ImageIcon },
  { href: "/admin/transactions", label: "거래 관리", Icon: ReceiptIcon },
  { href: "/admin/moderation", label: "모더레이션", Icon: ShieldAlertIcon },
  { href: "/admin/settings", label: "시스템 설정", Icon: SettingsIcon },
];
```

### 3.3 공통 관리 테이블 컴포넌트

모든 관리 페이지가 동일한 테이블 패턴을 사용:

```typescript
// components/admin/AdminTable.tsx
interface AdminTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading: boolean;
  pagination: { total: number; offset: number; limit: number };
  onPageChange: (offset: number) => void;
}
```

```
┌──────────────────────────────────────────────────┐
│ [검색: _________]  [필터 ▼]  [상태 ▼]  [+ 추가] │
├──────────────────────────────────────────────────┤
│ 이름        이메일          역할   상태   가입일   │
│ ────────────────────────────────────────────────  │
│ @kim_art   kim@snu.ac.kr  작가   활성   01/15   │
│ @maria     maria@ex.com   유저   활성   01/20   │
│ @alex      alex@ex.com    유저   정지   02/01   │
│ ...                                              │
├──────────────────────────────────────────────────┤
│ ← 이전  1 2 3 ... 8  다음 →    총 150명          │
└──────────────────────────────────────────────────┘
```

### 3.4 페이지별 와이어프레임

#### 유저 관리 (`/admin/users`)
```
┌──────────────────────────────────────────┐
│ 유저 관리                                │
│ [검색] [역할 ▼] [상태 ▼] [국가 ▼]       │
├──────────────────────────────────────────┤
│ 이름     이메일     역할  등급  상태 조치 │
│ @kim..  kim@..    작가  🎓   활성 [⋯]  │
│                                ├─ 상세  │
│                                ├─ 정지  │
│                                └─ 등급변경│
└──────────────────────────────────────────┘
```

#### 학교 관리 (`/admin/schools`)
```
┌──────────────────────────────────────────┐
│ 학교 관리                     [+ 학교 추가]│
│ [검색] [국가 ▼] [상태 ▼]                │
├──────────────────────────────────────────┤
│ 학교명           도메인         국가 상태 │
│ 서울대학교       snu.ac.kr     KR   ✅  │
│ 홍익대학교       hongik.ac.kr  KR   ✅  │
│ Tokyo Univ Arts  geidai.ac.jp  JP   ✅  │
│ (신청) XYZ       xyz.edu       US   ⏳  │
└──────────────────────────────────────────┘
```

#### 콘텐츠 관리 (`/admin/posts`)
```
┌──────────────────────────────────────────┐
│ 콘텐츠 관리                              │
│ [검색] [종류 ▼] [상태 ▼] [장르 ▼]       │
├──────────────────────────────────────────┤
│ 썸네일 제목         작가    상태   조치    │
│ [🖼] Sunrise..    @maria  공개   [⋯]   │
│                                ├─ 상세  │
│                                ├─ 숨김  │
│                                └─ 삭제  │
└──────────────────────────────────────────┘
```

#### 거래 관리 (`/admin/transactions`)
```
┌──────────────────────────────────────────┐
│ 거래 관리                                │
│ [경매]  [주문]  [정산]  ← 3탭            │
├──────────────────────────────────────────┤
│ 경매 탭:                                 │
│ 작품명    판매자  현재가  상태  마감일     │
│ Sunrise  @maria  $200   진행   04/20    │
│                                          │
│ 주문 탭:                                 │
│ 주문번호  구매자  판매자  금액  상태       │
│ #001     @alex  @maria  $200  결제완료   │
│                                          │
│ 정산 탭:                                 │
│ 작가     미정산 건  미정산 금액  [정산]    │
│ @maria   3건       $540        [실행]    │
└──────────────────────────────────────────┘
```

---

## 4. 학교 초기 시드 데이터

```python
INITIAL_SCHOOLS = [
    # 한국 미대
    {"name_ko": "서울대학교", "name_en": "Seoul National University", "country_code": "KR", "email_domain": "snu.ac.kr", "school_type": "university"},
    {"name_ko": "홍익대학교", "name_en": "Hongik University", "country_code": "KR", "email_domain": "hongik.ac.kr", "school_type": "university"},
    {"name_ko": "국민대학교", "name_en": "Kookmin University", "country_code": "KR", "email_domain": "kookmin.ac.kr", "school_type": "university"},
    {"name_ko": "이화여자대학교", "name_en": "Ewha Womans University", "country_code": "KR", "email_domain": "ewha.ac.kr", "school_type": "university"},
    {"name_ko": "중앙대학교", "name_en": "Chung-Ang University", "country_code": "KR", "email_domain": "cau.ac.kr", "school_type": "university"},
    {"name_ko": "한국예술종합학교", "name_en": "Korea National University of Arts", "country_code": "KR", "email_domain": "karts.ac.kr", "school_type": "art_school"},
    {"name_ko": "계원예술대학교", "name_en": "Kaywon University of Art & Design", "country_code": "KR", "email_domain": "kaywon.ac.kr", "school_type": "art_school"},
    # 일본
    {"name_ko": "도쿄예술대학", "name_en": "Tokyo University of the Arts", "country_code": "JP", "email_domain": "geidai.ac.jp", "school_type": "art_school"},
    {"name_ko": "무사시노미술대학", "name_en": "Musashino Art University", "country_code": "JP", "email_domain": "musabi.ac.jp", "school_type": "art_school"},
    # 글로벌
    {"name_ko": "로열 칼리지 오브 아트", "name_en": "Royal College of Art", "country_code": "GB", "email_domain": "rca.ac.uk", "school_type": "art_school"},
    {"name_ko": "파슨스 디자인 스쿨", "name_en": "Parsons School of Design", "country_code": "US", "email_domain": "newschool.edu", "school_type": "art_school"},
    {"name_ko": "로드아일랜드 디자인 스쿨", "name_en": "Rhode Island School of Design", "country_code": "US", "email_domain": "risd.edu", "school_type": "art_school"},
]
```

---

## 5. 구현 순서

| Step | 작업 | 파일 | 의존성 |
|---|---|---|---|
| 1 | Alembic 마이그레이션 (schools 테이블 + 시드) | `alembic/versions/0013_*` | 없음 |
| 2 | AdminTable 공통 컴포넌트 | `components/admin/AdminTable.tsx` | 없음 |
| 3 | 학교 관리 API (CRUD) | `api/admin.py` 확장 | Step 1 |
| 4 | 학교 관리 페이지 | `app/admin/schools/page.tsx` | Step 2, 3 |
| 5 | 유저 관리 API | `api/admin.py` 확장 | 없음 |
| 6 | 유저 관리 페이지 | `app/admin/users/page.tsx` | Step 2, 5 |
| 7 | 콘텐츠 관리 API | `api/admin.py` 확장 | 없음 |
| 8 | 콘텐츠 관리 페이지 | `app/admin/posts/page.tsx` | Step 2, 7 |
| 9 | 거래 관리 API (경매/주문/정산) | `api/admin.py` 확장 | 없음 |
| 10 | 거래 관리 페이지 (3탭) | `app/admin/transactions/page.tsx` | Step 2, 9 |
| 11 | 사이드바 Admin 메뉴 확장 | `components/Sidebar.tsx` | Step 4~10 |

**병렬화**: Step 3~10 (각 페이지)은 Step 2 (AdminTable) 완료 후 병렬 가능

---

## 6. 다음 단계

✅ `/pdca do domo-admin-panel`로 구현 착수
