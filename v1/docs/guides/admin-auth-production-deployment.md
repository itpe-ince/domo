# Domo 운영 배포 & 관리자 인증 가이드

**범위**: Domo 서비스 (backend + frontend + admin) 의 production 배포부터 운영까지 전 과정. 관리자 인증 시스템(비밀번호 + TOTP 2FA + Recovery Codes + WebAuthn/Passkey)도 포함.
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
| 5 | PostgreSQL — `tuzi-postgres` 컨테이너 (외부 `tuzi-network` 안) | 자동 백업 활성화 — [§14.6](#146-tuzi-network--외부-의존-컨테이너) 참조 |
| 6 | Redis — `tuzi-redis` 컨테이너 (동일 네트워크) | rate limit + 세션용 |
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

## 3. HTTPS 셋업 (Nginx)

WebAuthn은 HTTPS 또는 `localhost`에서만 동작합니다. http로 접근하면 브라우저가 silent fail (콘솔 에러도 없는 경우 있음).

### 3.1. 단일 nginx config 파일 사용

3개 도메인 (frontend / admin / API) 모두를 하나의 파일로 관리합니다:

📄 **[v1/infra/nginx/sites-available/domo.conf](../../infra/nginx/sites-available/domo.conf)** — 풀 본문 + 주석

| 도메인 | upstream | 핵심 설정 |
|---|---|---|
| `domo.tuzigroup.com` | `127.0.0.1:3700` | Next.js SSR + `_next/static` 30일 캐시 |
| `domo-admin.tuzigroup.com` | `127.0.0.1:3800` | + `X-Frame-Options DENY` + `Permissions-Policy: publickey-credentials-*` (Passkey) |
| `domo-api.tuzigroup.com` | `127.0.0.1:3710` | `client_max_body_size 1100M` (1GB upload) + `/v1/media/upload`만 `proxy_request_buffering off` + Stripe webhook raw body 보존 |

### 3.2. 설치

```bash
# 1) repo에서 서버로 복사 (이미 rsync된 경우 생략)
scp v1/infra/nginx/sites-available/domo.conf \
    deploy@<DEPLOY_HOST>:/tmp/domo.conf

# 2) 서버에서 설치
ssh deploy@<DEPLOY_HOST>
sudo mv /tmp/domo.conf /etc/nginx/sites-available/domo
sudo ln -s /etc/nginx/sites-available/domo /etc/nginx/sites-enabled/domo
sudo rm -f /etc/nginx/sites-enabled/default   # 기본 사이트 비활성 (선택)

# 3) 문법 검증 + 리로드
sudo nginx -t
sudo systemctl reload nginx
```

### 3.3. TLS 인증서 (와일드카드)

3개 도메인을 별도로 발급하지 말고 wildcard 1장으로:

```bash
# Cloudflare DNS-01 challenge 사용 시
sudo apt install -y certbot python3-certbot-dnscloudflare

# Cloudflare API token (Zone:DNS:Edit) 저장
sudo tee /etc/letsencrypt/cloudflare.ini > /dev/null <<EOF
dns_cloudflare_api_token = <your-cf-api-token>
EOF
sudo chmod 600 /etc/letsencrypt/cloudflare.ini

sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d "*.tuzigroup.com" \
  -d "tuzigroup.com"
```

다른 DNS provider도 plugin 존재: `python3-certbot-dns-route53`, `python3-certbot-dns-google` 등.

발급 결과:
```
/etc/letsencrypt/live/tuzigroup.com/fullchain.pem
/etc/letsencrypt/live/tuzigroup.com/privkey.pem
```
→ domo.conf의 `ssl_certificate` 경로와 일치.

### 3.4. 인증서 자동 갱신 검증

```bash
sudo certbot renew --dry-run
sudo systemctl list-timers | grep certbot
# certbot.timer가 weekly 트리거되면 OK
```

갱신 후 nginx 자동 reload:
```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh > /dev/null <<'EOF'
#!/bin/bash
systemctl reload nginx
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

### 3.5. 핵심 결정 사항 — 왜 이 설정인가

| 결정 | 이유 |
|---|---|
| **단일 파일에 3개 server 블록** | 도메인이 모두 같은 서비스 + 같은 인증서 → 분리하면 관리 부담만 ↑ |
| `127.0.0.1`로만 upstream 바인드 | 외부에서 backend / frontend 컨테이너 직접 접근 차단 |
| `client_max_body_size 1100M` | 1GB making_video + 헤더/multipart 오버헤드 여유 |
| `proxy_request_buffering off` (업로드만) | nginx 디스크 버퍼링 → 메모리 효율 + 첫 응답 latency↓ |
| `Permissions-Policy` (admin만) | WebAuthn API 활성화 — 일부 브라우저 정책 |
| `X-Frame-Options DENY` (admin만) | clickjacking 방어. 사용자 frontend는 oEmbed 등에 iframe될 수 있어 제외 |
| `Cache-Control immutable` (`_next/static`) | Next.js의 hash-named 파일 → 영구 캐시 안전 |
| Stripe webhook `proxy_request_buffering off` | HMAC signature가 raw body 기준 → 변형 금지 |

상세 주석은 [domo.conf](../../infra/nginx/sites-available/domo.conf) 인라인 참조.

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
# tuzi-postgres 컨테이너에서 직접 dump (host에서 실행)
docker exec tuzi-postgres pg_dump -U domo -F c domo > domo-pre-admin-auth.dump
# 또는 외부 host에서 (도커 외부 접근 가능 시):
# pg_dump -h <host> -U domo -d domo -F c -f domo-pre-admin-auth.dump
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

## 13. CI/CD 파이프라인 (GitHub Actions)

### 13.1. 아키텍처

```
┌─────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│  git push   │───▶│ GitHub Actions       │───▶│ Production Server   │
│  to main    │    │  ① Build 3 images    │    │  (Tailscale + SSH)  │
│  or v* tag  │    │  ② Push to GHCR      │    │  - .env (운영자 관리)│
└─────────────┘    │  ③ Verify 6 secrets  │    │  - docker pull      │
                   │  ④ Tailscale connect │    │  - alembic upgrade  │
                   │  ⑤ SSH deploy        │    │  - compose up -d    │
                   │  ⑥ Health check      │    │  - health verify    │
                   └──────────────────────┘    └──────────┬──────────┘
                                                          │
                                                          ▼
                                  ┌──────────────────────────────────────┐
                                  │ Nginx (TLS terminate, 와일드카드 cert)│
                                  │  ├ :3700 → domo_frontend             │
                                  │  ├ :3710 → domo_backend              │
                                  │  └ :3800 → domo_admin                │
                                  └────────────────┬─────────────────────┘
                                                   │  (host에서 127.0.0.1 바인드)
                                                   ▼
                                  ┌──────────────────────────────────────┐
                                  │ docker network: tuzi-network         │
                                  │  ├ domo_backend  (FastAPI)           │
                                  │  ├ domo_frontend (Next.js)           │
                                  │  ├ domo_admin    (Next.js)           │
                                  │  ├ tuzi-postgres ◀ DATABASE_URL host │
                                  │  └ tuzi-redis    ◀ REDIS_URL host    │
                                  └──────────────────────────────────────┘
```

**핵심**: Postgres / Redis는 **Domo가 자체적으로 띄우지 않고**, 같은 host의 다른 서비스들과 공유하는 외부 컨테이너 (`tuzi-postgres`, `tuzi-redis`)를 [tuzi-network](../../docker-compose.prod.yml) 통해 사용합니다. 자세히는 [§14.6](#146-tuzi-network--외부-의존-컨테이너).

**핵심 결정**:
- **이미지 3개 분리 빌드** (backend/frontend/admin) — 변경 없는 컴포넌트는 캐시 hit
- **GHCR 사용** — GitHub와 통합, 추가 무료 (퍼블릭/private 모두), Docker Hub rate limit 회피
- **Tailscale VPN** — production 서버를 공인 IP로 노출하지 않음. SSH 포트도 닫음
- **DB 마이그레이션은 새 컨테이너 기동 전** — 스키마-앱 호환성 유지
- **`.env`는 서버 영구 보관 (패턴 B)** — workflow는 절대 안 건드림. 운영자가 SSH로 직접 관리. 자세히는 [§15](#15-secret-관리--패턴-b-서버-env--github은-배포-인프라만)

### 13.2. Tailscale VPN 셋업

**왜 Tailscale인가**:
- Production 서버를 공인 IP에 SSH 노출 = brute force 공격 표적
- VPN으로 격리하면 관리자/CI만 접근 가능
- Tailscale은 WireGuard 기반 zero-config VPN — 서버 + GitHub Actions runner 양쪽에 설치만 하면 동작

#### Step 1 — Tailscale 계정 + tailnet 생성
1. https://login.tailscale.com 가입 (Google/MS/GitHub 계정)
2. 무료 plan으로 시작 (개인은 100 device까지)
3. Admin Console → Settings → General → tailnet 이름 확인 (예: `tuzigroup.ts.net`)

#### Step 2 — Production 서버에 Tailscale 설치
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --advertise-tags=tag:prod

# 출력된 https://login.tailscale.com/a/... URL 클릭해서 인증
```

설치 후:
```bash
tailscale ip -4
# 출력: 100.x.x.x (Tailscale 100.64.0.0/10 대역)
```
이 IP가 `DEPLOY_HOST` GitHub secret 값.

#### Step 3 — GitHub Actions용 OAuth client 발급
1. Tailscale Admin Console → Settings → OAuth clients → Generate OAuth client
2. **Scopes**: `Devices > Read`, `Auth Keys > Write`
3. **Tags**: `tag:ci` (반드시 ACL에 정의되어 있어야 함 — 다음 step)
4. 생성된 `Client ID` + `Client Secret` 저장 → GitHub secrets `TS_OAUTH_CLIENT_ID`, `TS_OAUTH_SECRET`

#### Step 4 — Tailscale ACL 설정
Admin Console → Access Controls → 다음 추가:
```jsonc
{
  "tagOwners": {
    "tag:prod": ["autogroup:admin"],
    "tag:ci": ["autogroup:admin"]
  },
  "acls": [
    // CI runners (tag:ci) → production server (tag:prod) SSH/HTTP만 허용
    {
      "action": "accept",
      "src": ["tag:ci"],
      "dst": ["tag:prod:22", "tag:prod:3710", "tag:prod:3700", "tag:prod:3800"]
    },
    // Admin (사용자) → production server 전체
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["tag:prod:*"]
    }
  ],
  "ssh": [
    {
      "action": "accept",
      "src": ["autogroup:admin"],
      "dst": ["tag:prod"],
      "users": ["root", "deploy"]
    }
  ]
}
```

#### Step 5 — 검증
GitHub Actions runner에서 Tailscale 연결 후 production 서버 ping:
```yaml
- uses: tailscale/github-action@v2
  with:
    oauth-client-id: ${{ secrets.TS_OAUTH_CLIENT_ID }}
    oauth-secret: ${{ secrets.TS_OAUTH_SECRET }}
    tags: tag:ci
- run: ping -c 3 ${{ secrets.DEPLOY_HOST }}
```

### 13.3. 워크플로우 파일

[.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml) 가 production-ready 버전입니다. 주요 단계:

| Job | 역할 | 트리거 |
|---|---|---|
| **build** | backend / frontend / admin 3개 이미지를 matrix 빌드 → GHCR push | 항상 |
| **verify-secrets** | 11개 필수 secret 존재 여부 검증 (누락 시 cryptic 에러 방지) | build 후 |
| **deploy** | Tailscale 연결 → SSH → compose pull → alembic → up → health check | verify-secrets 후 |

전체 워크플로우 yaml 본문은 **부록 E** 참조.

### 13.4. 배포 트리거 방식

| 방식 | 동작 |
|---|---|
| `git push origin main` (with `v1/**` 변경) | 자동 빌드 + 배포, 이미지 태그 = `<commit-sha>` 첫 7자 |
| `git tag v1.2.3 && git push --tags` | 자동 빌드 + 배포, 이미지 태그 = `v1.2.3` |
| GitHub UI → Actions → Run workflow | 수동 트리거, `tag` input으로 특정 버전 강제 배포 가능 |
| 수동 + `skip_migration=true` | 비상시 alembic 건너뛰고 코드만 배포 |

### 13.5. Rollback

세 가지 방법:

**A. 이전 이미지 태그로 재배포 (가장 안전)**
```
GitHub Actions → Run workflow → tag = "v1.2.2" (직전 태그)
```

**B. SSH로 직접 docker compose 명령**
```bash
ssh deploy@<DEPLOY_HOST>
cd <DEPLOY_PATH>     # GitHub secret DEPLOY_PATH 값
IMAGE_TAG=v1.2.2 docker compose -f docker-compose.prod.yml pull
IMAGE_TAG=v1.2.2 docker compose -f docker-compose.prod.yml up -d
```

**C. 코드 + DB 동시 롤백 (마이그레이션 포함)**
```bash
# 1) DB 먼저 downgrade
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1

# 2) 이전 이미지로 컨테이너 재기동
IMAGE_TAG=v1.2.2 docker compose -f docker-compose.prod.yml up -d
```
⚠️ DB downgrade는 데이터 손실 가능성 있으므로 사전에 `pg_dump` 백업 필수.

---

## 14. 서버 사전 준비 (Bare metal / EC2)

배포 전 production 서버에 한 번만 수행:

### 14.1. OS + 사용자

```bash
# Ubuntu 22.04 LTS 가정. 다른 배포판은 적절히 변경.

# 1) deploy 전용 사용자 생성 (root 직접 SSH 금지)
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG sudo deploy

# 2) SSH 키 등록 (GitHub Actions이 사용할 deploy_key)
sudo -u deploy mkdir -p /home/deploy/.ssh
sudo -u deploy chmod 700 /home/deploy/.ssh
# GitHub Actions secret DEPLOY_SSH_KEY와 짝이 되는 공개키를 등록
echo "ssh-ed25519 AAAA..." | sudo -u deploy tee /home/deploy/.ssh/authorized_keys
sudo -u deploy chmod 600 /home/deploy/.ssh/authorized_keys

# 3) SSH config 강화 (선택)
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### 14.2. Docker 설치

```bash
# Docker CE + compose v2 (공식 스크립트)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
# 새 그룹 적용을 위해 재로그인 필요
```

### 14.3. 디렉토리 구조

```bash
# 아래 경로는 예시. 본인이 GitHub secret `DEPLOY_PATH`로 등록한 값 사용.
DEPLOY_PATH=/opt/domo/v1     # ← 예시값. 다른 경로 가능
sudo mkdir -p "$DEPLOY_PATH"
sudo chown -R deploy:deploy "$(dirname $DEPLOY_PATH)"
```

⚠️ 이 경로는 **GitHub secret `DEPLOY_PATH`로 등록한 값과 정확히 일치**해야 합니다. 가이드 본문에서는 일관성을 위해 `/opt/domo/v1` 예시를 사용하지만, 본인이 등록한 값으로 치환하세요.

배포 후 디렉토리 (예시 `DEPLOY_PATH=/opt/domo/v1`):
```
$DEPLOY_PATH/
├── docker-compose.prod.yml    ← workflow가 rsync
├── alembic.ini                ← workflow가 rsync (migration 실행용)
├── alembic/                   ← workflow가 rsync
└── .env                       ← 운영자가 한 번 만들고 직접 관리 (§15.3)
```

### 14.4. 방화벽

```bash
sudo ufw allow OpenSSH        # 또는 Tailscale ACL에서 처리하면 닫아도 됨
sudo ufw allow 80/tcp         # Nginx HTTP (Let's Encrypt challenge)
sudo ufw allow 443/tcp        # Nginx HTTPS
sudo ufw enable

# 백엔드 포트 (3700/3710/3800)는 절대 공인 노출 금지
# 위 docker-compose.prod.yml이 127.0.0.1:port로 바인드하므로 외부 접근 불가
```

### 14.5. PostgreSQL 클라이언트 (옵션 — 디버깅용)

```bash
sudo apt install -y postgresql-client
# 이후 deploy 사용자에서:
docker exec -it tuzi-postgres psql -U domo -d domo -c '\d users'
```

### 14.6. `tuzi-network` + 외부 의존 컨테이너

Domo의 [docker-compose.prod.yml](../../docker-compose.prod.yml)은 **Postgres와 Redis를 자체적으로 띄우지 않습니다**. 같은 host의 다른 서비스들(LLM Gateway, vzen, sodapop 등)과 공유하는 외부 네트워크 `tuzi-network` 안의 `tuzi-postgres` / `tuzi-redis` 컨테이너를 사용합니다.

#### 사전 확인

```bash
# 1) 네트워크 존재 확인
docker network ls | grep tuzi-network
# 없으면 생성:
docker network create tuzi-network

# 2) 의존 컨테이너가 떠있는지
docker ps --filter "name=tuzi-postgres" --filter "name=tuzi-redis" \
  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
# 둘 다 Up 상태여야 함

# 3) 같은 네트워크에 있는지
docker network inspect tuzi-network | jq -r '.[].Containers[].Name'
# tuzi-postgres, tuzi-redis 둘 다 보여야 함
```

#### 새로 셋업하는 경우 (참고)

만약 host에 Postgres/Redis 컨테이너가 없다면 한 번 셋업:

```bash
# Postgres
docker run -d --name tuzi-postgres \
  --network tuzi-network \
  --restart unless-stopped \
  -e POSTGRES_PASSWORD=<강력한-비밀번호> \
  -v tuzi_postgres_data:/var/lib/postgresql/data \
  -p 127.0.0.1:5432:5432 \
  postgres:16-alpine

# Redis
docker run -d --name tuzi-redis \
  --network tuzi-network \
  --restart unless-stopped \
  -v tuzi_redis_data:/data \
  -p 127.0.0.1:6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru

# Domo용 DB / 사용자 생성
docker exec -it tuzi-postgres psql -U postgres <<EOF
CREATE USER domo WITH PASSWORD '<DB-비밀번호>';
CREATE DATABASE domo OWNER domo;
GRANT ALL PRIVILEGES ON DATABASE domo TO domo;
EOF
```

#### .env 연결 문자열

`tuzi-network` 내부에서는 컨테이너명이 DNS 이름으로 해석됩니다:

```env
DATABASE_URL=postgresql+asyncpg://domo:<pw>@tuzi-postgres:5432/domo
REDIS_URL=redis://tuzi-redis:6379/0
```

→ `localhost`나 IP가 아니라 **컨테이너명**을 host로 사용. backend 컨테이너가 `tuzi-network`에 join되어 있어야 동작.

#### 검증

backend 배포 후:
```bash
# DB 연결 테스트
docker exec domo_backend python -c "
import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
async def t():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text('SELECT current_database(), current_user'))
        print('DB:', r.first())
