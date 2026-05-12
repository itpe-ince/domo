# /metrics Endpoint 보안 가이드

Phase 6 D'-5 기준 (2026-05-04).

---

## 1. 개요

`GET /metrics` 엔드포인트는 Prometheus 수집 전용이며, 서비스 내부 트래픽 정보·인프라 토폴로지가 노출됩니다. 외부 공개 시 공격자에게 유용한 정보를 제공할 수 있으므로 인증 + 네트워크 격리가 필수입니다.

---

## 2. 인증 방식

### Bearer Token

```http
GET /metrics HTTP/1.1
Host: domo-api:3710
Authorization: Bearer <METRICS_TOKEN>
```

- `METRICS_TOKEN` 환경 변수로 설정
- 미설정 시 토큰 검사 생략 — **개발 환경 전용** (로컬 및 dev 브랜치)
- `METRICS_ENABLED=false` (기본값) 이면 `/metrics` 자체가 503 반환

### 환경 변수 설정 예시

```env
# production / staging
METRICS_ENABLED=true
METRICS_TOKEN=<64자 이상 cryptographically-random hex string>

# local dev (토큰 없이 수집 가능)
METRICS_ENABLED=true
# METRICS_TOKEN 미설정
```

토큰 생성 예시:

```bash
# Linux / macOS
openssl rand -hex 32
# → 64자 hex string, 256-bit entropy
```

---

## 3. 토큰 로테이션 정책

### 정기 로테이션

| 환경 | 주기 | 비고 |
|------|------|------|
| production | 분기 1회 (3개월) | 정기 배포 사이클과 연동 |
| staging | 반기 1회 (6개월) | production 로테이션 직후 |
| dev | 로테이션 불필요 | 토큰 사용 안 함 |

### 즉시 로테이션 트리거 (보안 사고)

다음 중 하나라도 발생 시 즉시 교체:

- 토큰이 코드·커밋·로그에 노출된 경우
- Secrets Manager / 환경 변수 저장소에 비인가 접근 확인
- 팀원 퇴사 또는 권한 회수
- Prometheus 서버 탈취 또는 접근 로그 이상

### 로테이션 절차

```
1. 신규 토큰 생성
   openssl rand -hex 32

2. Secret Manager / 배포 환경에 신규 값 등록
   (AWS SSM, Vault, Railway env, Render env 등)

3. Prometheus scrape config의 bearer_token 업데이트
   (prometheus.yml 또는 Prometheus Operator PrometheusRule CRD)

4. 애플리케이션 재배포 (rolling restart — downtime 없음)

5. 기존 토큰으로의 수집 실패 확인 (Prometheus targets 페이지)

6. 기존 토큰 폐기 (Secret Manager에서 삭제)
```

---

## 4. 네트워크 격리 (internal-only)

### 권장 구성

`/metrics` 엔드포인트는 Prometheus scraper와 동일 VPC 내부에서만 접근 가능하도록 설정:

| 구성 방식 | 설명 |
|-----------|------|
| **VPC 내부 전용 포트** | 메트릭 포트(3710)를 internal ALB 또는 security group으로 제한 |
| **방화벽 규칙** | 0.0.0.0:3710 DENY, Prometheus IP ALLOW |
| **Prometheus + App 동일 호스트** | Docker Compose network bridge 격리 |
| **Kubernetes NetworkPolicy** | prometheus namespace → app namespace ingress only |

### Docker Compose 예시

```yaml
# docker-compose.yml
services:
  domo-api:
    ports:
      - "8000:8000"       # public API
      # 3710 (metrics) 은 포트 바인딩 없음 → internal only
    networks:
      - internal
      - public

  prometheus:
    image: prom/prometheus:v2.51.0
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks:
      - internal             # domo-api 접근 가능
    # prometheus UI는 별도 포트 (9090) — 외부 공개 여부 별도 결정

networks:
  internal:
    driver: bridge
  public:
    driver: bridge
```

### 운영 환경 권장 — 별도 메트릭 포트

```python
# app/main.py (참고용 — 현재 미적용)
# 운영에서 Prometheus scrape 포트를 API 포트와 분리하려면:
# prometheus_client.start_http_server(port=9090)  # 별도 WSGI 서버
# FastAPI /metrics 라우트 제거
```

현재 구현은 FastAPI 라우트 (`/metrics`) 방식 — 같은 포트(8000/3710)에서 Bearer token으로 보호.
별도 포트 분리는 Phase 6+ carry-over.

---

## 5. Secret Manager 통합 패턴

### AWS Systems Manager Parameter Store

```bash
# 저장
aws ssm put-parameter \
  --name "/domo/prod/METRICS_TOKEN" \
  --value "$(openssl rand -hex 32)" \
  --type "SecureString" \
  --overwrite

# 애플리케이션에서 읽기 (배포 시 주입)
aws ssm get-parameter \
  --name "/domo/prod/METRICS_TOKEN" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text
```

### HashiCorp Vault

```bash
# 저장
vault kv put secret/domo/prod/metrics METRICS_TOKEN=$(openssl rand -hex 32)

# 읽기
vault kv get -field=METRICS_TOKEN secret/domo/prod/metrics
```

### Railway / Render / Fly.io

서비스 콘솔의 Environment Variables 탭에 직접 등록.  
GitHub Actions 사용 시 `${{ secrets.METRICS_TOKEN }}` 활용.

---

## 6. Rate Limiting

현재 Prometheus self-throttling 권장 (`scrape_interval: 30s`) — 별도 rate limiter 미설치.

| 근거 | 내용 |
|------|------|
| Prometheus 기본 scrape 간격 | 15~30s — 분당 2~4 req/IP |
| 토큰 인증 보호 | 무단 반복 요청 차단 효과 |
| 오버헤드 비용 | rate limiter 미들웨어 추가 시 정상 scrape에도 영향 |

비인가 대량 요청이 우려될 경우 nginx upstream rate limit 권장:

```nginx
limit_req_zone $binary_remote_addr zone=metrics:10m rate=10r/m;

location /metrics {
    limit_req zone=metrics burst=5 nodelay;
    proxy_pass http://domo-api:3710;
}
```

---

## 7. 체크리스트

- [ ] `METRICS_TOKEN` Secret Manager에 저장 (코드·로그에 노출 금지)
- [ ] `METRICS_ENABLED=true` production 배포 전 확인
- [ ] `/metrics` 포트 내부망 전용 firewall 설정
- [ ] Prometheus scrape config `bearer_token` 동기화
- [ ] 분기별 토큰 로테이션 캘린더 등록
- [ ] 신입 팀원 온보딩 시 Secret Manager 접근 권한 검토
