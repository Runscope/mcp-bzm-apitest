"""
Integration tests for MCP Server
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from mcp.server.fastmcp import FastMCP
from src.server import register_tools
from src.config.token import BzmApimToken


@pytest.mark.asyncio
class TestMCPServerIntegration:
    """Integration tests for the MCP server"""

    def test_register_tools_with_token(self):
        """Test registering all tools with a valid token"""
        mcp = Mock(spec=FastMCP)
        token = BzmApimToken("test_token")

        # This should not raise any exceptions
        register_tools(mcp, token)

        # Verify that tool decorator was called multiple times
        assert mcp.tool.call_count >= 7  # We have at least 7 managers

    def test_register_tools_without_token(self):
        """Test registering tools without a token"""
        mcp = Mock(spec=FastMCP)

        # Should still work without token (tools will check token when called)
        register_tools(mcp, None)

        assert mcp.tool.call_count >= 7

    async def test_tool_execution_flow(self):
        """Test end-to-end tool execution flow"""
        mcp = Mock(spec=FastMCP)
        token = BzmApimToken("test_token")

        # Track registered tools
        registered_tools = []

        def mock_tool_decorator(name=None, description=None):
            def decorator(func):
                registered_tools.append({
                    'name': name,
                    'description': description,
                    'func': func
                })
                return func
            return decorator

        mcp.tool = mock_tool_decorator

        register_tools(mcp, token)

        # Verify tools are registered with correct names
        tool_names = [tool['name'] for tool in registered_tools]
        expected_tools = [
            'blazemeter_apitest_results',
            'blazemeter_apitest_teams',
            'blazemeter_apitest_buckets',
            'blazemeter_apitest_tests',
            'blazemeter_apitest_schedules',
            'blazemeter_apitest_steps',
            'blazemeter_apitest_environments'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    async def test_tool_error_handling(self):
        """Test that tools handle errors gracefully"""
        from src.tools.test_manager import TestManager
        from mcp.server.fastmcp import Context

        token = BzmApimToken("test_token")
        ctx = Mock(spec=Context)
        manager = TestManager(token, ctx)

        with patch("src.tools.test_manager.api_request") as mock_api:
            # Simulate API error
            from src.models import BaseResult
            mock_api.return_value = BaseResult(
                error="API connection failed"
            )

            result = await manager.read("bucket_abc", "test_123")

            assert result.error is not None
            assert "API connection failed" in result.error

    async def test_multiple_manager_interactions(self):
        """Test interactions between multiple managers"""
        from src.tools.test_manager import TestManager
        from src.tools.bucket_manager import BucketManager
        from src.tools.step_manager import StepManager
        from mcp.server.fastmcp import Context
        from src.models import BaseResult

        token = BzmApimToken("test_token")
        ctx = Mock(spec=Context)

        # Create managers
        bucket_manager = BucketManager(token, ctx)
        test_manager = TestManager(token, ctx)
        step_manager = StepManager(token, ctx)

        with patch("src.tools.bucket_manager.api_request") as mock_bucket_api, \
             patch("src.tools.test_manager.api_request") as mock_test_api, \
             patch("src.tools.step_manager.api_request") as mock_step_api:

            # Setup mock responses
            mock_bucket_api.return_value = BaseResult(
                result=[{"key": "bucket_123", "name": "Test Bucket"}],
                total=1
            )
            mock_test_api.return_value = BaseResult(
                result=[{"id": "test_123", "name": "Test"}],
                total=1
            )
            mock_step_api.return_value = BaseResult(
                result=[{"id": "step_123", "step_type": "request"}],
                total=1
            )

            # Simulate workflow: read bucket -> read test -> add step
            bucket_result = await bucket_manager.read("bucket_123")
            assert bucket_result.error is None

            test_result = await test_manager.read("bucket_123", "test_123")
            assert test_result.error is None

            step_result = await step_manager.add_request_step(
                "bucket_123", "test_123", "GET", "https://api.example.com"
            )
            assert step_result.error is None

