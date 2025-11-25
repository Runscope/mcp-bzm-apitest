"""
Unit tests for StepManager
"""
import pytest
from unittest.mock import patch
from src.tools.step_manager import StepManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestStepManager:
    """Test cases for StepManager"""

    async def test_read_step(self, mock_token, mock_context):
        """Test reading a step"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "step_123",
                    "step_type": "request",
                    "url": "https://api.example.com"
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123", "step_123")

            assert result.error is None
            assert result.result[0]["id"] == "step_123"

    async def test_list_steps(self, mock_token, mock_context):
        """Test listing steps"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "step_1", "step_type": "request"},
                    {"id": "step_2", "step_type": "pause"}
                ],
                total=2
            )

            result = await manager.list("bucket_abc", "test_123")

            assert result.error is None
            assert len(result.result) == 2

    async def test_add_pause_step(self, mock_token, mock_context):
        """Test adding a pause step"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "new_step",
                    "step_type": "pause",
                    "duration": 5000
                }],
                total=1
            )

            result = await manager.add_pause_step("bucket_abc", "test_123", 5)

            assert result.error is None
            assert result.result[0]["step_type"] == "pause"

    async def test_add_request_step(self, mock_token, mock_context):
        """Test adding a request step"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "new_step",
                    "step_type": "request",
                    "method": "GET",
                    "url": "https://api.example.com"
                }],
                total=1
            )

            result = await manager.add_request_step(
                "bucket_abc",
                "test_123",
                method="GET",
                url="https://api.example.com"
            )

            assert result.error is None
            assert result.result[0]["method"] == "GET"

    async def test_add_body_to_step_json(self, mock_token, mock_context):
        """Test adding JSON body to step"""
        manager = StepManager(mock_token, mock_context)

        # Mock both the read and the PUT request
        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            # Mock read to return a request step
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            json_body = '{"key": "value"}'
            result = await manager.add_body_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "json",
                json_body
            )

            assert result.error is None

    async def test_add_body_to_step_xml(self, mock_token, mock_context):
        """Test adding XML body to step"""
        manager = StepManager(mock_token, mock_context)

        # Mock both the read and the PUT request
        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            # Mock read to return a request step
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            xml_body = '<?xml version="1.0"?><root><item>value</item></root>'
            result = await manager.add_body_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "xml",
                xml_body
            )

            assert result.error is None

    async def test_add_body_to_step_invalid_json(self, mock_token, mock_context):
        """Test adding invalid JSON body returns error"""
        manager = StepManager(mock_token, mock_context)

        invalid_json = '{"key": invalid}'
        result = await manager.add_body_to_step(
            "bucket_abc",
            "test_123",
            "step_123",
            "json",
            invalid_json
        )

        assert result.error is not None
        assert "Invalid JSON" in result.error

    async def test_add_body_to_step_invalid_xml(self, mock_token, mock_context):
        """Test adding invalid XML body returns error"""
        manager = StepManager(mock_token, mock_context)

        invalid_xml = '<root><unclosed>'
        result = await manager.add_body_to_step(
            "bucket_abc",
            "test_123",
            "step_123",
            "xml",
            invalid_xml
        )

        assert result.error is not None
        assert "Invalid XML" in result.error

    async def test_add_assertion_to_step(self, mock_token, mock_context):
        """Test adding assertion to step"""
        manager = StepManager(mock_token, mock_context)

        # Mock both the read and the PUT request
        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            # Mock read to return a request step
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com",
                "assertions": []
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_assertion_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "response_status",
                "equals",
                None,
                "200"
            )

            assert result.error is None