asyncio.run(t())
"

# Redis 연결 테스트
docker exec domo_backend python -c "
import asyncio
from app.core.redis_client import get_redis
async def t():
    r = await get_redis()
    await r.set('domo:healthcheck', 'ok')
    print('Redis:', await r.get('domo:healthcheck'))
asyncio.run(t())
"
```

### 14.7. systemd 자동 시작 (선택)

서버 재부팅 시 docker compose가 자동 기동되도록:
```bash
sudo tee /etc/systemd/system/domo.service > /dev/null <<EOF
[Unit]
Description=Domo (docker compose)
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
# WorkingDirectory는 절대경로 필요 — 본인의 DEPLOY_PATH 값으로 치환
WorkingDirectory=/opt/domo/v1
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
User=deploy
Group=deploy

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable domo.service
```

⚠️ docker compose 자체의 `restart: unless-stopped`로도 충분한 경우가 많음. systemd unit은 host 재부팅 후 자동 기동만 보장.

---

## 15. Secret 관리 — 패턴 B (서버 .env + GitHub은 배포 인프라만)

Domo는 **GitHub Secrets에 앱 환경변수를 두지 않고**, production 서버의 `$DEPLOY_PATH/.env` (= GitHub secret `DEPLOY_PATH`로 등록한 디렉토리 안의 .env)에 영구 저장하는 패턴을 사용합니다. GitHub은 Tailscale + SSH 같은 **배포 인프라 secret만** 가집니다.

### 15.1. 왜 패턴 B인가

| 비교 | 패턴 A (전체 GitHub) | **패턴 B (서버 .env)** ⭐ |
|---|---|---|
| GitHub secret 개수 | 18+ | **6개** |
| 환경변수 변경 | GitHub UI → workflow 재실행 | SSH → `vi .env` → `compose up -d` |
| 운영자 인지부담 | 높음 (무엇이 어디에) | 낮음 (.env 한 파일) |
| Secret 유출 risk | GitHub 침해 시 | 서버 침해 시 (chmod 600 + Tailscale 격리) |
| 외부 서비스 회전 | secret 업데이트 → 재배포 | SSH로 .env edit → `up -d` |
| 적합 규모 | 다중 환경 + 자동 회전 | **소규모 단일 서버** |

→ Domo의 1인 운영 + tuzi 단일 서버 환경에는 패턴 B가 자연스럽습니다.

### 15.2. GitHub Secrets — 6개만

GitHub repo → **Settings → Secrets and variables → Actions → Secrets** 에 등록:

| 이름 | 용도 | 발급 / 예시 |
|---|---|---|
| `TS_OAUTH_CLIENT_ID` | Tailscale GitHub Action 인증 | Tailscale Admin → OAuth clients |
| `TS_OAUTH_SECRET` | 동일 | 동일 |
| `DEPLOY_HOST` | Production 서버 Tailscale IP | `tailscale ip -4` 출력 (예: `100.64.10.20`) |
| `DEPLOY_USER` | SSH 사용자 | `deploy` |
| `DEPLOY_PATH` | 서버 내 배포 디렉토리 | `/opt/domo/v1` |
| `DEPLOY_SSH_KEY` | deploy 사용자의 SSH private key | `ssh-keygen -t ed25519 -f /tmp/domo_deploy -N ""` 후 `cat /tmp/domo_deploy` |

**그 외 Variables 등록 불필요** — 모든 앱 설정은 서버 .env에서 관리.

### 15.3. 서버 `.env` — 첫 셋업 (한 번만)

배포가 처음 동작하려면 서버에 `.env`가 있어야 합니다 (workflow가 `if [ ! -f .env ]`로 체크 → 없으면 실패).

`<DEPLOY_PATH>`는 GitHub secret으로 등록한 경로 (예: `/opt/domo/v1`):

```bash
ssh deploy@<DEPLOY_HOST>

