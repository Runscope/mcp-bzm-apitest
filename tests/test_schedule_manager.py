"""
Unit tests for ScheduleManager
"""
import pytest
from unittest.mock import patch
from src.tools.schedule_manager import ScheduleManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestScheduleManager:
    """Test cases for ScheduleManager"""

    async def test_read_schedule(self, mock_token, mock_context):
        """Test reading a schedule"""
        manager = ScheduleManager(mock_token, mock_context)

        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "schedule_123",
                    "interval": "1h",
                    "environment_id": "env_123"
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123", "schedule_123")

            assert result.error is None
            assert result.result[0]["id"] == "schedule_123"

    async def test_create_schedule(self, mock_token, mock_context):
        """Test creating a schedule"""
        manager = ScheduleManager(mock_token, mock_context)

        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "new_schedule",
                    "interval": "6h",
                    "environment_id": "env_123"
                }],
                total=1
            )

            result = await manager.create(
                "bucket_abc",
                "test_123",
                "env_123",
                "6h"
            )

            assert result.error is None
            assert result.result[0]["interval"] == "6h"

    async def test_list_schedules(self, mock_token, mock_context):
        """Test listing schedules"""
        manager = ScheduleManager(mock_token, mock_context)

        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "schedule_1", "interval": "1h"},
                    {"id": "schedule_2", "interval": "6h"}
                ],
                total=2
            )

            result = await manager.list("bucket_abc", "test_123")

            assert result.error is None
            assert len(result.result) == 2

