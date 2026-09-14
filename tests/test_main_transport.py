import sys
from unittest.mock import Mock

import pytest

import main


class DummyFastMCP:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.run_calls = []

    def run(self, transport="stdio"):
        self.run_calls.append(transport)


def patch_server_dependencies(monkeypatch):
    monkeypatch.setattr(main, "FastMCP", DummyFastMCP)
    monkeypatch.setattr(main, "init_telemetry", Mock())
    monkeypatch.setattr(main, "register_tools", Mock())
    monkeypatch.setattr(main, "get_api_token", Mock(return_value=Mock()))


def test_transport_prefers_cli_then_environment_then_stdio(monkeypatch):
    monkeypatch.delenv("BZM_API_TEST_MCP_TRANSPORT", raising=False)
    assert main.resolve_mcp_transport("") == "stdio"

    monkeypatch.setenv("BZM_API_TEST_MCP_TRANSPORT", "http")
    assert main.resolve_mcp_transport("") == "http"
    assert main.resolve_mcp_transport("stdio") == "stdio"


def test_invalid_transport_has_clear_error():
    with pytest.raises(ValueError, match="Invalid MCP transport"):
        main.resolve_mcp_transport("invalid")


def test_bare_mcp_uses_environment_transport(monkeypatch):
    run = Mock()
    monkeypatch.setattr(main, "run", run)
    monkeypatch.setenv("BZM_API_TEST_MCP_TRANSPORT", "http")
    monkeypatch.setattr(sys, "argv", ["main.py", "--mcp"])

    main.main()

    run.assert_called_once_with(log_level="CRITICAL", base_url=None, transport="http")


def test_http_uses_streamable_http_and_request_scoped_credentials(monkeypatch):
    patch_server_dependencies(monkeypatch)
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    monkeypatch.setenv("FASTMCP_PORT", "8012")

    mcp, wire_transport = main.build_mcp_server(transport="http")

    assert wire_transport == "streamable-http"
    assert mcp.kwargs["host"] == "0.0.0.0"
    assert mcp.kwargs["port"] == 8012
    assert mcp.kwargs["streamable_http_path"] == "/mcp"
    assert mcp.kwargs["stateless_http"] is True
    main.register_tools.assert_called_once_with(mcp, None, hosted=True)
    main.get_api_token.assert_not_called()


def test_stdio_preserves_startup_credential_behavior(monkeypatch):
    patch_server_dependencies(monkeypatch)

    mcp, wire_transport = main.build_mcp_server(transport="stdio")

    assert wire_transport == "stdio"
    main.register_tools.assert_called_once_with(mcp, main.get_api_token.return_value, hosted=False)


def test_http_run_uses_the_asgi_server(monkeypatch):
    patch_server_dependencies(monkeypatch)
    mcp = DummyFastMCP()
    monkeypatch.setattr(main, "build_mcp_server", Mock(return_value=(mcp, "streamable-http")))
    monkeypatch.setattr(main, "run_streamable_http", Mock())

    main.run(transport="http")

    main.run_streamable_http.assert_called_once_with(mcp)
    assert mcp.run_calls == []