# 본인이 등록한 DEPLOY_PATH 값으로 치환
DEPLOY_PATH=/opt/domo/v1

# 디렉토리가 없으면 먼저
sudo mkdir -p "$DEPLOY_PATH"
sudo chown deploy:deploy "$DEPLOY_PATH"
cd "$DEPLOY_PATH"

# .env 작성 — 아래는 템플릿. 실제 값으로 채우세요.
cat > .env <<'EOF'
ENVIRONMENT=production
NODE_ENV=production

# ── Database / Cache (외부 tuzi-network 컨테이너) ──
DATABASE_URL=postgresql+asyncpg://domo:<강력한-비밀번호>@tuzi-postgres:5432/domo
REDIS_URL=redis://tuzi-redis:6379/0

# ── Auth secrets ──
# 발급: openssl rand -hex 32
JWT_SECRET=<발급값>
# 발급: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOTP_ENCRYPTION_KEY=<발급값>

# ── WebAuthn ──
WEBAUTHN_RP_ID=domo-admin.tuzigroup.com
WEBAUTHN_RP_NAME=Domo Admin
WEBAUTHN_RP_ORIGIN=https://domo-admin.tuzigroup.com

# ── URLs ──
API_URL=https://domo-api.tuzigroup.com/v1
FRONTEND_URL=https://domo.tuzigroup.com
ADMIN_URL=https://domo-admin.tuzigroup.com
EXTRA_CORS_ORIGINS=

