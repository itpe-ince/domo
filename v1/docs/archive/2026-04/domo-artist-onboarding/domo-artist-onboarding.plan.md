# Plan — Domo Artist Onboarding (작가 가입/인증 체계)

**Feature**: domo-artist-onboarding
**Created**: 2026-04-14
**Phase**: Plan
**Status**: Confirmed

---

## 1. Problem Statement

현재 작가 심사 절차는 **텍스트 입력 기반의 단순 신청서**만 존재한다. 고객이 요구하는 "대학생/신진작가 플랫폼"으로서의 **신뢰성 있는 인증 체계**가 부재하다.

현재: 학교명 텍스트 입력 → 포트폴리오 URL → 관리자 수동 승인
요구: 본인인증 → 학교 이메일(.edu) 인증 → 재학/졸업 증빙 → 포트폴리오 검토 → 승인 → 졸업 시 자동 전환

---

## 2. Implementation Phases

### Phase 1 — 프로필 필드 확장 (자체 구현, 즉시 가능)

**범위**: ArtistApplication + ArtistProfile 모델 확장 + 신청 폼 업데이트

**신규/변경 필드**:

| 필드 | 테이블 | 타입 | 필수 | 설명 |
|---|---|---|---|---|
| `department` | artist_applications, artist_profiles | VARCHAR(100) | ✅ | 학과 (예: 서양화과) |
| `graduation_year` | artist_applications, artist_profiles | INT | ✅ | 졸업(예정) 연도 |
| `is_enrolled` | artist_applications, artist_profiles | BOOLEAN | ✅ | 현재 재학 중 여부 |
| `genre_tags` | artist_applications, artist_profiles | TEXT[] | ✅ | 작업 장르 태그 3~5개 |
| `enrollment_proof_url` | artist_applications | TEXT | ✅ | 재학/졸업 증빙 파일 URL |
| `representative_works` | artist_applications | JSONB | ✅ | 대표 작품 3~6개 구조화 |
| `exhibitions` | artist_applications, artist_profiles | JSONB | 선택 | 전시 이력 |
| `awards` | artist_applications, artist_profiles | JSONB | 선택 | 수상 이력 |

**`representative_works` 구조**:
```json
[
  {
    "title": "Sunrise in Lima",
    "description": "리마의 아침 햇살을 담은 유화",
    "image_url": "https://...",
    "dimensions": "50x70cm",
    "medium": "Oil on canvas",
    "year": 2026
  }
]
```

**`exhibitions` / `awards` 구조**:
```json
[
  {
    "title": "서울시립미술관 신진작가전",
    "year": 2025,
    "description": "단체전 참여"
  }
]
```

**변경 사항**:
- `statement` 200자 제한 추가 (백엔드 Pydantic max_length + 프론트 maxLength)
- `sample_images` 폐기 → `representative_works` JSONB로 대체
- 등급 명칭 변경: `emerging` → `student`, `featured` → `emerging`, `popular` → `recommended`, `master` → `popular`
- 신청 폼 UI 전면 리팩터 (단계별 위저드 형태)

**외부 의존성**: 없음
**작업량**: M (모델 + 마이그레이션 + 폼 + API)

---

### Phase 2 — 학교 이메일 인증 (이메일 인프라 필요)

**범위**: `.edu` 등 학교 도메인 이메일로 인증 코드 발송 + 확인

**플로우**:
```
작가 신청 폼 → 학교 이메일 입력 (예: kim@snu.ac.kr)
    ↓
도메인 화이트리스트 체크 (.edu, .ac.kr, .ac.jp 등)
    ↓
6자리 인증 코드 이메일 발송 (기존 EmailProvider 활용)
    ↓
코드 입력 + 검증 (5분 만료)
    ↓
edu_email + edu_email_verified_at 저장
```

**신규 필드**:

| 필드 | 테이블 | 타입 | 설명 |
|---|---|---|---|
| `edu_email` | artist_applications | VARCHAR(255) | 학교 이메일 |
| `edu_email_verified_at` | artist_applications | TIMESTAMPTZ | 인증 완료 시각 |
| `edu_verification_code` | (Redis) | STRING | 6자리 코드 (5분 TTL) |

**학교 도메인 화이트리스트**:
- 1차: `.edu`, `.ac.kr`, `.ac.jp`, `.edu.tw`, `.edu.hk`, `.edu.sg`, `.edu.vn`, `.edu.ph`, `.edu.my`
- system_settings에 동적 관리 (관리자가 추가 가능)

