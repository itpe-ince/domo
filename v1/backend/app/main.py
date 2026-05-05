import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import activity as activity_router
from app.api import admin as admin_router
from app.api.health import metrics_endpoint, router as health_router
from app.api import admin_auth as admin_auth_router
from app.api import admin_dashboard as admin_dashboard_router
from app.api import admin_webauthn as admin_webauthn_router
from app.api import artists as artists_router
from app.api import auctions as auctions_router
from app.api import auth as auth_router
from app.api import guardian as guardian_router
from app.api import kyc as kyc_router
from app.api import legal as legal_router
from app.api import me as me_router
from app.api import media as media_router
from app.api import moderation as moderation_router
from app.api import notifications as notifications_router
from app.api import orders as orders_router
from app.api import collections as collections_router
from app.api import communities as communities_router
from app.api import drafts as drafts_router
from app.api import posts as posts_router
from app.api import series as series_router
from app.api import rankings as rankings_router
from app.api import reports as reports_router
from app.api import rewards as rewards_router
from app.api import settlements as settlements_router
from app.api import me_patronage as me_patronage_router
from app.api import payments as payments_router
from app.api import tier_benefits as tier_benefits_router
from app.api import sponsorships as sponsorships_router
from app.api import users as users_router
from app.api import webhooks as webhooks_router
from app.api import admin_coupons as admin_coupons_router
from app.api import me_coupons as me_coupons_router
from app.api import admin_featured as admin_featured_router
from app.api import admin_interviews as admin_interviews_router
from app.api import admin_press_kits as admin_press_kits_router
from app.api import featured as featured_router
from app.api import me_interviews as me_interviews_router
from app.api import me_bio as me_bio_router
from app.api import admin_media_coverage as admin_media_coverage_router
from app.api import media_coverage as media_coverage_router
from app.api import admin_newsletter as admin_newsletter_router
from app.api import me_newsletter as me_newsletter_router
from app.api.search import me_search_router, search_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import AsyncSessionLocal
from app.services.auction_jobs import auction_cron_loop
from app.services.community_jobs import seed_default_communities
from app.services.draft_cleanup_jobs import draft_cleanup_cron_loop
from app.services.gdpr_jobs import gdpr_cron_loop
from app.services.badge_jobs import badge_cron_loop
from app.services.schedule_jobs import schedule_cron_loop
from app.services.tier_release_jobs import tier_release_cron_loop
from app.services.auction_promotion_jobs import auction_promotion_cron_loop
from app.services.settlement_jobs import settlement_cron_loop
from app.services.artist_index_jobs import artist_index_cron_loop
from app.services.post_engagement_jobs import post_engagement_cron_loop
from app.services.subscription_expiry_jobs import subscription_expiry_cron_loop
from app.services.webhook_cleanup_jobs import webhook_cleanup_cron_loop
from app.services.newsletter_jobs import newsletter_cron_loop
from app.services.analytics import init_posthog, shutdown_posthog

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: analytics SDK init (G'-4 backend-posthog-integration)
    init_posthog()

    # Startup: run-once idempotent seed then schedule cron tasks
    async with AsyncSessionLocal() as db:
        try:
            await seed_default_communities(db)
        except Exception as exc:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning("community seed failed: %s", exc)

    auction_task = asyncio.create_task(auction_cron_loop(interval_seconds=300))
    gdpr_task = asyncio.create_task(gdpr_cron_loop(interval_seconds=3600))
    schedule_task = asyncio.create_task(schedule_cron_loop(interval_seconds=60))
    badge_task = asyncio.create_task(badge_cron_loop(interval_seconds=86400))
    settle_task = asyncio.create_task(settlement_cron_loop(interval_seconds=86400))
    webhook_cleanup_task = asyncio.create_task(webhook_cleanup_cron_loop(interval_seconds=86400))
    draft_cleanup_task = asyncio.create_task(draft_cleanup_cron_loop(interval_seconds=86400))
    tier_release_task = asyncio.create_task(tier_release_cron_loop(interval_seconds=60))
    auction_promotion_task = asyncio.create_task(auction_promotion_cron_loop(interval_seconds=60))
    artist_index_task = asyncio.create_task(artist_index_cron_loop(interval_seconds=3600))
    post_engagement_task = asyncio.create_task(post_engagement_cron_loop(interval_seconds=3600))
    subscription_expiry_task = asyncio.create_task(subscription_expiry_cron_loop(interval_seconds=3600))
    newsletter_task = asyncio.create_task(newsletter_cron_loop(interval_seconds=3600))
    try:
        yield
    finally:
        all_tasks = (
            auction_task, gdpr_task, schedule_task, badge_task, settle_task,
            webhook_cleanup_task, draft_cleanup_task, tier_release_task,
            auction_promotion_task, artist_index_task, post_engagement_task,
            subscription_expiry_task, newsletter_task,
        )
        for task in all_tasks:
            task.cancel()
        for task in all_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        # Shutdown: flush PostHog batch queue before exit (G'-4)
        shutdown_posthog()


app = FastAPI(
    title="Domo API",
    version="0.1.0",
    description="Domo prototype API (Phase 0)",
    lifespan=lifespan,
)

# CORS origins: allow both localhost and 127.0.0.1 on each configured port
# (browsers treat these as different origins, so we need to list both)
#   3000  Next.js default
#   3700  user-facing frontend (v1/frontend)
#   3800  admin console      (v1/admin)
_cors_origins = [
    settings.frontend_url,
    settings.frontend_url.replace("localhost", "127.0.0.1"),
    settings.admin_url,
    settings.admin_url.replace("localhost", "127.0.0.1"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3700",
    "http://127.0.0.1:3700",
    "http://localhost:3800",
    "http://127.0.0.1:3800",
]
# Optional extra origins from env (comma-separated, e.g. staging URLs)
if settings.extra_cors_origins:
    _cors_origins.extend(
        o.strip() for o in settings.extra_cors_origins.split(",") if o.strip()
    )
# Deduplicate while preserving order
_cors_origins = list(dict.fromkeys(_cors_origins))

_cors_kwargs = dict(
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.add_middleware(CORSMiddleware, **_cors_kwargs)

register_error_handlers(app)

# Versioned API root
api_v1 = FastAPI(title="Domo API v1")
# Same CORS on the sub-app — FastAPI sub-app mount doesn't inherit
# the parent's middleware stack, so we must register it here too.
api_v1.add_middleware(CORSMiddleware, **_cors_kwargs)
register_error_handlers(api_v1)
api_v1.include_router(auth_router.router)
api_v1.include_router(admin_auth_router.router)
api_v1.include_router(admin_webauthn_router.router)
api_v1.include_router(me_router.router)
api_v1.include_router(legal_router.router)
api_v1.include_router(guardian_router.router)
api_v1.include_router(users_router.router)
api_v1.include_router(artists_router.router)
api_v1.include_router(activity_router.router)
api_v1.include_router(collections_router.router)
api_v1.include_router(communities_router.router)
api_v1.include_router(drafts_router.router)
api_v1.include_router(kyc_router.router)
api_v1.include_router(posts_router.router)
api_v1.include_router(series_router.router)
api_v1.include_router(rankings_router.router)
api_v1.include_router(reports_router.router)
api_v1.include_router(rewards_router.router)
api_v1.include_router(settlements_router.router)
api_v1.include_router(media_router.router)
api_v1.include_router(me_patronage_router.router)
api_v1.include_router(payments_router.router)
api_v1.include_router(tier_benefits_router.router)
api_v1.include_router(sponsorships_router.sponsorship_router)
api_v1.include_router(sponsorships_router.subscription_router)
api_v1.include_router(auctions_router.router)
api_v1.include_router(orders_router.orders_router)
api_v1.include_router(orders_router.products_router)
api_v1.include_router(moderation_router.reports_router)
api_v1.include_router(moderation_router.warnings_router)
api_v1.include_router(notifications_router.router)
api_v1.include_router(webhooks_router.router)
api_v1.include_router(admin_router.router)
api_v1.include_router(admin_dashboard_router.router)
api_v1.include_router(admin_coupons_router.router)
api_v1.include_router(me_coupons_router.router)
api_v1.include_router(admin_featured_router.router)
api_v1.include_router(admin_interviews_router.router)
api_v1.include_router(admin_press_kits_router.router)
api_v1.include_router(featured_router.router)
api_v1.include_router(me_interviews_router.router)
api_v1.include_router(me_bio_router.router)
api_v1.include_router(admin_media_coverage_router.router)
api_v1.include_router(media_coverage_router.router)
api_v1.include_router(admin_newsletter_router.router)
api_v1.include_router(me_newsletter_router.router)
api_v1.include_router(search_router)
api_v1.include_router(me_search_router)
api_v1.include_router(health_router)


@api_v1.get("/health")
async def health():
    return {"data": {"status": "ok", "version": "0.1.0"}}


app.mount("/v1", api_v1)

# Prometheus metrics endpoint — mounted on root app (not /v1) to allow
# internal scrape without API version prefix.
# Security: METRICS_ENABLED=true + METRICS_TOKEN required (see config.py).
app.add_route("/metrics", metrics_endpoint, methods=["GET"])


@app.get("/")
async def root():
    return {"data": {"name": "Domo API", "version": "0.1.0", "docs": "/docs"}}