# ── Google OAuth (사용자 SNS — admin은 차단) ──
GOOGLE_CLIENT_ID=<production용>
GOOGLE_CLIENT_SECRET=<production용>

# ── Stripe (Phase 2 이후) ──
PAYMENT_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLIC_KEY=pk_live_...

# ── Storage (S3) ──
STORAGE_PROVIDER=s3
S3_BUCKET=domo-prod-media
S3_REGION=ap-northeast-2
CDN_BASE_URL=https://cdn.tuzigroup.com
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# ── Email ──
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_...
EMAIL_FROM_ADDRESS=no-reply@tuzigroup.com
EMAIL_FROM_NAME=Domo

# ── Behavior ──
RATE_LIMIT_MODE=enforce
EOF

# 권한 강화 — deploy 사용자만 읽기 가능
chmod 600 .env
ls -la .env       # -rw------- 1 deploy deploy ... 확인
```

⚠️ **이 파일은 workflow가 절대 덮어쓰지 않습니다** ([deploy.yml](../../../.github/workflows/deploy.yml)에 `.env` 생성 코드 없음). 운영자가 SSH로 직접 관리.

### 15.4. 환경변수 변경 (운영 중)

```bash
ssh deploy@<DEPLOY_HOST>
cd <DEPLOY_PATH>     # GitHub secret DEPLOY_PATH 값
vi .env              # 값 수정

