from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.config.auth import HttpSecurityMiddleware


async def ok_response(_request):
    return JSONResponse({"status": "ok"})


def make_client():
    app = Starlette(routes=[Route("/{path:path}", ok_response, methods=["GET", "POST"])])
    return TestClient(HttpSecurityMiddleware(app))


def test_mcp_request_requires_bearer_token():
    response = make_client().post("/mcp")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_mcp_request_accepts_bearer_token_without_browser_origin():
    response = make_client().post("/mcp", headers={"Authorization": "Bearer request-token"})

    assert response.status_code == 200


def test_mcp_request_rejects_untrusted_browser_origin_before_authentication():
    response = make_client().post("/mcp", headers={"Origin": "https://untrusted.example"})

    assert response.status_code == 403


def test_health_endpoint_does_not_require_credentials():
    response = make_client().get("/health")

    assert response.status_code == 200