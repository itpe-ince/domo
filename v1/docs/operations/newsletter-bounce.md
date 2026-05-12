# Newsletter Bounce Handling — SES + SNS Setup Guide

Phase: H'-5 | Component: newsletter-bounce-handling | Status: Production-ready

---

## Overview

AWS SES automatically detects bounced emails and spam complaints. This guide
explains how to route those events to the Domo backend so users are
automatically unsubscribed (GDPR compliance) and delivery quality is maintained.

Architecture:

```
SES sends email
    ↓ (bounce / complaint / delivery event)
SES Event Notification → SNS Topic
    ↓ HTTP subscription
POST /v1/webhooks/ses-bounce   (Domo backend)
    ↓
Handler processes event:
  - Hard bounce  → auto-unsubscribe + in-app notification
  - Soft bounce  → increment counter; 3× → suspend 7 days
  - Complaint    → immediate unsubscribe + admin alert email
  - Delivery     → increment delivered_count on newsletter_issue
```

---

## 1. AWS SES Configuration

### 1.1 Enable Event Notifications on SES Identity

1. Open the AWS SES console → **Email Identities** → select your sending domain (`domo.art`)
2. Go to **Notifications** tab
3. Under **SNS Topic Configuration**, configure for each event type:
   - **Bounces** → Select SNS topic (create below)
   - **Complaints** → Same SNS topic
   - **Deliveries** → Same SNS topic (optional but recommended for tracking)
4. Uncheck "Include original email headers" if not needed (reduces message size)

### 1.2 Create SNS Topic

```bash
aws sns create-topic --name domo-ses-events --region us-east-1
# Note the TopicArn: arn:aws:sns:us-east-1:ACCOUNT_ID:domo-ses-events
```

### 1.3 Subscribe Domo Webhook to SNS Topic

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:domo-ses-events \
  --protocol https \
  --notification-endpoint https://api.domo.art/v1/webhooks/ses-bounce
```

SNS will send a `SubscriptionConfirmation` message to the endpoint. The Domo
backend automatically confirms it by fetching the `SubscribeURL`. No manual
action needed — watch the backend logs for:

```
INFO SNS subscription confirmed: TopicArn=arn:aws:sns:...
```

---

## 2. Backend Environment Variables

Add to your production `.env`:

```env
# H'-5 SES Bounce Handling
AWS_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:ACCOUNT_ID:domo-ses-events

# Admin alert email (receives complaint notifications)
ADMIN_ALERT_EMAIL=alerts@domo.art
```

Existing SES credentials are reused for the admin alert email:

```env
AWS_SES_ACCESS_KEY_ID=AKIA...
AWS_SES_SECRET_ACCESS_KEY=...
AWS_SES_FROM_ADDRESS=noreply@domo.art
AWS_SES_REGION=us-east-1
```

---

## 3. Database Migration

Run migration `0060_ses_bounce_tracking` to add bounce tracking columns:

```bash
# From v1/backend/
alembic upgrade 0060_ses_bounce_tracking
```

New columns added:

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| `newsletter_preferences` | `bounce_count` | INTEGER | Consecutive soft bounce counter |
| `newsletter_preferences` | `last_bounce_at` | TIMESTAMPTZ | Most recent bounce timestamp |
| `newsletter_preferences` | `suspended_until` | TIMESTAMPTZ | NULL = active; future = suspended |
| `newsletter_preferences` | `last_bounce_type` | VARCHAR(20) | `permanent` / `transient` / `complaint` |
| `newsletter_issues` | `delivered_count` | INTEGER | SES Delivery events received |
| `newsletter_issues` | `bounced_count` | INTEGER | SES Bounce events received |
| `newsletter_issues` | `complained_count` | INTEGER | SES Complaint events received |
| `newsletter_issues` | `ses_configuration_set` | VARCHAR(64) | Configuration Set name (optional) |

---

## 4. Bounce Handling Logic

### 4.1 Hard Bounce (Permanent)

Triggered when: recipient email address does not exist or domain rejects email permanently.

Actions:
- `newsletter_preferences.is_subscribed = False`
- `newsletter_preferences.last_bounce_type = 'permanent'`
- Creates `Notification` row for the user (type: `newsletter_bounce`)
- Audit log: `AUDIT action=NEWSLETTER_HARD_BOUNCE_UNSUBSCRIBED`

The user must explicitly re-subscribe (opt-in) to receive newsletters again.
This complies with GDPR: delivery to an invalid address is not purposeful.

### 4.2 Soft Bounce (Transient)

Triggered when: recipient mailbox is temporarily full, server is temporarily unavailable, etc.

Actions on each soft bounce:
- `newsletter_preferences.bounce_count += 1`
- `newsletter_preferences.last_bounce_at = NOW()`

When `bounce_count >= 3`:
- `newsletter_preferences.suspended_until = NOW() + 7 days`
- Audit log: `AUDIT action=NEWSLETTER_SOFT_BOUNCE_SUSPENDED`

After suspension window passes:
- Cron naturally re-includes the user (SQL filter: `suspended_until IS NULL OR suspended_until <= NOW()`)
- If delivery succeeds, `bounce_count` resets to 0 (via Delivery event handler)

### 4.3 Complaint

Triggered when: recipient marks the email as spam in their email client.

Actions:
- `newsletter_preferences.is_subscribed = False` immediately
- `newsletter_preferences.last_bounce_type = 'complaint'`
- Admin alert email sent to `ADMIN_ALERT_EMAIL`
- Audit log: `AUDIT action=NEWSLETTER_COMPLAINT_UNSUBSCRIBED`

GDPR note: a complaint is an explicit signal of unwanted contact — must be treated as
stronger than an opt-out request.

---

## 5. SES Configuration Set (Optional — Delivery Tracking)

For per-issue delivery counter tracking, create a Configuration Set:

```bash
aws ses create-configuration-set \
  --configuration-set-name domo-newsletter \
  --region us-east-1

