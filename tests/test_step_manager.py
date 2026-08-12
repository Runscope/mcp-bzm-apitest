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
            # Header values must be arrays per the REST API contract
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["headers"]["Content-Type"] == ["application/json"]

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

    async def test_add_body_to_step_unsupported_type(self, mock_token, mock_context):
        """Test adding body with unsupported body_type returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_body_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "yaml",
                "key: value"
            )

            assert result.error is not None
            assert "Unsupported body_type" in result.error
            mock_api.assert_not_called()

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

    async def test_add_assertion_to_non_request_step(self, mock_token, mock_context):
        """Test adding assertion to a non-request step returns error"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "pause",
                "duration": 5
            }

            result = await manager.add_assertion_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "response_status",
                "equals",
                None,
                "200"
            )

            assert result.error is not None
            assert "cannot have an assertion added" in result.error


    async def test_add_request_step_with_headers_and_note(self, mock_token, mock_context):
        """Test adding a request step with headers and note in a single POST"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "new_step", "step_type": "request"}],
                total=1
            )

            result = await manager.add_request_step(
                "bucket_abc",
                "test_123",
                method="GET",
                url="https://api.example.com",
                headers={"Accept": "application/json", "X-API-Key": ["{{api_key}}"]},
                note="Fetch users"
            )

            assert result.error is None
            post_payload = mock_api.call_args.kwargs["json"]
            # String values are normalized to arrays; array values pass through
            assert post_payload["headers"] == {
                "Accept": ["application/json"],
                "X-API-Key": ["{{api_key}}"]
            }
            assert post_payload["note"] == "Fetch users"

    async def test_add_request_step_invalid_headers(self, mock_token, mock_context):
        """Test adding a request step with malformed headers returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_request_step(
                "bucket_abc",
                "test_123",
                method="GET",
                url="https://api.example.com",
                headers={"Accept": 123}
            )

            assert result.error is not None
            assert "Invalid headers" in result.error
            mock_api.assert_not_called()

    async def test_add_request_step_invalid_note(self, mock_token, mock_context):
        """Test adding a request step with a non-string note returns a clear validation error"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_request_step(
                "bucket_abc",
                "test_123",
                method="GET",
                url="https://api.example.com",
                note=123
            )

            assert result.error is not None
            assert "Invalid note" in result.error
            mock_api.assert_not_called()

    async def test_add_headers_to_step(self, mock_token, mock_context):
        """Test merging headers into an existing request step"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            # Existing step with a legacy bare-string header value
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com",
                "headers": {"Content-Type": "application/json"}
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_headers_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                {"content-type": "application/xml", "Accept": "*/*"}
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            # Case-insensitive match replaces the existing header instead of duplicating it
            assert put_payload["headers"] == {
                "content-type": ["application/xml"],
                "Accept": ["*/*"]
            }

    async def test_add_headers_to_step_invalid_headers(self, mock_token, mock_context):
        """Test adding malformed headers returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_headers_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                {}
            )

            assert result.error is not None
            assert "Invalid headers" in result.error
            mock_api.assert_not_called()

    async def test_add_headers_to_non_request_step(self, mock_token, mock_context):
        """Test adding headers to a non-request step returns error"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "pause",
                "duration": 5
            }

            result = await manager.add_headers_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                {"Accept": "*/*"}
            )

            assert result.error is not None
            assert "cannot have headers added" in result.error

    async def test_add_variable_to_step(self, mock_token, mock_context):
        """Test adding an extraction variable to a request step"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_json",
                "data.id"
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["variables"] == [
                {"name": "user_id", "source": "response_json", "property": "data.id"}
            ]

    async def test_add_variable_to_step_no_property(self, mock_token, mock_context):
        """Test adding a variable whose source does not require a property"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com",
                "variables": [{"name": "existing", "source": "response_text"}]
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "status_code",
                "response_status",
                None
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            # Appends after existing variables; property omitted when not provided
            assert put_payload["variables"][-1] == {"name": "status_code", "source": "response_status"}

    async def test_add_variable_to_step_invalid_source(self, mock_token, mock_context):
        """Test adding a variable with an unsupported source returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_body",
                None
            )

            assert result.error is not None
            assert "Unsupported variable_source" in result.error
            mock_api.assert_not_called()

    async def test_add_variable_to_step_missing_property(self, mock_token, mock_context):
        """Test adding a response_json variable without a property returns error"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_json",
                None
            )

            assert result.error is not None
            assert "variable_property is required" in result.error
            mock_api.assert_not_called()

    async def test_add_variable_to_step_invalid_property_type(self, mock_token, mock_context):
        """Test a non-string variable_property returns a validation error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_json",
                123
            )

            assert result.error is not None
            assert "variable_property must be a string" in result.error
            mock_api.assert_not_called()

    async def test_add_variable_to_step_property_ignored_when_unused(self, mock_token, mock_context):
        """Test variable_property is dropped for sources that do not use it"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "status_code",
                "response_status",
                "anything"
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["variables"] == [
                {"name": "status_code", "source": "response_status"}
            ]

    async def test_add_variable_to_step_property_stripped(self, mock_token, mock_context):
        """Test surrounding whitespace is stripped from variable_property"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_json",
                "  data.id  "
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["variables"][-1]["property"] == "data.id"

    async def test_add_variable_to_step_whitespace_property(self, mock_token, mock_context):
        """Test a whitespace-only variable_property fails the required-property check"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_variable_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "user_id",
                "response_json",
                "   "
            )

            assert result.error is not None
            assert "variable_property is required" in result.error
            mock_api.assert_not_called()

    async def test_add_script_to_step_post(self, mock_token, mock_context):
        """Test adding a post-response script to a request step"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            script = 'var data = JSON.parse(response.body);'
            result = await manager.add_script_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                script,
                "post"
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["scripts"] == [script]
            assert "before_scripts" not in put_payload

    async def test_add_script_to_step_pre(self, mock_token, mock_context):
        """Test adding a pre-request script to a request step"""
        manager = StepManager(mock_token, mock_context)

        with patch.object(manager, 'read') as mock_read, \
             patch("src.tools.step_manager.api_request") as mock_api:
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "request",
                "url": "https://api.example.com"
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123"}],
                total=1
            )

            result = await manager.add_script_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                'variables.set("ts", Date.now());',
                "pre"
            )

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            assert put_payload["before_scripts"] == ['variables.set("ts", Date.now());']
            assert "scripts" not in put_payload

    async def test_add_script_to_step_invalid_type(self, mock_token, mock_context):
        """Test adding a script with an unsupported script_type returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_script_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "var x = 1;",
                "during"
            )

            assert result.error is not None
            assert "Unsupported script_type" in result.error
            mock_api.assert_not_called()

    async def test_add_script_to_step_empty_script(self, mock_token, mock_context):
        """Test adding an empty script returns error without calling the API"""
        manager = StepManager(mock_token, mock_context)

        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.add_script_to_step(
                "bucket_abc",
                "test_123",
                "step_123",
                "   ",
                "post"
            )

            assert result.error is not None
            assert "script is required" in result.error
            mock_api.assert_not_called()
