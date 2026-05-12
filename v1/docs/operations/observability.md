# Domo Observability Guide

v0.2 — Phase 6 D'-5 (2026-05-04). v0.1 Phase 5 D-6 → v0.2 Production Checklist + 링크 추가.

---

## 1. Prometheus 엔드포인트

| 항목 | 값 |
|------|-----|
| 경로 | `GET /metrics` (root app, NOT `/v1/metrics`) |
| Content-Type | `text/plain; version=0.0.4` (CONTENT_TYPE_LATEST) |
| 인증 | `Authorization: Bearer <METRICS_TOKEN>` |
| 활성화 | `METRICS_ENABLED=true` (기본: 비활성) |

### 환경 변수

```env
METRICS_ENABLED=true
METRICS_TOKEN=<secure_random_token>   # 미설정 시 토큰 검사 생략 (개발 전용)
```

### 503 응답 조건

`METRICS_ENABLED`가 `false`이거나 미설정인 경우 `503 Service Unavailable` 반환.

---

## 2. 노출 Metrics 목록

### 2.1 Cron Worker Metrics

| Metric | Type | Labels | 설명 |
|--------|------|--------|------|
| `domo_cron_runs_total` | Counter | `worker` | cron sweep 실행 횟수 |
| `domo_cron_errors_total` | Counter | `worker` | cron sweep 에러 횟수 |
| `domo_cron_rows_processed_total` | Counter | `worker` | 처리된 row 수 (worker별 정의 다름) |
| `domo_cron_duration_seconds` | Histogram | `worker` | sweep 실행 시간 (bucket: 0.01~60s) |

**Worker label 값:**

| worker | 주기 | rows_processed 의미 |
|--------|------|---------------------|
| `auction` | 300s | expired + second_chance_offered + relisted_or_ended |
| `auction_promotion` | 60s | 발송된 알림 수 (24h+6h+1h 슬롯 합산) |
| `tier_release` | 60s | 만료 처리된 early_access post 수 |
| `schedule` | 60s | 발행된 scheduled post 수 |

### 2.2 Share Card Metrics

| Metric | Type | Labels | 설명 |
|--------|------|--------|------|
| `domo_share_card_cache_hits_total` | Counter | — | 1h TTL 캐시 히트 수 |
| `domo_share_card_cache_misses_total` | Counter | — | 캐시 미스 (재생성 필요) 수 |
| `domo_share_card_generation_seconds` | Histogram | — | Pillow 합성 시간 (bucket: 0.01~5s) |

### 2.3 Notification Dispatch Metrics

| Metric | Type | Labels | 설명 |
|--------|------|--------|------|
| `domo_notification_dispatched_total` | Counter | `type` | 발송된 알림 수 |

**type label 값:** `auction_ending_24h`, `auction_ending_6h`, `auction_ending_1h`

### 2.4 Tier Release Metrics

| Metric | Type | Labels | 설명 |
|--------|------|--------|------|
| `domo_tier_release_cleared_rows_total` | Counter | — | 만료 처리된 early_access post 누적 수 |

---

## 3. Prometheus Scrape 설정 예시

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "domo-backend"
    scrape_interval: 30s
    metrics_path: /metrics
    bearer_token: "<METRICS_TOKEN>"
    static_configs:
      - targets: ["domo-api:3710"]   # or production host
    # production: add TLS config
```

토큰 보안 운영 가이드 → [metrics-security.md](metrics-security.md)

---

## 4. Grafana Dashboard 권장 패널

import-ready JSON → [grafana/domo-dashboard.json](grafana/domo-dashboard.json)

Grafana UI: Dashboards → Import → Upload JSON file → 위 파일 선택 → Prometheus datasource 매핑.

### 4.1 Cron Worker Health

```
# 패널: Cron Success Rate (5분 창)
rate(domo_cron_runs_total[5m]) - rate(domo_cron_errors_total[5m])
/ rate(domo_cron_runs_total[5m])

# 패널: Cron Error Rate by Worker
rate(domo_cron_errors_total[5m])

# 패널: Cron P95 Duration by Worker
histogram_quantile(0.95, rate(domo_cron_duration_seconds_bucket[5m]))
```

### 4.2 Share Card Cache

```
# 패널: Cache Hit Rate
rate(domo_share_card_cache_hits_total[5m])
/ (rate(domo_share_card_cache_hits_total[5m]) + rate(domo_share_card_cache_misses_total[5m]))

# 패널: Generation Latency P95
histogram_quantile(0.95, rate(domo_share_card_generation_seconds_bucket[5m]))
```

### 4.3 Notification Dispatch

```
# 패널: Notifications/min by Type
rate(domo_notification_dispatched_total[5m]) * 60
```

### 4.4 HTTP Latency (prometheus-client 기본 제공)

```
# 패널: P50 / P95 / P99 HTTP Latency
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

---

## 5. Alerting 권장

완성된 Alertmanager rules YAML → [prometheus/alerts.yml](prometheus/alerts.yml)

