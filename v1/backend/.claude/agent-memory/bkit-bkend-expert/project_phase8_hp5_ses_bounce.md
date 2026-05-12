---
name: Phase 8 H'-5 SES Bounce Handling
description: H'-5 완료 — SES bounce/complaint SNS webhook, 4 bounce 필드, 4 issue 카운터, 6 tests, newsletter-bounce.md ops guide
type: project
---

H'-5 newsletter-bounce-handling 완료 (2026-05-04).

**Why:** AWS SES 자동 bounce/complaint 이벤트를 백엔드에서 처리하여 GDPR 준수 및 이메일 deliverability 유지

**How to apply:** Phase 9+ analytics PDCA에서 open rate tracking 구현 시 이 bounce infrastructure 위에 추가

## 신규/수정 파일

- `alembic/versions/0060_ses_bounce_tracking.py` — newsletter_preferences +4컬럼, newsletter_issues +4컬럼, suspended_until 인덱스
- `app/api/webhooks_ses.py` (신규) — POST /webhooks/ses-bounce, SNS 3가지 메시지 타입 처리
- `app/models/newsletter_preferences.py` (수정) — bounce_count, last_bounce_at, suspended_until, last_bounce_type
- `app/models/newsletter_issue.py` (수정) — delivered_count, bounced_count, complained_count, ses_configuration_set
- `app/core/config.py` (수정) — aws_sns_topic_arn, admin_alert_email
- `app/core/metrics.py` (수정) — 6개 SES bounce/complaint/delivery 메트릭
- `app/services/newsletter_jobs.py` (수정) — _get_recipient_emails에서 suspended_until 필터링
- `app/main.py` (수정) — webhooks_ses_router 등록
- `tests/integration/test_ses_bounce.py` (신규) — 6 tests
- `docs/operations/newsletter-bounce.md` (신규) — SNS setup + IAM + ops runbook

## SNS Signature Verification

- 프로덕션: `cryptography` 라이브러리로 x509/SHA1WithRSA 검증
- TopicArn validate + SigningCertURL URL 검증
- Dev/CI: `AWS_SNS_TOPIC_ARN` 비어있으면 검증 건너뜀

## Bounce 처리 규칙

- Hard bounce (Permanent): is_subscribed=False + Notification 생성
- Soft bounce: bounce_count++; 3회 누적 → suspended_until = NOW()+7d
- Complaint: 즉시 unsubscribe + admin_alert_email로 알림
- Delivery: bounce_count 리셋, delivered_count++ (issue별)

## Idempotency

WebhookEvent 테이블에 `sns_{message_id}` 형식으로 dedup (Stripe webhook과 동일 패턴)

## Open Rate Tracking

Phase 9+ carry-over: SES Configuration Set Open event 또는 tracking pixel (privacy opt-out 포함)
