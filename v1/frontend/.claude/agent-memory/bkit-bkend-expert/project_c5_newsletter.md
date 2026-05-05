---
name: C-5 newsletter-digest
description: Phase 7 C-5 (final sub-PDCA): AWS SES newsletter + opt-in model + cron worker + admin UI. Completes Phase 7.
type: project
---

Phase 7 C-5 newsletter-digest implementation. Phase 7 is now 15/15 complete.

**Why:** Subscriber differentiation + Featured Artist / ranking changes marketing hub. OQ-6=B (AWS SES), OQ-7=D (user-chosen frequency), OQ-8=C (Featured Artist monthly).

**alembic:** 0058_newsletter (NewsletterPreferences + NewsletterIssue tables)

**Backend files:**
- `app/models/newsletter_preferences.py` — GDPR opt-in (default False), unsubscribe_token field
- `app/models/newsletter_issue.py` — issue history with JSONB content snapshot
- `app/services/email_ses.py` — aioboto3 SES wrapper + Mock mode (aws_ses_access_key_id empty)
- `app/services/newsletter_composer.py` — auto-composes from G'-7/A-6/G'-9/C-4 data; md_to_html()
- `app/services/newsletter_jobs.py` — 1h cron R-5 격리, batch=50, newsletter_sent/failed metrics
- `app/schemas/newsletter.py` — NewsletterIssueOut, NewsletterPreferencesOut, PatchRequest schemas
- `app/api/admin_newsletter.py` — 4 endpoints: POST compose, GET list, PATCH, POST send
- `app/api/me_newsletter.py` — 3 endpoints: GET/PATCH preferences + GET unsubscribe (no auth)
- `app/core/config.py` — aws_ses_region, aws_ses_access_key_id, aws_ses_secret_access_key, aws_ses_from_address
- `app/core/rate_limit.py` — newsletter_admin_write/read, newsletter_me_read/write scopes
- `app/core/metrics.py` — newsletter_sent_total, newsletter_failed_total, opt_in/out counters

**Endpoints:**
- POST /admin/newsletter/issues/compose?issue_date=&locale= → 201 draft
- GET /admin/newsletter/issues → list (status/locale/limit filter)
- PATCH /admin/newsletter/issues/{id} → edit body/subject (blocked on sent/sending)
- POST /admin/newsletter/issues/{id}/send → draft → sending (cron picks up)
- GET /me/newsletter/preferences → auto-create default opt-out row
- PATCH /me/newsletter/preferences → opt-in/out + frequency + locale
- GET /newsletter/unsubscribe?token= → 1-click unsubscribe (no auth)

**Frontend files:**
- `app/admin/newsletter/page.tsx` — admin UI (compose + list + editor)
- `app/me/newsletter/page.tsx` — user preferences (opt-in toggle + frequency + locale)
- `app/newsletter/unsubscribe/page.tsx` — 1-click unsubscribe landing page
- `components/admin/NewsletterIssueEditor.tsx` — markdown editor + preview + send
- `components/admin/NewsletterIssuesList.tsx` — issue table with status badges
- `lib/hooks/useAdminNewsletter.ts` — compose/list/patch/send state
- `lib/hooks/useMyNewsletterPreferences.ts` — fetch/patch preferences state
- `lib/api.ts` — 7 new newsletter functions + NewsletterIssueOut/PreferencesOut types
- `i18n/{ko,en,ja,zh,es}.json` — newsletter.* namespace (~25 keys × 5 locales = 125 entries)

**Tests:** 10 tests in test_newsletter.py (293 baseline → 303+ target)

**Key constraints satisfied:**
- GDPR opt-in: is_subscribed=False default + 1-click unsubscribe via token
- Mock mode: aws_ses_access_key_id empty → no real AWS calls
- R-5 격리: newsletter_jobs.py uses AsyncSessionLocal directly
- Metrics imported from app.core.metrics (no duplicate registration)
- C-5 namespace in i18n, no conflict with C-4

**Phase 7 status:** 15/15 complete (G' 10/10 + C 5/5). Phase 7 closed.

**How to apply:** Phase 8 carry-overs include: SES bounce/complaint webhooks, per-recipient delivery tracking table, A/B test subject lines (PostHog), personalized content (ML), newsletter analytics dashboard.
