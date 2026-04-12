# Domo Phase 4 Design — Production Hardening 상세 설계

> **작성일**: 2026-04-11
> **선행**: [phase4.plan.md](../01-plan/phase4.plan.md), [design.md](./design.md) (v1 핵심 설계)
> **단계**: PDCA Design Phase
> **범위**: M1 실 Stripe / M2 JWT 회전 / M3 GDPR / M4 S3 스토리지 / M5 미성년자 / M6 Rate limiting

---

## 목차

1. [개요](#1-개요)
2. [M2 JWT Refresh Token 회전](#2-m2-jwt-refresh-token-회전)
3. [M6 Rate Limiting](#3-m6-rate-limiting)
4. [M1 실 Stripe 연동](#4-m1-실-stripe-연동)
5. [M4 S3 미디어 스토리지](#5-m4-s3-미디어-스토리지)
6. [M3 GDPR / 개인정보 보호](#6-m3-gdpr--개인정보-보호)
7. [M5 미성년자 보호자 동의](#7-m5-미성년자-보호자-동의)
8. [공통: 이메일 발송 서비스](#8-공통-이메일-발송-서비스)
9. [데이터 모델 변경 요약](#9-데이터-모델-변경-요약)
10. [환경변수 추가](#10-환경변수-추가)
11. [구현 우선순위](#11-구현-우선순위)
12. [Definition of Done](#12-definition-of-done)

---

## 1. 개요

### 1.1 설계 원칙

- **인터페이스 유지**: Phase 0~3 mock 어댑터(Stripe, Storage)의 인터페이스를 그대로 활용. 구현 클래스만 교체.
- **하위 호환**: 마이그레이션 0006~0009는 기존 데이터 보존 (soft delete, dual-write 등).
- **점진적 cutover**: 새 시스템과 기존 mock을 환경변수로 분기. 1주 dual-run 후 mock 제거.
- **보안 우선**: M2/M6를 Week 15에 먼저 배치한 이유는 다른 작업의 전제 조건이기 때문.

### 1.2 영향 범위

| 컴포넌트 | 변경 |
|----------|------|
| 마이그레이션 | 0006 (refresh_tokens) → 0007 (gdpr) → 0008 (s3 url) → 0009 (guardian) |
| 백엔드 라우터 | `auth`, `me`, `guardian`, `admin` (refund), `payments webhook 강화` |
| 백엔드 서비스 | `auth_tokens`, `rate_limit`, `payments/stripe_real`, `storage/s3`, `guardian`, `email` |
| 프론트엔드 | 쿠키 배너, /legal, /me/account, 미성년 가입 플로우, refresh 자동 회전 |
| 인프라 | Stripe 라이브 키, AWS S3 + CloudFront, SES/Resend, Sentry |

---

## 2. M2 JWT Refresh Token 회전

### 2.1 문제

현재 `/auth/refresh`는 stateless JWT를 그대로 발급하므로:
- 탈취 시 무효화 불가
- 작가 승인 후 새 role을 즉시 반영하려면 클라이언트가 refresh 호출까지 대기
- 로그아웃 후에도 토큰이 만료까지 유효

### 2.2 데이터 모델

```sql
-- 0006_auth_refresh_tokens
CREATE TABLE refresh_tokens (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash   VARCHAR(128) NOT NULL UNIQUE,  -- SHA-256 of raw token
  family_id    UUID NOT NULL,                 -- 같은 로그인 세션 묶음
  parent_id    UUID REFERENCES refresh_tokens(id),  -- 회전 체인 추적
  issued_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at   TIMESTAMPTZ NOT NULL,
  revoked_at   TIMESTAMPTZ,
  revoked_reason VARCHAR(50),                 -- 'logout' | 'rotation' | 'family_compromised' | 'admin_action'
  user_agent   TEXT,
  ip_address   INET
);
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id, expires_at);
CREATE INDEX idx_refresh_family ON refresh_tokens(family_id);
```

### 2.3 토큰 회전 알고리즘

```
POST /auth/refresh { refresh_token }
  ↓
1. token_hash = sha256(raw)
2. SELECT * FROM refresh_tokens WHERE token_hash = ? FOR UPDATE
3. row 없음 → UNAUTHORIZED
4. revoked_at IS NOT NULL && reason = 'rotation' →
     → REUSE DETECTED → family_id 전체 revoke + 보안 알림
     → UNAUTHORIZED
5. expires_at < now → UNAUTHORIZED
6. revoke 현재 토큰 (reason='rotation')
7. 새 raw 토큰 생성 + INSERT (parent_id = 현재, family_id 유지)
8. 새 access_token 발급 (DB에서 user.role/status 다시 조회)
9. response { access_token, refresh_token: new_raw }
```

### 2.4 작가 승인 시 즉시 반영

```python
# api/admin.py approve_application
async def approve_application(...):
    ...  # 기존 로직
    user.role = "artist"

    # 기존 access_token은 1시간 내 만료
    # 강제 즉시 반영이 필요하면 refresh tokens revoke
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now(), revoked_reason="admin_role_change")
    )
    # → 다음 refresh 호출 시 401 → 클라이언트 재로그인 → 새 role 반영
```

### 2.5 API 변경

| 엔드포인트 | 변경 |
|------------|------|
| `POST /auth/sns/google` | 응답에 family_id 없음(클라 비공개), refresh_token DB 저장 |
| `POST /auth/refresh` | 회전 알고리즘 적용 |
| `POST /auth/logout` | 현 family 모든 refresh revoke (reason='logout') |
| `GET /auth/sessions` (신규) | 본인 활성 세션 목록 (다중 디바이스 관리) |
| `DELETE /auth/sessions/{id}` (신규) | 특정 세션 강제 로그아웃 |

### 2.6 클라이언트 변경

`frontend/src/lib/api.ts`:
- `apiFetch`에서 401 응답 시 자동으로 `/auth/refresh` 호출 → 새 토큰 저장 → 원 요청 재시도
- 무한 루프 방지를 위해 1회만 재시도

---

## 3. M6 Rate Limiting

### 3.1 라이브러리 선택

**Redis 기반 자체 구현** (slowapi 대신). 이유:
- 이미 Redis가 stack에 있음
- 엔드포인트 + IP + user_id 3중 카운팅 필요
- 동적 한도 변경 (system_settings) 가능

### 3.2 데이터 구조

Redis 키 패턴:
```
rl:{scope}:{key}:{window}
  scope = endpoint name (e.g. 'sponsorship_create')
  key   = user_id 또는 ip
  window = unix_minute (Redis SETEX TTL = 60s)
```

INCR + EXPIRE 패턴으로 race-free 카운팅.

### 3.3 한도 정책

| 엔드포인트 | 한도 (분당) | 식별자 |
|------------|:----------:|:------:|
| POST /auth/sns/* | 10 | IP |
| POST /auth/refresh | 30 | user_id |
| POST /sponsorships | 30 | user_id |
| POST /subscriptions | 10 | user_id |
| POST /auctions/{id}/bids | 60 | user_id |
| POST /products/{id}/buy-now | 10 | user_id |
| POST /reports | 5 | user_id |
| POST /media/upload | 20 | user_id |
| GET /posts/feed | 120 | user_id |
| GET /posts/explore | 60 | IP |
| 일반 GET | 120 | user_id |

이 값들은 `system_settings.rate_limits`에 JSONB로 저장하여 런타임 변경 가능.

### 3.4 미들웨어 설계

```python
# app/core/rate_limit.py
class RateLimiter:
    async def check(
        self,
        scope: str,
        key: str,
        limit: int,
        window_sec: int = 60,
    ) -> tuple[bool, int]:
        """Returns (allowed, remaining)."""
        bucket_key = f"rl:{scope}:{key}:{int(time.time()) // window_sec}"
        async with redis.pipeline() as pipe:
            await pipe.incr(bucket_key)
            await pipe.expire(bucket_key, window_sec)
            count, _ = await pipe.execute()
        return count <= limit, max(0, limit - count)


# Usage decorator
def rate_limit(scope: str, limit: int, by: str = "user"):
    async def dependency(
        request: Request,
        user: User | None = Depends(get_optional_user),
    ):
        key = (
            str(user.id)
            if by == "user" and user
            else request.client.host
        )
        allowed, remaining = await limiter.check(scope, key, limit)
        if not allowed:
            raise ApiError(
                "RATE_LIMITED",
                f"Rate limit exceeded ({limit}/min)",
                http_status=429,
            )
        # Set X-RateLimit-Remaining header in response
        request.state.rate_limit_remaining = remaining
    return Depends(dependency)
```

### 3.5 응답 헤더

모든 응답에 다음 헤더 추가:
- `X-RateLimit-Limit: 30`
- `X-RateLimit-Remaining: 25`
- `X-RateLimit-Reset: 1705392060` (다음 윈도우 시작 unix 초)

### 3.6 모니터링 모드

Phase 4 첫 1주는 `RATE_LIMIT_MODE=monitor`로 시작 — 차단 대신 로그만 기록. 정상 트래픽 패턴 확인 후 `enforce`로 전환.

---

## 4. M1 실 Stripe 연동

### 4.1 설계 원칙

Phase 2에서 만든 `PaymentProvider` 인터페이스 그대로 활용. 새 클래스만 추가.

```python
# services/payments/stripe_real.py
class StripeProvider(PaymentProvider):
    name = "stripe"

    def __init__(self):
        stripe.api_key = settings.stripe_secret_key
        self.webhook_secret = settings.stripe_webhook_secret

    async def create_payment_intent(...) -> PaymentIntent:
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=int(amount),  # KRW 정수
            currency=currency.lower(),
            metadata=metadata,
            automatic_payment_methods={"enabled": True},
        )
        return PaymentIntent(
            id=intent.id,
            client_secret=intent.client_secret,
            amount=Decimal(intent.amount),
            currency=intent.currency.upper(),
            status=intent.status,
            metadata=intent.metadata or {},
        )

    async def verify_webhook_signature(payload, signature):
        event = await asyncio.to_thread(
            stripe.Webhook.construct_event,
            payload,
            signature,
            self.webhook_secret,
        )
        return event.to_dict()
```

### 4.2 Factory 변경

```python
# services/payments/factory.py
@lru_cache
def get_payment_provider() -> PaymentProvider:
    settings = get_settings()
    if settings.payment_provider == "stripe":
        from app.services.payments.stripe_real import StripeProvider
        return StripeProvider()
    return MockStripeProvider()
```

환경변수 한 줄 변경으로 전환 — 코드 변경 없이 dual-run 가능.

### 4.3 Webhook 이벤트 처리

| Stripe 이벤트 | 처리 |
|---------------|------|
| `payment_intent.succeeded` | sponsorship.status='completed' or order.status='paid' |
| `payment_intent.payment_failed` | sponsorship.status='failed', 알림 발송 |
| `customer.subscription.deleted` | subscription.status='cancelled' |
| `customer.subscription.updated` | cancel_at_period_end 동기화 |
| `invoice.payment_failed` | subscription.status='past_due' |
| `charge.refunded` | order.status='refunded', 작가 정산 차감 |

```python
# api/webhooks.py 강화
@router.post("/payments")
async def payments_webhook(request: Request, ...):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    provider = get_payment_provider()

    try:
        event = await provider.verify_webhook_signature(payload, signature)
    except ValueError:
        raise ApiError("INVALID_REQUEST", "Invalid signature", http_status=400)

    # 멱등성: event.id를 webhook_events 테이블에 INSERT (UNIQUE 제약)
    try:
        db.add(WebhookEvent(id=event["id"], type=event["type"], payload=event))
        await db.commit()
    except IntegrityError:
        return {"data": {"received": True, "duplicate": True}}

    # Dispatch
    handler = WEBHOOK_HANDLERS.get(event["type"])
    if handler:
        await handler(db, event["data"]["object"])
    return {"data": {"received": True}}
```

신규 테이블:
```sql
CREATE TABLE webhook_events (
  id           VARCHAR(100) PRIMARY KEY,  -- Stripe event id
  type         VARCHAR(100) NOT NULL,
  payload      JSONB NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4.4 환불 API

```python
# api/admin.py
@router.post("/orders/{order_id}/refund")
async def refund_order(
    order_id: UUID,
    body: RefundRequest,  # { reason: str, amount?: Decimal }
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    order = ...
    if order.status != "paid":
        raise ApiError("CONFLICT", "Only paid orders can be refunded", http_status=409)

    refund = await asyncio.to_thread(
        stripe.Refund.create,
        payment_intent=order.payment_intent_id,
        amount=int(body.amount or order.amount),
        reason=body.reason,
    )

    order.status = "refunded"
    # 작가에게 알림
    db.add(Notification(...))
    await db.commit()
    return {"data": _serialize_order(order)}
```

### 4.5 Stripe 라이브 모드 전환 체크리스트

- [ ] 사업자 등록증 제출
- [ ] 통신판매업 신고증
- [ ] 대표자 신원 확인
- [ ] 정산 계좌 등록
- [ ] 약관/개인정보 처리방침 URL 등록 (M3 의존)
- [ ] Webhook URL 등록 + 시그니처 키 발급
- [ ] 테스트 모드에서 dual-run 1주 → 라이브 cutover

---

## 5. M4 S3 미디어 스토리지

### 5.1 인터페이스

```python
# services/storage/base.py
class StorageProvider(ABC):
    @abstractmethod
    async def create_presigned_upload(
        self,
        key: str,
        content_type: str,
        max_bytes: int,
        expires_sec: int = 600,
    ) -> dict: ...
    # Returns: { url, fields, public_url }

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    def public_url(self, key: str) -> str: ...
```

### 5.2 S3 구현

```python
# services/storage/s3.py
class S3Storage(StorageProvider):
    def __init__(self):
        self.bucket = settings.s3_bucket
        self.cdn_base = settings.cdn_base_url
        self.client = aioboto3.Session().client("s3")

    async def create_presigned_upload(self, key, content_type, max_bytes, expires_sec):
        async with self.client as s3:
            post = await s3.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Conditions=[
                    ["content-length-range", 0, max_bytes],
                    {"Content-Type": content_type},
                ],
                ExpiresIn=expires_sec,
            )
        return {
            "url": post["url"],
            "fields": post["fields"],
            "public_url": self.public_url(key),
        }

    def public_url(self, key: str) -> str:
        return f"{self.cdn_base}/{key}"
```

### 5.3 업로드 플로우 변경

기존 (Phase 0~3):
```
Client → POST /v1/media/upload (multipart) → Backend → 로컬 디스크 → URL 반환
```

신규 (Phase 4):
```
1. Client → POST /v1/media/presign { filename, content_type, size } → Backend
2. Backend → S3 Presigned POST 발급 → { url, fields, public_url } 반환
3. Client → POST 직접 S3 (multipart with fields) → 200
4. Client → POST /v1/posts { media: [{ url: public_url, ... }] }
```

장점:
- 백엔드 대역폭 절약
- 큰 파일(making_video 1GB) 처리 부담 감소
- CDN 자동 캐싱

### 5.4 키 생성 + 보안

```python
def generate_key(user_id: UUID, kind: str, ext: str) -> str:
    # uploads/2026/04/{user_id}/{uuid}.jpg
    today = datetime.utcnow()
    return f"uploads/{today:%Y/%m}/{user_id}/{uuid.uuid4().hex}{ext}"
```

- Path traversal 자체가 사라짐 (S3 키는 자유 텍스트)
- 키에 user_id 포함으로 audit trail
- S3 버킷 정책: PUBLIC READ + AUTHENTICATED WRITE만

### 5.5 이미지 처리 파이프라인

S3에 업로드 완료 시 Lambda 트리거 (또는 백엔드 백그라운드 task):
1. EXIF 제거 (Pillow)
2. 썸네일 생성: 400x500, 800x1000, 1600x2000
3. 원본은 `uploads/.../original.jpg`, 썸네일은 `uploads/.../thumb_400.jpg`
4. `media_assets.thumbnail_url = CDN URL`

### 5.6 마이그레이션 0008

기존 로컬 파일은 그대로 두되, 새 업로드만 S3로. 1주 dual-run 후 기존 파일 마이그레이션 스크립트 실행.

```sql
-- 0008_media_storage_url
ALTER TABLE media_assets ADD COLUMN storage_provider VARCHAR(20) DEFAULT 'local';
ALTER TABLE media_assets ADD COLUMN storage_key TEXT;
```

### 5.7 환경변수

```
STORAGE_PROVIDER=s3   # 또는 'local'
S3_BUCKET=domo-prod-media
S3_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
CDN_BASE_URL=https://cdn.domo.tuzigroup.com
```

---

## 6. M3 GDPR / 개인정보 보호

### 6.1 데이터 모델 변경

```sql
-- 0007_gdpr
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN deletion_scheduled_for TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN gdpr_export_count INT DEFAULT 0;
ALTER TABLE users ADD COLUMN privacy_policy_version VARCHAR(20);
ALTER TABLE users ADD COLUMN terms_version VARCHAR(20);
```

### 6.2 Soft Delete 정책

```
사용자 → POST /me/delete
  ↓
1. users.deleted_at = NOW()
2. users.deletion_scheduled_for = NOW() + 30일
3. users.email = "deleted_<id>@deleted.local" (이메일 unique 회피)
4. users.display_name = "Deleted User"
5. 모든 세션 revoke
6. 30일 후 cron이 hard delete (FK CASCADE 또는 익명화)

복구 가능 기간 (30일):
- 사용자가 다시 로그인 → deleted_at IS NOT NULL → "복구하시겠습니까?" 안내
```

### 6.3 데이터 Export

```python
# api/me.py
@router.get("/me/export")
async def export_my_data(user: User = Depends(get_current_user), db = ...):
    data = {
        "user": user_to_dict(user),
        "artist_application": ...,
        "artist_profile": ...,
        "posts": [...],
        "comments": [...],
        "follows": {"following": [...], "followers": [...]},
        "sponsorships_made": [...],
        "subscriptions": [...],
        "orders_made": [...],
        "warnings": [...],
        "notifications": [...],
        "exported_at": now().isoformat(),
    }
    user.gdpr_export_count += 1
    await db.commit()
    return JSONResponse(content=data, headers={
        "Content-Disposition": f'attachment; filename="domo_export_{user.id}.json"'
    })
```

Rate limit: 사용자당 24시간 1회.

### 6.4 쿠키 배너

```typescript
// components/CookieConsent.tsx
const CONSENT_KEY = "domo_cookie_consent_v1";

export function CookieConsent() {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!localStorage.getItem(CONSENT_KEY)) setShown(true);
  }, []);

  function accept(level: "essential" | "all") {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({
      level,
      accepted_at: new Date().toISOString(),
      version: "v1",
    }));
    setShown(false);
  }

  if (!shown) return null;
  return (
    <div className="fixed bottom-0 inset-x-0 bg-surface border-t border-border p-4 z-50">
      ...
      <button onClick={() => accept("essential")}>필수만 허용</button>
      <button onClick={() => accept("all")}>모두 허용</button>
      <Link href="/legal/privacy">자세히</Link>
    </div>
  );
}
```

### 6.5 Legal 페이지

```
/legal/privacy   — 개인정보 처리방침 (한/영)
/legal/terms     — 이용약관 (한/영)
/legal/cookies   — 쿠키 정책
```

각 페이지 하단에 버전과 시행일자 명시. 사용자 가입 시 `privacy_policy_version` 기록.

### 6.6 API

| 엔드포인트 | 설명 |
|------------|------|
| `GET /me/export` | 자기 데이터 JSON 다운로드 |
| `POST /me/delete` | 30일 grace period soft delete |
| `POST /me/delete/cancel` | 30일 내 복구 |
| `GET /legal/versions` | 현재 정책 버전 조회 |

### 6.7 30일 후 Hard Delete Cron

```python
# services/gdpr_jobs.py
async def hard_delete_pending_users(db):
    expired = await db.execute(
        select(User).where(
            User.deletion_scheduled_for.is_not(None),
            User.deletion_scheduled_for < now(),
        )
    )
    for user in expired.scalars():
        # 익명화 (FK 보존을 위해 delete 대신 익명화)
        user.email = f"anon_{user.id}@deleted.local"
        user.display_name = "Anonymous"
        user.bio = None
        user.avatar_url = None
        user.birth_date = None
        # 작품/댓글은 보존하되 author 표시는 "Anonymous"
    await db.commit()
```

---

## 7. M5 미성년자 보호자 동의

### 7.1 데이터 모델 변경

```sql
-- 0009_minor_guardian
ALTER TABLE users ADD COLUMN birth_year INT;  -- birth_date 대신 연도만 (KISA 권장)
-- birth_date는 GDPR 위험으로 birth_year로 대체

CREATE TABLE guardian_consents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  minor_user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  guardian_email  VARCHAR(255) NOT NULL,
  guardian_name   VARCHAR(100),
  consent_token   VARCHAR(128) UNIQUE NOT NULL,  -- magic link token
  consented_at    TIMESTAMPTZ,
  withdrawn_at    TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ NOT NULL,  -- magic link 만료 (24h)
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_guardian_minor ON guardian_consents(minor_user_id);
```

### 7.2 국가별 연령 기준

```python
# services/guardian.py
MINOR_AGE = {
    "KR": 14,  # 정보통신망법
    "US": 13,  # COPPA
    "EU": 16,  # GDPR-K
    "JP": 18,  # 청소년 보호
    "default": 16,
}

def is_minor(birth_year: int, country_code: str) -> bool:
    age = datetime.now().year - birth_year
    threshold = MINOR_AGE.get(country_code, MINOR_AGE["default"])
    return age < threshold
```

### 7.3 가입 플로우

```
1. /auth/sns/google 호출 (기존)
2. 첫 가입이면 → 응답에 onboarding_required=true
3. Frontend → /onboarding 화면
4. 사용자 → 생년 + 국가 입력
5. POST /me/onboarding { birth_year, country_code }
   ↓ Backend
   is_minor 계산 → users.is_minor = TRUE
   if minor:
     return { onboarding_status: "guardian_required" }
6. Frontend → 보호자 이메일 입력
7. POST /me/guardian/request { guardian_email, guardian_name }
   ↓ Backend
   create guardian_consent row + 매직 링크 토큰
   send_email(guardian_email, magic_link_url)
   users.status = "pending_guardian"
   return 202
8. 보호자 → 이메일 클릭 → /guardian/consent/{token}
9. /guardian/consent 화면 → "동의" 클릭
10. POST /guardian/consent/{token}/approve
    ↓ Backend
    consented_at = now
    users.status = "active"
    artist_profile.guardian_consent = true (작가인 경우)
```

### 7.4 미성년자 작가 정산 가드

```python
# api/sponsorships.py 또는 정산 모듈
async def create_payout(artist_id):
    artist = await get_user(artist_id)
    if artist.is_minor:
        consent = await get_active_guardian_consent(artist.id)
        if not consent:
            raise ApiError(
                "FORBIDDEN",
                "Guardian consent required for minor payout",
                http_status=403,
            )
        # 정산 계좌가 보호자 명의인지 검증
        # → Phase 4는 placeholder, Phase 5 정산 시스템에서 본격 처리
```

### 7.5 입찰 금액 상한

```python
# api/auctions.py place_bid
if user.is_minor:
    minor_limit = (await get_setting(db, "minor_max_bid_amount"))["amount"]
    if amount > Decimal(str(minor_limit)):
        raise ApiError(
            "VALIDATION_ERROR",
            f"Minor bid limit: ₩{minor_limit:,}",
            http_status=422,
        )
```

`system_settings.minor_max_bid_amount = {"amount": 100000}` 시드.

### 7.6 보호자 동의 철회

```python
# api/guardian.py
@router.post("/guardian/withdraw/{token}")
async def withdraw_consent(token: str, db = ...):
    consent = await find_consent(token)
    consent.withdrawn_at = now()
    minor = await get_user(consent.minor_user_id)
    minor.status = "guardian_revoked"  # 작품 비공개 + 거래 중단
    # 모든 활성 경매 cancelled, 정기 후원 cancel
    await db.commit()
```

---

## 8. 공통: 이메일 발송 서비스

M1(영수증), M3(법적 안내), M5(보호자 동의) 모두 이메일이 필요합니다.

### 8.1 어댑터 패턴

```python
# services/email/base.py
class EmailProvider(ABC):
    @abstractmethod
    async def send(
        self,
        to: str,
        subject: str,
        html: str,
        text: str | None = None,
        tags: list[str] | None = None,
    ) -> str: ...  # message_id
```

### 8.2 Provider 후보

| 서비스 | 장점 | 단점 |
|--------|------|------|
| Resend | 개발자 친화, 한글 잘됨 | 한국 SMS는 별도 |
| AWS SES | 저렴 | 도메인 검증 + 평판 관리 필요 |
| Mailgun | 안정적 | 가격 |

**추천**: 초기 Resend → 트래픽 증가 시 SES.

### 8.3 템플릿

`templates/email/{language}/{template}.html` 구조:
- `payment_receipt.html`
- `auction_won.html`
- `guardian_consent.html`
- `account_deleted.html`
- `warning_issued.html`

i18n은 Phase 6 (Could C3) 범위지만 ko/en 2개는 Phase 4에서 처리.

---

## 9. 데이터 모델 변경 요약

| 마이그레이션 | 신규 테이블 | 수정 컬럼 |
|--------------|-------------|----------|
| 0006_auth_refresh_tokens | refresh_tokens | — |
| 0007_gdpr | webhook_events (M1과 함께) | users (deleted_at, deletion_scheduled_for, gdpr_export_count, privacy_policy_version, terms_version) |
| 0008_media_storage_url | — | media_assets (storage_provider, storage_key) |
| 0009_minor_guardian | guardian_consents | users (birth_year — birth_date 폐기 권장) |

---

## 10. 환경변수 추가

```bash
# Stripe (M1)
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLIC_KEY=pk_live_...   # frontend NEXT_PUBLIC_

# Storage (M4)
STORAGE_PROVIDER=s3
S3_BUCKET=domo-prod-media
S3_REGION=ap-northeast-2
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
CDN_BASE_URL=https://cdn.domo.tuzigroup.com

# Email (공통)
EMAIL_PROVIDER=resend  # 또는 ses
RESEND_API_KEY=
EMAIL_FROM=noreply@domo.tuzigroup.com

# Rate limit (M6)
RATE_LIMIT_MODE=enforce  # 또는 monitor

# Frontend
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_live_...
```

---

## 11. 구현 우선순위

### Week 15 (보안 페어)
**Day 1~2**: M2 마이그레이션 + refresh token 회전 + 클라이언트 자동 회전
**Day 3**: M2 작가 승인 시 강제 revoke + sessions API
**Day 4~5**: M6 RateLimiter + monitor 모드 배포 + 트래픽 관찰

### Week 16 (Stripe)
**Day 1**: webhook_events 테이블 + 멱등성 처리
**Day 2~3**: StripeProvider 구현 + factory 분기 + Payment Intent 흐름
**Day 4**: Subscription 흐름 + cancel_at_period_end webhook
**Day 5**: Refund API + dual-run 시작 (mock + stripe 양쪽)

### Week 17 (S3 + GDPR 절반)
**Day 1**: S3 버킷 + IAM 정책 + 마이그레이션 0008
**Day 2**: S3Storage 구현 + presigned upload API
**Day 3**: 프론트 업로드 플로우 변경 + 기존 파일 마이그레이션 스크립트
**Day 4**: GDPR 0007 마이그레이션 + soft delete + export API
**Day 5**: 쿠키 배너 + Legal 페이지 + 가입 시 동의

### Week 18 (GDPR 마무리 + 미성년자)
**Day 1**: 30일 hard delete cron + 복구 플로우
**Day 2**: M5 0009 마이그레이션 + 미성년 판정 로직
**Day 3**: 보호자 매직 링크 발급 + 이메일 발송
**Day 4**: 보호자 동의/철회 API + 가드 적용
**Day 5**: Phase 4 종합 검증 + gap-detector 분석

---

## 12. Definition of Done

### 기능
- [ ] M1 실 Stripe로 결제 1건 + 환불 1건 성공
- [ ] M2 토큰 탈취 시뮬레이션 → family revoke 동작
- [ ] M3 Export → JSON 다운로드 → 모든 데이터 포함 검증
- [ ] M3 Soft delete → 30일 후 hard delete cron 동작
- [ ] M4 S3 업로드 → CDN 서빙 → 썸네일 자동 생성
- [ ] M5 미성년 가입 → 보호자 이메일 → 매직 링크 → 동의 → active 전이
- [ ] M5 미성년 입찰 상한 차단
- [ ] M6 Rate limit 초과 시 429 + 헤더

### 비기능
- [ ] gap-detector Phase 4 분석 95%+
- [ ] OWASP Top 10 high/critical 0건
- [ ] Stripe webhook 멱등성 검증
- [ ] CDN cache hit > 80%
- [ ] Rate limit 정상 트래픽 차단 X (1주 모니터링)
- [ ] 모든 신규 API E2E 테스트 통과

---

## 13. 다음 단계

1. **본 Design 검토 + 확정**
2. **외부 의존성 발주 진행 상황 확인** (Stripe, AWS, 법률)
3. **Week 15 착수** — M2 + M6 (외부 의존성 무관, 즉시 시작 가능)
4. **외부 의존성 도착 순서대로** Week 16~18 진행

---

## 부록 A — Phase 0~3에서 의도적으로 남긴 hooks

| Hook | Phase 4 활용 |
|------|-------------|
| `PaymentProvider` 인터페이스 | M1 StripeProvider 추가만으로 교체 |
| `system_settings` JSONB | M5 minor_max_bid_amount, M6 rate_limits |
| `RATE_LIMITED` 에러 코드 | M6 미들웨어가 그대로 사용 |
| `users.is_minor`, `birth_date`, `guardian_id` | M5에서 활용 + birth_year로 마이그레이션 |
| `webhook_events` (M1에서 신규) | 멱등성 |
| `users.gdpr_consent_at` | M3 가입 시 기록 |

이 모든 hook은 Phase 0~3에서 "지금은 안 쓰지만 Phase 4에서 활용한다"는 가정으로 의도적으로 추가된 것이며, Phase 4에서 그대로 활용 가능합니다.
