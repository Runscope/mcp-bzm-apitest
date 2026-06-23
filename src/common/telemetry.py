"""
OpenTelemetry instrumentation helpers for the BlazeMeter API Test MCP server.

All functions degrade gracefully to no-ops when opentelemetry-api is not installed,
and TracerProvider/MeterProvider setup is skipped when opentelemetry-sdk is not installed.
"""

import contextlib
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_OTLP_ENDPOINT = "https://grpc.public.prd.shared.perforce.com"

try:
    from opentelemetry import metrics, trace
    from opentelemetry.trace import SpanKind, Status, StatusCode

    _OTEL_API_AVAILABLE = True
except ImportError:
    _OTEL_API_AVAILABLE = False


def _otlp_exporters():
    """
    Return (OTLPSpanExporter class, OTLPMetricExporter class, endpoint) based on
    OTEL_EXPORTER_OTLP_PROTOCOL / OTEL_EXPORTER_OTLP_ENDPOINT env vars.

    Defaults to gRPC with the Perforce shared ingress endpoint.
    """
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc").strip().lower()
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_OTLP_ENDPOINT)

    if protocol in ("http/protobuf", "http/json"):
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    else:
        if protocol != "grpc":
            logger.debug("Unknown OTEL_EXPORTER_OTLP_PROTOCOL=%r; falling back to gRPC", protocol)
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

    return OTLPSpanExporter, OTLPMetricExporter, endpoint, protocol


def init_telemetry(service_name: str, service_version: str) -> None:
    """
    Initialise TracerProvider and MeterProvider with service.name / service.version
    resource attributes and OTLP exporters.

    Protocol and endpoint are read from OTEL_EXPORTER_OTLP_PROTOCOL /
    OTEL_EXPORTER_OTLP_ENDPOINT env vars; default to gRPC + Perforce shared ingress.
    No-op when opentelemetry-sdk is not installed.
    """
    if not _OTEL_API_AVAILABLE:
        return
    try:
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({SERVICE_NAME: service_name, SERVICE_VERSION: service_version})

        try:
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            SpanExporter, MetricExporter, endpoint, protocol = _otlp_exporters()

            trace_provider = TracerProvider(resource=resource)
            trace_provider.add_span_processor(BatchSpanProcessor(SpanExporter(endpoint=endpoint)))
            trace.set_tracer_provider(trace_provider)

            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[PeriodicExportingMetricReader(MetricExporter(endpoint=endpoint))],
            )
            metrics.set_meter_provider(meter_provider)

            logger.debug(
                "OTel initialised (protocol=%s, endpoint=%s, service=%s, version=%s)",
                protocol,
                endpoint,
                service_name,
                service_version,
            )
        except ImportError:
            logger.debug("OTLP exporter package not installed; telemetry not exported.")

    except ImportError:
        # SDK not installed — api's no-op providers are already active, nothing to do.
        pass
    except Exception:
        logger.debug("OTel init failed; continuing without telemetry.", exc_info=True)


def get_meta_from_ctx(ctx: Any) -> Optional[Dict[str, Any]]:
    """Extract the MCP _meta dict from a FastMCP Context, if present."""
    try:
        return ctx.request_context.request.params.meta or {}
    except Exception:
        return {}


def extract_trace_context(meta: Optional[Dict[str, Any]]):
    """
    Extract a W3C TraceContext from the MCP _meta dict and return an OTel Context.

    Returns None when tracing is unavailable or no trace headers are present.
    """
    if not _OTEL_API_AVAILABLE or not meta:
        return None
    try:
        from opentelemetry.propagate import extract

        carrier = {}
        if "traceparent" in meta:
            carrier["traceparent"] = meta["traceparent"]
        if "tracestate" in meta:
            carrier["tracestate"] = meta["tracestate"]
        if not carrier:
            return None
        return extract(carrier)
    except Exception:
        return None


def record_span_error(span: Any, error_type: str) -> None:
    """Mark a span as failed and set the error.type attribute."""
    if not _OTEL_API_AVAILABLE or span is None:
        return
    try:
        span.set_attribute("error.type", error_type)
        span.set_status(Status(StatusCode.ERROR))
    except Exception:
        pass


def check_result_error(span: Any, result: Any) -> Any:
    """Mark span as failed if the returned BaseResult carries an error.

    Covers cases where api_request() absorbs errors and returns BaseResult(error=...)
    instead of raising, which would otherwise leave the span successful.
    """
    if result is not None and getattr(result, "error", None):
        record_span_error(span, "tool_error")
    return result


def http_status_to_error_type(status_code: int) -> str:
    """Map an HTTP status code to an OTel error.type string (OTel MCP semconv values)."""
    if status_code in (401, 403):
        return "auth_failed"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    return "tool_error"


def _record_operation_duration(tool_name: str, span: Any, duration: float) -> None:
    """Record mcp.server.operation.duration histogram per OTel MCP semconv."""
    if not _OTEL_API_AVAILABLE:
        return
    try:
        meter = metrics.get_meter("mcp-bzm-apitest")
        histogram = meter.create_histogram(
            name="mcp.server.operation.duration",
            unit="s",
            description="Duration of MCP server tool calls",
        )
        attrs: Dict[str, Any] = {
            "mcp.method.name": "tools/call",
            "gen_ai.tool.name": tool_name,
        }
        if span is not None:
            try:
                error_type = span.attributes.get("error.type")
                if error_type:
                    attrs["error.type"] = error_type
            except Exception:
                pass
        histogram.record(duration, attributes=attrs)
    except Exception:
        pass


@contextlib.asynccontextmanager
async def tool_span(tool_name: str, action: str, parent_context=None):
    """
    Async context manager that wraps a tool call in an OTel span and records
    mcp.server.operation.duration on exit.

    Usage::

        async with tool_span(tool_name, action, parent_context) as span:
            ...  # span is the active Span, or None when OTel is unavailable

    Attributes set on the span follow MCP / GenAI semantic conventions:
      - mcp.method.name = "tools/call"
      - gen_ai.tool.name = <tool_name>
      - gen_ai.operation.name = "execute_tool"
      - mcp.tool.action = <action>
    """
    if not _OTEL_API_AVAILABLE:
        yield None
        return

    tracer = trace.get_tracer("mcp-bzm-apitest")
    start = time.perf_counter()
    with tracer.start_as_current_span(
        f"tools/call {tool_name}",
        context=parent_context,
        kind=SpanKind.SERVER,
    ) as span:
        span.set_attribute("mcp.method.name", "tools/call")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("mcp.tool.action", action)
        try:
            yield span
        finally:
            _record_operation_duration(tool_name, span, time.perf_counter() - start)