# Add SNS event destination
aws ses create-configuration-set-event-destination \
  --configuration-set-name domo-newsletter \
  --event-destination '{
    "Name": "ses-bounce-sns",
    "Enabled": true,
    "MatchingEventTypes": ["send", "bounce", "complaint", "delivery"],
    "SNSDestination": {
      "TopicARN": "arn:aws:sns:us-east-1:ACCOUNT_ID:domo-ses-events"
    }
  }' \
  --region us-east-1
```

When using a Configuration Set, add the `ConfigurationSetName` header when
sending emails. Currently the cron worker sends via SES `send_email` API — the
Configuration Set name can be passed optionally; the backend stores it in
`newsletter_issues.ses_configuration_set` for audit purposes.

---

## 6. Signature Verification

The webhook verifies SNS message signatures to prevent spoofing.

Requirements:
- `AWS_SNS_TOPIC_ARN` must be set
- `cryptography` Python package must be installed (already in pyproject.toml)

Verification steps:
1. Validate `TopicArn` matches `AWS_SNS_TOPIC_ARN`
2. Validate `SigningCertURL` is an AWS SNS HTTPS URL
3. Fetch signing certificate
4. Verify RSA-SHA1 signature over canonical fields

Dev/CI mode: when `AWS_SNS_TOPIC_ARN` is empty, signature verification is
skipped. Never deploy to production with this setting empty.

---

## 7. Prometheus Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `domo_ses_bounce_received_total` | `bounce_type` | Total bounce events by type |
| `domo_ses_complaint_received_total` | — | Total complaint events |
| `domo_ses_delivery_received_total` | — | Total delivery events |
| `domo_ses_sns_webhook_received_total` | `message_type` | All SNS messages received |
| `domo_ses_hard_bounce_unsubscribed_total` | — | Auto-unsubscribed (hard bounce) |
| `domo_ses_soft_bounce_suspended_total` | — | Users suspended (3× soft bounce) |

Monitor with Grafana alert rule: if `domo_ses_bounce_received_total{bounce_type="permanent"}` rate
exceeds 5% of send volume, investigate sending domain reputation.

---

## 8. Testing

```bash
# From v1/backend/
pytest tests/integration/test_ses_bounce.py -v
```

6 tests covering:
1. SNS SubscriptionConfirmation auto-confirm
2. Hard bounce → unsubscribe + notification
3. Soft bounce (1st) → counter increment
4. Soft bounce (3rd) → suspension
5. Complaint → unsubscribe + admin alert
6. Suspended users excluded from send batch

---

## 9. Operational Runbook

### Check bounce rate for an issue

```sql
SELECT
  id,
  sent_count,
  delivered_count,
  bounced_count,
  complained_count,
  ROUND(bounced_count::numeric / NULLIF(sent_count, 0) * 100, 2) AS bounce_pct
FROM newsletter_issues
ORDER BY created_at DESC
LIMIT 10;
```

### List hard-bounced users

```sql
SELECT np.user_id, u.email, np.last_bounce_at, np.last_bounce_type
FROM newsletter_preferences np
JOIN users u ON u.id = np.user_id
WHERE np.is_subscribed = FALSE
  AND np.last_bounce_type IN ('permanent', 'complaint')
ORDER BY np.last_bounce_at DESC;
```

### Check currently suspended users

```sql
SELECT np.user_id, u.email, np.bounce_count, np.suspended_until
FROM newsletter_preferences np
JOIN users u ON u.id = np.user_id
WHERE np.suspended_until > NOW()
ORDER BY np.suspended_until;
```

### Re-enable a falsely bounced user (admin action)

```sql
UPDATE newsletter_preferences
SET is_subscribed = TRUE,
    bounce_count = 0,
    suspended_until = NULL,
    last_bounce_type = NULL
WHERE user_id = '<user-uuid>';
```

---

## 10. SNS IAM Policy

The SNS topic must allow SES to publish to it. Attach this policy to the SNS topic:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ses.amazonaws.com"
      },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:ACCOUNT_ID:domo-ses-events",
      "Condition": {
        "StringEquals": {
          "AWS:SourceAccount": "ACCOUNT_ID"
        }
      }
    }
  ]
}
```
