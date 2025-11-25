"""
Unit tests for BucketManager
"""
import pytest
from unittest.mock import patch
from src.tools.bucket_manager import BucketManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestBucketManager:
    """Test cases for BucketManager"""

    async def test_read_bucket(self, mock_token, mock_context):
        """Test reading a bucket"""
        manager = BucketManager(mock_token, mock_context)

        with patch("src.tools.bucket_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "key": "bucket_abc",
                    "name": "Test Bucket",
                    "verify_ssl": True
                }],
                total=1
            )

            result = await manager.read("bucket_abc")

            assert result.error is None
            assert result.result[0]["key"] == "bucket_abc"

    async def test_create_bucket(self, mock_token, mock_context):
        """Test creating a new bucket"""
        manager = BucketManager(mock_token, mock_context)

        with patch("src.tools.bucket_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "key": "new_bucket",
                    "name": "New Bucket"
                }],
                total=1
            )

            result = await manager.create("New Bucket", "team_123")

            assert result.error is None
            assert result.result[0]["name"] == "New Bucket"

            # Verify API call - bucket manager uses params not json
            call_args = mock_api.call_args
            assert call_args[0][1] == "POST"
            assert "params" in call_args[1]
            assert call_args[1]["params"]["name"] == "New Bucket"

    async def test_list_buckets(self, mock_token, mock_context):
        """Test listing buckets"""
        manager = BucketManager(mock_token, mock_context)

        with patch("src.tools.bucket_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"key": "bucket_1", "name": "Bucket 1"},
                    {"key": "bucket_2", "name": "Bucket 2"}
                ],
                total=2
            )

            result = await manager.list()

            assert result.error is None
            assert len(result.result) == 2