```yaml
# prometheus.yml — rule_files 등록
rule_files:
  - "rules/domo-alerts.yml"
```

```yaml
# alertmanager rules

- alert: CronWorkerError
  expr: increase(domo_cron_errors_total[5m]) > 0
  for: 0m
  labels:
    severity: warning
  annotations:
    summary: "Cron worker {{ $labels.worker }} encountered an error"

- alert: ShareCardCacheLow
  expr: |
    rate(domo_share_card_cache_hits_total[10m])
    / (rate(domo_share_card_cache_hits_total[10m]) + rate(domo_share_card_cache_misses_total[10m]))
    < 0.30
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Share card cache hit rate below 30% (check 1h TTL effectiveness)"

- alert: DBConnectionFailure
  expr: up{job="domo-backend"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Domo backend /metrics unreachable (DB or app down)"
```

---

## 6. Health Check 엔드포인트

| 경로 | 설명 |
|------|------|
| `GET /v1/health` | 기본 liveness (항상 200) |
| `GET /v1/health/ready` | DB 연결 확인 (200 ok / 503 unhealthy) |

`/v1/health/ready` 응답 예시:
```json
{"status": "ok", "checks": {"db": "ok"}}
{"status": "unhealthy", "checks": {"db": "error: connection refused"}}
```

---

## 7. EXPLAIN ANALYZE 게이트

`scripts/check_query_plans.sh` — 핵심 쿼리 8개의 실행 계획 검사.

```bash
# 최초 실행 (권한 부여 필요)
chmod +x scripts/check_query_plans.sh

# 실행 (alembic upgrade head 후)
DB_HOST=localhost DB_USER=domo PGPASSWORD=domo_dev_pw ./scripts/check_query_plans.sh
```

Seq Scan 발견 시 non-zero exit → CI 게이트로 사용 가능.

검사 쿼리 목록:
1. `posts.visibility_filter` — feed/explore status 필터
2. `posts.early_access_until_expiry` — tier_release worker
3. `auctions.promotion_24h_slot` — auction_promotion cron
4. `orders.expired_pending_payment` — auction settlement cron
5. `posts.scheduled_publish` — schedule worker
6. `bids.by_auction_amount_desc` — 입찰 순위 조회
7. `notifications.unread_by_user` — 미읽음 알림
8. `drafts.expired_cleanup` — draft cleanup worker

---

## 8. Production Deployment Checklist

Phase 6 D'-5 기준. 운영 환경 배포 전 항목별 확인.

### 설치 & 설정

- [ ] `prometheus-client>=0.21` pip 설치 확인
  ```bash
  pip show prometheus-client   # 또는 uv pip list | grep prometheus
  ```
- [ ] `METRICS_ENABLED=true` 환경 변수 설정
- [ ] `METRICS_TOKEN` 안전하게 생성 및 Secret Manager 저장
  ```bash
  openssl rand -hex 32   # 256-bit entropy
  ```
- [ ] Secret Manager에서 `METRICS_TOKEN` 불러와 배포 주입 (코드·로그에 직접 기입 금지)

### 네트워크 & 보안

- [ ] `/metrics` 포트 내부망(VPC) 전용 — 외부 공개 포트에서 제외
- [ ] Prometheus 서버에서 `Authorization: Bearer <METRICS_TOKEN>` 헤더 scrape 설정 완료
- [ ] 분기별 토큰 로테이션 캘린더 등록 (→ [metrics-security.md §3](metrics-security.md))

### Grafana & Alerting

- [ ] Grafana dashboard JSON import 완료 (→ [grafana/domo-dashboard.json](grafana/domo-dashboard.json))
  - Dashboards → Import → Upload JSON → Prometheus datasource 매핑
- [ ] Alerting rules YAML Prometheus에 등록 (→ [prometheus/alerts.yml](prometheus/alerts.yml))
  - `prometheus.yml` rule_files 섹션에 경로 추가 후 `prometheus --reload`

### 검증

- [ ] First scrape 성공 확인 (Prometheus UI → Status → Targets → `domo-backend` UP)
- [ ] Grafana 패널 7개 데이터 수신 확인 (No data 없음)
- [ ] Sample alert fire 검증
  ```bash
  # CronWorkerStalled 강제 트리거 테스트 (dev 환경)
  # METRICS_ENABLED=true 상태에서 cron 비활성화 10분 대기 → Prometheus alert 발생 확인
  ```
- [ ] `/v1/health/ready` 200 OK 확인 후 /metrics scrape 순서 점검

---

## 9. Out of Scope (Phase 6+ carry-over)

- **Distributed Tracing** (OpenTelemetry) — Phase 6+
- **Log Aggregation** (ELK / Grafana Loki) — 인프라 별도 구성 필요
- **Alertmanager 배포** (Slack/PagerDuty webhook) — 별도 PDCA
- **/metrics 별도 포트 분리** (prometheus_client.start_http_server) — Phase 6+
- **Custom Grafana panels** (작가별/리전별 analytics) — A 단계 analytics PDCA
