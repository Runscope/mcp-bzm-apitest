"""
OpenTelemetry instrumentation helpers for the BlazeMeter API Test MCP server.

All functions degrade gracefully to no-ops when opentelemetry-api is not installed,
and TracerProvider setup is skipped when opentelemetry-sdk is not installed.
"""

import contextlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode

    _OTEL_API_AVAILABLE = True
except ImportError:
    _OTEL_API_AVAILABLE = False


def init_telemetry(service_name: str, service_version: str) -> None:
    """
    Initialise a TracerProvider with service.name / service.version resource attributes.

    No-op when opentelemetry-sdk is not installed (opentelemetry-api's no-op provider
    is used automatically in that case).
    """
    if not _OTEL_API_AVAILABLE:
        return
    try:
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider

        resource = Resource.create({SERVICE_NAME: service_name, SERVICE_VERSION: service_version})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        logger.debug(
            "OTel TracerProvider initialised (service=%s, version=%s)", service_name, service_version
        )
    except ImportError:
        # SDK not installed — api's no-op provider is already active, nothing to do.
        pass
    except Exception:
        logger.debug("OTel TracerProvider init failed; continuing without tracing.", exc_info=True)


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

    Covers cases where api_request() absorbs HTTP errors (e.g. 401/403) and returns
    BaseResult(error=...) instead of raising, which would otherwise leave the span successful.
    """
    if result is not None and getattr(result, "error", None):
        record_span_error(span, "api_error")
    return result


def http_status_to_error_type(status_code: int) -> str:
    """Map an HTTP status code to an OTel error.type string."""
    if status_code in (401, 403):
        return "auth_error"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "server_error"
    return f"http_{status_code}"


@contextlib.asynccontextmanager
async def tool_span(tool_name: str, action: str, parent_context=None):
    """
    Async context manager that wraps a tool call in an OTel span.

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
    with tracer.start_as_current_span(
        f"tools/call {tool_name}",
        context=parent_context,
    ) as span:
        span.set_attribute("mcp.method.name", "tools/call")
        span.set_attribute("gen_ai.tool.name", tool_name)
        span.set_attribute("gen_ai.operation.name", "execute_tool")
        span.set_attribute("mcp.tool.action", action)
        yield span
