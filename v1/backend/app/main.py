import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import activity as activity_router
from app.api import admin as admin_router
from app.api.health import metrics_endpoint, router as health_router
from app.api import admin_auth as admin_auth_router
from app.api import admin_dashboard as admin_dashboard_router

try:
    from app.api import admin_webauthn as admin_webauthn_router
except ImportError as _e:
    admin_webauthn_router = None
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "admin_webauthn router unavailable (webauthn library missing): %s — endpoint disabled",
        _e,
    )

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
from app.api import webhooks_ses as webhooks_ses_router
from app.api import admin_coupons as admin_coupons_router
from app.api import me_coupons as me_coupons_router
from app.api import admin_diversity as admin_diversity_router
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
from app.api import exchange_rates as exchange_rates_router
from app.api import me_preferences as me_preferences_router
from app.api import me_devices as me_devices_router
from app.api import conversations as conversations_router
from app.api import group_conversations as group_conversations_router
from app.api import websocket_dm as websocket_dm_router
from app.api import og as og_router
from app.api import newsletter_tracking as newsletter_tracking_router
from app.api import admin_experiments as admin_experiments_router
from app.api import admin_analytics as admin_analytics_router
from app.api import admin_featured_artist as admin_featured_artist_router
from app.api import ai_collections as ai_collections_router
from app.api import admin_ai_collections as admin_ai_collections_router
from app.api import admin_payouts as admin_payouts_router  # Phase 12 B-3
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import AsyncSessionLocal, engine
from app.services.auction_jobs import auction_cron_loop
from app.services.exchange_rate_jobs import exchange_rate_cron_loop
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
from app.services.auto_renewal_jobs import auto_renewal_cron_loop
from app.services.email_digest_jobs import email_digest_cron_loop
from app.services.embedding_jobs import embedding_cron_loop
from app.services.rss_fetch_jobs import rss_fetch_cron_loop
from app.services.cohort_alert_jobs import cohort_alert_cron_loop
from app.services.ml_feed_training import ml_training_cron_loop
from app.services.artwork_caption_jobs import artwork_caption_cron_loop
from app.services.featured_artist_jobs import feature_artist_cron_loop
from app.services.ai_curation_jobs import ai_curation_cron_loop
from app.services.audit_log_cleanup_jobs import audit_log_cleanup_cron_loop
from app.services.analytics import init_posthog, shutdown_posthog
from app.services.cache import cache
from app.services.otel_setup import init_otel, shutdown_otel

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: distributed tracing SDK init (G''-1 opentelemetry-tracing)
    init_otel(app, engine)
    # Startup: analytics SDK init (G'-4 backend-posthog-integration)
    init_posthog()
    # Startup: Redis cache connect (G''-2 redis-cache-layer)
    await cache.connect()

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
    # 9th cron worker — exchange_rate (R-5 isolated, 1h interval)
    exchange_rate_task = asyncio.create_task(exchange_rate_cron_loop(interval_seconds=3600))
    # 10th cron worker — email_digest (R-5 isolated, 1h interval, B'-3)
    email_digest_task = asyncio.create_task(email_digest_cron_loop(interval_seconds=3600))
    # 11th cron worker — auto_renewal (R-5 isolated, 1h interval, B'-4)
    auto_renewal_task = asyncio.create_task(auto_renewal_cron_loop(interval_seconds=3600))
    # 12th cron worker — embedding (R-5 isolated, quick 60s + batch 86400s, L-A)
    import os as _os
    if _os.getenv("EMBEDDING_WORKER_ENABLED", "true").lower() != "false":
        embedding_task = asyncio.create_task(embedding_cron_loop())
    else:
        embedding_task = None
    # 13th cron worker — rss_fetch (R-5 isolated, 1h interval, L-B)
    if _os.getenv("RSS_FETCH_WORKER_ENABLED", "true").lower() != "false":
        rss_fetch_task = asyncio.create_task(rss_fetch_cron_loop(interval_seconds=3600))
    else:
        rss_fetch_task = None
    # 14th cron worker — cohort_alert (R-5 isolated, 1일 1회 86400s, L-F)
    if _os.getenv("COHORT_ALERT_WORKER_ENABLED", "true").lower() != "false":
        cohort_alert_task = asyncio.create_task(cohort_alert_cron_loop(interval_seconds=86400))
    else:
        cohort_alert_task = None
    # 20th cron worker — ml_training (R-5 isolated, 1일 1회 86400s, K-1)
    if _os.getenv("ML_TRAINING_WORKER_ENABLED", "true").lower() != "false":
        ml_training_task = asyncio.create_task(ml_training_cron_loop())
    else:
        ml_training_task = None
        import logging as _logging
        _logging.getLogger(__name__).info(
            "ML training worker disabled (ML_TRAINING_WORKER_ENABLED=false)"
        )
    # 21st cron worker — artwork_caption (K-3, quick 60s + batch 24h)
    if settings.artwork_caption_worker_enabled:
        artwork_caption_task = asyncio.create_task(
            artwork_caption_cron_loop(
                quick_interval_seconds=60,
                batch_interval_seconds=86400,
            )
        )
    else:
        artwork_caption_task = None
    # 22nd cron worker — featured_artist (R-5 isolated, weekly Monday 09:00 UTC, K-4)
    if _os.getenv("FEATURED_ARTIST_WORKER_ENABLED", "true").lower() != "false":
        featured_artist_task = asyncio.create_task(feature_artist_cron_loop())
    else:
        featured_artist_task = None
        import logging as _logging2
        _logging2.getLogger(__name__).info(
            "Featured artist worker disabled (FEATURED_ARTIST_WORKER_ENABLED=false)"
        )
    # 23rd cron worker — ai_curation (R-5 isolated, weekly Monday 09:00 UTC, K-7)
    if _os.getenv("AI_CURATION_WORKER_ENABLED", "true").lower() != "false":
        ai_curation_task = asyncio.create_task(ai_curation_cron_loop())
    else:
        ai_curation_task = None
        import logging as _logging3
        _logging3.getLogger(__name__).info(
            "AI curation worker disabled (AI_CURATION_WORKER_ENABLED=false)"
        )
    # 24th cron worker — audit_log_cleanup (D-2, 일 1회 86400s, 1년 보존)
    if _os.getenv("AUDIT_LOG_CLEANUP_WORKER_ENABLED", "true").lower() != "false":
        audit_log_cleanup_task = asyncio.create_task(
            audit_log_cleanup_cron_loop(interval_seconds=86400)
        )
    else:
        audit_log_cleanup_task = None
        import logging as _logging4
        _logging4.getLogger(__name__).info(
            "Audit log cleanup worker disabled (AUDIT_LOG_CLEANUP_WORKER_ENABLED=false)"
        )

    try:
        yield
    finally:
        _base_tasks = (
            auction_task, gdpr_task, schedule_task, badge_task, settle_task,
            webhook_cleanup_task, draft_cleanup_task, tier_release_task,
            auction_promotion_task, artist_index_task, post_engagement_task,
            subscription_expiry_task, newsletter_task, exchange_rate_task,
            email_digest_task, auto_renewal_task,
        )
        all_tasks = (
            _base_tasks
            + ((embedding_task,) if embedding_task else ())
            + ((rss_fetch_task,) if rss_fetch_task else ())
            + ((cohort_alert_task,) if cohort_alert_task else ())
            + ((ml_training_task,) if ml_training_task else ())
            + ((artwork_caption_task,) if artwork_caption_task else ())
            + ((featured_artist_task,) if featured_artist_task else ())
            + ((ai_curation_task,) if ai_curation_task else ())
            + ((audit_log_cleanup_task,) if audit_log_cleanup_task else ())
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
        # Shutdown: flush OTel span buffer before exit (G''-1)
        shutdown_otel()
        # Shutdown: close Redis connection pool (G''-2)
        await cache.shutdown()


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
if admin_webauthn_router is not None:
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
api_v1.include_router(webhooks_ses_router.router)
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
api_v1.include_router(exchange_rates_router.router)
api_v1.include_router(me_preferences_router.router)
api_v1.include_router(me_devices_router.router)
api_v1.include_router(conversations_router.router)
api_v1.include_router(conversations_router.admin_router)
# L-C Group DM + WebSocket (Phase 9)
api_v1.include_router(group_conversations_router.router)
api_v1.include_router(websocket_dm_router.router)
api_v1.include_router(og_router.router)
api_v1.include_router(newsletter_tracking_router.router)
# Phase 10 K-8: ML A/B 테스트 관리 API
api_v1.include_router(admin_experiments_router.router)
# Phase 10 K-2: Diversity Reranking 설정 관리 API
api_v1.include_router(admin_diversity_router.router)
# Phase 12 B-2: 통합 Analytics 대시보드 API
api_v1.include_router(admin_analytics_router.router)
# Phase 10 K-4: AI Featured Artist 주간 자동 선정 admin 검수 큐 API
api_v1.include_router(admin_featured_artist_router.router)
# Phase 10 K-7: AI 큐레이션 컬렉션 (Editor's Pick 자동 생성)
api_v1.include_router(ai_collections_router.router)
api_v1.include_router(admin_ai_collections_router.router)
# Phase 12 B-3: KYC 검수 큐 + 정산 이력 + Stripe Connect 상태 admin API
api_v1.include_router(admin_payouts_router.router)
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