# 변경 즉시 적용
docker compose -f docker-compose.prod.yml up -d --force-recreate
# 또는 특정 서비스만:
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
```

⚠️ `docker compose restart`만으로는 **새 .env가 적용 안 됩니다**. `up -d --force-recreate`가 컨테이너 재생성 + .env 재로드.

### 15.5. Secret 회전 절차

#### `JWT_SECRET` (6개월 권장)
```bash
NEW_SECRET=$(openssl rand -hex 32)
ssh deploy@<DEPLOY_HOST>
cd <DEPLOY_PATH>
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${NEW_SECRET}|" .env
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
# ⚠️ 모든 활성 admin/user 세션 무효화됨 — 사전 공지 필요
```

#### `TOTP_ENCRYPTION_KEY` (유출 시만)
```bash
# ⚠️ 회전하면 기존 admin의 TOTP secret을 복호화 못 함 → 모든 admin TOTP 재등록 필요
# 사전에 admin들에게 안내 + 회전 직후 admin이 /settings/totp-setup에서 재등록
```

#### `STRIPE_SECRET_KEY`
1. Stripe Dashboard → 새 secret 발급 (구 키 자동 비활성 안 됨)
2. 서버 `.env` 업데이트 → `up -d --force-recreate backend`
3. 1주일 모니터링 (구 키로 들어오는 요청 없는지 Stripe 로그)
4. Stripe Dashboard에서 구 키 폐기

#### `DEPLOY_SSH_KEY` (1년)
```bash
# 1) 새 키 생성
ssh-keygen -t ed25519 -f /tmp/domo_deploy_new -N ""

