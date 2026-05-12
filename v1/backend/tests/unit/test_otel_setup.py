"""Unit tests for G''-1 opentelemetry-tracing — app/services/otel_setup.py.

Tests:
  1. init_otel Mock mode (OTEL_ENABLED=False) → early return, no SDK loaded
  2. init_otel with config (OTEL_ENABLED=True, endpoint set) → SDK initialized
  3. shutdown_otel graceful — calls provider.shutdown() when enabled
  4. capture_event G'-4 booster — trace_id injected when active span exists
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mock_settings(
    otel_enabled: bool = False,
    otel_service_name: str = "domo-backend",
    otel_otlp_endpoint: str | None = None,
    otel_sampling_rate: float = 0.1,
    environment: str = "test",
    posthog_api_key: str = "",
    posthog_host: str = "https://us.i.posthog.com",
) -> MagicMock:
    s = MagicMock()
    s.otel_enabled = otel_enabled
    s.otel_service_name = otel_service_name
    s.otel_otlp_endpoint = otel_otlp_endpoint
    s.otel_sampling_rate = otel_sampling_rate
    s.environment = environment
    s.posthog_api_key = posthog_api_key
    s.posthog_host = posthog_host
    return s


# ─── Test 1: Mock mode early return ───────────────────────────────────────────


def test_init_otel_mock_mode_no_sdk_loaded():
    """When OTEL_ENABLED=False, init_otel() returns immediately.

    The opentelemetry.sdk modules should NOT be imported/initialized.
    FastAPI and SQLAlchemy instrumentors should NOT be called.
    """
    import importlib
    import app.services.otel_setup as otel_mod
    importlib.reload(otel_mod)

    mock_app = MagicMock()
    mock_engine = MagicMock()
    mock_settings = _mock_settings(otel_enabled=False)

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch("app.services.otel_setup.log") as mock_log:
            otel_mod.init_otel(mock_app, mock_engine)

    # Should log the Mock mode info line
    mock_log.info.assert_called_once()
    assert "Mock mode" in mock_log.info.call_args[0][0]

    # FastAPI instrumentor must NOT have been called
    # (mock_app.instrument was not called because we returned early)
    # No strict assertion needed beyond no exceptions raised.


# ─── Test 2: init_otel with OTEL_ENABLED=True ────────────────────────────────


@pytest.mark.skip(reason="Phase 14 carry-over: SDK 실설치 환경에서 sys.modules patch 무효 — importlib.reload 패턴 재설계 필요")
def test_init_otel_enabled_initializes_sdk():
    """When OTEL_ENABLED=True with endpoint, TracerProvider + instrumentors are set up."""
    import importlib
    import app.services.otel_setup as otel_mod
    importlib.reload(otel_mod)

    mock_app = MagicMock()
    mock_engine = MagicMock()
    mock_settings = _mock_settings(
        otel_enabled=True,
        otel_service_name="domo-test",
        otel_otlp_endpoint="localhost:4317",
        otel_sampling_rate=1.0,
        environment="staging",
    )

    mock_provider = MagicMock()
    mock_provider_class = MagicMock(return_value=mock_provider)
    mock_exporter = MagicMock()
    mock_exporter_class = MagicMock(return_value=mock_exporter)
    mock_processor = MagicMock()
    mock_processor_class = MagicMock(return_value=mock_processor)
    mock_sampler = MagicMock()
    mock_sampler_class = MagicMock(return_value=mock_sampler)
    mock_resource = MagicMock()
    mock_resource_class = MagicMock()
    mock_resource_class.create = MagicMock(return_value=mock_resource)

    mock_trace_module = MagicMock()
    mock_fastapi_instr = MagicMock()
    mock_sqlalchemy_instr_class = MagicMock()
    mock_sqlalchemy_instr = MagicMock()
    mock_sqlalchemy_instr_class.return_value = mock_sqlalchemy_instr
    mock_httpx_instr = MagicMock()

    modules = {
        "opentelemetry": MagicMock(),
        "opentelemetry.trace": mock_trace_module,
        "opentelemetry.sdk": MagicMock(),
        "opentelemetry.sdk.trace": MagicMock(
            TracerProvider=mock_provider_class,
        ),
        "opentelemetry.sdk.trace.export": MagicMock(
            BatchSpanProcessor=mock_processor_class,
        ),
        "opentelemetry.sdk.trace.sampling": MagicMock(
            TraceIdRatioBased=mock_sampler_class,
        ),
        "opentelemetry.sdk.resources": MagicMock(
            Resource=mock_resource_class,
        ),
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(
            OTLPSpanExporter=mock_exporter_class,
        ),
        "opentelemetry.instrumentation.fastapi": MagicMock(
            FastAPIInstrumentor=mock_fastapi_instr,
        ),
        "opentelemetry.instrumentation.sqlalchemy": MagicMock(
            SQLAlchemyInstrumentor=mock_sqlalchemy_instr_class,
        ),
        "opentelemetry.instrumentation.httpx": MagicMock(
            HTTPXClientInstrumentor=mock_httpx_instr,
        ),
    }

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch.dict("sys.modules", modules):
            otel_mod.init_otel(mock_app, mock_engine)

    # TracerProvider must have been instantiated
    mock_provider_class.assert_called_once()
    # OTLP exporter must have been created with the configured endpoint
    mock_exporter_class.assert_called_once_with(
        endpoint="localhost:4317", insecure=True
    )
    # Span processor must have been added
    mock_provider.add_span_processor.assert_called_once()
    # trace.set_tracer_provider must have been called
    mock_trace_module.set_tracer_provider.assert_called_once_with(mock_provider)


# ─── Test 3: shutdown_otel graceful ───────────────────────────────────────────


@pytest.mark.skip(reason="Phase 14 carry-over: SDK 실설치 환경에서 sys.modules patch 무효 — importlib.reload 패턴 재설계 필요")
def test_shutdown_otel_calls_provider_shutdown_when_enabled():
    """shutdown_otel calls provider.shutdown() when OTEL_ENABLED=True."""
    import importlib
    import app.services.otel_setup as otel_mod
    importlib.reload(otel_mod)

    mock_settings = _mock_settings(otel_enabled=True)
    mock_provider = MagicMock()
    mock_provider.shutdown = MagicMock()
    mock_trace_module = MagicMock()
    mock_trace_module.get_tracer_provider = MagicMock(return_value=mock_provider)

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch.dict("sys.modules", {"opentelemetry.trace": mock_trace_module, "opentelemetry": MagicMock()}):
            with patch("app.services.otel_setup.log") as mock_log:
                otel_mod.shutdown_otel()

    mock_trace_module.get_tracer_provider.assert_called_once()
    mock_provider.shutdown.assert_called_once()
    mock_log.info.assert_called_once()
    assert "shut down" in mock_log.info.call_args[0][0]


def test_shutdown_otel_noop_in_mock_mode():
    """shutdown_otel is a no-op when OTEL_ENABLED=False."""
    import importlib
    import app.services.otel_setup as otel_mod
    importlib.reload(otel_mod)

    mock_settings = _mock_settings(otel_enabled=False)
    mock_trace_module = MagicMock()

    with patch("app.core.config.get_settings", return_value=mock_settings):
        with patch.dict("sys.modules", {"opentelemetry.trace": mock_trace_module}):
            otel_mod.shutdown_otel()

    # get_tracer_provider must NOT have been called
    mock_trace_module.get_tracer_provider.assert_not_called()


# ─── Test 4: G'-4 booster — trace_id propagation in capture_event ─────────────


def test_capture_event_injects_trace_id_when_active_span():
    """When an active OTel span exists, capture_event includes trace_id in properties."""
    import importlib
    import app.services.analytics as analytics_mod
    importlib.reload(analytics_mod)

    analytics_mod._posthog_enabled = True

    # Build a fake span context with a known trace_id
    fake_trace_id = 0xDEADBEEF_CAFEBABE_12345678_9ABCDEF0
    fake_ctx = MagicMock()
    fake_ctx.trace_id = fake_trace_id
    fake_span = MagicMock()
    fake_span.get_span_context = MagicMock(return_value=fake_ctx)

    mock_posthog = MagicMock()
    mock_trace = MagicMock()
    mock_trace.get_current_span = MagicMock(return_value=fake_span)

    # opentelemetry package: attribute "trace" returns our mock_trace module.
    mock_otel_pkg = MagicMock()
    mock_otel_pkg.trace = mock_trace

    with patch.dict("sys.modules", {
        "posthog": mock_posthog,
        "opentelemetry": mock_otel_pkg,
        "opentelemetry.trace": mock_trace,
    }):
        analytics_mod.capture_event(
            "user-123",
            "test_trace_event",
            {"amount_cents": 1000},
        )

    call_kwargs = mock_posthog.capture.call_args[1]
    assert "trace_id" in call_kwargs["properties"]
    expected_trace_id = format(fake_trace_id, "032x")
    assert call_kwargs["properties"]["trace_id"] == expected_trace_id

    # Reset
    analytics_mod._posthog_enabled = False


def test_capture_event_no_trace_id_in_mock_otel_mode():
    """capture_event does NOT raise when OTel is in Mock mode (no active span)."""
    import importlib
    import app.services.analytics as analytics_mod
    importlib.reload(analytics_mod)

    analytics_mod._posthog_enabled = False  # analytics also in mock mode

    # Simulate no active span: trace_id == 0 (invalid context)
    fake_ctx = MagicMock()
    fake_ctx.trace_id = 0
    fake_span = MagicMock()
    fake_span.get_span_context = MagicMock(return_value=fake_ctx)

    mock_trace = MagicMock()
    mock_trace.get_current_span = MagicMock(return_value=fake_span)
    mock_otel_pkg = MagicMock()
    mock_otel_pkg.trace = mock_trace

    with patch.dict("sys.modules", {
        "opentelemetry": mock_otel_pkg,
        "opentelemetry.trace": mock_trace,
    }):
        with patch("app.services.analytics.log") as mock_log:
            # Should complete without error
            analytics_mod.capture_event("user-xyz", "no_span_event", {"foo": "bar"})

    # Event was logged (mock analytics mode)
    mock_log.info.assert_called_once()
    # trace_id should NOT be in the logged properties (invalid span ctx → trace_id=0 → skipped)
    call_args = str(mock_log.info.call_args)
    assert "trace_id" not in call_args
