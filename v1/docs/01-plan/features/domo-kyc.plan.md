# Plan — Domo KYC (본인인증 시스템)

**Feature**: domo-kyc
**Created**: 2026-04-18
**Phase**: Plan
**Status**: Draft

---

## 1. Problem Statement

Domo Lounge는 실물 작품 거래 + 블루버드 후원이 발생하는 **금융거래 플랫폼**이다. 현재 Google OAuth만으로 가입 가능하며 **실명 확인 없이** 거래가 이루어져 다음 리스크가 존재:

- 허위 계정으로 가짜 매매/허위 입찰
- 미성년 작가/컬렉터의 무단 금융거래
- 정산 시 실명 불일치 (세금 처리 불가)
- 분쟁 발생 시 상대방 특정 불가

고객 요구: **작가와 컬렉터 모두** 금융거래 발생 전 본인인증 필수.

---

## 2. Goals & Non-Goals

### Goals

1. **어댑터 패턴**: Mock → Toss → PASS → Stripe Identity 전환 가능
2. **작가**: 심사 신청 시 본인인증 필수 게이트
3. **컬렉터**: 첫 구매/후원 시 본인인증 필수 게이트
4. **인증 상태**: `identity_verified_at` 필드로 전역 관리
5. **관리자**: KYC 인증 현황 조회 + 수동 승인/거부

### Non-Goals

- 기업 법인 인증 (개인만)
- AML(자금세탁방지) 모니터링 (Phase 2)
- 신분증 사본 저장 (외부 서비스가 관리)

---

## 3. KYC Provider 비교

| Provider | 방식 | 비용 | 글로벌 | 한국 | 추천 |
|---|---|---|---|---|---|
| **Mock** | 개발용 즉시 인증 | 무료 | - | - | 개발 |
| **Toss 신분증** | 신분증 촬영 + OCR | ₩100~300/건 | ❌ | ✅ | 한국 1차 |
| **PASS 인증** | 통신사 본인확인 | ₩50~100/건 | ❌ | ✅ | 한국 대안 |
| **Stripe Identity** | 신분증 + Selfie | $1.50/건 | ✅ | ✅ | 글로벌 |
| **Sumsub** | 종합 KYC/AML | $0.5~2/건 | ✅ | ✅ | Enterprise |

### 추천 전략

1. **개발/프로토타입**: MockProvider (즉시 인증)
2. **한국 런칭**: TossProvider 또는 PASSProvider
3. **글로벌 확장**: StripeIdentityProvider

환경변수 `KYC_PROVIDER=mock|toss|pass|stripe`로 전환.

---

## 4. 사용자 플로우

### 4.1 작가 심사 신청 시

```
작가 심사 폼 Step 1
    ↓
본인인증 미완료 시 → "본인인증이 필요합니다" 게이트
    ↓
[본인인증 시작] 버튼 → KYC 외부 페이지 리다이렉트 (또는 모달)
    ↓
인증 완료 → 콜백 → identity_verified_at 저장
    ↓
심사 폼 계속 진행
```

### 4.2 컬렉터 첫 구매/후원 시

```
[구매하기] / [후원하기] 클릭
    ↓
identity_verified_at IS NULL → "본인인증이 필요합니다" 모달
    ↓
인증 완료 → 구매/후원 진행
    ↓
이후 거래는 재인증 없이 진행
```

### 4.3 Mock 플로우 (개발용)

```
[본인인증 시작] → 이름/생년월일 입력 폼 → [인증 완료]
    ↓
즉시 identity_verified_at = NOW() 저장
```

---

## 5. Data Model

### 5.1 users 테이블 확장

```sql
ALTER TABLE users ADD COLUMN identity_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN identity_provider VARCHAR(20);  -- 'mock' | 'toss' | 'pass' | 'stripe'
ALTER TABLE users ADD COLUMN identity_session_id VARCHAR(100);
```

### 5.2 인증 세션 테이블 (신규)

