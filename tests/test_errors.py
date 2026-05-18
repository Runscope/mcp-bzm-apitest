"""
Tests for src/common/errors.py — http_error_message() and UNEXPECTED_ERROR_MESSAGE.
"""

from unittest.mock import Mock

import httpx

from src.common.errors import UNEXPECTED_ERROR_MESSAGE, http_error_message


def make_http_error(status_code: int) -> httpx.HTTPStatusError:
    response = Mock()
    response.status_code = status_code
    return httpx.HTTPStatusError("error", request=Mock(), response=response)


class TestHttpErrorMessage:
    def test_401_returns_auth_error(self):
        result = http_error_message(make_http_error(401))
        assert "Authentication error (HTTP 401)" in result
        assert "BZM_API_TEST_TOKEN" in result

    def test_403_returns_auth_error(self):
        result = http_error_message(make_http_error(403))
        assert "Authentication error (HTTP 403)" in result
        assert "BZM_API_TEST_TOKEN" in result

    def test_404_returns_not_found(self):
        result = http_error_message(make_http_error(404))
        assert "Not found (HTTP 404)" in result
        assert "IDs you provided" in result

    def test_429_returns_rate_limited(self):
        result = http_error_message(make_http_error(429))
        assert "Rate limited (HTTP 429)" in result
        assert "Wait before retrying" in result

    def test_500_returns_server_error(self):
        result = http_error_message(make_http_error(500))
        assert "server error (HTTP 500)" in result
        assert "BlazeMeter's side" in result

    def test_503_returns_server_error(self):
        result = http_error_message(make_http_error(503))
        assert "server error (HTTP 503)" in result

    def test_400_returns_generic_fallback(self):
        result = http_error_message(make_http_error(400))
        assert "HTTP 400 error" in result

    def test_422_returns_generic_fallback(self):
        result = http_error_message(make_http_error(422))
        assert "HTTP 422 error" in result

    def test_no_traceback_in_any_message(self):
        for status in (401, 403, 404, 429, 500, 503, 400):
            result = http_error_message(make_http_error(status))
            assert "Traceback" not in result
            assert "File " not in result


class TestUnexpectedErrorMessage:
    def test_contains_github_issues_url(self):
        assert "https://github.com/Runscope/mcp-bzm-apitest/issues" in UNEXPECTED_ERROR_MESSAGE

    def test_no_traceback_in_message(self):
        assert "Traceback" not in UNEXPECTED_ERROR_MESSAGE
        assert "File " not in UNEXPECTED_ERROR_MESSAGE
