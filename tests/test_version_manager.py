"""
Tests for src/tools/version_manager.py
"""

from unittest.mock import Mock, patch

from src.config.token import BzmApimToken


def _register_and_get_tool(token=None):
    """Helper: register version tool and return the underlying async function."""
    from src.tools.version_manager import register

    captured = []

    def mock_tool_decorator(name=None, description=None):
        def decorator(func):
            captured.append(func)
            return func

        return decorator

    mcp = Mock()
    mcp.tool = mock_tool_decorator
    register(mcp, token)
    return captured[0]


class TestVersionManagerRegistration:
    def test_register_calls_mcp_tool(self):
        from src.tools.version_manager import register

        mcp = Mock()
        register(mcp, None)
        assert mcp.tool.called

    def test_register_uses_correct_tool_name(self):
        from src.config.defaults import TOOLS_PREFIX
        from src.tools.version_manager import register

        tool_names = []

        def mock_tool_decorator(name=None, description=None):
            tool_names.append(name)

            def decorator(func):
                return func

            return decorator

        mcp = Mock()
        mcp.tool = mock_tool_decorator
        register(mcp, None)
        assert tool_names[0] == f"{TOOLS_PREFIX}_version"

    def test_register_accepts_token(self):
        from src.tools.version_manager import register

        mcp = Mock()
        token = BzmApimToken("test_token")
        register(mcp, token)
        assert mcp.tool.called


class TestVersionTool:
    async def test_returns_version_and_changelog(self, mock_context):
        version_func = _register_and_get_tool()
        result = await version_func(ctx=mock_context)

        assert result.error is None
        assert result.result is not None
        assert len(result.result) == 1
        assert "version" in result.result[0]
        assert "changelog" in result.result[0]

    async def test_changelog_url_points_to_github_releases(self, mock_context):
        version_func = _register_and_get_tool()
        result = await version_func(ctx=mock_context)

        changelog = result.result[0]["changelog"]
        assert changelog.startswith("https://github.com/Runscope/mcp-bzm-apitest/releases/tag/v")

    async def test_version_matches_changelog_url(self, mock_context):
        version_func = _register_and_get_tool()
        result = await version_func(ctx=mock_context)

        version = result.result[0]["version"]
        changelog = result.result[0]["changelog"]
        assert changelog.endswith(f"v{version}")

    async def test_version_is_not_unknown(self, mock_context):
        """Warn if __version__ resolves to 'unknown' — produces a broken changelog URL."""
        version_func = _register_and_get_tool()
        result = await version_func(ctx=mock_context)

        version = result.result[0]["version"]
        assert version != "unknown", (
            "Version resolved to 'unknown' — pyproject.toml may not be accessible "
            "at runtime (e.g. in a PyInstaller binary). "
            f"The changelog URL would be broken: {result.result[0]['changelog']}"
        )

    async def test_unknown_version_produces_broken_changelog_url(self, mock_context):
        """Document the known edge case: 'unknown' version yields a non-resolvable URL."""
        import src.tools.version_manager as vm_module

        with patch.object(vm_module, "__version__", "unknown"):
            version_func = _register_and_get_tool()
            result = await version_func(ctx=mock_context)

        assert result.result[0]["version"] == "unknown"
        assert result.result[0]["changelog"].endswith("vunknown")
