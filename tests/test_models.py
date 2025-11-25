"""
Unit tests for BaseResult model
"""
import pytest
from src.models import BaseResult


class TestBaseResult:
    """Test cases for BaseResult model"""

    def test_base_result_creation_with_success(self):
        """Test creating a BaseResult with success data"""
        result = BaseResult(
            result=[{"id": "1", "name": "test"}],
            total=1,
            has_more=False,
            error=None
        )

        assert result.result == [{"id": "1", "name": "test"}]
        assert result.total == 1
        assert result.has_more is False
        assert result.error is None

    def test_base_result_creation_with_error(self):
        """Test creating a BaseResult with error"""
        result = BaseResult(
            result=None,
            error="API Error occurred"
        )

        assert result.result is None
        assert result.error == "API Error occurred"

    def test_base_result_append_warnings(self):
        """Test appending warnings to BaseResult"""
        result = BaseResult()
        result.append_warnings(["Warning 1", "Warning 2"])

        assert result.warning == ["Warning 1", "Warning 2"]

        result.append_warnings(["Warning 3"])
        assert len(result.warning) == 3

    def test_base_result_append_info(self):
        """Test appending info messages to BaseResult"""
        result = BaseResult()
        result.append_info(["Info message 1"])

        assert result.info == ["Info message 1"]

    def test_base_result_append_hints(self):
        """Test appending hints to BaseResult"""
        result = BaseResult()
        result.append_hints(["Hint 1", "Hint 2"])

        assert result.hint == ["Hint 1", "Hint 2"]

    def test_base_result_model_dump_excludes_none(self):
        """Test that model_dump excludes None values"""
        result = BaseResult(
            result=[{"id": "1"}],
            total=1,
            error=None
        )

        dumped = result.model_dump()
        assert "result" in dumped
        assert "total" in dumped
        assert "error" not in dumped  # None values should be excluded

    def test_base_result_model_dump_json(self):
        """Test JSON serialization"""
        result = BaseResult(
            result=[{"id": "1", "name": "test"}],
            total=1
        )

        json_str = result.model_dump_json()
        assert isinstance(json_str, str)
        assert "result" in json_str
        assert "test" in json_str

    def test_base_result_with_all_fields(self):
        """Test BaseResult with all fields populated"""
        result = BaseResult(
            result=[{"id": "1"}],
            total=10,
            has_more=True,
            error=None,
            info=["Information message"],
            warning=["Warning message"],
            hint=["Helpful hint"]
        )

        assert result.total == 10
        assert result.has_more is True
        assert len(result.info) == 1
        assert len(result.warning) == 1
        assert len(result.hint) == 1

    def test_base_result_empty(self):
        """Test creating empty BaseResult"""
        result = BaseResult()

        assert result.result is None
        assert result.total is None
        assert result.has_more is None
        assert result.error is None

