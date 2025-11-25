"""
Unit tests for ResultManager
"""
import pytest
from unittest.mock import patch
from src.tools.result_manager import ResultManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestResultManager:
    """Test cases for ResultManager"""

    async def test_read_result(self, mock_token, mock_context):
        """Test reading a test result"""
        manager = ResultManager(mock_token, mock_context)

        with patch("src.tools.result_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "test_run_id": "run_123",
                    "result": "pass",
                    "started_at": 1234567890
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123", "run_123")

            assert result.error is None
            assert result.result[0]["test_run_id"] == "run_123"

    async def test_list_results(self, mock_token, mock_context):
        """Test listing test results"""
        manager = ResultManager(mock_token, mock_context)

        with patch("src.tools.result_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"test_run_id": "run_1", "result": "pass"},
                    {"test_run_id": "run_2", "result": "fail"}
                ],
                total=2
            )

            result = await manager.list("bucket_abc", "test_123", limit=10)

            assert result.error is None
            assert len(result.result) == 2

    async def test_start_test_run(self, mock_token, mock_context):
        """Test starting a test run"""
        manager = ResultManager(mock_token, mock_context)

        with patch("src.tools.result_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "test_run_id": "new_run_123",
                    "status": "queued"
                }],
                total=1
            )

            trigger_url = "https://api.blazemeter.com/trigger/abc123"
            result = await manager.start(trigger_url)

            assert result.error is None

