"""OpenTelemetry SDK setup — G''-1 opentelemetry-tracing.

Provides init_otel() / shutdown_otel() helpers called from main.py lifespan.

Mock mode (default — OTEL_ENABLED=False):
  init_otel() returns immediately after logging a single info line.
  All tracer.start_as_current_span() calls in manual-span sites remain no-op
  because opentelemetry.trace.get_tracer() returns a NoOpTracer when no
  TracerProvider has been set.

Production (OTEL_ENABLED=True):
  - TracerProvider with TraceIdRatioBased sampler (OTEL_SAMPLING_RATE=0.1)
  - OTLP gRPC exporter → AWS X-Ray ADOT Collector sidecar (localhost:4317)
  - Auto-instrumentation for FastAPI, SQLAlchemy, httpx (covers Stripe/SES/LLM
    Gateway calls transparently)
  - BatchSpanProcessor for low-overhead async export

PII policy (constraint #6):
  span attributes must NEVER contain email, phone, card_number, iban, ssn.
  Use only IDs (user_id, auction_id, post_id) as string attributes.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def init_otel(app, engine) -> None:  # type: ignore[type-arg]
    """Initialize the OpenTelemetry SDK and register auto-instrumentation.

    Args:
        app:    The FastAPI application instance (root app, before /v1 sub-mount).
        engine: The SQLAlchemy async engine (from app.db.session).

    No-op when OTEL_ENABLED=False (default). In that case the opentelemetry-api
    stubs still exist in the process so all tracer.start_as_current_span() calls
    in cron workers / critical-path endpoints return a no-op span with zero
    allocation overhead.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.otel_enabled:
        log.info(
            "[OTel] Mock mode — OTEL_ENABLED=false, tracing disabled (zero overhead)"
        )
        return

    # All heavy imports intentionally inside the if-branch so that the OTel
    # packages are never loaded in Mock mode (faster cold-start, smaller
    # production footprint for environments that skip OTel entirely).
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "1.0",
            "deployment.environment": settings.environment,
        }
    )

    sampler = TraceIdRatioBased(settings.otel_sampling_rate)
    provider = TracerProvider(resource=resource, sampler=sampler)

    if settings.otel_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        exporter = OTLPSpanExporter(
            endpoint=settings.otel_otlp_endpoint,
            insecure=True,  # TLS terminated at ADOT sidecar / VPC boundary
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        log.info(
            "[OTel] OTLP exporter configured → %s (sampling=%.0f%%)",
            settings.otel_otlp_endpoint,
            settings.otel_sampling_rate * 100,
        )
    else:
        log.warning(
            "[OTel] OTEL_ENABLED=true but OTEL_OTLP_ENDPOINT not set — "
            "spans will be created but not exported"
        )

    trace.set_tracer_provider(provider)

    # ── Auto-instrumentation ─────────────────────────────────────────────────
    # FastAPI: captures route handler spans with HTTP method/status attributes.
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)

    # SQLAlchemy: captures every DB statement span (query text + row count).
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    SQLAlchemyInstrumentor().instrument(engine=engine)

    # httpx: covers Stripe API, AWS SES, tuzigroup LLM Gateway calls.
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    HTTPXClientInstrumentor().instrument()

    log.info(
        "[OTel] SDK initialized: service=%s env=%s sampling=%.0f%%",
        settings.otel_service_name,
        settings.environment,
        settings.otel_sampling_rate * 100,
    )


def shutdown_otel() -> None:
    """Flush and shut down the TracerProvider on app exit.

    No-op in Mock mode (OTEL_ENABLED=False) — the NoOpTracerProvider has no
    pending spans to flush.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if not settings.otel_enabled:
        return

    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
            log.info("[OTel] TracerProvider flushed and shut down")
    except Exception:  # noqa: BLE001
        log.exception("[OTel] shutdown_otel failed — spans may have been dropped")


def get_tracer(name: str):
    """Return an opentelemetry.trace.Tracer for the given instrumentation scope.

    In Mock mode this returns a NoOpTracer — all .start_as_current_span() calls
    are lightweight no-ops. Import this helper in cron workers and service files
    instead of importing opentelemetry.trace directly so that the import path is
    consistent and easy to search.

    Usage:
        tracer = get_tracer(__name__)

        async def some_cron_loop():
            with tracer.start_as_current_span("cron.some_worker") as span:
                span.set_attribute("rows_processed", n)
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        # opentelemetry-api not installed — return no-op tracer for graceful degrade
        return _NoOpTracer()


class _NoOpSpan:
    def set_attribute(self, *args, **kwargs): pass
    def set_attributes(self, *args, **kwargs): pass
    def record_exception(self, *args, **kwargs): pass
    def add_event(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def is_recording(self): return False
    def get_span_context(self):
        class _Ctx:
            trace_id = 0
            span_id = 0
        return _Ctx()


class _NoOpTracer:
    def start_as_current_span(self, *args, **kwargs): return _NoOpSpan()
    def start_span(self, *args, **kwargs): return _NoOpSpan()