# 2) 새 공개키를 서버에 추가 (구 키 일단 유지 — rollback 대비)
cat /tmp/domo_deploy_new.pub | ssh deploy@<DEPLOY_HOST> \
  "cat >> ~/.ssh/authorized_keys"

# 3) GitHub secret 업데이트
gh secret set DEPLOY_SSH_KEY < /tmp/domo_deploy_new

# 4) workflow_dispatch로 새 키 정상 동작 검증

# 5) 구 공개키 제거
ssh deploy@<DEPLOY_HOST> "vi ~/.ssh/authorized_keys"
```

### 15.6. 등록 자동화 (gh CLI) — 6개

```bash
# 한 줄씩 — secret은 git history / shell history에 안 남게 stdin 사용
echo "tskey-client-..." | gh secret set TS_OAUTH_CLIENT_ID
echo "tskey-..."        | gh secret set TS_OAUTH_SECRET
echo "100.64.10.20"     | gh secret set DEPLOY_HOST
echo "deploy"           | gh secret set DEPLOY_USER
echo "/opt/domo/v1"     | gh secret set DEPLOY_PATH    # 본인이 사용할 경로로 치환
gh secret set DEPLOY_SSH_KEY < /tmp/domo_deploy
```

### 15.7. Sensitive vs Non-sensitive 구분 (참고)

서버 .env 안에서도 보안 등급은 다릅니다 — 백업/스냅샷에서 분리해 보관할 가치:

| 등급 | 변수 | 처리 |
|---|---|---|
| 🔴 Critical | `JWT_SECRET`, `TOTP_ENCRYPTION_KEY`, `DATABASE_URL` (pw 포함), `STRIPE_SECRET_KEY` | 서버 .env + 1Password 별도 백업 |
| 🟡 High | `GOOGLE_CLIENT_SECRET`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY`, `AWS_*_KEY` | 서버 .env |
| 🟢 Low | `GOOGLE_CLIENT_ID`, `STRIPE_PUBLIC_KEY`, URL, 도메인 | 평문 OK |

---

## 16. 운영 모니터링 — 배포 이후 일상

### 16.1. 로그 확인

```bash
# 컨테이너 로그
ssh deploy@<DEPLOY_HOST>
cd <DEPLOY_PATH>     # GitHub secret DEPLOY_PATH 값
docker compose -f docker-compose.prod.yml logs -f backend --tail 200
docker compose -f docker-compose.prod.yml logs -f admin --tail 100

# 특정 키워드만
docker compose -f docker-compose.prod.yml logs backend | grep -E "ERROR|admin_login_alert|SECOND_FACTOR"

# 모든 서비스
docker compose -f docker-compose.prod.yml logs --tail 50 -f
```

### 16.2. 이미지 / 디스크 사용량

