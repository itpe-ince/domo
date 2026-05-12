---
name: B'-1 multi-currency-foundation
description: Phase 8 B'-1: 4-currency support (USD/KRW/EUR/JPY) with exchange rate cron, CurrencySwitcher, and display conversion across PostCard/FeedItem. alembic 0061+0062. 22 new tests.
type: project
---

Phase 8 B'-1 multi-currency-foundation implementation (2026-05-04).

Baseline: alembic 0060, 354+ tests.

**Why:** B'-2/B'-3/B'-4/B'-5 all depend on this foundation. Critical Path for Phase 8.

**How to apply:** B'-2/B'-3/B'-4/B'-5 can now consume exchange rates via `currency.get_rate(target, db)`, user preference via `user.preferred_currency`, and frontend via `useExchangeRates()`.

## Migrations
- 0061_multi_currency: users.preferred_currency, product_posts.buy_now_currency, sponsorships/subscriptions server_default → USD
- 0062_exchange_rates: exchange_rates table (base/target/rate/fetched_at/expires_at, 1h TTL)

## Backend (new/modified)
- `app/models/exchange_rate.py` — ExchangeRate model
- `app/models/user.py` — preferred_currency field
- `app/models/post.py` — buy_now_currency field on ProductPost
- `app/services/exchange_rate_jobs.py` — 9th cron worker (R-5 isolated, 3600s)
- `app/services/currency.py` — get_rate, convert_amount, format_currency, get_all_rates
- `app/api/exchange_rates.py` — GET /v1/exchange-rates (public, 5min Redis cache)
- `app/api/me_preferences.py` — PATCH/GET /v1/me/preferences/currency
- `app/core/config.py` — exchange_rate_api_key setting
- `app/core/metrics.py` — EXCHANGE_RATE_FETCH_TOTAL counter
- `app/core/rate_limit.py` — exchange_rates_read (60/min IP), me_currency_preference (10/min user)
- `app/schemas/post.py` — buy_now_currency in ProductPostIn/ProductPostOut
- `app/schemas/auth.py` — preferred_currency in UserPublic
- `app/main.py` — exchange_rate_task registered as 9th cron worker

## Frontend (new/modified)
- `components/CurrencySwitcher.tsx` — localStorage "domo-currency", event "domo-currency-changed"
- `lib/format.ts` — convertAndFormat, convertCents, getPreferredCurrency helpers
- `lib/hooks/useExchangeRates.ts` — module-level 5min cache, currency state
- `components/PostCard.tsx` — convertAndFormat for buy_now_price display
- `components/FeedItem.tsx` — convertAndFormat for buy_now_price display
- `components/Sidebar.tsx` — CurrencySwitcher above language switcher
- `lib/api.ts` — buy_now_currency in ProductPostView, preferred_currency in ApiUser
- i18n: 8 keys × 5 locales = 40 entries (currency.label.*, currency.switcher.*)

## Tests
- `tests/integration/test_multi_currency.py` — 12 tests (endpoints + jobs)
- `tests/unit/test_currency_service.py` — 10 tests (get_rate, convert_amount, format_currency, get_all_rates)

## Operations
- Mock mode: EXCHANGE_RATE_API_KEY not set → hardcoded rates (KRW=1300, EUR=0.92, JPY=150)
- Open Exchange Rates: 1000 req/month free → 432 req/month (1h interval = well within quota)
- Prometheus: domo_exchange_rate_fetch_total{status=ok|mock|error}
- Docs: /Users/sangincha/dev/domo/v1/docs/operations/multi-currency.md