```sql
CREATE TABLE kyc_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    external_session_id VARCHAR(200),
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending' | 'processing' | 'verified' | 'failed' | 'expired'
    result_data JSONB,  -- 인증 결과 (이름, 생년월일 등)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

---

## 6. API 설계

```
POST /kyc/start
  → { redirect_url, session_id }
  (외부 인증 페이지로 리다이렉트할 URL 반환)

GET /kyc/status
  → { verified, provider, verified_at }
  (현재 인증 상태 조회)

POST /kyc/callback
  → webhook (외부 서비스에서 인증 완료 시 호출)
  (identity_verified_at 저장)

POST /kyc/mock-verify  (개발용)
  body: { name, birth_date }
  → 즉시 인증 완료
```

---

## 7. 어댑터 패턴

```python
class KYCProvider(ABC):
    async def start_verification(self, user_id, redirect_url) -> KYCSession
    async def check_status(self, session_id) -> KYCResult
    async def handle_webhook(self, payload) -> KYCResult

class MockKYCProvider(KYCProvider): ...
class TossKYCProvider(KYCProvider): ...
class StripeIdentityProvider(KYCProvider): ...
```

기존 Payment/Storage/Email/Translation과 동일한 어댑터 패턴. `config.py`에 `kyc_provider` 설정.

---

## 8. 프론트엔드 컴포넌트

```
components/
  KYCGate.tsx          # 인증 필요 시 보여주는 모달/배너
  KYCVerifyModal.tsx   # Mock: 이름/생년 입력 폼
                       # Real: 외부 리다이렉트 안내
```

### KYCGate 사용 위치

```tsx
// 구매 버튼
<KYCGate onVerified={() => handlePurchase()}>
  <button>구매하기</button>
</KYCGate>

// 후원 버튼
<KYCGate onVerified={() => openSponsorModal()}>
  <button>후원하기</button>
</KYCGate>

// 작가 심사 (Step 1 진입 전)
if (!me.identity_verified_at) {
  return <KYCVerifyModal onComplete={reload} />;
}
```

---

## 9. 구현 순서

| Step | 작업 | 의존성 |
|---|---|---|
| 1 | Alembic 마이그레이션 (users + kyc_sessions) | 없음 |
| 2 | KYCProvider 어댑터 + MockProvider | 없음 |
| 3 | KYC API 엔드포인트 (start/status/callback/mock-verify) | Step 1, 2 |
| 4 | 프론트: KYCGate + KYCVerifyModal | Step 3 |
| 5 | 작가 심사 폼에 KYC 게이트 적용 | Step 4 |
| 6 | 구매/후원 버튼에 KYC 게이트 적용 | Step 4 |
| 7 | 관리자: KYC 인증 현황 조회 | Step 3 |

---

## 10. Dependencies & Risks

### Dependencies

| 항목 | 종류 | 상태 |
|---|---|---|
| MockProvider | 내부 | 즉시 구현 가능 |
| TossProvider | 외부 | Toss 계약 + API 키 필요 |
| StripeIdentityProvider | 외부 | Stripe 계정 (이미 존재) + Identity 활성화 |

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| 외부 서비스 계약 지연 | 높음 | MockProvider로 전체 플로우 개발 → 도입 시 어댑터 교체 |
| 인증 실패율 | 중 | 재시도 허용 + 관리자 수동 승인 fallback |
| 개인정보 저장 범위 | 중 | 인증 결과는 외부 서비스가 보관, 서버는 verified_at만 저장 |

---

## 11. Success Metrics

- [ ] MockProvider로 전체 KYC 플로우 동작
- [ ] 작가 심사 → KYC 게이트 → 인증 → 신청 진행
- [ ] 구매/후원 → KYC 게이트 → 인증 → 거래 진행
- [ ] 이미 인증된 유저는 게이트 없이 바로 진행
- [ ] 관리자 페이지에서 인증 현황 조회
- [ ] TossProvider 어댑터 코드 준비 (API 키만 넣으면 동작)

---

## 12. Next Step

✅ `/pdca design domo-kyc`로 상세 설계 → MockProvider부터 구현
