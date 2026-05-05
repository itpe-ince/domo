"""Health check endpoint with DB liveness and Prometheus /metrics.

GET /v1/health         — basic (existing), now enhanced with DB check
GET /v1/health/ready   — DB connection check
GET /metrics           — Prometheus exposition (mounted on root app, not api_v1)

Notes:
- /metrics is mounted on the root ASGI app so it lives at /metrics (not /v1/metrics)
- prometheus_client is optional: /metrics returns 503 if not installed
"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # type: ignore[import]
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


@router.get("/health/ready")
async def health_ready():
    """Deep health check: DB connection liveness.

    Returns:
        200 {status: "ok"}           — DB responding
        503 {status: "unhealthy"}    — DB unreachable
    """
    checks: dict[str, Any] = {}

    # DB check
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "unhealthy"
    status_code = 200 if overall == "ok" else 503
    return Response(
        content=f'{{"status": "{overall}", "checks": {_checks_json(checks)}}}',
        media_type="application/json",
        status_code=status_code,
    )


def _checks_json(checks: dict[str, Any]) -> str:
    parts = ", ".join(f'"{k}": "{v}"' for k, v in checks.items())
    return "{" + parts + "}"


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus text exposition endpoint.

    Protected by METRICS_ENABLED env flag and Authorization Bearer token.
    Mount on root app (not api_v1) to avoid /v1 prefix.
    """
    settings = get_settings()

    if not settings.metrics_enabled:
        return Response(
            content='{"error": "metrics not enabled"}',
            media_type="application/json",
            status_code=503,
        )

    if not _PROMETHEUS_AVAILABLE:
        return Response(
            content='{"error": "prometheus_client not installed"}',
            media_type="application/json",
            status_code=503,
        )

    # Token auth
    if settings.metrics_token:
        auth = request.headers.get("Authorization", "")
        expected = f"Bearer {settings.metrics_token}"
        if not secrets.compare_digest(auth, expected):
            return Response(
                content='{"error": "unauthorized"}',
                media_type="application/json",
                status_code=401,
            )

    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
