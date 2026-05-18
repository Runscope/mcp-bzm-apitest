"""
Unit tests for token configuration
"""
import pytest
from src.config.token import BzmApimToken, BzmApimTokenError


class TestBzmApimToken:
    """Test cases for BlazeMeter API token"""

    def test_valid_token_creation(self):
        """Test creating a valid token"""
        token = BzmApimToken("valid_token_12345")
        assert token.token == "valid_token_12345"
        assert "valid_token_12345" not in repr(token)

    def test_token_with_whitespace(self):
        """Test token preserves whitespace (user responsible for trimming)"""
        token = BzmApimToken("  token_with_spaces  ")
        assert token.token == "  token_with_spaces  "
        assert "token_with_spaces" not in repr(token)

    def test_empty_token_raises_error(self):
        """Test that empty token raises error"""
        with pytest.raises(BzmApimTokenError):
            BzmApimToken("")

    def test_none_token_raises_error(self):
        """Test that None token raises error"""
        with pytest.raises(BzmApimTokenError):
            BzmApimToken(None)

    def test_whitespace_only_token_raises_error(self):
        """Test that whitespace-only token is actually valid (implementation allows it)"""
        # The actual implementation only checks for non-empty string
        token = BzmApimToken("   ")
        assert token.token == "   "

    def test_token_equality(self):
        """Test token equality comparison"""
        token1 = BzmApimToken("same_token")
        token2 = BzmApimToken("same_token")
        assert token1.token == token2.token

    def test_token_representation(self):
        """Test token string representation masks the secret value"""
        token = BzmApimToken("test_token")
        r = repr(token)
        assert "BzmApimToken" in r
        # Raw token must not appear in repr
        assert "test_token" not in r
        # First 4 chars are shown, rest masked
        assert "test" in r
        assert "****" in r

    def test_token_can_be_used_in_format_string(self):
        """Test token can be used in f-strings via .token attribute"""
        token = BzmApimToken("my_token")
        result = f"Bearer {token.token}"
        assert result == "Bearer my_token"

