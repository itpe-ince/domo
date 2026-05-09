# Phase 13 C-1: admin-system-cron-monitor 설계

## 1. 개요

25개 cron worker의 실행 상태를 Redis hash에 기록하고,
`/admin/system` 페이지에서 실시간 모니터링 + Slack overdue alert를 제공한다.

- alembic 0089: **생략** (Redis hash TTL 1h 충분)
- overdue 기준: 5분 이상 미실행
- alert 채널: Slack webhook (SLACK_WEBHOOK_URL env)

---

## 2. Redis Hash 스키마

### Key 구조

```
cron:status:{worker_name}
```

- 예: `cron:status:auction`, `cron:status:audit_partition`

### Hash Fields

| Field | Type | 설명 |
|-------|------|------|
| `last_run_at` | ISO8601 string | 마지막 실행 시각 (UTC) |
| `status` | string | `running` / `success` / `failed` |
| `error_message` | string | 에러 메시지 (없으면 빈 문자열) |
| `run_count` | int-string | 누적 실행 횟수 |

### TTL 전략

- 각 key TTL: **3600초 (1시간)**
- cron이 정상 실행 중이면 매 실행마다 갱신됨
- TTL 만료 = 1시간 이상 미실행 → `overdue` 판정 대상

### 전체 Worker Registry (25개)

```python
WORKER_REGISTRY = [
    "auction",             # 1 — 5분 interval
    "gdpr",               # 2 — 1h interval
    "schedule",           # 3 — 1분 interval
    "badge",              # 4 — 1일 interval
    "settlement",         # 5 — 1일 interval
    "webhook_cleanup",    # 6 — 1일 interval
    "draft_cleanup",      # 7 — 1일 interval
    "tier_release",       # 8 — 1분 interval
    "auction_promotion",  # 9 — 1분 interval
    "artist_index",       # 10 — 1h interval
    "post_engagement",    # 11 — 1h interval
    "subscription_expiry",# 12 — 1h interval
    "newsletter",         # 13 — 1h interval
    "exchange_rate",      # 14 — 1h interval
    "email_digest",       # 15 — 1h interval
    "auto_renewal",       # 16 — 1h interval
    "embedding",          # 17 — quick 60s + batch 24h
    "rss_fetch",          # 18 — 1h interval
    "cohort_alert",       # 19 — 1일 interval
    "ml_training",        # 20 — 1일 interval
    "artwork_caption",    # 21 — quick 60s + batch 24h
    "featured_artist",    # 22 — 주 1회 (월요일)
    "ai_curation",        # 23 — 주 1회 (월요일)
    "audit_log_cleanup",  # 24 — 1일 interval
    "audit_partition",    # 25 — 1일 interval
    "slack_alert",        # 26 — 1분 interval (자기참조 OK)
]
```

---

## 3. Overdue 감지 로직

```
overdue 기준: last_run_at 기준 5분(300초) 이상 경과 OR Redis key 미존재
```

```python
def is_overdue(last_run_at: str | None, now: datetime) -> bool:
    if last_run_at is None:
        return True  # 한 번도 실행 안 됨
    last = datetime.fromisoformat(last_run_at)
    return (now - last).total_seconds() > 300
```

**주의:** 실제 cron interval이 5분 이상인 worker (예: badge=86400s)도 5분 기준이 적용된다.
이는 "cron 데몬이 살아있는지" 확인용이 아니라 "process가 실행 중인지" 확인용이다.
interval이 긴 worker는 `is_overdue=true`가 정상일 수 있으므로, UI에서 interval 정보와 함께 표시한다.

---

## 4. Slack Alert 포맷

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": ":warning: Cron Worker Overdue Alert"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "다음 cron worker가 5분 이상 미실행 상태입니다:\n\n*auction* — 마지막 실행: 2026-05-09T03:00:00Z\n*badge* — 마지막 실행: 없음"
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "Domo API | 2026-05-09T03:05:00Z | 총 2개 overdue"
        }
      ]
    }
  ]
}
```

---

## 5. API 응답 스키마

### GET /admin/system/crons

```json
{
  "workers": [
    {
      "name": "auction",
      "status": "success",
      "last_run_at": "2026-05-09T03:00:00Z",
      "error_message": null,
      "run_count": 1440,
      "is_overdue": false,
      "interval_label": "5분"
    },
    {
      "name": "badge",
      "status": null,
      "last_run_at": null,
      "error_message": null,
      "run_count": 0,
      "is_overdue": true,
      "interval_label": "1일"
    }
  ],
  "summary": {
    "total": 26,
    "success": 24,
    "failed": 0,
    "running": 1,
    "overdue": 1
  }
}
```

### GET /admin/system/crons/{worker_name}

단일 worker 상세 — 위 배열 원소 1개 반환.

---

## 6. Frontend 페이지 Wireframe

```
/admin/system
┌─────────────────────────────────────────────────────────────────┐
│ [Domo Admin]  시스템 > Cron 모니터                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Cron Worker 상태                                [새로고침 30s] │
│                                                                  │
│  요약: 전체 26  성공 24  실패 0  실행중 1  지연 1               │
│                                                                  │
│  ┌──────────────┬──────────┬──────────────────┬──────┬──────┐  │
│  │ Worker       │ 상태     │ 마지막 실행       │ 횟수 │ 간격 │  │
│  ├──────────────┼──────────┼──────────────────┼──────┼──────┤  │
│  │ auction      │ ✓ success│ 2분 전           │ 1440 │ 5분  │  │
│  │ badge        │ ⚠ overdue│ -                │ 0    │ 1일  │  │ ← 빨간 행
│  │ schedule     │ ● running│ 방금             │ 8640 │ 1분  │  │
│  │ ...          │          │                  │      │      │  │
│  └──────────────┴──────────┴──────────────────┴──────┴──────┘  │
│                                                                  │
│  * overdue: 빨간 배경  * failed: 노란 배경                       │
│  * 30초마다 자동 새로고침                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 파일 목록

| 파일 | 역할 |
|------|------|
| `app/services/cron_monitor.py` | Redis hash 기록 + status 조회 |
| `app/services/slack_alert_cron.py` | 26번째 worker — overdue → Slack |
| `app/api/admin_system.py` | GET /admin/system/crons (+ /{name}) |
| `frontend/src/app/admin/system/page.tsx` | Admin 모니터 페이지 |
| `tests/unit/test_cron_monitor.py` | 단위 테스트 |

---

## 8. 데코레이터 패턴

```python
# app/services/cron_monitor.py

def track_cron(worker_name: str):
    """cron loop 본체를 감싸는 async 데코레이터.

    Usage:
        @track_cron("auction")
        async def _run():
            ...actual work...
        await _run()
    """
```

기존 cron worker의 `with record_cron_run("worker"):` 블록과 공존.
`track_cron` 데코레이터는 Redis hash에만 기록하며, Prometheus metrics는 기존 `record_cron_run`이 담당.
