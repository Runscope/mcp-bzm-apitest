"""
Unit tests for API client
"""
import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from src.common.api_client import api_request
from src.config.token import BzmApimToken
from src.models import BaseResult


@pytest.mark.asyncio
class TestApiClient:
    """Test cases for API client"""

    async def test_api_request_without_token(self):
        """Test API request fails gracefully without token"""
        result = await api_request(None, "GET", "/test/endpoint")

        assert result.error is not None
        assert "No API token" in result.error

    async def test_api_request_success(self):
        """Test successful API request"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"id": "1", "name": "test"}],
            "error": None
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await api_request(token, "GET", "/test/endpoint")

            assert result.error is None
            assert len(result.result) == 1
            assert result.result[0]["id"] == "1"

    async def test_api_request_with_formatter(self):
        """Test API request with result formatter"""
        token = BzmApimToken("test_token")

        def custom_formatter(data, params=None):
            return [{"formatted": True, **item} for item in data]

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"id": "1"}],
            "error": None
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await api_request(
                token, "GET", "/test/endpoint",
                result_formatter=custom_formatter
            )

            assert result.result[0]["formatted"] is True

    async def test_api_request_403_error(self):
        """Test API request handles 403 Forbidden error"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "error": {"message": "Invalid Credentials"}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_exception = httpx.HTTPStatusError(
                "403 Forbidden",
                request=Mock(),
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=mock_exception
            )

            result = await api_request(token, "GET", "/test/endpoint")

            assert result.error is not None
            assert "Invalid Credentials" in result.error

    async def test_api_request_401_error(self):
        """Test API request handles 401 Unauthorized error"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_exception = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=mock_exception
            )

            result = await api_request(token, "GET", "/test/endpoint")

            assert result.error is not None
            assert "Unauthorized" in result.error

    async def test_api_request_with_headers(self):
        """Test API request includes proper headers"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "error": None}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            await api_request(token, "GET", "/test/endpoint")

            # Verify the request was called with proper headers
            call_kwargs = mock_request.call_args[1]
            assert "headers" in call_kwargs
            assert "Authorization" in call_kwargs["headers"]
            assert call_kwargs["headers"]["Authorization"] == f"Bearer {token}"
            assert "User-Agent" in call_kwargs["headers"]

    async def test_api_request_with_params(self):
        """Test API request with query parameters"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "error": None}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            params = {"limit": 10, "offset": 0}
            await api_request(token, "GET", "/test/endpoint", params=params)

            call_kwargs = mock_request.call_args[1]
            assert "params" in call_kwargs
            assert call_kwargs["params"] == params

    async def test_api_request_post_with_json(self):
        """Test POST API request with JSON body"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": {"id": "new_123", "name": "Created"},
            "error": None
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            json_body = {"name": "Test", "description": "Test description"}
            await api_request(token, "POST", "/test/endpoint", json=json_body)

            call_kwargs = mock_request.call_args[1]
            assert "json" in call_kwargs
            assert call_kwargs["json"] == json_body

    async def test_api_request_with_hint(self):
        """Test API request includes hints in result"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {"data": [{"id": "1"}], "error": None}
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            hints = ["This is a helpful hint"]
            result = await api_request(token, "GET", "/test/endpoint", hint=hints)

            assert result.hint == hints

    async def test_api_request_pagination_has_more(self):
        """Test API request correctly calculates has_more flag"""
        token = BzmApimToken("test_token")

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"id": "1"}],
            "error": None,
            "total": 100,
            "skip": 0,
            "limit": 10
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await api_request(token, "GET", "/test/endpoint")

            assert result.has_more is True
            assert result.total == 100

