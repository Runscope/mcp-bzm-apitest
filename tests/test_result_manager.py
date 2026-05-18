"""
Unit tests for ResultManager
"""

from unittest.mock import patch

import pytest

from src.models import BaseResult
from src.tools.result_manager import ResultManager


@pytest.mark.asyncio
class TestResultManager:
    """Test cases for ResultManager"""

    async def test_read_result(self, mock_token, mock_context):
        """Test reading a test result"""
        manager = ResultManager(mock_token, mock_context)

        with patch("src.tools.result_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"test_run_id": "run_123", "result": "pass", "started_at": 1234567890}], total=1
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
                    {"test_run_id": "run_2", "result": "fail"},
                ],
                total=2,
            )

            result = await manager.list("bucket_abc", "test_123", limit=10)

            assert result.error is None
            assert len(result.result) == 2

    async def test_start_test_run(self, mock_token, mock_context):
        """Test starting a test run with a valid relative trigger URL"""
        manager = ResultManager(mock_token, mock_context)

        with patch("src.tools.result_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"test_run_id": "new_run_123", "status": "queued"}], total=1
            )

            trigger_url = "/radar/trigger/abc123?runscope_environment=env456"
            result = await manager.start(trigger_url)

            assert result.error is None
            mock_api.assert_called_once()

    async def test_start_rejects_absolute_https_url(self, mock_token, mock_context):
        """Absolute HTTPS URLs must be rejected to prevent host override"""
        manager = ResultManager(mock_token, mock_context)
        result = await manager.start("https://api.runscope.com/radar/trigger/abc123")
        assert result.error is not None
        assert "relative path" in result.error

    async def test_start_rejects_absolute_http_url(self, mock_token, mock_context):
        """Absolute HTTP URLs must be rejected (e.g. internal metadata endpoints)"""
        manager = ResultManager(mock_token, mock_context)
        result = await manager.start("http://169.254.169.254/latest/meta-data/")
        assert result.error is not None
        assert "relative path" in result.error

    async def test_start_rejects_url_without_leading_slash(self, mock_token, mock_context):
        """Relative paths without a leading slash are rejected"""
        manager = ResultManager(mock_token, mock_context)
        result = await manager.start("radar/trigger/abc123")
        assert result.error is not None
        assert "must start with '/'" in result.error

    async def test_start_rejects_empty_trigger_url(self, mock_token, mock_context):
        """Empty trigger_url is rejected"""
        manager = ResultManager(mock_token, mock_context)
        result = await manager.start("")
        assert result.error is not None

    async def test_start_rejects_none_trigger_url(self, mock_token, mock_context):
        """None trigger_url is rejected"""
        manager = ResultManager(mock_token, mock_context)
        result = await manager.start(None)
        assert result.error is not None

    def test_validate_trigger_url_valid(self):
        """_validate_trigger_url returns None for valid relative paths"""
        assert ResultManager._validate_trigger_url("/radar/trigger/abc123") is None
        assert ResultManager._validate_trigger_url("/radar/trigger/abc123?env=xyz") is None

    def test_validate_trigger_url_rejects_absolute(self):
        """_validate_trigger_url rejects absolute URLs"""
        assert ResultManager._validate_trigger_url("https://evil.com/steal") is not None
        assert ResultManager._validate_trigger_url("http://169.254.169.254/") is not None
