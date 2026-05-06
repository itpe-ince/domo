# Multi-Currency Operations Guide — B'-1

## Overview

Domo supports 4 display currencies: **USD / KRW / EUR / JPY**.

Prices are stored in the DB in the artist's native currency (cents).
Display is converted to the user's preferred currency via live exchange rates.

## Architecture

```
Open Exchange Rates API (1h)
  ↓
exchange_rate_cron_loop (9th worker, 3600s interval)
  ↓ upsert
exchange_rates table (DB, 1h TTL)
  ↓ read
GET /v1/exchange-rates (Redis cache 5min)
  ↓
Frontend: useExchangeRates() hook
  ↓
convertAndFormat(cents, native, preferred, rates)
  ↓
PostCard / FeedItem / posts/[id]
```

## Configuration

| Env var | Required | Default | Description |
|---------|----------|---------|-------------|
| `EXCHANGE_RATE_API_KEY` | No | — | Open Exchange Rates APP_ID (1000 req/month free). If unset, Mock mode. |

### Mock mode (no API key)
When `EXCHANGE_RATE_API_KEY` is not set, the cron uses hardcoded rates:
- USD: 1.0
- KRW: 1300.0
- EUR: 0.92
- JPY: 150.0

Mock mode is safe for development and CI. Prometheus counter: `domo_exchange_rate_fetch_total{status="mock"}`.

### Production setup
1. Sign up at https://openexchangerates.org (free tier: 1000 req/month)
2. Get your APP_ID
3. Set `EXCHANGE_RATE_API_KEY=<your-app-id>` in backend `.env`
4. Cron runs at startup and every 3600s (432 req/month — well within free tier)

## Database

**Table**: `exchange_rates`
**Migration**: alembic `0062_exchange_rates`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| base_currency | String(3) | Always "USD" |
| target_currency | String(3) | KRW / EUR / JPY / USD |
| rate | Numeric(18,8) | 1 USD = rate target |
| fetched_at | DateTime TZ | When API was called |
| expires_at | DateTime TZ | fetched_at + 1h |

Unique index on `(base_currency, target_currency)` enables upsert pattern.

## Cron Worker

- **Worker name**: `exchange_rate` (9th worker — R-5 isolated)
- **Interval**: 3600 seconds (1 hour)
- **Prometheus metric**: `domo_exchange_rate_fetch_total{status=ok|mock|error}`
- **Log prefix**: `exchange_rate_cron:`

The worker runs independently of all other cron workers. It does not share a DB session with others.

## API Endpoints

### GET /v1/exchange-rates

Public endpoint. Returns current rates.

```json
{
  "data": {
    "base": "USD",
    "rates": {
      "USD": 1.0,
      "KRW": 1300.0,
      "EUR": 0.92,
      "JPY": 150.0
    },
    "cached": false
  }
}
```

Rate limit: 60/min by IP.
Redis cache: 5 minutes (`exchange_rates:USD`).

### PATCH /v1/me/preferences/currency

Updates the authenticated user's preferred display currency.

```json
{ "currency": "KRW" }
```

Supported: `USD`, `KRW`, `EUR`, `JPY`. Returns 422 for unsupported currencies.

### GET /v1/me/preferences/currency

Returns current preferred currency.

## Frontend

### CurrencySwitcher

`components/CurrencySwitcher.tsx` — mirrors LocaleSwitcher pattern.

- localStorage key: `domo-currency`
- Custom event: `domo-currency-changed`
- Mounted in Sidebar (bottom, above language switcher)
- When user is authenticated (`syncToServer=true`): also PATCHes `/v1/me/preferences/currency`

### useExchangeRates hook

`lib/hooks/useExchangeRates.ts` — module-level cache (5min TTL).

```ts
const { rates, currency, loading } = useExchangeRates();
// rates: { USD: 1, KRW: 1300, EUR: 0.92, JPY: 150 }
// currency: user's preferred currency (from localStorage)
```

### Price display

All components use `convertAndFormat(cents, nativeCurrency, preferredCurrency, rates)`:

- `PostCard` — buy_now_price display
- `FeedItem` — buy_now_price in engagement bar

DB stores prices in native currency (artist's choice). Display is always converted.

## User Flow

1. Artist creates product post → sets `buy_now_currency` (USD default) and `buy_now_price` (cents)
2. Collector visits site → opens CurrencySwitcher → selects KRW
3. PostCard calls `convertAndFormat(post.product.buy_now_price, "USD", "KRW", rates)`
4. Display shows `₩XXX,XXX` — rate fetched from API 1h ago

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| All prices show fallback rates | API key not set or cron hasn't run | Check `EXCHANGE_RATE_API_KEY`, check `exchange_rate_cron` logs |
| exchange_rate_fetch_total{status="error"} | API call failed | Check network, API quota (1000/month) |
| Stale rates > 2h | Cron stopped | Check cron task in lifespan logs |
| Redis cache serving old rates | Cache not invalidated | Wait 5min or restart server |

## Metrics

| Metric | Labels | Description |
|--------|--------|-------------|
| `domo_exchange_rate_fetch_total` | `status` (ok/mock/error) | Fetch cycle count |
