# Design — Domo KYC (본인인증)

**Feature**: domo-kyc
**Created**: 2026-04-18
**Plan Reference**: [domo-kyc.plan.md](../../01-plan/features/domo-kyc.plan.md)

---

## 1. Data Model

### users 확장
```sql
ALTER TABLE users ADD COLUMN identity_verified_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN identity_provider VARCHAR(20);
```

### kyc_sessions (신규)
```sql
CREATE TABLE kyc_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    external_session_id VARCHAR(200),
    status VARCHAR(20) DEFAULT 'pending',
    result_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

## 2. API
- POST /kyc/start → 세션 생성
- GET /kyc/status → 인증 상태
- POST /kyc/mock-verify → Mock 즉시 인증
- POST /kyc/callback → 외부 webhook

## 3. 프론트
- KYCGate: 인증 필요 시 모달 트리거
- KYCVerifyModal: Mock 입력 폼 / Real 리다이렉트 안내

## 4. 적용 위치
- 작가 심사 Step 1 진입 전
- 구매/후원 버튼 클릭 시
- 관리자: 인증 현황 조회

## 5. 구현 순서
1. 마이그레이션 (0021)
2. KYCProvider 어댑터 + MockProvider
3. KYC API (4개)
4. KYCGate + KYCVerifyModal
5. 작가 심사/구매/후원 게이트 적용
