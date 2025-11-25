"""
Unit tests for EnvironmentManager
"""
import pytest
from unittest.mock import patch
from src.tools.environment_manager import EnvironmentManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestEnvironmentManager:
    """Test cases for EnvironmentManager"""

    async def test_list_environments(self, mock_token, mock_context):
        """Test listing environments"""
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "env_1", "name": "Development"},
                    {"id": "env_2", "name": "Production"}
                ],
                total=2
            )

            result = await manager.list("bucket_abc", "test_123")

            assert result.error is None
            assert len(result.result) == 2

    async def test_read_environment(self, mock_token, mock_context):
        """Test reading an environment"""
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "env_123",
                    "name": "Production",
                    "initial_variables": {"API_KEY": "secret"}
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123", "env_123")

            assert result.error is None
            assert result.result[0]["name"] == "Production"

