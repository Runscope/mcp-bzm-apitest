import anyio
import uvicorn
from mcp.server.fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from src.config.token import BzmApimToken, BzmApimTokenError

HEALTH_PATHS = frozenset({"/health", "/healthz"})


def parse_bearer_token(authorization: str | None) -> BzmApimToken | None:
    """Parse an API Test token from an HTTP Authorization header."""
    if not authorization:
        return None

    scheme, separator, credentials = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not separator or not credentials.strip():
        return None

    try:
        return BzmApimToken(credentials.strip())
    except BzmApimTokenError:
        return None


class TokenResolver:
    """Resolve API Test credentials for local or hosted tool invocations."""

    def __init__(self, startup_token: BzmApimToken | str | None, hosted: bool = False):
        # api_request interpolates this into the header, and BzmApimToken.__repr__ masks itself.
        self._startup_token = (
            startup_token.token if isinstance(startup_token, BzmApimToken) else startup_token
        )
        self._hosted = hosted

    def get_token(self, ctx: Context) -> str | None:
        if not self._hosted:
            return self._startup_token

        request_context = getattr(ctx, "request_context", None)
        request = getattr(request_context, "request", None)
        headers = getattr(request, "headers", None)
        authorization = headers.get("authorization") if headers is not None else None
        token = parse_bearer_token(authorization)
        return token.token if token is not None else None


class HttpSecurityMiddleware:
    """Reject untrusted browser origins and unauthenticated MCP requests."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        origin = request.headers.get("origin")
        if origin:
            response = JSONResponse({"error": "Forbidden origin"}, status_code=403)
            await response(scope, receive, send)
            return

        if (
            scope.get("path") not in HEALTH_PATHS
            and parse_bearer_token(request.headers.get("authorization")) is None
        ):
            response = JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def register_health_routes(mcp: FastMCP) -> None:
    """Register unauthenticated health probes for a hosted MCP deployment."""

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})


def run_streamable_http(mcp: FastMCP) -> None:
    """Serve FastMCP over Streamable HTTP behind the HTTP security boundary."""
    register_health_routes(mcp)

    async def serve() -> None:
        app = HttpSecurityMiddleware(mcp.streamable_http_app())
        config = uvicorn.Config(
            app,
            host=mcp.settings.host,
            port=mcp.settings.port,
            log_level=mcp.settings.log_level.lower(),
        )
        await uvicorn.Server(config).serve()

    anyio.run(serve)