```bash
docker system df
docker images
# 오래된 이미지 정리 (배포 워크플로우의 prune이 처리하지만 수동도 가능)
docker image prune -a --filter "until=72h"
```

### 16.3. 컨테이너 재시작 (수동)

```bash
# 단일 서비스만
docker compose -f docker-compose.prod.yml restart backend

# 새 .env 적용 + 전체 재시작 (WebAuthn RP_ID 등 변경 시)
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### 16.4. 배포 실패 시 진단 순서

| 단계 | 확인 |
|---|---|
| 1 | GitHub Actions 로그 — 어느 job/step에서 실패? |
| 2 | Build 실패: Dockerfile 문법 / 의존성 / 타임아웃 |
| 3 | Verify-secrets 실패: 6개 deploy-infra secret 중 누락 → 등록 |
| 4 | Tailscale 실패: OAuth client 만료 / ACL `tag:ci` 누락 |
| 5 | SSH 실패: `DEPLOY_SSH_KEY` 형식 / `authorized_keys` 등록 / SSH port 차단 |
| 6 | **`.env not found`**: 서버 `$DEPLOY_PATH/.env`가 없음 → [§15.3](#153-서버-env--첫-셋업-한-번만) 따라 한 번 셋업 |
| 7 | Compose pull 실패: GHCR 인증 (`GITHUB_TOKEN` packages: read 권한) |
| 8 | Compose up 실패 — `network tuzi-network not found`: [§14.6](#146-tuzi-network--외부-의존-컨테이너)의 `docker network create tuzi-network` 누락 |
| 9 | Migration 실패: alembic conflict / DB 권한 / 백업 후 수동 fix → DB host가 `tuzi-postgres`인지 ([§16.4.1](#1641-네트워크--외부-컨테이너-진단)) |
| 10 | Health check 실패: backend 컨테이너 로그 직접 확인 |

#### 16.4.1. 네트워크 / 외부 컨테이너 진단

backend가 떴는데 `/v1/health`가 500이면 대부분 DB/Redis 연결 실패:

```bash
# 1) backend가 tuzi-network에 join되어 있나
docker inspect domo_backend --format '{{json .NetworkSettings.Networks}}' | jq
# "tuzi-network" 키 보여야 함

# 2) 같은 네트워크에서 DB / Redis 컨테이너로 핑
docker exec domo_backend getent hosts tuzi-postgres
docker exec domo_backend getent hosts tuzi-redis
# IP 주소 출력되면 DNS 해석 OK

# 3) Postgres 포트 reachable
docker exec domo_backend python -c "
import socket
s = socket.socket(); s.settimeout(3)
s.connect(('tuzi-postgres', 5432))
print('Postgres port reachable')
"

# 4) backend 컨테이너 로그
docker logs domo_backend --tail 50 | grep -iE "error|connection|refused"
```

**자주 나오는 에러 → 원인 매핑**:

| 에러 메시지 | 원인 | 해결 |
|---|---|---|
| `network tuzi-network not found` | 네트워크 미생성 | `docker network create tuzi-network` |
| `could not translate host name "tuzi-postgres"` | backend가 tuzi-network에 미연결 | compose의 `networks: [tuzi-network]` 누락 |
| `connection refused tuzi-postgres:5432` | tuzi-postgres 컨테이너 down | `docker start tuzi-postgres` |
| `password authentication failed` | DATABASE_URL의 user/pw 틀림 | GitHub secret 재확인 |
| `database "domo" does not exist` | DB 미생성 | [§14.6](#146-tuzi-network--외부-의존-컨테이너)의 `CREATE DATABASE` 단계 누락 |

### 16.5. 자주 쓰는 운영 SQL

```sql
-- admin 계정 상태
SELECT email, totp_enabled_at, failed_login_count, locked_until,
  (SELECT count(*) FROM webauthn_credentials WHERE user_id = u.id) AS passkeys
FROM users u WHERE role = 'admin';

-- 최근 1시간 admin 로그인 시도
SELECT u.email, rt.issued_at, rt.user_agent, rt.ip_address
FROM refresh_tokens rt JOIN users u ON u.id = rt.user_id
WHERE u.role = 'admin' AND rt.issued_at > NOW() - INTERVAL '1 hour'
ORDER BY rt.issued_at DESC;

-- 최근 1일 결제 실패
SELECT id, buyer_id, amount, status, created_at
FROM orders
WHERE status IN ('payment_failed', 'cancelled') AND created_at > NOW() - INTERVAL '1 day';
```

### 16.6. 알림 채널 권장 (Slack/Discord webhook)

GitHub Actions이 배포 결과를 알림으로 보내고 싶다면 마지막 step에 추가:
```yaml
- name: Notify Slack
  if: always()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {"text": "Domo deploy ${{ job.status }}: ${{ needs.build.outputs.image_tag }}"}
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 부록 A — 환경변수 종합 요약

