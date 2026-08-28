from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.common.api_client import api_request
from src.config.auth import TokenResolver


def make_context(authorization: str | None = None):
    headers = {} if authorization is None else {"authorization": authorization}
    return SimpleNamespace(request_context=SimpleNamespace(request=SimpleNamespace(headers=headers)))


def test_stdio_uses_startup_token(mock_token, mock_context):
    resolver = TokenResolver(mock_token)

    assert resolver.get_token(mock_context) == "test_token_12345"


def test_hosted_uses_request_bearer_token_instead_of_startup_token(mock_token):
    resolver = TokenResolver(mock_token, hosted=True)

    token = resolver.get_token(make_context("Bearer request-token"))

    assert token == "request-token"


def test_hosted_rejects_missing_or_malformed_request_credentials(mock_token):
    resolver = TokenResolver(mock_token, hosted=True)

    assert resolver.get_token(make_context()) is None
    assert resolver.get_token(make_context("Basic request-token")) is None
    assert resolver.get_token(make_context("Bearer")) is None


def test_hosted_resolves_each_request_independently(mock_token):
    resolver = TokenResolver(mock_token, hosted=True)

    first_token = resolver.get_token(make_context("Bearer first-token"))
    second_token = resolver.get_token(make_context("Bearer second-token"))

    assert first_token == "first-token"
    assert second_token == "second-token"


@pytest.mark.asyncio
async def test_resolved_token_reaches_api_as_raw_credential(mock_token):
    """BzmApimToken.__repr__ masks itself, so a non-string token would send a masked header."""
    resolver = TokenResolver(mock_token, hosted=True)
    resolved = resolver.get_token(make_context("Bearer request-token"))

    response = Mock()
    response.json.return_value = {"data": []}
    response.raise_for_status = Mock()
    client = AsyncMock()
    client.request.return_value = response

    with patch("src.common.api_client.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value = client
        await api_request(resolved, "GET", "/teams")

    sent = client.request.call_args.kwargs["headers"]["Authorization"]
    assert sent == "Bearer request-token"
    assert "BzmApimToken" not in sent
    assert "*" not in sent
