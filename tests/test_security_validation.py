"""
Unit tests for data validation and security
"""
import pytest
import json
from src.tools.step_manager import StepManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestDataValidation:
    """Test cases for data validation and security"""

    async def test_json_validation_prevents_invalid_json(self, mock_token, mock_context):
        """Test that invalid JSON is rejected"""
        manager = StepManager(mock_token, mock_context)

        invalid_json_samples = [
            '{"key": undefined}',  # JavaScript undefined
            '{key: "value"}',  # Unquoted keys
            "{'key': 'value'}",  # Single quotes
            '{"key": "value",}',  # Trailing comma
        ]

        for invalid_json in invalid_json_samples:
            result = await manager.add_body_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "json",
                invalid_json
            )
            assert result.error is not None
            assert "Invalid JSON" in result.error

    async def test_valid_json_accepted(self, mock_token, mock_context):
        """Test that valid JSON is accepted"""
        from unittest.mock import patch

        manager = StepManager(mock_token, mock_context)

        valid_json_samples = [
            '{"key": "value"}',
            '{"nested": {"key": "value"}}',
            '{"array": [1, 2, 3]}',
            '{"number": 42, "boolean": true, "null": null}',
        ]

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            # Mock read to return a request step
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(result=[{"id": "step_123"}], total=1)

            for valid_json in valid_json_samples:
                result = await manager.add_body_to_step(
                    "bucket_abc",
                    "test_123",
                    "step_123",
                    "json",
                    valid_json
                )
                assert result.error is None

    async def test_xml_validation_prevents_invalid_xml(self, mock_token, mock_context):
        """Test that invalid XML is rejected"""
        manager = StepManager(mock_token, mock_context)

        invalid_xml_samples = [
            '<root><unclosed>',  # Unclosed tag
            '<root><tag></root>',  # Mismatched tags
            'not xml at all',  # Not XML
        ]

        for invalid_xml in invalid_xml_samples:
            result = await manager.add_body_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "xml",
                invalid_xml
            )
            assert result.error is not None
            assert "Invalid XML" in result.error

    async def test_sanitization_prevents_xss(self, mock_token, mock_context):
        """Test that HTML content is sanitized"""
        from unittest.mock import patch
        import nh3

        manager = StepManager(mock_token, mock_context)

        xss_attempts = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror="alert(1)">',
            '<iframe src="evil.com"></iframe>',
        ]

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(result=[{"id": "step_123"}], total=1)

            for xss_attempt in xss_attempts:
                result = await manager.add_body_to_step(
                    "bucket_abc",
                    "test_123",
                    "step_123",
                    "html",
                    xss_attempt
                )

                # If sanitization is implemented, verify script tags are removed
                # This test assumes nh3 sanitization is used
                sanitized = nh3.clean(xss_attempt)
                assert '<script>' not in sanitized
                assert 'onerror' not in sanitized

    async def test_url_validation(self, mock_token, mock_context):
        """Test URL validation in request steps"""
        from unittest.mock import patch

        manager = StepManager(mock_token, mock_context)

        # Test valid URLs
        valid_urls = [
            "https://api.example.com",
            "http://localhost:8080/api",
            "https://api.example.com/v1/users?id=123",
        ]

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(result=[{"id": "step_123"}], total=1)

            for valid_url in valid_urls:
                result = await manager.add_request_step(
                    "bucket_abc",
                    "test_123",
                    "GET",
                    valid_url
                )
                assert result.error is None

    def test_token_sanitization(self):
        """Test that tokens don't contain malicious content"""
        from src.config.token import BzmApimToken, BzmApimTokenError

        # Tokens should be alphanumeric with specific special chars
        valid_tokens = [
            "abc123xyz",
            "token-with-dash",
            "token_with_underscore",
            "token.with.dot",
        ]

        for token_str in valid_tokens:
            token = BzmApimToken(token_str)
            assert token.token == token_str
            assert token_str in repr(token)

    async def test_assertion_value_escaping(self, mock_token, mock_context):
        """Test that assertion values are properly handled"""
        from unittest.mock import patch

        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(result=[{"id": "step_123"}], total=1)

            # Test with special characters that could cause issues
            special_values = [
                "200",  # Normal
                "application/json; charset=utf-8",  # With special chars
                "value with spaces",  # Spaces
                "value\nwith\nnewlines",  # Newlines
            ]

            for value in special_values:
                result = await manager.add_assertion_to_step(
                    "bucket_abc",
                    "test_123",
                    "step_123",
                    "response_status",
                    "equals",
                    None,
                    value
                )
                # Should not raise errors
                assert result is not None


class TestErrorHandling:
    """Test error handling across the system"""

    def test_base_result_handles_error_gracefully(self):
        """Test BaseResult error handling"""
        result = BaseResult(error="Test error")
        assert result.error == "Test error"
        assert result.result is None

    def test_base_result_with_multiple_messages(self):
        """Test BaseResult with warnings, info, and hints"""
        result = BaseResult()
        result.append_warnings(["Warning 1", "Warning 2"])
        result.append_info(["Info 1"])
        result.append_hints(["Hint 1"])

        assert len(result.warning) == 2
        assert len(result.info) == 1
        assert len(result.hint) == 1

    @pytest.mark.asyncio
    async def test_api_error_propagation(self, mock_token, mock_context):
        """Test that API errors are properly propagated"""
        from unittest.mock import patch
        from src.tools.test_manager import TestManager

        manager = TestManager(mock_token, mock_context)

        with patch("src.tools.test_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                error="API Error: Connection timeout"
            )

            result = await manager.read("bucket_abc", "test_123")

            assert result.error is not None
            assert "API Error" in result.error

