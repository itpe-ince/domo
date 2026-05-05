#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# D-6 Observability: EXPLAIN ANALYZE gate
#
# Checks key query plans for Seq Scan on critical tables.
# Exits non-zero if any Seq Scan is detected — intended as a CI gate after
# `alembic upgrade head`.
#
# Usage:
#   ./scripts/check_query_plans.sh
#
# Env vars (override defaults):
#   DB_HOST     (default: localhost)
#   DB_PORT     (default: 5432)
#   DB_USER     (default: domo)
#   DB_NAME     (default: domo)
#   PGPASSWORD  (default: domo_dev_pw)
#
# Note: This script performs EXPLAIN (not EXPLAIN ANALYZE) so it does NOT
# modify data. Safe to run against any environment with SELECT permissions.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-domo}"
DB_NAME="${DB_NAME:-domo}"
export PGPASSWORD="${PGPASSWORD:-domo_dev_pw}"

PSQL="psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A"

ERRORS=0

check_plan() {
    local label="$1"
    local query="$2"
    local plan
    plan=$($PSQL -c "EXPLAIN $query" 2>&1)
    if echo "$plan" | grep -q "Seq Scan"; then
        echo "FAIL [$label]: Seq Scan detected"
        echo "$plan" | head -5
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS [$label]"
    fi
}

echo "=== D-6 EXPLAIN ANALYZE gate ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""

# ─── 1. Feed/explore visibility filter (posts table) ─────────────────────────
# Critical: post feed list uses status + author_id index
check_plan "posts.visibility_filter" \
    "SELECT id FROM posts WHERE status = 'published' ORDER BY created_at DESC LIMIT 20"

# ─── 2. Tier release eligibility — early_access_until expiry sweep ───────────
# Critical: tier_release worker bulk UPDATE — needs index on early_access_until
check_plan "posts.early_access_until_expiry" \
    "SELECT id FROM posts WHERE early_access_until IS NOT NULL AND early_access_until <= NOW()"

# ─── 3. Auction promotion cron — active auctions with end_at window ──────────
# Critical: notified_24h_at IS NULL + status + end_at range
check_plan "auctions.promotion_24h_slot" \
    "SELECT id FROM auctions WHERE status = 'active' AND end_at > NOW() AND end_at <= NOW() + INTERVAL '24 hours' AND notified_24h_at IS NULL"

# ─── 4. Auction settlement — expired pending_payment orders ──────────────────
# Critical: auction settlement cron WHERE status = 'pending_payment' + payment_due_at
check_plan "orders.expired_pending_payment" \
    "SELECT id FROM orders WHERE status = 'pending_payment' AND payment_due_at IS NOT NULL AND payment_due_at < NOW()"

# ─── 5. Scheduled posts publish cron ─────────────────────────────────────────
# Critical: schedule worker WHERE status = 'scheduled' AND scheduled_at <= NOW()
check_plan "posts.scheduled_publish" \
    "SELECT id FROM posts WHERE status = 'scheduled' AND scheduled_at <= NOW()"

# ─── 6. Bid lookup for auction — compound (auction_id, amount DESC) ──────────
check_plan "bids.by_auction_amount_desc" \
    "SELECT id FROM bids WHERE auction_id = '00000000-0000-0000-0000-000000000001' ORDER BY amount DESC LIMIT 1"

# ─── 7. Notifications by user_id (unread feed) ───────────────────────────────
check_plan "notifications.unread_by_user" \
    "SELECT id FROM notifications WHERE user_id = '00000000-0000-0000-0000-000000000001' AND is_read = false ORDER BY created_at DESC LIMIT 20"

# ─── 8. Draft cleanup — drafts by user + updated_at expiry ──────────────────
check_plan "drafts.expired_cleanup" \
    "SELECT id FROM drafts WHERE updated_at < NOW() - INTERVAL '30 days'"

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "RESULT: $ERRORS query plan(s) use Seq Scan — add missing indexes before deploying."
    exit 1
else
    echo "RESULT: All query plans OK (no Seq Scan detected)."
    exit 0
fi