> 패턴 B에서는 이 `.env`가 **서버에 영구 보관**됩니다 ([§15.3](#153-서버-env--첫-셋업-한-번만)). GitHub에 등록 X, workflow가 덮어쓰지 않음.

`$DEPLOY_PATH/.env` (예: `/opt/domo/v1/.env`) 최종 형태:

```env
# ============================
# Database / Cache
# ============================
# 외부 tuzi-network에 이미 떠있는 컨테이너를 host로 사용 (자세히는 §14.6)
DATABASE_URL=postgresql+asyncpg://<user>:<pw>@tuzi-postgres:5432/<db>
REDIS_URL=redis://tuzi-redis:6379/0

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

---

## 부록 E — CI/CD 파일 위치

배포 자동화 관련 파일:

| 파일 | 역할 |
|---|---|
| [.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml) | Build (matrix) → Verify secrets → Tailscale → SSH deploy → Health check |
| [v1/docker-compose.prod.yml](../../docker-compose.prod.yml) | Production compose — GHCR 이미지 사용, .env는 workflow가 매번 재생성 |
| [v1/backend/Dockerfile](../../backend/Dockerfile) | Backend 이미지 (FastAPI + alembic) |
| [v1/frontend/Dockerfile](../../frontend/Dockerfile) | Frontend Next.js standalone 빌드 (없으면 추가 필요) |
| [v1/admin/Dockerfile](../../admin/Dockerfile) | Admin Next.js standalone 빌드 (없으면 추가 필요) |

⚠️ **주의**: frontend / admin 의 Dockerfile이 아직 없을 수 있습니다. Next.js standalone 빌드 표준 Dockerfile 템플릿:

```dockerfile
# v1/frontend/Dockerfile (또는 v1/admin/Dockerfile)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

→ next.config.mjs에 `output: "standalone"` 설정 필수 (이미 둘 다 적용됨, [v1/frontend/next.config.mjs](../../frontend/next.config.mjs), [v1/admin/next.config.mjs](../../admin/next.config.mjs)).

⚠️ **`public/` 디렉토리 존재 필수** — `COPY --from=builder /app/public ./public`이 폴더가 없으면 `not found` 에러로 빌드 실패. 빈 폴더라도 OK이므로 `.gitkeep` 하나 두세요:
```bash
mkdir -p v1/admin/public v1/frontend/public
touch v1/admin/public/.gitkeep v1/frontend/public/.gitkeep
```

---

## 부록 F — 첫 배포 체크리스트

**처음 production 배포 시** 다음을 순서대로 한 번씩 수행:

- [ ] DNS 레코드 3개 발급 ([§0.1](#01-dns-설정-예시))
- [ ] 와일드카드 TLS 인증서 발급 ([§0.2](#02-tls-인증서--와일드카드-권장))
- [ ] `tuzi-network` 도커 네트워크 생성 + `tuzi-postgres` / `tuzi-redis` 컨테이너 셋업 ([§14.6](#146-tuzi-network--외부-의존-컨테이너))
- [ ] Domo용 DB 사용자 + database 생성 (Postgres 컨테이너 내부에서)
- [ ] Tailscale 가입 + 서버에 설치 + tailnet ACL 설정 ([§13.2](#132-tailscale-vpn-셋업))
- [ ] Production 서버 deploy 사용자 + Docker 설치 ([§14](#14-서버-사전-준비-bare-metal--ec2))
- [ ] SSH 키페어 생성 → 서버 `authorized_keys` 등록 → private key는 `DEPLOY_SSH_KEY` secret으로
- [ ] GitHub repo Settings에 **Secrets 6개 등록** (deploy-infra만 — [§15.2](#152-github-secrets--6개만)) ✅ 이미 완료됨
- [ ] **서버 `$DEPLOY_PATH/.env` 첫 셋업** (DEPLOY_PATH는 GitHub secret 값 — [§15.3](#153-서버-env--첫-셋업-한-번만))
- [ ] Frontend / Admin Dockerfile 추가 (없을 경우 — [부록 E](#부록-e--cicd-파일-위치))
- [ ] Nginx 설정 3개 + 활성화 ([§3](#3-https-셋업))
- [ ] DB 마이그레이션 (수동 1회 — workflow가 두 번째부터 자동) — `psql` 또는 `alembic upgrade head`
- [ ] 첫 admin 계정 생성 ([§6.1](#61-cli로-admin-생성))
- [ ] `git push origin main` 또는 GitHub Actions UI에서 workflow_dispatch
- [ ] Build → Verify → Deploy → Health check 모두 ✅ 확인
- [ ] 브라우저로 `https://domo-admin.tuzigroup.com/login` 접속 → 첫 admin 로그인
- [ ] TOTP 등록 + 복구 코드 안전한 곳에 보관 ([§6.2](#62-첫-로그인-흐름))
- [ ] (강력 권장) Passkey 등록
- [ ] [§7 운영 시작 직후 체크리스트](#7-운영-시작-직후-체크리스트) 모두 ✓
- [ ] KYC enforcement `enforce`로 전환 ([§7.3](#73-kyc-enforcement-활성화))
- [ ] 다음 배포부터는 `git push` 만으로 자동 배포
