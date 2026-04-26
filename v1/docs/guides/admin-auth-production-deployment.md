# 관리자 인증 시스템 Production 배포 가이드

**대상**: 비밀번호 + TOTP 2FA + Recovery Codes + WebAuthn/Passkey가 통합된 admin 인증 시스템 ([v1/admin](../../admin), [v1/backend/app/api/admin_auth.py](../../backend/app/api/admin_auth.py), [v1/backend/app/api/admin_webauthn.py](../../backend/app/api/admin_webauthn.py))
**전제**: 마이그레이션 0034까지 적용된 dev 환경에서 정상 동작 확인 완료
**최종 수정**: 2026-04-26

**Production 도메인**:

| 용도 | 도메인 |
|---|---|
| 관리자 콘솔 (admin Next.js) | `domo-admin.tuzigroup.com` |
| 사용자 앱 (frontend Next.js) | `domo.tuzigroup.com` |
| Backend API (FastAPI) | `domo-api.tuzigroup.com` |

이 문서는 dev → staging → production 단계별 cutover 절차를 다룹니다. 한 줄도 빼지 않고 순서대로 따라가시면 됩니다.

---

## 0. 사전 준비물 체크리스트

배포 시작 전 다음 항목이 모두 확보되어 있어야 합니다:

| # | 항목 | 비고 |
|:--:|---|---|
| 1 | DNS A/CNAME 레코드 — `domo-admin.tuzigroup.com` | 서버 IP 또는 LB 가리킴 |
| 2 | DNS A/CNAME 레코드 — `domo.tuzigroup.com` | 동일 |
| 3 | DNS A/CNAME 레코드 — `domo-api.tuzigroup.com` | 동일 |
| 4 | TLS 인증서 (Let's Encrypt 또는 상용) | 위 3개 도메인 모두에 유효 — wildcard `*.tuzigroup.com` 1장으로 처리하면 편함 |
| 5 | PostgreSQL 인스턴스 (RDS / Cloud SQL 등) | 자동 백업 활성화 |
| 6 | Redis 인스턴스 (ElastiCache / MemoryStore) | rate limit + 세션용 |
| 7 | 운영자 이메일 1개 이상 (수신 가능) | 로그인 알림 수신용 |
| 8 | Email provider 계정 (Resend / SES) — `tuzigroup.com` 도메인 검증 완료 | new device alert 발송용 — DKIM/SPF 셋업 필수 |
| 9 | TOTP 앱 설치된 폰 | 운영자 본인용 (Google Authenticator / Authy / 1Password 등) |
| 10 | Hardware security key 또는 OS 생체인증 가능 디바이스 | Passkey 등록용 (선택, 강력 권장) |

### 0.1. DNS 설정 예시

도메인을 같은 서버에 모두 가리키는 가장 단순한 형태:
```
domo-admin.tuzigroup.com    A    <server-public-ip>
domo.tuzigroup.com          A    <server-public-ip>
domo-api.tuzigroup.com      A    <server-public-ip>
```

분리 배포 시 (admin/frontend는 Vercel, backend는 EC2 등):
```
domo-admin.tuzigroup.com    CNAME    cname.vercel-dns.com.
domo.tuzigroup.com          CNAME    cname.vercel-dns.com.
domo-api.tuzigroup.com      A        <ec2-elastic-ip>
```

### 0.2. TLS 인증서 — 와일드카드 권장

3개 도메인을 별도로 발급받는 것보다 wildcard 1장이 관리 편리:
```bash
# certbot DNS-01 (Route53 / Cloudflare 등)
certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d "*.tuzigroup.com" \
  -d "tuzigroup.com"
```

---

## 1. 환경변수 발급

**중요**: 아래 시크릿들은 한 번 발급한 후 **분실하면 모두 다시 만들어야 하고**, 이미 저장된 데이터를 복호화할 수 없게 됩니다. 1Password / AWS Secrets Manager / Hashicorp Vault 등 안전한 저장소에 미리 저장하세요.

### 1.1. JWT 서명 키 (`JWT_SECRET`)

JWT access/refresh 토큰 서명에 사용합니다. 32바이트 이상.

```bash
openssl rand -hex 32
# 출력 예: 8f4a9c2e1b...  (64자 hex)
```

저장 후 `.env`:
```env
JWT_SECRET=8f4a9c2e1b5d3f7a9c8e1b2d4f6a8c0e1b3d5f7a9c1e3b5d7f9a1c3e5b7d9f1c
```

**회전 정책**: 6개월. 회전 시 모든 활성 세션이 무효화되므로 사용자 점검시간 공지 후 진행.

### 1.2. TOTP secret 암호화 키 (`TOTP_ENCRYPTION_KEY`)

DB의 `users.totp_secret`을 Fernet (AES-128-CBC + HMAC-SHA256)으로 암호화합니다. **반드시** 설정해야 합니다 (미설정 시 평문 저장 + boot 경고).

```bash
# venv가 활성화된 상태에서
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 출력 예: gAAAAABh...  (44자 URL-safe base64)
```

저장 후 `.env`:
```env
TOTP_ENCRYPTION_KEY=g7K3r9X2pQ8vN4mZ1aB5cD6eF7gH8iJ9kL0mN1oP2qR=
```

**회전 정책**: 키가 유출되었을 때만. 회전 시 모든 admin이 TOTP 재등록 필요 (자동 마이그레이션 없음 — 의도적 단순함).

### 1.3. Google OAuth (사용자 SNS 로그인용 — admin 무관)

admin은 SNS 차단 상태라 admin 인증과는 직접 무관하지만, 일반 사용자 SNS 로그인을 위해 필요합니다. Google Cloud Console에서 OAuth client 등록 시 **승인된 자바스크립트 출처**에 `https://domo.tuzigroup.com` 추가:

```env
GOOGLE_CLIENT_ID=<google-cloud-console에서-발급>
GOOGLE_CLIENT_SECRET=<동일>
```

### 1.4. Email provider

운영 환경에서 `EMAIL_PROVIDER=mock` 사용 절대 금지. Resend 권장:

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
EMAIL_FROM_ADDRESS=no-reply@tuzigroup.com
EMAIL_FROM_NAME=Domo
```

⚠️ **DNS 레코드 필수**: Resend 대시보드에서 `tuzigroup.com` 도메인을 등록한 뒤 가이드에 따라 SPF / DKIM / DMARC TXT 레코드를 추가해야 메일이 spam으로 안 떨어집니다.

대안: AWS SES 사용 시 [v1/backend/app/services/email/](../../backend/app/services/email/) 에 `ses.py` 어댑터 추가 필요.

### 1.5. Rate limit 모드

dev: `monitor` (로깅만), production: `enforce` (실제 차단)
```env
RATE_LIMIT_MODE=enforce
```

### 1.6. KYC enforcement

dev seed 통과를 위해 default가 `off`. 결제/후원 가능한 production에서는 반드시 `enforce`:
```env
# 환경변수가 아닌 system_settings 테이블에서 관리됨
# 부팅 후 admin 콘솔의 시스템 설정 페이지에서 변경 권장 (재배포 불필요)
```

또는 운영 cutover 직후 1회 직접 SQL:
```sql
UPDATE system_settings SET value = '"enforce"' WHERE key = 'kyc_enforcement';
```

---

## 2. WebAuthn Relying Party 설정

WebAuthn은 도메인 단위로 신원이 결속되는 표준입니다. 잘못 설정하면 **모든 Passkey 로그인이 silent fail**합니다.

### 2.1. 핵심 개념

| 용어 | 의미 | 예시 |
|---|---|---|
| `rp_id` | 등록 도메인 (브라우저가 정확히 일치 검증) | `domo-admin.tuzigroup.com` |
| `rp_name` | 사용자 화면에 표시되는 이름 | `Domo Admin` |
| `rp_origin` | 전체 origin (scheme + host + port) | `https://domo-admin.tuzigroup.com` |

### 2.2. 도메인 정책 결정

선택 가능한 두 가지 패턴:

**패턴 A — 별도 admin 서브도메인 (권장)**
- `rp_id`: `domo-admin.tuzigroup.com`
- `rp_origin`: `https://domo-admin.tuzigroup.com`
- 장점: 권한 격리, 사용자 앱(`domo.tuzigroup.com`)과 admin 앱(`domo-admin.tuzigroup.com`)이 독립적으로 배포
- 단점: 사용자 앱(`domo.tuzigroup.com`)에서는 같은 Passkey를 쓸 수 없음 (다른 RP)

**패턴 B — 루트 도메인 공유**
- `rp_id`: `tuzigroup.com`
- `rp_origin`: `https://domo-admin.tuzigroup.com` (admin URL이지만 RP는 루트)
- 장점: 추후 사용자 앱에도 Passkey 도입 시 동일 credential 재사용
- 단점: admin 권한 격리 약함, RP scope가 광범위 (`tuzigroup.com`의 다른 서브도메인 앱들이 같은 credential 접근 가능)

**Domo는 패턴 A 권장** — admin 보안 격리가 우선.

### 2.3. .env 설정

```env
WEBAUTHN_RP_ID=domo-admin.tuzigroup.com
WEBAUTHN_RP_NAME=Domo Admin
WEBAUTHN_RP_ORIGIN=https://domo-admin.tuzigroup.com
```

⚠️ **주의사항**:
- `rp_id`에 `https://` / 포트 / 경로 절대 포함하지 말 것 (도메인만)
- `rp_origin`은 정확히 일치해야 함 (`https://domo-admin.tuzigroup.com`와 `https://domo-admin.tuzigroup.com/`는 다름)
- 한 번 등록된 Passkey는 다른 `rp_id`로 옮길 수 없음 — 도메인 변경 시 전 admin 재등록 필요

### 2.4. localhost 예외

WebAuthn 표준은 `localhost`를 HTTPS 없이 허용합니다 (dev 편의):
```env
# 로컬 개발
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_ORIGIN=http://localhost:3800
```

이는 실제 배포 환경에서 사용 금지 — `127.0.0.1`도 동일 도메인으로 인식하지 않으므로 항상 `localhost`로만 접근.

---

## 3. HTTPS 셋업

WebAuthn은 HTTPS 또는 `localhost`에서만 동작합니다. http로 접근하면 브라우저가 silent fail (콘솔 에러도 없는 경우 있음).

### 3.1. Let's Encrypt + Nginx — admin 콘솔

```nginx
# /etc/nginx/sites-available/domo-admin
server {
    listen 80;
    server_name domo-admin.tuzigroup.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name domo-admin.tuzigroup.com;

    ssl_certificate     /etc/letsencrypt/live/tuzigroup.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuzigroup.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 보안 헤더
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "publickey-credentials-get=*, publickey-credentials-create=*";

    # admin Next.js 앱 (3800)
    location / {
        proxy_pass http://localhost:3800;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

⚠️ **`Permissions-Policy` 필수**: 일부 브라우저는 이 헤더 없이 Passkey API를 차단합니다.

### 3.2. Backend API 도메인

```nginx
# /etc/nginx/sites-available/domo-api
server {
    listen 80;
    server_name domo-api.tuzigroup.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name domo-api.tuzigroup.com;

    ssl_certificate     /etc/letsencrypt/live/tuzigroup.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuzigroup.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;

    # FastAPI backend (3710)
    location / {
        proxy_pass http://localhost:3710;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # 미디어 업로드 등 큰 요청 허용
        client_max_body_size 1G;

        # SSE / 장시간 응답 대응
        proxy_read_timeout 120s;
    }
}
```

### 3.3. 사용자 frontend 도메인

```nginx
# /etc/nginx/sites-available/domo
server {
    listen 80;
    server_name domo.tuzigroup.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name domo.tuzigroup.com;

    ssl_certificate     /etc/letsencrypt/live/tuzigroup.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tuzigroup.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # frontend Next.js 앱 (3700)
    location / {
        proxy_pass http://localhost:3700;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

### 3.4. 활성화

```bash
sudo ln -s /etc/nginx/sites-available/domo-admin /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/domo-api /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/domo /etc/nginx/sites-enabled/
sudo nginx -t        # 문법 검증
sudo systemctl reload nginx
```

### 3.5. 인증서 자동 갱신 검증

```bash
sudo certbot renew --dry-run
# Cron 또는 systemd timer로 자동 등록 확인
sudo systemctl list-timers | grep certbot
```

---

## 4. CORS / Frontend URL 설정

backend는 admin / frontend / staging 등 **여러 origin**을 허용해야 합니다.

[v1/backend/app/main.py](../../backend/app/main.py#L83) 의 `_cors_origins`는 다음을 자동 포함:
- `settings.frontend_url`, `settings.admin_url`
- localhost / 127.0.0.1 의 3000, 3700, 3800 (dev fallback)
- `settings.extra_cors_origins` (CSV)

production `.env`:
```env
FRONTEND_URL=https://domo.tuzigroup.com
ADMIN_URL=https://domo-admin.tuzigroup.com
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1
EXTRA_CORS_ORIGINS=
```

⚠️ admin Next.js 앱의 `NEXT_PUBLIC_API_URL`은 **빌드 타임에 인라인**됩니다. production 빌드 시 반드시 production API URL로 빌드:

```bash
cd v1/admin
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1 npm run build
```

또는 `v1/admin/.env.production`에 저장:
```env
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1
```

frontend도 동일:
```bash
cd v1/frontend
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1 npm run build
```

---

## 5. 데이터베이스 마이그레이션

### 5.1. 백업 먼저

```bash
# RDS / Cloud SQL의 자동 스냅샷 외에도 수동 백업 권장
pg_dump -h <host> -U <user> -d domo -F c -f domo-pre-admin-auth.dump
```

### 5.2. 마이그레이션 적용

```bash
# 컨테이너 안에서
docker compose exec backend alembic upgrade head

# 또는 호스트 venv
cd v1/backend
.venv/bin/alembic upgrade head
```

새로 적용되는 마이그레이션:
| 버전 | 내용 |
|---|---|
| 0032 | `users` 테이블에 `password_hash` / `totp_secret` / `totp_enabled_at` / `failed_login_count` / `locked_until` 컬럼 |
| 0033 | `admin_recovery_codes` 테이블 |
| 0034 | `webauthn_credentials` + `webauthn_challenges` 테이블 |

### 5.3. 마이그레이션 검증

```sql
\d users  -- password_hash, totp_secret 컬럼 존재 확인
\d admin_recovery_codes
\d webauthn_credentials
\d webauthn_challenges

-- 인덱스 확인
SELECT indexname FROM pg_indexes WHERE tablename IN
  ('admin_recovery_codes', 'webauthn_credentials', 'webauthn_challenges');
```

---

## 6. 첫 admin 계정 생성

운영 환경의 첫 admin은 dev seed가 아닌 **수동으로** 만드는 것을 권장합니다 (dev seed의 `admin@domo.example.com`는 도메인이 reserved example).

### 6.1. CLI로 admin 생성

```bash
# backend 컨테이너 안에서 Python REPL
docker compose exec backend python
```

```python
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

async def create_admin():
    async with AsyncSessionLocal() as db:
        email = "ops@tuzigroup.com"  # 본인 이메일로 변경
        password = "TempPw_Change_On_First_Login!2026"  # 강력한 임시 비밀번호

        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"이미 존재: {email}")
            return

        user = User(
            email=email,
            display_name="Operator",
            role="admin",
            status="active",
            password_hash=hash_password(password),
            password_changed_at=datetime.now(timezone.utc),
            sns_provider=None,
            sns_id=None,
        )
        db.add(user)
        await db.commit()
        print(f"생성 완료. 임시 비밀번호: {password}")
        print("→ 첫 로그인 후 비밀번호 변경 + TOTP 등록 + Passkey 등록 필수")

asyncio.run(create_admin())
exit()
```

### 6.2. 첫 로그인 흐름

브라우저로 `https://domo-admin.tuzigroup.com/login` 접속:

1. **이메일 + 임시 비밀번호 입력** → 자동으로 `/settings/totp-setup`로 redirect
2. **TOTP 등록** — 폰의 Authenticator 앱으로 QR 스캔 → 6자리 코드 입력 → 활성화
3. **복구 코드 10개 표시** — **반드시 다운로드/인쇄/복사**한 후 안전한 곳에 보관 (1Password / 인쇄 후 금고)
4. 체크박스 동의 후 "완료 → 대시보드"
5. (권장) 좌측 메뉴 → **Security → 패스키** → **+ 등록** → 디바이스 생체인증 → "MacBook TouchID" 등 닉네임 저장
6. (권장) 임시 비밀번호 → 강력한 비밀번호로 변경 (현재 변경 UI 미구현 — 필요 시 추가 작업)

### 6.3. 2FA 미등록 admin은 어디로도 갈 수 없음 (강제 정책)

비밀번호만 통과한 admin (TOTP / Passkey 미등록)이 URL 직접 입력으로 dashboard 접근을 시도해도 **두 단계에서 차단**됩니다:

**Layer 1 — Backend (진짜 차단)**
- [v1/backend/app/core/admin_deps.py](../../backend/app/core/admin_deps.py)의 `require_admin_with_2fa` dep가 `users.totp_enabled_at` 또는 `webauthn_credentials` 보유 여부를 매 API 호출마다 검증
- 둘 다 없으면 **403 `SECOND_FACTOR_REQUIRED`** 반환 + `details.setup_url = "/settings/totp-setup"`
- 모든 admin 엔드포인트에 적용 — `/admin/users`, `/admin/dashboard/*`, `/settlements/admin/*`, `/admin/orders/*/refund` 등 전부

**Layer 2 — Frontend (UX redirect)**
- [v1/admin/src/components/AdminShell.tsx](../../admin/src/components/AdminShell.tsx)가 `/auth/me` 응답의 `second_factor_enrolled` 값을 검사
- false인 경우 `ALLOW_WITHOUT_2FA` 화이트리스트(`/login`, `/settings/totp-setup`, `/settings/passkeys`, `/settings/recovery-codes`) 외 모든 경로에서 `/settings/totp-setup`로 즉시 `router.replace()`
- DevTools / curl로 frontend 우회해도 Layer 1이 차단

**Whitelist 엔드포인트** (2FA 등록 자체를 위해 필수 허용):
| 카테고리 | 경로 |
|---|---|
| TOTP 등록 | `GET /auth/admin/totp/setup`, `POST /auth/admin/totp/enable`, `POST /auth/admin/totp/disable` |
| Recovery codes | `GET /auth/admin/recovery-codes/status`, `POST /auth/admin/recovery-codes/regenerate` |
| WebAuthn | `POST /auth/admin/webauthn/register/begin`, `POST /auth/admin/webauthn/register/finish`, `GET /auth/admin/webauthn/credentials`, `DELETE /auth/admin/webauthn/credentials/{id}` |
| 자기 정보 / 세션 | `GET /auth/me`, `POST /auth/logout`, `GET /auth/sessions`, `DELETE /auth/sessions/{id}` |

→ 의미: 비밀번호만 가진 신규 admin은 위 4종 외 어떤 비즈니스 기능에도 접근할 수 없음. 강제로 TOTP 또는 Passkey를 등록하게 됨.

### 6.4. `/auth/me` 응답 — admin 추가 필드

[v1/backend/app/api/auth.py](../../backend/app/api/auth.py) `GET /auth/me`는 admin 사용자에게 다음 필드를 추가로 반환:

```json
{
  "data": {
    "id": "...",
    "email": "ops@tuzigroup.com",
    "role": "admin",
    "totp_enabled_at": "2026-04-26T10:30:00Z",   // null이면 미등록
    "passkey_count": 2,                           // 등록된 WebAuthn credential 수
    "second_factor_enrolled": true                // 둘 중 하나라도 있으면 true
  }
}
```

frontend는 이 3개 필드를 사용해 redirect 판단. 비-admin 사용자에게는 노출되지 않음.

---

## 7. 운영 시작 직후 체크리스트

### 7.1. 보안 검증

```bash
# 1) admin이 SNS 로그인 시도 시 차단되는지
curl -X POST https://domo-api.tuzigroup.com/v1/auth/sns/google \
  -H "Content-Type: application/json" \
  -d '{"id_token":"mock:ops@tuzigroup.com"}'
# 기대: 403 ADMIN_SNS_FORBIDDEN (단, mock fallback이 production에서 비활성이면 401)

# 2) admin login은 정상
curl -X POST https://domo-api.tuzigroup.com/v1/auth/admin/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ops@tuzigroup.com","password":"TempPw_..."}'
# 기대: 200 + {totp_required: true, challenge_token: "..."}

# 3) CORS preflight 확인
curl -i -X OPTIONS https://domo-api.tuzigroup.com/v1/auth/admin/login \
  -H "Origin: https://domo-admin.tuzigroup.com" \
  -H "Access-Control-Request-Method: POST"
# 기대: 200 + Access-Control-Allow-Origin: https://domo-admin.tuzigroup.com

# 4) /v1/health 확인
curl https://domo-api.tuzigroup.com/v1/health
# 기대: 200 {"data":{"status":"ok"}}

# 5) frontend도 reachable
curl -I https://domo.tuzigroup.com
# 기대: 200 (또는 next.js의 cache hit 응답)

# 6) 2FA 미등록 admin이 비즈니스 endpoint에 접근 시 차단되는지
#    (첫 admin 생성 직후, TOTP 등록 전 상태에서)
ACCESS_TOKEN="<로그인 step1로 받은 토큰>"
curl -i https://domo-api.tuzigroup.com/v1/admin/users \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# 기대: 403 + {"error":{"code":"SECOND_FACTOR_REQUIRED","details":{"setup_url":"/settings/totp-setup"}}}

# 7) /auth/me는 2FA 미등록이어도 접근 가능 (whitelist)
curl https://domo-api.tuzigroup.com/v1/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
# 기대: 200 + {"data":{...,"second_factor_enrolled":false,"passkey_count":0}}
```

### 7.2. Email 발송 검증

다른 디바이스(폰의 Chrome 등)로 admin 로그인 → 운영자 이메일에 "새 디바이스 로그인" 알림 도착해야 함. 미도달 시:

```bash
# 컨테이너 로그에서 admin_login_alert 검색
docker compose logs backend | grep admin_login_alert
```

가능 원인:
- `EMAIL_PROVIDER=mock` 그대로 → `.env` 수정
- Resend API key 무효 → API key 재발급
- Resend에 `tuzigroup.com` 도메인 미등록 → Resend 대시보드에서 도메인 추가
- DNS DKIM/SPF 미설정 → 운영자 메일 서버가 spam으로 분류 → DNS TXT 레코드 추가

DNS 레코드 (Resend 발급):
```
# TXT 레코드 (값은 Resend 대시보드에서 복사)
tuzigroup.com.          IN TXT "v=spf1 include:_spf.resend.com ~all"
resend._domainkey       IN TXT "p=MIGfMA0GCSqGSIb3..."
_dmarc                  IN TXT "v=DMARC1; p=none; rua=mailto:dmarc@tuzigroup.com"
```

### 7.3. KYC enforcement 활성화

```sql
-- 결제/후원 가능한 production이라면 필수
UPDATE system_settings
SET value = '"enforce"'::jsonb
WHERE key = 'kyc_enforcement';
```

또는 admin 콘솔의 "시스템 설정" 페이지에서 GUI 변경.

### 7.4. Mock provider 일소

| 환경변수 | dev 값 | production 값 |
|---|---|---|
| `PAYMENT_PROVIDER` | `mock_stripe` | `stripe` |
| `STORAGE_PROVIDER` | `local` | `s3` |
| `EMAIL_PROVIDER` | `mock` | `resend` |
| `KYC_PROVIDER` | `mock` | `toss` 또는 `stripe_identity` (구현 필요 — 현재는 NotImplemented) |

⚠️ KYC `toss` / `stripe_identity` provider는 [v1/backend/app/services/kyc.py:84-112](../../backend/app/services/kyc.py)에서 `RuntimeError`를 raise합니다. 결제/후원 막는 게 아니라면 `mock`으로 시작 후 추후 구현.

### 7.5. mock SNS 우회 차단 (필수)

[v1/backend/app/services/google_auth.py:21-22](../../backend/app/services/google_auth.py)에 `if token.startswith("mock:")` fallback이 있습니다. Production에서는 환경변수 가드 추가 **권장**:

```python
# google_auth.py
if token.startswith("mock:"):
    if settings.environment != "development":
        raise ApiError("INVALID_TOKEN", "Mock tokens not allowed", http_status=401)
    # ... 기존 로직
```

또는 아예 `if False and token.startswith("mock:")` 처리. 현재 admin은 SNS 차단되지만 일반 사용자 계정은 mock으로 임의 가입 가능 — production에서 큰 보안 구멍.

---

## 8. 모니터링 / 옵저버빌리티

### 8.1. 추가 모니터링 항목

이번 작업으로 새로 추적해야 할 메트릭:

| 메트릭 | 정상 | 비정상 | 대응 |
|---|---|---|---|
| `auth_admin_login` 성공률 | >95% | <80% | 비밀번호 분실 / TOTP drift / lockout 다발 |
| 새 디바이스 알림 발송 빈도 | <1/day | >10/day | 계정 탈취 의심 — 즉시 admin 통보 |
| `admin_recovery_code` 사용 횟수 | <1/quarter | >1/month | TOTP 손상 빈발 — 운영 절차 점검 |
| `webauthn_challenges` 잔여 수 | <100 | >10,000 | 만료 cron 미동작 |

### 8.2. 만료 challenge 정리 cron 추가 (TODO)

현재 `webauthn_challenges` 만료 5분 후 자동 삭제 코드 없음. 다음 중 하나 추가 권장:

**A. SQL 트리거 (간단)**
```sql
CREATE INDEX IF NOT EXISTS ix_webauthn_challenges_expires_at
  ON webauthn_challenges(expires_at);

-- 매시간 cron으로 실행
DELETE FROM webauthn_challenges WHERE expires_at < NOW();
```

**B. 백엔드 cron 잡 추가**
[v1/backend/app/services/webhook_cleanup_jobs.py](../../backend/app/services/webhook_cleanup_jobs.py) 패턴 참고하여 `webauthn_challenge_cleanup_jobs.py` 추가 후 [main.py lifespan](../../backend/app/main.py#L48-L60)에 등록.

### 8.3. Lockout 모니터링

5회 실패 → 15분 lockout. SQL로 모니터링:
```sql
SELECT email, failed_login_count, locked_until
FROM users
WHERE role = 'admin' AND failed_login_count > 0
ORDER BY locked_until DESC NULLS LAST;
```

대시보드에 위 query를 카드로 추가하면 brute force 시도 감지 용이.

---

## 9. Rollback Plan

신규 admin 인증이 production에서 문제를 일으킬 때 빠른 되돌림:

### 9.1. 코드 롤백

```bash
# 직전 PR 머지 커밋 hash 확인
git log --oneline -10
# 해당 커밋 직전으로 되돌림
git revert <commit-hash>
git push origin main
# CI/CD로 재배포
```

### 9.2. DB 마이그레이션 롤백

```bash
# 0032로 다시 내림 (recovery codes + webauthn 테이블 drop)
docker compose exec backend alembic downgrade 0032

# 0031로 더 내리면 admin password/totp 컬럼도 drop
docker compose exec backend alembic downgrade 0031
```

⚠️ downgrade 시 admin 비밀번호 / TOTP / Passkey 데이터 모두 소실. 백업 필수.

### 9.3. 긴급 admin 강제 unlock

DB 직접 접근 시:

```sql
-- 모든 admin lockout 해제
UPDATE users SET failed_login_count = 0, locked_until = NULL WHERE role = 'admin';

-- 특정 admin TOTP 강제 비활성 (TOTP secret 손상 시)
UPDATE users
SET totp_secret = NULL, totp_enabled_at = NULL
WHERE email = 'ops@tuzigroup.com' AND role = 'admin';
DELETE FROM admin_recovery_codes WHERE user_id = (
  SELECT id FROM users WHERE email = 'ops@tuzigroup.com'
);

-- 비상 비밀번호 재설정 (Python REPL에서)
-- hash_password("NewEmergencyPw!") 실행 후 hash 값을 사용
UPDATE users SET password_hash = '<bcrypt-hash>'
WHERE email = 'ops@tuzigroup.com' AND role = 'admin';
```

---

## 10. 흔한 실패 케이스 트러블슈팅

### 10.1. WebAuthn 등록이 silent fail

**증상**: 로그인 페이지의 "Passkey로 등록" 클릭 시 브라우저가 생체인증 다이얼로그를 띄우지 않음

**원인 후보**:
1. **HTTP로 접근 중** (`http://domo-admin.tuzigroup.com`) → HTTPS 필수
2. **`rp_id` 불일치**: backend `.env`의 `WEBAUTHN_RP_ID`가 브라우저 주소창의 호스트와 다름
3. **iframe 안에서 접근**: WebAuthn은 top-level frame만 허용 (admin은 iframe 사용 안 하니 무관)
4. **브라우저가 너무 오래됨**: Chrome 67+ / Safari 14+ / Firefox 60+

**진단**:
```js
// 브라우저 콘솔에서
console.log(window.location.origin);
// "https://domo-admin.tuzigroup.com" 와 backend의 WEBAUTHN_RP_ORIGIN이 정확히 일치해야 함
```

### 10.2. TOTP 코드가 항상 invalid

**원인**: 서버 시간이 NTP 동기화 안됨. TOTP는 ±30초 (`valid_window=1`) 만 허용.

```bash
# 서버에서
timedatectl status
# NTP 활성화 안 되어 있으면
sudo timedatectl set-ntp true
```

### 10.3. CORS preflight 실패

**증상**: 브라우저 콘솔에 `Access-Control-Allow-Origin missing`

**원인**: admin URL이 backend CORS allowlist에 없음

**해결**:
```env
ADMIN_URL=https://domo-admin.tuzigroup.com
EXTRA_CORS_ORIGINS=https://other-stage.tuzigroup.com
```
backend 재시작.

### 10.4. "INVALID_CHALLENGE" 매번 발생

**원인 1**: backend가 여러 인스턴스로 실행되는데 sticky session 없음 → challenge가 다른 인스턴스 메모리에 저장. **하지만 우리는 DB(`webauthn_challenges`)에 저장하므로 무관**.

**원인 2**: 5분 안에 finish 호출 안됨 → 사용자가 너무 오래 머뭇거림. UX 안내 추가 권장.

**원인 3**: DB 트랜잭션 격리 문제. `_consume_challenge`는 `delete + commit` 패턴이라 동시 호출 시 한쪽이 INVALID_CHALLENGE 받음. 의도된 동작.

### 10.5. Recovery code가 항상 invalid

**원인**: 사용자가 이미 사용한 코드를 재사용 시도. 1회용 정책. → 새 코드 발급 필요.

```sql
-- 특정 admin의 recovery code 상태 조회
SELECT id, used_at, used_user_agent, used_ip, created_at
FROM admin_recovery_codes
WHERE user_id = (SELECT id FROM users WHERE email = 'ops@tuzigroup.com')
ORDER BY created_at DESC;
```

### 10.6. New device alert 메일이 너무 많이 옴

**원인**: 동적 IP 사용자 (모바일 / VPN 사용자)

**완화책**: [v1/backend/app/api/admin_auth.py](../../backend/app/api/admin_auth.py) `_is_known_device` 함수에서 IP 매칭을 subnet 기반으로 변경:

```python
# 현재: 정확 일치
stmt = stmt.where(RefreshToken.ip_address == ip)
# 개선: /24 서브넷 매칭 (PostgreSQL inet 연산자)
stmt = stmt.where(RefreshToken.ip_address.op("<<=")(f"{ip}/24"))
```

### 10.7. `SECOND_FACTOR_REQUIRED` 응답이 떨어짐

**증상**: admin이 dashboard / 다른 페이지 접근 시 backend가 `403 SECOND_FACTOR_REQUIRED` 반환, 또는 frontend가 `/settings/totp-setup`로 자동 redirect

**원인**: admin이 password는 등록했지만 TOTP / Passkey 둘 다 미등록 상태

**정상 동작입니다.** ([§6.3](#63-2fa-미등록-admin은-어디로도-갈-수-없음-강제-정책) 참조) 다음 중 하나로 해결:

1. `/settings/totp-setup`에서 TOTP 등록 + 복구 코드 보관
2. `/settings/passkeys`에서 Passkey 등록 (TouchID / FaceID / 보안 키)

기존 admin이 갑자기 이 에러를 받는다면:
```sql
-- DB 직접 조회로 상태 확인
SELECT email, totp_enabled_at,
  (SELECT count(*) FROM webauthn_credentials WHERE user_id = u.id) AS passkey_count
FROM users u WHERE role = 'admin';
```

`totp_enabled_at IS NULL` 이고 `passkey_count = 0`이면 누군가 disable했거나 키 삭제됨. [§9.3](#93-긴급-admin-강제-unlock) 참조해 복구.

### 10.8. Nginx 502 Bad Gateway

**원인**: backend / Next.js 프로세스가 죽음 또는 다른 포트에서 listening

**진단**:
```bash
# backend 살아있나?
curl http://localhost:3710/v1/health
# admin Next.js 살아있나?
curl http://localhost:3800
# frontend 살아있나?
curl http://localhost:3700

# 안 살아있으면 logs 확인
journalctl -u domo-backend -n 50
journalctl -u domo-admin -n 50

# 또는 docker compose
docker compose logs backend --tail 50
```

---

## 11. 운영자 인수인계 체크리스트

신규 admin 운영자에게 인계 시:

- [ ] 본인 이메일로 admin 계정 생성 완료 ([§6](#6-첫-admin-계정-생성))
- [ ] 첫 로그인 + 비밀번호 즉시 변경 (현재 UI 미제공 — DB 직접 또는 추후 페이지 추가 필요)
- [ ] TOTP 등록 + 폰에 시크릿 동기화 (Authy 클라우드 백업 권장)
- [ ] **복구 코드 10개를 안전한 곳 2곳에 보관** (1Password + 인쇄본 금고)
- [ ] (강력 권장) Passkey 등록 (회사 노트북 TouchID + YubiKey 보조)
- [ ] 새 디바이스 로그인 알림 메일 수신 확인
- [ ] 비상 연락처 (다른 admin / 백업 운영자) 공유
- [ ] admin URL 북마크: `https://domo-admin.tuzigroup.com`
- [ ] 2FA 미등록 시 `SECOND_FACTOR_REQUIRED` 강제 정책 인지 ([§6.3](#63-2fa-미등록-admin은-어디로도-갈-수-없음-강제-정책)) — URL 직접 입력으로 우회 불가능함 학습

### 비상 절차

| 상황 | 절차 |
|---|---|
| 폰 분실 (TOTP 접근 불가) | 복구 코드로 로그인 → /settings/passkeys 또는 /settings/recovery-codes에서 새 TOTP 등록 |
| 복구 코드도 분실 | 다른 admin이 DB 직접 unlock ([§9.3](#93-긴급-admin-강제-unlock)) |
| admin 단독 운영자가 모두 분실 | DB 직접 접근 (DBA / SRE) — production secret 필수 보관 |
| 계정 탈취 의심 | 즉시 비밀번호 변경 + TOTP 재설정 + Passkey 모두 제거 + 모든 활성 세션 revoke |

---

## 12. 다음 작업 (이 가이드 범위 외)

이번 batch에서 누락되었지만 **production 운영 시 추가 권장** 작업:

| # | 항목 | 우선순위 | 노력 |
|:--:|---|:---:|---|
| 1 | admin 비밀번호 변경 UI (`/settings/password`) | 🔴 High | 2h |
| 2 | `webauthn_challenges` 만료 cron ([§8.2](#82-만료-challenge-정리-cron-추가-todo)) | 🟡 Med | 1h |
| 3 | mock SNS provider production 차단 ([§7.5](#75-mock-sns-우회-차단-필수)) | 🟡 Med | 30m |
| 4 | KYC `toss` provider 실 구현 | 🟡 Med | 1d |
| 5 | admin 활성 세션 관리 UI (`/settings/sessions`) | 🟢 Low | 3h |
| 6 | 비밀번호 변경 시 모든 세션 자동 revoke | 🟢 Low | 1h |
| 7 | TOTP secret 회전 cron (180일) | 🟢 Low | 2h |
| 8 | Audit log (모든 admin action 추적) | 🟢 Low | 1d |

---

## 부록 A — 환경변수 종합 요약

production `.env` 최종 형태:

```env
# ============================
# Database
# ============================
POSTGRES_USER=domo_prod
POSTGRES_PASSWORD=<강력한-비밀번호>
POSTGRES_DB=domo
DATABASE_URL=postgresql+asyncpg://domo_prod:<pw>@<rds-host>:5432/domo
REDIS_URL=redis://<elasticache-host>:6379/0

# ============================
# Auth secrets
# ============================
JWT_SECRET=<openssl rand -hex 32>
TOTP_ENCRYPTION_KEY=<Fernet.generate_key()>

# ============================
# WebAuthn (도메인별 정확히 일치 필수)
# ============================
WEBAUTHN_RP_ID=domo-admin.tuzigroup.com
WEBAUTHN_RP_NAME=Domo Admin
WEBAUTHN_RP_ORIGIN=https://domo-admin.tuzigroup.com

# ============================
# Application URLs
# ============================
FRONTEND_URL=https://domo.tuzigroup.com
ADMIN_URL=https://domo-admin.tuzigroup.com
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1
EXTRA_CORS_ORIGINS=

# ============================
# External services
# ============================
GOOGLE_CLIENT_ID=<production-client-id>
GOOGLE_CLIENT_SECRET=<production-client-secret>

PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLIC_KEY=pk_live_...

STORAGE_PROVIDER=s3
S3_BUCKET=domo-prod-media
S3_REGION=ap-northeast-2
CDN_BASE_URL=https://cdn.tuzigroup.com
AWS_ACCESS_KEY_ID=<iam-access-key>
AWS_SECRET_ACCESS_KEY=<iam-secret>

EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
EMAIL_FROM_ADDRESS=no-reply@tuzigroup.com
EMAIL_FROM_NAME=Domo

# ============================
# Behavior toggles
# ============================
ENVIRONMENT=production
RATE_LIMIT_MODE=enforce
NODE_ENV=production
```

---

## 부록 B — Frontend / Admin 빌드용 .env

각 Next.js 앱은 빌드 타임 환경변수가 인라인되므로 별도 파일 필요.

### v1/admin/.env.production
```env
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1
```

### v1/frontend/.env.production
```env
NEXT_PUBLIC_API_URL=https://domo-api.tuzigroup.com/v1
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<production-client-id>
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_live_...
```

빌드:
```bash
# admin
cd v1/admin && npm run build && npm start  # 포트 3800

# frontend
cd v1/frontend && npm run build && npm start  # 포트 3700
```

PM2로 데몬화 권장:
```bash
pm2 start "npm start" --name domo-admin --cwd /path/to/v1/admin -- -p 3800
pm2 start "npm start" --name domo-frontend --cwd /path/to/v1/frontend -- -p 3700
pm2 save
pm2 startup
```

---

## 부록 C — DNS 종합 요약

```
# A 레코드 (또는 CNAME — 배포 위치에 따라)
domo-admin.tuzigroup.com    A      <server-ip>      ; admin 콘솔
domo.tuzigroup.com          A      <server-ip>      ; 사용자 frontend
domo-api.tuzigroup.com      A      <server-ip>      ; backend API
cdn.tuzigroup.com           CNAME  <cloudfront-id>  ; CDN (optional)

# Email DNS (Resend)
tuzigroup.com               TXT    "v=spf1 include:_spf.resend.com ~all"
resend._domainkey           TXT    "p=MIGfMA0GCSqGSIb3..."  ; Resend 발급값
_dmarc                      TXT    "v=DMARC1; p=none; rua=mailto:dmarc@tuzigroup.com"

# Google OAuth (DV)
# Google Cloud Console에 https://domo.tuzigroup.com 출처 등록
```

---

## 부록 D — 관련 코드 위치

| 영역 | 파일 |
|---|---|
| Admin auth API | [v1/backend/app/api/admin_auth.py](../../backend/app/api/admin_auth.py) |
| WebAuthn API | [v1/backend/app/api/admin_webauthn.py](../../backend/app/api/admin_webauthn.py) |
| Auth (`/auth/me` 등) | [v1/backend/app/api/auth.py](../../backend/app/api/auth.py) — `/me`가 admin에 `second_factor_enrolled` / `passkey_count` 노출 |
| Admin 2FA gate dep | [v1/backend/app/core/admin_deps.py](../../backend/app/core/admin_deps.py) (`require_admin_with_2fa`) |
| Crypto helpers | [v1/backend/app/core/security.py](../../backend/app/core/security.py) |
| Settings | [v1/backend/app/core/config.py](../../backend/app/core/config.py) |
| User model | [v1/backend/app/models/user.py](../../backend/app/models/user.py) |
| Recovery codes model | [v1/backend/app/models/auth_token.py](../../backend/app/models/auth_token.py) (`AdminRecoveryCode`) |
| WebAuthn models | [v1/backend/app/models/webauthn.py](../../backend/app/models/webauthn.py) |
| Migrations | [v1/backend/alembic/versions/0032~0034](../../backend/alembic/versions/) |
| Email alert template | [v1/backend/app/services/email/templates/admin_login_alert.py](../../backend/app/services/email/templates/admin_login_alert.py) |
| CORS / main | [v1/backend/app/main.py](../../backend/app/main.py) |
| Admin login page | [v1/admin/src/app/login/page.tsx](../../admin/src/app/login/page.tsx) |
| TOTP setup page | [v1/admin/src/app/settings/totp-setup/page.tsx](../../admin/src/app/settings/totp-setup/page.tsx) |
| Recovery codes page | [v1/admin/src/app/settings/recovery-codes/page.tsx](../../admin/src/app/settings/recovery-codes/page.tsx) |
| Passkeys page | [v1/admin/src/app/settings/passkeys/page.tsx](../../admin/src/app/settings/passkeys/page.tsx) |
| API client | [v1/admin/src/lib/api.ts](../../admin/src/lib/api.ts) |
| Admin Shell (사이드바) | [v1/admin/src/components/AdminShell.tsx](../../admin/src/components/AdminShell.tsx) |
