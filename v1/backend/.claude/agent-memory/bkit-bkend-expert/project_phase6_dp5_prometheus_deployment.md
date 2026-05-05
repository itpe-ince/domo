---
name: Phase 6 D'-5 Prometheus Deployment
description: D'-5 완료 — Grafana dashboard JSON 7패널, Alerting rules 5개, metrics-security.md, observability.md v0.2 Production Checklist
type: project
---

Phase 6 D'-5 prometheus-deployment 완료 (2026-05-04).

**Why:** D-6 carry-over 항목 해소 — Grafana JSON 미제공, alerting rules 가이드 없음, METRICS_TOKEN rotation policy 미정의, production-ready 검증 체크리스트 부재.

**How to apply:** 운영 배포 시 observability.md §8 Production Deployment Checklist 참조. Grafana import는 domo-dashboard.json 직접 업로드. Prometheus rules는 alerts.yml을 rule_files에 등록.

신규 생성 파일:
- `docs/operations/grafana/domo-dashboard.json` — Grafana import-ready JSON, 7 panels (non-row)
  - Panel IDs: 1(Cron Run Rate/timeseries), 2(Cron Error Count/bargauge), 3(Cron Duration p50/p95/p99/timeseries), 4(Cache Hit Rate/stat), 5(Generation p95/timeseries), 6(Notification Dispatch Rate/timeseries), 7(Tier Release Cleared Rows/timeseries)
  - UID: domo-backend-obs-v1, refresh: 30s
- `docs/operations/prometheus/alerts.yml` — 5 alerts in 4 rule groups
  - CronWorkerError (critical, for:5m), CronWorkerStalled (critical, for:10m), ShareCardCacheLow (warning, for:1h), DBConnectionFailure (critical, for:5m), NotificationDispatchHigh (info, for:10m)
- `docs/operations/metrics-security.md` — METRICS_TOKEN rotation policy + Secret Manager 패턴 + Docker Compose 격리 예시

수정 파일:
- `docs/operations/observability.md` v0.1 → v0.2 (274L)
  - §3 scrape config에 metrics-security.md 링크
  - §4 Grafana에 domo-dashboard.json 링크 + import 안내
  - §5 Alerting에 alerts.yml 링크 + rule_files 등록법
  - §8 Production Deployment Checklist (신규 섹션, 12 check items)
  - §9 Out of Scope 보강

코드 변경 없음 (pyproject.toml prometheus-client>=0.21 이미 등록 확인됨).
147 baseline tests 영향 없음.

carry-over → Phase 6+:
- /metrics 별도 포트 분리 (prometheus_client.start_http_server)
- Alertmanager 실배포 (Slack/PagerDuty webhook)
- Custom Grafana panels (작가별/리전별 analytics)
