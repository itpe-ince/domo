#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# G''-3 n-plus-one-audit: EXPLAIN gate for 18 core queries
#
# Checks query plans for Seq Scan on critical tables.
# Exits non-zero if any Seq Scan is detected — intended as a CI gate after
# `alembic upgrade head`.
#
# D-6 original 8 queries (Phase 5 carry-over) + 10 Phase 6/7 new queries.
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
PASS_COUNT=0

check_plan() {
    local label="$1"
    local query="$2"
    local plan
    plan=$($PSQL -c "EXPLAIN $query" 2>&1)
    if echo "$plan" | grep -q "Seq Scan"; then
        echo "FAIL [$label]: Seq Scan detected"
        echo "$plan" | head -8
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS [$label]"
        PASS_COUNT=$((PASS_COUNT + 1))
    fi
}

echo "=== G''-3 EXPLAIN gate ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo "Database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
echo ""
echo "── D-6 Phase 5 queries (1~8) ──────────────────────────────────────────"

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
echo "── Phase 6/7 new queries (9~18) ────────────────────────────────────────"

# ─── 9. A-3 Personalized feed — follow posts (author_id + status) ────────────
# Critical: followee posts for home feed (N users followed)
check_plan "posts.personalized_feed_follow" \
    "SELECT id FROM posts WHERE author_id = '00000000-0000-0000-0000-000000000001' AND status = 'published' ORDER BY created_at DESC LIMIT 100"

# ─── 10. A-3 Trending pool — public + no active tier ─────────────────────────
# Critical: trending posts for feed mix (status + visibility + no tier lock)
check_plan "posts.trending_pool" \
    "SELECT id FROM posts WHERE status = 'published' AND visibility = 'public' AND (early_access_until IS NULL OR early_access_until <= NOW()) ORDER BY created_at DESC LIMIT 100"

# ─── 11. A-6 Artist index ranking — region/genre filter ─────────────────────
# Critical: artist_index ranking page with region/genre (G'-8 booster)
check_plan "artist_index.region_genre_ranking" \
    "SELECT user_id FROM artist_index WHERE region IS NOT NULL ORDER BY score DESC LIMIT 50"

# ─── 12. A-5 Search v2 — search_history by user ─────────────────────────────
# Critical: search history page (user_id + deleted_at partial filter)
check_plan "search_history.by_user" \
    "SELECT id FROM search_history WHERE user_id = '00000000-0000-0000-0000-000000000001' AND deleted_at IS NULL ORDER BY searched_at DESC LIMIT 20"

# ─── 13. A-5 Popular searches — last 24h query count ────────────────────────
# Critical: popular searches aggregation (searched_at range + group by query)
check_plan "search_logs.popular_24h" \
    "SELECT query, COUNT(*) as cnt FROM search_logs WHERE created_at >= NOW() - INTERVAL '24 hours' GROUP BY query ORDER BY cnt DESC LIMIT 10"

# ─── 14. Notifications unread count — WHERE is_read = false ─────────────────
# Critical: badge count query on every page load (user_id + is_read)
check_plan "notifications.unread_count" \
    "SELECT COUNT(*) FROM notifications WHERE user_id = '00000000-0000-0000-0000-000000000001' AND is_read = false"

# ─── 15. C-1 ArtistInterview list with status filter ────────────────────────
# Critical: admin interview list (status + created_at)
check_plan "artist_interviews.status_list" \
    "SELECT id FROM artist_interviews WHERE status = 'admin_review' ORDER BY created_at DESC LIMIT 20"

# ─── 16. C-2 PressKit cache lookup — artist + locale + expired_at ───────────
# Critical: press kit 30-day cache check (artist_id + locale + expires_at)
check_plan "press_kits.cache_lookup" \
    "SELECT id FROM press_kits WHERE artist_id = '00000000-0000-0000-0000-000000000001' ORDER BY created_at DESC LIMIT 1"

# ─── 17. C-4 MediaCoverage — locale + type + is_published filter ─────────────
# Critical: media coverage list page (is_published + locale + type)
check_plan "media_coverage.published_locale" \
    "SELECT id FROM media_coverage WHERE is_published = true AND locale = 'ko' ORDER BY published_at DESC LIMIT 20"

# ─── 18. C-5 Newsletter issues — status filter for cron ─────────────────────
# Critical: newsletter_jobs cron picks up 'sending' issues by status + locale
check_plan "newsletter_issues.sending_by_locale" \
    "SELECT id FROM newsletter_issues WHERE status = 'sending' AND locale = 'ko' ORDER BY issue_date DESC LIMIT 10"

echo ""
echo "─────────────────────────────────────────────────────────────────────────"
echo "TOTAL: $PASS_COUNT passed, $ERRORS failed (out of 18 queries)"
echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "RESULT: $ERRORS query plan(s) use Seq Scan — add missing indexes before deploying."
    exit 1
else
    echo "RESULT: All 18 query plans OK (no Seq Scan detected)."
    exit 0
fi
