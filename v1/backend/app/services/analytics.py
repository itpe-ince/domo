"""Server-side analytics service — G'-4 backend-posthog-integration.

Wraps the PostHog Python SDK with:
  - Mock mode fallback (POSTHOG_API_KEY unset → console log only)
  - PII redaction (email, phone, card_number, iban, ssn stripped before capture)
  - Graceful shutdown (flush on app exit)
  - OTel trace_id propagation (G''-1 booster): when an active span exists,
    "trace_id" is injected into event properties so PostHog events can be
    correlated with AWS X-Ray traces in production.

Usage:
    from app.services.analytics import capture_event

    capture_event(str(user.id), "user_signup_confirmed", {"method": "google"})

All captured events use user.id as distinct_id, consistent with the frontend
identifyUser(user.id) call from Phase 6 A-1 PostHog integration.

GDPR note:
  Phase 8+ carry-over — User.consent_analytics column + opt-out skip.
  This service captures for all user IDs. PII redact is the only GDPR control applied here.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# PII keys that must never reach PostHog — stripped from all event properties.
_PII_KEYS: frozenset[str] = frozenset(
    {"email", "phone", "card_number", "iban", "ssn", "phone_number"}
)

# Singleton flag: True once init_posthog() succeeds with a real API key.
_posthog_enabled: bool = False


def init_posthog() -> None:
    """Called once at app startup (lifespan).

    If POSTHOG_API_KEY is not set, runs in Mock mode — events are logged
    to the console instead of being sent to PostHog.
    """
    global _posthog_enabled  # noqa: PLW0603

    from app.core.config import get_settings
    settings = get_settings()

    if not settings.posthog_api_key:
        log.info("[Analytics] PostHog Mock mode — POSTHOG_API_KEY not set, events will be logged only")
        _posthog_enabled = False
        return

    import posthog as _ph
    _ph.api_key = settings.posthog_api_key
    _ph.host = settings.posthog_host or "https://us.i.posthog.com"
    # Disable the built-in default logging handler to avoid duplicate log lines.
    _ph.debug = False
    _posthog_enabled = True
    log.info("[Analytics] PostHog SDK initialized (host=%s)", _ph.host)


def _redact_pii(props: dict) -> dict:
    """Strip PII keys from event properties before capture.

    Removes: email, phone, phone_number, card_number, iban, ssn (case-insensitive key match).
    """
    return {k: v for k, v in props.items() if k.lower() not in _PII_KEYS}


def _inject_trace_id(props: dict) -> dict:
    """Inject current OTel trace_id into event properties for X-Ray correlation.

    No-op when:
    - OTel Mock mode (OTEL_ENABLED=False) — no active span, returns props unchanged.
    - No active span in the current execution context.
    - trace_id is already present in props (caller-provided value wins).

    The trace_id is a 32-char hex string matching the W3C TraceContext format
    used by AWS X-Ray. This enables PostHog → X-Ray trace correlation in
    production dashboards.
    """
    if "trace_id" in props:
        return props  # caller-provided value wins
    try:
        from opentelemetry import trace as _otel_trace
        span = _otel_trace.get_current_span()
        ctx = span.get_span_context()
        # trace_id == 0 means no active span (NoOpSpan / invalid context)
        if ctx.trace_id != 0:
            return {**props, "trace_id": format(ctx.trace_id, "032x")}
    except Exception:  # noqa: BLE001 — never raise from analytics helper
        pass
    return props


def capture_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
) -> None:
    """Capture a server-side analytics event.

    Args:
        distinct_id: The user's UUID string (user.id). Consistent with frontend identifyUser().
        event: Event name, e.g. "user_signup_confirmed".
        properties: Optional dict of event properties. PII keys are stripped automatically.

    Behavior:
        - Mock mode (POSTHOG_API_KEY unset): logs to console, no SDK call.
        - Real mode: sends via posthog.capture() with async batching (SDK handles flush).
        - Never raises — errors are logged and swallowed to avoid impacting main request path.
        - G''-1 booster: injects OTel trace_id when an active span exists.
    """
    safe_props = _inject_trace_id(_redact_pii(properties or {}))

    if not _posthog_enabled:
        log.info(
            "[Analytics] event=%s user=%s props=%s",
            event,
            distinct_id,
            safe_props,
        )
        return

    try:
        import posthog as _ph
        _ph.capture(distinct_id=distinct_id, event=event, properties=safe_props)
    except Exception:  # noqa: BLE001
        log.exception("[Analytics] capture_event failed (event=%s user=%s)", event, distinct_id)


def shutdown_posthog() -> None:
    """Called at app shutdown (lifespan finally block).

    Flushes the PostHog batch queue before process exit to avoid dropping
    buffered events. No-op in Mock mode.
    """
    if not _posthog_enabled:
        return
    try:
        import posthog as _ph
        _ph.shutdown()
        log.info("[Analytics] PostHog SDK flushed and shut down")
    except Exception:  # noqa: BLE001
        log.exception("[Analytics] shutdown_posthog failed")
