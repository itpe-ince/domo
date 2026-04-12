import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin as admin_router
from app.api import admin_dashboard as admin_dashboard_router
from app.api import artists as artists_router
from app.api import auctions as auctions_router
from app.api import auth as auth_router
from app.api import guardian as guardian_router
from app.api import legal as legal_router
from app.api import me as me_router
from app.api import media as media_router
from app.api import moderation as moderation_router
from app.api import notifications as notifications_router
from app.api import orders as orders_router
from app.api import posts as posts_router
from app.api import sponsorships as sponsorships_router
from app.api import users as users_router
from app.api import webhooks as webhooks_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services.auction_jobs import auction_cron_loop
from app.services.gdpr_jobs import gdpr_cron_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: schedule background cron tasks
    auction_task = asyncio.create_task(auction_cron_loop(interval_seconds=300))
    gdpr_task = asyncio.create_task(gdpr_cron_loop(interval_seconds=3600))
    try:
        yield
    finally:
        for task in (auction_task, gdpr_task):
            task.cancel()
        for task in (auction_task, gdpr_task):
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Domo API",
    version="0.1.0",
    description="Domo prototype API (Phase 0)",
    lifespan=lifespan,
)

# CORS origins: allow both localhost and 127.0.0.1 on the configured port
# (browsers treat these as different origins, so we need to list both)
_cors_origins = [
    settings.frontend_url,
    settings.frontend_url.replace("localhost", "127.0.0.1"),
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3700",
    "http://127.0.0.1:3700",
]
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
api_v1.include_router(me_router.router)
api_v1.include_router(legal_router.router)
api_v1.include_router(guardian_router.router)
api_v1.include_router(users_router.router)
api_v1.include_router(artists_router.router)
api_v1.include_router(posts_router.router)
api_v1.include_router(media_router.router)
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


@api_v1.get("/health")
async def health():
    return {"data": {"status": "ok", "version": "0.1.0"}}


app.mount("/v1", api_v1)


@app.get("/")
async def root():
    return {"data": {"name": "Domo API", "version": "0.1.0", "docs": "/docs"}}
