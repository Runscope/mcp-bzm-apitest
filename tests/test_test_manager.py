"""
Unit tests for TestManager
"""
import pytest
from unittest.mock import AsyncMock, patch
from src.tools.test_manager import TestManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestTestManager:
    """Test cases for TestManager"""

    async def test_read_test(self, mock_token, mock_context):
        """Test reading a test"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "test_123",
                    "name": "Sample Test",
                    "description": "Test description"
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123")

            assert result.error is None
            assert len(result.result) == 1
            assert result.result[0]["id"] == "test_123"
            mock_api.assert_called_once()

    async def test_create_test(self, mock_token, mock_context):
        """Test creating a new test"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "new_test_123",
                    "name": "New Test",
                    "description": "Test New Test created via MCP tool"
                }],
                total=1
            )

            result = await manager.create("New Test", "bucket_abc")

            assert result.error is None
            assert result.result[0]["name"] == "New Test"

            # Verify API was called with correct parameters
            call_args = mock_api.call_args
            assert call_args[0][1] == "POST"  # Method
            assert "json" in call_args[1]
            assert call_args[1]["json"]["name"] == "New Test"

    async def test_list_tests(self, mock_token, mock_context):
        """Test listing tests"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "test_1", "name": "Test 1"},
                    {"id": "test_2", "name": "Test 2"}
                ],
                total=2,
                has_more=False
            )

            result = await manager.list("bucket_abc", limit=10, offset=0)

            assert result.error is None
            assert len(result.result) == 2

            # Verify pagination parameters
            call_args = mock_api.call_args
            assert "params" in call_args[1]
            assert call_args[1]["params"]["count"] == 10
            assert call_args[1]["params"]["offset"] == 0

    async def test_list_tests_with_pagination(self, mock_token, mock_context):
        """Test listing tests with pagination"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "test_1", "name": "Test 1"}],
                total=50,
                has_more=True
            )

            result = await manager.list("bucket_abc", limit=10, offset=20)

            call_args = mock_api.call_args
            assert call_args[1]["params"]["count"] == 10
            assert call_args[1]["params"]["offset"] == 20
            assert result.has_more is True

    async def test_get_test_metrics(self, mock_token, mock_context):
        """Test getting test metrics"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "response_times": [],
                    "timeframe": "day",
                    "region": "all",
                    "environment_uuid": "all"
                }],
                total=1
            )

            result = await manager.get_test_metrics(
                "bucket_abc",
                "test_123",
                timeframe="day",
                environment_uuid="all",
                region="all"
            )

            assert result.error is None

            # Verify parameters
            call_args = mock_api.call_args
            assert "params" in call_args[1]
            assert call_args[1]["params"]["timeframe"] == "day"
            assert call_args[1]["params"]["environment_uuid"] == "all"
            assert call_args[1]["params"]["region"] == "all"

    async def test_get_test_metrics_with_custom_timeframe(self, mock_token, mock_context):
        """Test getting test metrics with custom timeframe"""
        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(result=[{}], total=1)

            await manager.get_test_metrics(
                "bucket_abc",
                "test_123",
                timeframe="week",
                environment_uuid="env_123",
                region="us1"
            )

            call_args = mock_api.call_args
            params = call_args[1]["params"]
            assert params["timeframe"] == "week"
            assert params["environment_uuid"] == "env_123"
            assert params["region"] == "us1"

    async def test_manager_without_token(self, mock_context):
        """Test manager operations without token"""
        manager = TestManager(None, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                error="No API token. Set BZM_API_TEST_TOKEN env var"
            )

            result = await manager.read("bucket_abc", "test_123")

            assert result.error is not None
            assert "No API token" in result.error