**졸업 후 자동 전환 규칙**:
- `edu_email_verified_at`이 있는 사용자는 "학교 인증 작가"로 표시
- `graduation_year <= 현재 연도`이고 `is_enrolled = false` → 자동으로 `badge_level = 'emerging'` (신진작가)
- 크론잡: 매년 3월 1일 배치 실행 또는 로그인 시 lazy 체크

**외부 의존성**: 이메일 발송 (기존 mock/Resend/SES 어댑터 이미 존재)
**작업량**: M

---

### Phase 3 — 본인인증 KYC (외부 서비스 연동)

**범위**: 실명 인증 (작가 + 컬렉터 금융거래 시 필수)

**후보 서비스**:

| 서비스 | 방식 | 비용 | 글로벌 | 추천 |
|---|---|---|---|---|
| **Toss 신분증 인증** | 신분증 촬영 + OCR | 건당 100~300원 | 한국만 | 한국 1차 |
| **PASS 인증** | 통신사 본인확인 | 건당 50~100원 | 한국만 | 한국 대안 |
| **Stripe Identity** | 신분증 + selfie | $1.50/건 | 글로벌 | 글로벌 확장 |
| **Sumsub** | 종합 KYC | $0.5~2/건 | 글로벌 | Enterprise |

**어댑터 패턴** (기존 Payment/Storage/Email과 동일):
```python
class IdentityProvider(ABC):
    async def start_verification(self, user_id, redirect_url) -> VerificationSession
    async def check_status(self, session_id) -> VerificationResult

class MockIdentityProvider(IdentityProvider): ...
class TossIdentityProvider(IdentityProvider): ...
class StripeIdentityProvider(IdentityProvider): ...
```

**신규 필드**:

| 필드 | 테이블 | 타입 | 설명 |
|---|---|---|---|
| `identity_verified_at` | users | TIMESTAMPTZ | 본인인증 완료 시각 |
| `identity_provider` | users | VARCHAR(20) | 인증 제공사 (toss/pass/stripe) |
| `identity_session_id` | users | VARCHAR(100) | 외부 세션 ID |

**적용 범위**:
- 작가: 심사 신청 시 필수
- 컬렉터: 첫 구매/후원 시 필수 (금융거래 발생 전 게이트)
- `is_verified` computed property: `identity_verified_at IS NOT NULL`

**외부 의존성**: KYC 서비스 계약 + API 키
**작업량**: L

---

### Phase 4 — 자동 전환 + 배지 자동 산정 (크론잡)

**범위**: 졸업 후 학생→신진작가 전환 + 활동 기반 배지 자동 승급

**등급 체계 (고객 확정)**:

| 등급 | 코드 | 조건 | 노출 |
|---|---|---|---|
| 학생 | `student` | 학교 이메일 인증 + `is_enrolled=true` | "🎓 학생 작가" |
| 신진작가 | `emerging` | 졸업 또는 학교 미인증 작가 | "✨ 신진 작가" |
| 추천작가 | `recommended` | 후원 50건+ 또는 총 후원금 $500+ | "🕊 추천 작가" |
| 인기작가 | `popular` | 팔로워 100+ 또는 총 거래 $1000+ | "🔥 인기 작가" |

**자동 전환 크론잡**:
```python
async def update_artist_badges():
    # 1. 학생 → 신진작가 (졸업)
    #    graduation_year <= current_year AND is_enrolled = false
    
    # 2. 신진작가 → 추천작가 (후원 기준 달성)
    #    total_sponsorships >= 50 OR total_sponsorship_amount >= 500
    
    # 3. 추천작가 → 인기작가 (팔로워/거래 기준 달성)
    #    follower_count >= 100 OR total_sales >= 1000
```

**실행 주기**: 매일 03:00 UTC (일일 배치)

**외부 의존성**: 없음 (기존 데이터 기반)
**작업량**: S

---

## 3. Phase별 우선순위 & 의존성

```
Phase 1 (프로필 확장)      ← 즉시 구현 가능
    ↓
Phase 2 (학교 이메일)      ← 이메일 인프라 (이미 존재)
    ↓ (병렬 가능)
Phase 3 (본인인증 KYC)     ← 외부 서비스 계약 필요
    ↓
Phase 4 (자동 전환/배지)   ← Phase 1 데이터 필요
```

Phase 4는 Phase 1만 완료되면 구현 가능 (Phase 2, 3과 독립).

---

