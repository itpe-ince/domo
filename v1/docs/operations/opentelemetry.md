# OpenTelemetry Tracing — Production Deployment Guide

**Feature**: G''-1 opentelemetry-tracing  
**Backend**: FastAPI + SQLAlchemy + httpx + asyncio  
**Target**: AWS X-Ray via ADOT (AWS Distro for OpenTelemetry) Collector sidecar

---

## Architecture Overview

```
domo-backend (FastAPI)
  │
  │ OTLP gRPC (localhost:4317)
  ▼
ADOT Collector sidecar (ECS task)
  │
  │ AWS X-Ray API (PutTraceSegments)
  ▼
AWS X-Ray Service Map / Trace Explorer
```

The backend SDK is **vendor-agnostic** (standard OpenTelemetry protocol). The
ADOT Collector handles X-Ray conversion. Swapping to Jaeger or Grafana Tempo
in future requires only changing `OTEL_OTLP_ENDPOINT`.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_ENABLED` | `false` | Set `true` to activate tracing |
| `OTEL_SERVICE_NAME` | `domo-backend` | Service name shown in X-Ray traces |
| `OTEL_OTLP_ENDPOINT` | (none) | ADOT Collector gRPC endpoint, e.g. `localhost:4317` |
| `OTEL_SAMPLING_RATE` | `0.1` | Fraction of requests traced (0.0–1.0) |

**Recommended per environment:**

| Environment | `OTEL_ENABLED` | `OTEL_SAMPLING_RATE` |
|-------------|---------------|---------------------|
| development | `false` | — |
| staging | `true` | `1.0` (100%) |
| production | `true` | `0.1` (10%) |

---

## ECS / Fargate Task Definition

Add the ADOT Collector as a sidecar container alongside the `domo-backend` container:

```json
{
  "family": "domo-backend",
  "containerDefinitions": [
    {
      "name": "domo-backend",
      "image": "your-ecr-repo/domo-backend:latest",
      "environment": [
        { "name": "OTEL_ENABLED",       "value": "true" },
        { "name": "OTEL_OTLP_ENDPOINT", "value": "localhost:4317" },
        { "name": "OTEL_SAMPLING_RATE", "value": "0.1" },
        { "name": "OTEL_SERVICE_NAME",  "value": "domo-backend" }
      ],
      "portMappings": [{ "containerPort": 8080, "protocol": "tcp" }]
    },
    {
      "name": "adot-collector",
      "image": "public.ecr.aws/aws-observability/aws-otel-collector:latest",
      "command": ["--config=/etc/ecs/ecs-xray.yaml"],
      "essential": false,
      "portMappings": [
        { "containerPort": 4317, "protocol": "tcp" },
        { "containerPort": 4318, "protocol": "tcp" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/adot-collector",
          "awslogs-region": "ap-northeast-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### ADOT Collector Config (`ecs-xray.yaml`)

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 5s
    send_batch_size: 50

exporters:
  awsxray:
    region: ap-northeast-2
    indexed_attributes:
      - service.name
      - deployment.environment

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [awsxray]
```

---

## IAM Permissions

The ECS task role must include:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    }
  ]
}
```

Attach this policy to the ECS Task Role (not the Task Execution Role).

---

## Auto-Instrumented Spans

The following spans are created automatically without code changes:

| Library | Span type | Notes |
|---------|-----------|-------|
| FastAPI | HTTP server span | `GET /v1/posts`, `POST /v1/auth/signin`, etc. |
| SQLAlchemy | DB statement span | Every `SELECT`/`INSERT`/`UPDATE`/`DELETE` |
| httpx | HTTP client span | Stripe API, AWS SES, LLM Gateway (tuzigroup) |

---

## Manual Spans

### Cron Workers (8)

Each cron worker wraps its sweep in a manual span:

| Span name | Worker | Key attributes |
|-----------|--------|----------------|
| `cron.auction` | auction_jobs | `rows_processed`, `expired_orders`, `second_chance_offered` |
| `cron.auction_promotion` | auction_promotion_jobs | `rows_processed` |
| `cron.tier_release` | tier_release_jobs | `rows_processed` |
| `cron.schedule` | schedule_jobs | `rows_processed` |
| `cron.artist_index` | artist_index_jobs | `artists_ranked` |
| `cron.subscription_expiry` | subscription_expiry_jobs | `notifications_created` |
| `cron.post_engagement` | post_engagement_jobs | (via Prometheus, no span attribute) |
| `cron.newsletter` | newsletter_jobs | `issues_processed` |

### Critical Operations

| Span name | File | Key attributes |
|-----------|------|----------------|
| `feed.personalized_v1` | api/posts.py | `user_id`, `has_cursor`, `limit` |
| `pillow.generate_share_card` | auction_promotion_jobs.py | `has_thumbnail`, `currency` |
| `press_kit.generate` | press_kit_generator.py | `artist_id`, `locale`, `force_regenerate` |
| `newsletter.compose_issue` | newsletter_composer.py | `locale`, `issue_date` |
| `llm.generate_interview` | llm_gateway.py | `model`, `max_tokens`, `mock_mode`, `usage_tokens` |

---

## PII Policy

**Never include in span attributes:**
- `email`, `phone`, `phone_number`
- `card_number`, `iban`, `ssn`
- Any raw personal identifier beyond UUIDs

**Safe to include:**
- UUIDs: `user_id`, `artist_id`, `auction_id`, `post_id`
- Counts: `rows_processed`, `artists_ranked`, `usage_tokens`
- Booleans: `mock_mode`, `has_cursor`, `force_regenerate`
- Environment-level: `deployment.environment`, `service.name`

---

## Mock Mode Verification

With `OTEL_ENABLED=false` (default):

```bash
# Boot log should contain:
# [OTel] Mock mode — OTEL_ENABLED=false, tracing disabled (zero overhead)

# No opentelemetry.sdk imports occur.
# All tracer.start_as_current_span() calls are no-op NoOpSpan.
# Zero performance impact on hot paths.
```

---

## Sampling Policy

| Environment | Rate | Rationale |
|-------------|------|-----------|
| production | 10% (`0.1`) | Cost/storage protection; sufficient for p99 latency analysis |
| staging | 100% (`1.0`) | Full visibility for integration testing |
| development | disabled | Zero overhead, no X-Ray costs |

Production sampling is `TraceIdRatioBased(0.1)` — deterministic per trace ID,
so all spans within one request are included or excluded together.

---

## Trace ID → PostHog Correlation

When `OTEL_ENABLED=true`, every `capture_event()` call in `analytics.py` automatically
injects `trace_id` (32-char hex) into PostHog event properties. This enables:

1. Identify a slow/failing PostHog event in the analytics dashboard.
2. Copy the `trace_id` value.
3. Search AWS X-Ray by trace ID to see the full distributed trace for that request.

No extra code changes required in callers — the injection happens transparently
in `_inject_trace_id()` via `opentelemetry.trace.get_current_span()`.

---

## Out of Scope (Phase 9+)

- Grafana Tempo integration (currently using AWS X-Ray console)
- Custom span semantic convention schema
- Distributed tracing across microservices (current monolith)
- Span exemplars in Prometheus (G''-1 + G''-2 post-merge)
- Span attribute exemplar linking in Grafana dashboards
