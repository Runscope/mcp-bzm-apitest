"""
Unit tests for TeamManager
"""
import pytest
from unittest.mock import patch
from src.tools.team_manager import TeamManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestTeamManager:
    """Test cases for TeamManager"""

    async def test_list_teams(self, mock_token, mock_context):
        """Test listing teams"""
        manager = TeamManager(mock_token, mock_context)

        with patch("src.tools.team_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"uuid": "team_1", "name": "Team 1"},
                    {"uuid": "team_2", "name": "Team 2"}
                ],
                total=2
            )

            result = await manager.list()

            assert result.error is None
            assert len(result.result) == 2

    async def test_read_team(self, mock_token, mock_context):
        """Test reading a team"""
        manager = TeamManager(mock_token, mock_context)

        with patch("src.tools.team_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "uuid": "team_123",
                    "name": "Test Team",
                    "user_count": 5,
                    "bucket_count": 10
                }],
                total=1
            )

            result = await manager.read("team_123")

            assert result.error is None
            assert result.result[0]["uuid"] == "team_123"

    async def test_get_team_users(self, mock_token, mock_context):
        """Test getting team users"""
        manager = TeamManager(mock_token, mock_context)

        with patch("src.tools.team_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"uuid": "user_1", "name": "User 1", "email": "user1@example.com"},
                    {"uuid": "user_2", "name": "User 2", "email": "user2@example.com"}
                ],
                total=2
            )

            result = await manager.get_team_users("team_123")

            assert result.error is None
            assert len(result.result) == 2
            assert result.result[0]["email"] == "user1@example.com"