## 4. 작가 신청 폼 UI (Phase 1 와이어프레임)

### 단계별 위저드 형태

```
┌──────────────────────────────────────┐
│ 작가 심사 신청                        │
│ Step 1/4 — 기본 정보                  │
├──────────────────────────────────────┤
│                                      │
│ 소속 학교 *          [           ]    │
│ 학과 *               [           ]    │
│ 졸업연도 *           [2026  ▼]       │
│ ☑ 현재 재학 중                       │
│                                      │
│ 장르/스타일 태그 *                    │
│ [painting] [oil] [+ 추가]           │
│                                      │
│                        [다음 →]      │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Step 2/4 — 대표 작품 (3~6개)         │
├──────────────────────────────────────┤
│                                      │
│ 작품 1                               │
│ ┌──────┐ 작품명 *  [           ]    │
│ │ 사진 │ 설명     [           ]    │
│ │ 업로드│ 크기     [50x70cm   ]    │
│ └──────┘ 매체     [Oil on...  ]    │
│          연도     [2026       ]    │
│                                      │
│ [+ 작품 추가]                        │
│                                      │
│                  [← 이전] [다음 →]   │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Step 3/4 — 포트폴리오 & 영상         │
├──────────────────────────────────────┤
│                                      │
│ 자기소개 * (200자 이내)              │
│ [                              ]    │
│ [                         142/200]   │
│                                      │
│ 재학/졸업 증빙 * [파일 선택]         │
│ ✓ 재학증명서.pdf 업로드 완료          │
│                                      │
│ 포트폴리오 URL (줄바꿈 구분)         │
│ [                              ]    │
│                                      │
│ 소개 영상 URL (선택)                 │
│ [                              ]    │
│                                      │
│                  [← 이전] [다음 →]   │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│ Step 4/4 — 이력 (선택)               │
├──────────────────────────────────────┤
│                                      │
│ 전시 이력                            │
│ [+ 전시 추가]                        │
│                                      │
│ 수상 이력                            │
│ [+ 수상 추가]                        │
│                                      │
│              [← 이전] [심사 신청 →]  │
└──────────────────────────────────────┘
```

---

## 5. Success Metrics

### Phase 1
- [ ] 신청 폼 4단계 위저드 동작
- [ ] 대표 작품 3~6개 구조화 입력 (이미지+제목+설명+크기+매체)
- [ ] 재학/졸업 증빙 파일 업로드
- [ ] 장르 태그 3~5개 선택
- [ ] 자기소개 200자 제한
- [ ] 관리자 승인 화면에서 확장된 필드 표시

### Phase 2
- [ ] `.edu` 등 학교 이메일 인증 코드 발송 + 확인
- [ ] 인증 완료 시 프로필에 "🎓 학교 인증" 배지 표시

### Phase 3
- [ ] 본인인증 MockProvider로 개발/테스트
- [ ] 작가 신청 시 본인인증 필수 게이트
- [ ] 컬렉터 첫 구매/후원 시 본인인증 요구

### Phase 4
- [ ] 졸업 연도 도달 시 학생→신진작가 자동 전환
- [ ] 후원/팔로워 기준 달성 시 배지 자동 승급
- [ ] 관리자 대시보드에서 등급 분포 확인

---

## 6. Risks & Dependencies

| Phase | Risk | Mitigation |
|---|---|---|
| 1 | 대표 작품 이미지 업로드 용량 | 기존 미디어 업로드 인프라 재사용 (10MB/이미지) |
| 2 | 학교 이메일 도메인 DB 불완전 | 관리자 추가 가능한 화이트리스트 + 수동 승인 fallback |
| 3 | KYC 서비스 계약 지연 | MockProvider로 개발 진행, 도입 시 어댑터 교체 |
| 4 | 자동 전환 오류 (잘못된 졸업연도) | 수동 override 유지 + 관리자 알림 |

---

## 7. Timeline

| Phase | 작업량 | 예상 | 의존성 |
|---|---|---|---|
| Phase 1 | M | 1~2일 | 없음 (즉시 시작) |
| Phase 2 | M | 1일 | 이메일 인프라 (이미 있음) |
| Phase 3 | L | 2~3일 | KYC 서비스 계약 |
| Phase 4 | S | 0.5일 | Phase 1 완료 |

---

## 8. Next Step

✅ Phase 1부터 즉시 시작 → `/pdca design domo-artist-onboarding`
Phase 2~4는 Phase 1 완료 후 순차 또는 병렬 진행.
