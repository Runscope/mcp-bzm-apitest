"""
Pytest configuration and fixtures for MCP BlazeMeter API Test server
"""
import pytest
from unittest.mock import Mock, AsyncMock
from mcp.server.fastmcp import Context
from src.config.token import BzmApimToken
from src.models import BaseResult


@pytest.fixture
def mock_token():
    """Create a mock BlazeMeter API token"""
    return BzmApimToken("test_token_12345")


@pytest.fixture
def mock_context():
    """Create a mock MCP context"""
    ctx = Mock(spec=Context)
    ctx.request_context = Mock()
    ctx.request_context.meta = {}
    return ctx


@pytest.fixture
def sample_test_data():
    """Sample test data"""
    return {
        "id": "test_123",
        "name": "Sample Test",
        "description": "Test description",
        "bucket_key": "bucket_abc"
    }


@pytest.fixture
def sample_bucket_data():
    """Sample bucket data"""
    return {
        "key": "bucket_abc",
        "name": "Sample Bucket",
        "verify_ssl": True,
        "default": False,
        "trigger_token": "trigger_123"
    }


@pytest.fixture
def sample_team_data():
    """Sample team data"""
    return {
        "uuid": "team_uuid_123",
        "name": "Sample Team",
        "user_count": 5,
        "bucket_count": 10
    }


@pytest.fixture
def sample_step_data():
    """Sample step data"""
    return {
        "id": "step_123",
        "step_type": "request",
        "url": "https://api.example.com/test",
        "method": "GET"
    }


@pytest.fixture
def sample_schedule_data():
    """Sample schedule data"""
    return {
        "id": "schedule_123",
        "interval": "1h",
        "environment_id": "env_123",
        "note": "Test schedule"
    }


@pytest.fixture
def sample_result_data():
    """Sample result data"""
    return {
        "test_run_id": "run_123",
        "test_uuid": "test_uuid_123",
        "result": "pass",
        "started_at": 1234567890
    }


@pytest.fixture
def sample_environment_data():
    """Sample environment data"""
    return {
        "id": "env_123",
        "name": "Production",
        "initial_variables": {"key": "value"}
    }


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response"""
    def _create_response(status_code=200, json_data=None):
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = {
            "data": json_data or [],
            "error": None
        }
        mock_response.raise_for_status = Mock()
        return mock_response
    return _create_response


@pytest.fixture
def mock_api_request(monkeypatch):
    """Mock the api_request function"""
    async def _mock_api_request(*args, **kwargs):
        return BaseResult(
            result=[{"id": "test_123", "name": "Test"}],
            total=1,
            error=None
        )

    from src.common import api_client
    monkeypatch.setattr(api_client, "api_request", _mock_api_request)
    return _mock_api_request

