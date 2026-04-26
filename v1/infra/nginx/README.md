# Domo Nginx 설정

`/etc/nginx/sites-available/domo`로 배치되는 단일 reverse proxy 설정 파일입니다.

## 구성

| 도메인 | upstream | 용도 |
|---|---|---|
| `domo.tuzigroup.com` | `127.0.0.1:3700` | 사용자 frontend (Next.js) |
| `domo-admin.tuzigroup.com` | `127.0.0.1:3800` | Admin 콘솔 (Next.js) |
| `domo-api.tuzigroup.com` | `127.0.0.1:3710` | Backend API (FastAPI) |

3개 도메인 모두 같은 와일드카드 인증서 (`*.tuzigroup.com`)를 사용합니다.

## 설치

```bash
# 1. config 복사
sudo cp sites-available/domo.conf /etc/nginx/sites-available/domo

# 2. 활성화
sudo ln -s /etc/nginx/sites-available/domo /etc/nginx/sites-enabled/domo

# 3. 기본 사이트 비활성화 (선택)
sudo rm /etc/nginx/sites-enabled/default

# 4. 문법 검증 + 리로드
sudo nginx -t
sudo systemctl reload nginx
```

## TLS 인증서 (와일드카드)

```bash
# Cloudflare DNS 사용 시
sudo apt install -y certbot python3-certbot-dnscloudflare
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
  -d "*.tuzigroup.com" \
  -d "tuzigroup.com"

# 갱신 자동화 검증
sudo certbot renew --dry-run
```

## 핵심 설정 포인트

| 영역 | 처리 |
|---|---|
| `domo-api/.../v1/media/upload` | 1GB 업로드 + 분 단위 처리 → `client_max_body_size 1100M`, `proxy_request_buffering off`, `proxy_read_timeout 600s` |
| `domo-api/.../v1/webhooks/stripe` | Stripe HMAC 검증 위해 raw body 보존 → `proxy_request_buffering off` |
| `domo-admin` | WebAuthn/Passkey 활성화 → `Permissions-Policy: publickey-credentials-*` |
| 모든 도메인 | `_next/static/*` 30일 immutable 캐시 |
| 모든 upstream | `127.0.0.1`로만 바인드 — 외부 직접 접근 차단 |

## 트러블슈팅

가이드 [§3 HTTPS 셋업](../../../docs/guides/admin-auth-production-deployment.md#3-https-셋업)과 [§10 트러블슈팅](../../../docs/guides/admin-auth-production-deployment.md#10-흔한-실패-케이스-트러블슈팅) 참조.
