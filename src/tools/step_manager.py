import json
import logging
from typing import Any, Dict, Optional, Union

import defusedxml.ElementTree as DET
import httpx
import nh3
from mcp.server.fastmcp import Context

from src.common.api_client import api_request
from src.common.errors import UNEXPECTED_ERROR_MESSAGE, http_error_message
from src.common.telemetry import (
    check_result_error,
    extract_trace_context,
    get_meta_from_ctx,
    http_status_to_error_type,
    record_span_error,
    tool_span,
)
from src.config.defaults import STEPS_ENDPOINT, TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.formatters.step import format_steps
from src.models import BaseResult

logger = logging.getLogger(__name__)

VARIABLE_SOURCES = ("response_status", "response_headers", "response_json", "response_xml", "response_text")
VARIABLE_SOURCES_REQUIRING_PROPERTY = ("response_headers", "response_json", "response_xml")
SCRIPT_TYPES = ("pre", "post")


def _sanitize_text(content: str) -> str:
    """Remove null bytes and control characters except newlines/tabs."""
    return "".join(char for char in content if char.isprintable() or char in "\n\r\t")


def _normalize_headers(headers: Any) -> Optional[Dict[str, list]]:
    """
    Normalize a headers mapping to the REST API contract: header name -> array of string values.

    Accepts string values (wrapped in a single-element array) or arrays of strings (passed through).
    Returns None when the input is not a non-empty mapping of that shape.
    """
    if not isinstance(headers, dict) or not headers:
        return None
    normalized: Dict[str, list] = {}
    for name, value in headers.items():
        if not isinstance(name, str) or not name.strip():
            return None
        if isinstance(value, str):
            normalized[name] = [value]
        elif isinstance(value, list) and value and all(isinstance(item, str) for item in value):
            normalized[name] = value
        else:
            return None
    return normalized


def _merge_headers(existing: Any, new: Dict[str, list]) -> Dict[str, list]:
    """
    Merge new headers into a step's existing headers.

    Existing bare-string values are normalized to single-element arrays. A new header replaces any
    existing header whose name matches case-insensitively, so case drift cannot create duplicates.
    """
    merged: Dict[str, list] = {}
    if isinstance(existing, dict):
        for name, value in existing.items():
            merged[name] = value if isinstance(value, list) else [str(value)]
    for name, value in new.items():
        for existing_name in list(merged):
            if existing_name.lower() == name.lower():
                del merged[existing_name]
        merged[name] = value
    return merged


class StepManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(
        self, bucket_key: str, test_id: str, step_id: str, result_formatter=format_steps
    ) -> Union[BaseResult, dict]:
        step_result = await api_request(
            self.token,
            "GET",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=result_formatter,
        )
        if result_formatter:
            return step_result
        return step_result.result[0] if step_result else {}

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        steps_result = await api_request(
            self.token, "GET", STEPS_ENDPOINT.format(bucket_key, test_id), result_formatter=format_steps
        )
        return steps_result

    async def add_pause_step(self, bucket_key: str, test_id: str, duration: int) -> BaseResult:
        pause_step_body = {"step_type": "pause", "duration": duration or 5}
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=pause_step_body,
        )

    async def add_request_step(
        self,
        bucket_key: str,
        test_id: str,
        method: str,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
    ) -> BaseResult:
        request_step_body: Dict[str, Any] = {
            "step_type": "request",
            "method": method or "GET",
            "url": url or "https://yourapihere.com",
        }
        if headers is not None:
            normalized_headers = _normalize_headers(headers)
            if normalized_headers is None:
                return BaseResult(
                    error="Invalid headers: provide a non-empty object mapping header names to string "
                    "values or arrays of strings."
                )
            request_step_body["headers"] = normalized_headers
        if note is not None:
            if not isinstance(note, str):
                return BaseResult(error="Invalid note: must be a string.")
            request_step_body["note"] = _sanitize_text(note).strip()
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=request_step_body,
        )

    async def add_inbound_step(
        self, bucket_key: str, test_id: str, token: Optional[str], is_dynamic_url: bool
    ) -> BaseResult:
        inbound_step_body = {
            "step_type": "inbound",
            "token": token,
            "isDynamicUrl": bool(is_dynamic_url),
        }
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=inbound_step_body,
        )

    async def add_condition_step(
        self,
        bucket_key: str,
        test_id: str,
        comparison: str,
        left_value: str,
        right_value: str,
        steps: Optional[list] = None,
    ) -> BaseResult:
        condition_step_body: Dict[str, Any] = {
            "step_type": "condition",
            "condition_type": "start",
            "comparison": comparison,
            "left_value": left_value,
            "right_value": right_value,
        }
        if steps is not None:
            condition_step_body["steps"] = steps
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=condition_step_body,
        )

    async def add_conditional_loop_step(
        self,
        bucket_key: str,
        test_id: str,
        comparison: str,
        left_value: str,
        right_value: str,
        steps: Optional[list] = None,
    ) -> BaseResult:
        loop_step_body: Dict[str, Any] = {
            "step_type": "conditional-loop",
            "condition_type": "start",
            "comparison": comparison,
            "left_value": left_value,
            "right_value": right_value,
        }
        if steps is not None:
            loop_step_body["steps"] = steps
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=loop_step_body,
        )

    async def add_subtest_step(
        self,
        bucket_key: str,
        test_id: str,
        test_uuid: str,
        trigger_token: str,
        environment_uuid: str,
        subtest_bucket_key: str,
        use_parent_environment: bool,
        params: Optional[list] = None,
    ) -> BaseResult:
        subtest_step_body: Dict[str, Any] = {
            "step_type": "subtest",
            "test_uuid": test_uuid,
            "trigger_token": trigger_token,
            "environment_uuid": environment_uuid,
            "bucket_key": subtest_bucket_key,
            "use_parent_environment": bool(use_parent_environment),
        }
        if params is not None:
            subtest_step_body["params"] = params
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=subtest_step_body,
        )

    async def update_step(
        self, bucket_key: str, test_id: str, step_id: str, updates: Dict[str, Any]
    ) -> BaseResult:
        if not isinstance(updates, dict) or not updates:
            return BaseResult(error="updates must be a non-empty object of fields to change.")
        step = await self.read(bucket_key, test_id, step_id, result_formatter=None)
        if not step:
            return BaseResult(error=f"Step {step_id} not found.")
        step.update(updates)
        return await self._put_step(bucket_key, test_id, step_id, step)

    async def reorder_steps(self, bucket_key: str, test_id: str, step_order: list) -> BaseResult:
        if not isinstance(step_order, list) or not step_order:
            return BaseResult(error="step_order must be a non-empty list of step ids.")
        return await api_request(
            self.token,
            "PUT",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=step_order,
        )

    async def add_body_to_step(
        self, bucket_key: str, test_id: str, step_id: str, body_type: str, body_content: str
    ) -> BaseResult:
        request_step_body = {"body": ""}
        request_headers = {}

        match body_type:
            case "json":
                try:
                    parsed_json = json.loads(body_content)
                    safe_json = json.dumps(parsed_json)
                    request_step_body["body"] = safe_json
                except json.JSONDecodeError as e:
                    return BaseResult(error=f"Invalid JSON content provided for body_content: {str(e)}")
                request_headers["Content-Type"] = ["application/json"]

            case "xml":
                try:
                    parsed_xml = DET.fromstring(
                        body_content
                    )  # Validate XML content using defusedxml (prevents XXE)
                    safe_xml = DET.tostring(parsed_xml, encoding="unicode")
                    request_step_body["body"] = safe_xml
                except DET.ParseError as e:
                    return BaseResult(error=f"Invalid XML content provided for body_content: {str(e)}")
                except Exception as e:
                    return BaseResult(error=f"Error processing XML content: {str(e)}")
                request_headers["Content-Type"] = ["application/xml"]

            case "html":
                try:
                    # Sanitize HTML content (prevents XSS)
                    safe_html = nh3.clean(body_content)
                    request_step_body["body"] = safe_html
                except Exception as e:
                    return BaseResult(error=f"Error processing HTML content: {str(e)}")
                request_headers["Content-Type"] = ["text/html"]

            case "text":
                # Remove any null bytes and control characters except newlines/tabs
                try:
                    request_step_body["body"] = _sanitize_text(body_content)
                except Exception as e:
                    return BaseResult(error=f"Error processing text content: {str(e)}")
                request_headers["Content-Type"] = ["text/plain"]
            case _:
                return BaseResult(
                    error=f"Unsupported body_type {body_type}. Supported types are: json, xml, html, text"
                )

        request_result = await self.read(bucket_key, test_id, step_id, result_formatter=None)
        if not request_result or request_result.get("step_type") != "request":
            return BaseResult(error=f"Step {step_id} is not a request step and cannot have a body added.")

        request_result["body"] = request_step_body["body"]
        if "headers" not in request_result or not isinstance(request_result["headers"], dict):
            request_result["headers"] = {}
        request_result["headers"].update(request_headers)

        return await api_request(
            self.token,
            "PUT",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=format_steps,
            json=request_result,
        )

    async def add_assertion_to_step(
        self,
        bucket_key: str,
        test_id: str,
        step_id: str,
        assertion_source: str,
        assertion_comparison: str,
        assertion_property: Optional[str],
        assertion_value: Optional[str],
    ) -> BaseResult:
        request_result = await self.read(bucket_key, test_id, step_id, result_formatter=None)
        if not request_result or request_result.get("step_type") != "request":
            return BaseResult(
                error=f"Step {step_id} is not a request step and cannot have an assertion added."
            )
        if "assertions" not in request_result or not isinstance(request_result["assertions"], list):
            request_result["assertions"] = []
        new_assertion = {"source": assertion_source, "comparison": assertion_comparison}
        if assertion_property is not None:
            new_assertion["property"] = assertion_property
        if assertion_value is not None:
            new_assertion["value"] = assertion_value
        request_result["assertions"].append(new_assertion)

        return await api_request(
            self.token,
            "PUT",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=format_steps,
            json=request_result,
        )

    async def _read_request_step(self, bucket_key: str, test_id: str, step_id: str, capability: str):
        """Read a step and verify it is a request step. Returns (step, None) or (None, error result)."""
        step = await self.read(bucket_key, test_id, step_id, result_formatter=None)
        if not step or step.get("step_type") != "request":
            return None, BaseResult(
                error=f"Step {step_id} is not a request step and cannot have {capability} added."
            )
        return step, None

    async def _put_step(self, bucket_key: str, test_id: str, step_id: str, step: dict) -> BaseResult:
        return await api_request(
            self.token,
            "PUT",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=format_steps,
            json=step,
        )

    async def add_headers_to_step(
        self, bucket_key: str, test_id: str, step_id: str, headers: Optional[Dict[str, Any]]
    ) -> BaseResult:
        normalized_headers = _normalize_headers(headers)
        if normalized_headers is None:
            return BaseResult(
                error="Invalid headers: provide a non-empty object mapping header names to string "
                "values or arrays of strings."
            )
        step, error = await self._read_request_step(bucket_key, test_id, step_id, "headers")
        if error:
            return error
        step["headers"] = _merge_headers(step.get("headers"), normalized_headers)
        return await self._put_step(bucket_key, test_id, step_id, step)

    async def add_variable_to_step(
        self,
        bucket_key: str,
        test_id: str,
        step_id: str,
        variable_name: Optional[str],
        variable_source: Optional[str],
        variable_property: Optional[str],
    ) -> BaseResult:
        if not isinstance(variable_name, str) or not variable_name.strip():
            return BaseResult(error="variable_name is required and must be a non-empty string.")
        if variable_source not in VARIABLE_SOURCES:
            return BaseResult(
                error=f"Unsupported variable_source {variable_source}. Supported sources are: "
                f"{', '.join(VARIABLE_SOURCES)}"
            )
        if variable_property is not None and not isinstance(variable_property, str):
            return BaseResult(error="variable_property must be a string when provided.")
        requires_property = variable_source in VARIABLE_SOURCES_REQUIRING_PROPERTY
        if requires_property and not (variable_property or "").strip():
            return BaseResult(error=f"variable_property is required for variable_source {variable_source}.")
        step, error = await self._read_request_step(bucket_key, test_id, step_id, "a variable")
        if error:
            return error
        if "variables" not in step or not isinstance(step["variables"], list):
            step["variables"] = []
        new_variable = {"name": variable_name.strip(), "source": variable_source}
        if requires_property:
            new_variable["property"] = variable_property.strip()
        step["variables"].append(new_variable)
        return await self._put_step(bucket_key, test_id, step_id, step)

    async def add_script_to_step(
        self, bucket_key: str, test_id: str, step_id: str, script: Optional[str], script_type: str
    ) -> BaseResult:
        if not isinstance(script, str) or not script.strip():
            return BaseResult(error="script is required and must be a non-empty string.")
        script_type = script_type or "post"
        if script_type not in SCRIPT_TYPES:
            return BaseResult(
                error=f"Unsupported script_type {script_type}. Supported types are: pre, post"
            )
        step, error = await self._read_request_step(bucket_key, test_id, step_id, "a script")
        if error:
            return error
        field = "before_scripts" if script_type == "pre" else "scripts"
        if field not in step or not isinstance(step[field], list):
            step[field] = []
        step[field].append(_sanitize_text(script))
        return await self._put_step(bucket_key, test_id, step_id, step)


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_steps",
        description="""
        Operations on test steps. Test steps are always associated with a test.
        Actions:
        - read: Read a test step. Get the detailed information of a step.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the step to read.
        - list: List all steps for a given test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test whose steps to list.
        - add_pause_step: Add a pause step to a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the pause step will be
                 added.
                duration (int): The required parameter. Duration of the pause in seconds.
        - add_request_step: Add a request step to a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the request step will be
                 added.
                method (str): The optional parameter. HTTP method for the request step.
                url (str): The optional parameter. URL for the request step. If not provided, use the
                 default value: "https://yourapihere.com".
                headers (dict): The optional parameter. Request headers as an object mapping header names
                 to string values (e.g. {"Accept": "application/json", "X-API-Key": "{{api_key}}"}).
                 A value may also be an array of strings for multi-value headers.
                note (str): The optional parameter. A short annotation describing the step. Must be a
                 string.
        - add_headers_to_step: Add request headers to an existing request step. New headers are merged
           into the step's existing headers; a header whose name matches an existing one
           (case-insensitively) replaces it.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the headers
                 will be added.
                headers (dict): The required parameter. An object mapping header names to string values
                 (e.g. {"Authorization": "Bearer {{token}}", "Accept": "application/json"}). A value may
                 also be an array of strings for multi-value headers.
        - add_variable_to_step: Add an extraction variable to an existing request step. Variables capture
           values from the step's response for reuse in later steps via {{variable_name}} syntax.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the variable
                 will be added.
                variable_name (str): The required parameter. The name of the variable. Reference it in
                 later steps as {{variable_name}}.
                variable_source (str): The required parameter. The location of the data to extract.
                  Possible values are
                    -  'response_status': The HTTP status code of the response
                    -  'response_headers': A response header. Requires variable_property
                    -  'response_json': Parse the response body as JSON. Requires variable_property with
                        the JSON path to extract
                    -  'response_xml': Parse the response body as XML. Requires variable_property with the
                        XPath to extract
                    -  'response_text': The response body as plain text
                variable_property (str): The optional parameter. The property of the source data to
                 extract. Required for response_headers (header name), response_json (JSON path, e.g.
                 "data.items[0].id"), and response_xml (XPath). Ignored (dropped from the request) for
                 response_status and response_text.
        - add_script_to_step: Add a JavaScript snippet to an existing request step, either running before
           the request is sent or after the response is received.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the script will
                 be added.
                script (str): The required parameter. The JavaScript source code to add.
                script_type (str): The optional parameter. When the script runs. Possible values are
                    -  'pre': Before the request is sent (added to before_scripts). Use to set variables
                        or pre-process the request
                    -  'post': After the response is received (added to scripts). Use to extract variables
                        or run custom validations. This is the default
        - add_body_to_step: Add body to an existing request step in a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the body will be
                 added.
                body_type (str): The required parameter. The type of the body to add. Possible values are
                 'json', 'xml', 'html', 'text'.
                    - 'json': Validates JSON format and sets Content-Type to 'application/json'
                    - 'xml': Validates XML format and sets Content-Type to 'application/xml'
                    - 'html': Sets Content-Type to 'text/html'
                    - 'text': Sets Content-Type to 'text/plain'
                body_content (str): The required parameter. The body content to add to the request step.
                 - For 'json' body_type: Provide valid JSON string (e.g., '{"key": "value"}')
                 - For 'xml' body_type: Provide valid XML string
                   (e.g., '<?xml version="1.0"?><root><element>value</element></root>')
                 - For 'html' body_type: Provide HTML string
                   (e.g., '<html><body><h1>Hello</h1></body></html>')
                 - For 'text' body_type: Provide any plain text string
        - add_assertion_to_step: Add an assertion to an existing request, Ghost Inspector, subtest, or
           conditional step in a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the assertion
                 will be added.
                assertion_source (str): The required parameter. The location of the data to extract for
                  comparison. Possible values are
                    -  'response_status': Assert on the value of the HTTP status code from the Response
                    -  'response_time': Assert on the execution time of the response in milliseconds
                    -  'response_size': Assert on the size of the Response body in bytes
                    -  'response_text': Parse the response body as plain text. This source does not specify
                        a Property
                    -  'response_json': Parse the response body as JSON. You must include a Property with
                        the JSON path to assert on
                    -  'response_xml': Parse the response body as XML. You must include a Property with the
                        XPath to assert on
                assertion_comparison (str): The required parameter. The comparison operator for the
                  assertion. Possible values are
                    -  'equals': A string equality check on the given property and value
                    -  'greater_than': Asserts that the actual value is greater than the expected value
                    -  'is_less_than': The given property is numerically less than the given value
                    -  'is_less_than_or_equal': The given property is numerically less than or equal to the
                        given value
                    -  'is_greater_than': The given property is numerically greater than the given value
                    -  'is_greater_than_or_equal': The given property is numerically greater than or equal
                        to the given value
                    -  'has_key': The JSON property evaluates to an object and contains the given value as
                        a key. Source must be response_json
                    -  'has_value': The JSON property evaluates to an array and contains the given value as
                        an element. Source must be response_json
                    -  'is_null': The JSON property has a NULL value. Source must be response_json
                    -  'contains': The given string value is found in the given property
                    -  'does_not_contain': The given string value is not found in the given property
                    -  'empty': The given value is an empty string
                    -  'not_empty': The given value is not an empty string
                    -  'not_equal': The given string property is not equal to the given string value
                    -  'is_a_number': The source property can be converted to a numeric value. This
                        comparison does not take a value
                    -  'equal_number': The source property is numerically equal to the given value. This
                         comparison ensures the values are able to be converted to numbers
                assertion_property (str): The optional parameter. The property of the source data to
                 retrieve.
                    - response_json: JSON path notation (e.g., "headers.Host", "data.items[0].name")
                    - response_xml: XPath expression
                    - response_headers: Header name (e.g., "Server", "Content-Type", "Content-Length")
                    - Not required for response_status, response_time, response_size, response_text
                assertion_value (str): The optional parameter. The expected value used to compare against
                  the actual value.
                    - Set to null for comparisons like 'is_a_number', 'not_empty', 'is_null' that don't
                       require a value
                    - Provide the expected value for other comparisons
                       (e.g., "200", "yourapihere.com", "application")
        - add_inbound_step: Add an inbound (webhook) step to a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the inbound step will
                 be added.
                token (str): The required parameter. The inbound webhook token.
                is_dynamic_url (bool): The required parameter. Whether the inbound webhook uses a dynamic
                 URL.
        - add_condition_step: Add a conditional-if (branching) step to a test. The branch runs its nested
           steps only when the comparison holds. The end of the conditional block is appended automatically
           by the server; do not add an explicit end step.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the condition step will
                 be added.
                comparison (str): The required parameter. The comparison operator (same set as
                 add_assertion_to_step's assertion_comparison, e.g. 'equals', 'is_greater_than').
                left_value (str): The required parameter. The left-hand value of the comparison (may use
                 {{variable}} references).
                right_value (str): The required parameter. The right-hand value of the comparison.
                steps (list): The optional parameter. Nested steps to run inside the conditional block.
        - add_conditional_loop_step: Add a conditional-loop (while) step to a test. The loop repeats its
           nested steps while the comparison holds. The end of the loop block is appended automatically by
           the server; do not add an explicit end step.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the loop step will be
                 added.
                comparison (str): The required parameter. The comparison operator (same set as
                 add_condition_step's comparison).
                left_value (str): The required parameter. The left-hand value of the comparison.
                right_value (str): The required parameter. The right-hand value of the comparison.
                steps (list): The optional parameter. Nested steps to run inside the loop block.
        - add_subtest_step: Add a subtest step that triggers another test as part of this test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where this (parent) test
                 resides.
                test_id (str): The required parameter. The id of the (parent) test to which the subtest
                 step will be added.
                test_uuid (str): The required parameter. The id of the subtest (the test to trigger).
                trigger_token (str): The required parameter. The trigger token of the subtest.
                environment_uuid (str): The required parameter. The id of the environment to run the
                 subtest in.
                subtest_bucket_key (str): The required parameter. The id of the bucket that contains the
                 subtest (may differ from the parent test's bucket).
                use_parent_environment (bool): The required parameter. Whether the subtest should use the
                 parent test's environment instead of environment_uuid.
                params (list): The optional parameter. Trigger parameters to pass to the subtest.
        - update_step: Update any existing step by merging the given fields into it. The current step is
           read, the provided fields are shallow-merged over it, and the full merged step is saved.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the step to update.
                updates (dict): The required parameter. A non-empty object of step fields to change (e.g.
                 {"duration": 30} for a pause step, {"url": "https://new"} for a request step).
        - reorder_steps: Change the order of a test's steps. Pass the full ordered list of step ids; the
           server applies the new order (max 100 steps). Known limitation: a conditional-loop block's
           children cannot be nested under a reorder entry (the server pairs end-blocks only for
           conditional-if); reorder every step as a flat id entry instead.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test whose steps to reorder.
                step_order (list): The required parameter. The full ordered list of step ids as objects,
                 e.g. [{"id": "step_2"}, {"id": "step_1"}].
        Examples:
            - List steps: action="list", args={"bucket_key": "abc123def456", "test_id": "abc123def456"}
            - Add a GET request step: action="add_request_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "method": "GET", "url": "https://api.example.com/users"}
            - Add a pause step: action="add_pause_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "duration": 3}
            - Add JSON body: action="add_body_to_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "body_type": "json", "body_content": "{\"key\": \"value\"}"}
            - Assert HTTP 200: action="add_assertion_to_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "assertion_source": "response_status", "assertion_comparison": "equals",
                    "assertion_value": "200"}
            - Add headers: action="add_headers_to_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "headers": {"Authorization": "Bearer {{token}}", "Accept": "application/json"}}
            - Extract a value for later steps: action="add_variable_to_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "variable_name": "user_id", "variable_source": "response_json",
                    "variable_property": "data.id"}
            - Add a post-response script: action="add_script_to_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "script": "var data = JSON.parse(response.body);", "script_type": "post"}
            - Add an inbound step: action="add_inbound_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "token": "inbound_token_xyz", "is_dynamic_url": true}
            - Add a conditional-if step: action="add_condition_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "comparison": "equals", "left_value": "{{status}}", "right_value": "200"}
            - Add a conditional-loop step: action="add_conditional_loop_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "comparison": "is_greater_than", "left_value": "{{counter}}", "right_value": "10"}
            - Add a subtest step: action="add_subtest_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "test_uuid": "sub_test_uuid", "trigger_token": "trig_abc",
                    "environment_uuid": "env_abc", "subtest_bucket_key": "bucket_other",
                    "use_parent_environment": false}
            - Update a step: action="update_step",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "step_id": "abc123def456",
                    "updates": {"duration": 30}}
            - Reorder steps: action="reorder_steps",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "step_order": [{"id": "step_2"}, {"id": "step_1"}]}
        """,
    )
    async def steps(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        step_manager = StepManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_steps", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span,
                            await step_manager.read(args["bucket_key"], args["test_id"], args["step_id"]),
                        )
                    case "list":
                        return check_result_error(
                            span, await step_manager.list(args["bucket_key"], args["test_id"])
                        )
                    case "add_pause_step":
                        return check_result_error(
                            span,
                            await step_manager.add_pause_step(
                                args["bucket_key"], args["test_id"], args["duration"]
                            ),
                        )
                    case "add_request_step":
                        return check_result_error(
                            span,
                            await step_manager.add_request_step(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("method"),
                                args.get("url"),
                                args.get("headers"),
                                args.get("note"),
                            ),
                        )
                    case "add_headers_to_step":
                        return check_result_error(
                            span,
                            await step_manager.add_headers_to_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("headers"),
                            ),
                        )
                    case "add_variable_to_step":
                        return check_result_error(
                            span,
                            await step_manager.add_variable_to_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("variable_name"),
                                args.get("variable_source"),
                                args.get("variable_property"),
                            ),
                        )
                    case "add_script_to_step":
                        return check_result_error(
                            span,
                            await step_manager.add_script_to_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("script"),
                                args.get("script_type", "post"),
                            ),
                        )
                    case "add_body_to_step":
                        return check_result_error(
                            span,
                            await step_manager.add_body_to_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("body_type"),
                                args.get("body_content"),
                            ),
                        )
                    case "add_assertion_to_step":
                        return check_result_error(
                            span,
                            await step_manager.add_assertion_to_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("assertion_source"),
                                args.get("assertion_comparison"),
                                args.get("assertion_property"),
                                args.get("assertion_value"),
                            ),
                        )
                    case "add_inbound_step":
                        return check_result_error(
                            span,
                            await step_manager.add_inbound_step(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("token"),
                                args.get("is_dynamic_url"),
                            ),
                        )
                    case "add_condition_step":
                        return check_result_error(
                            span,
                            await step_manager.add_condition_step(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("comparison"),
                                args.get("left_value"),
                                args.get("right_value"),
                                args.get("steps"),
                            ),
                        )
                    case "add_conditional_loop_step":
                        return check_result_error(
                            span,
                            await step_manager.add_conditional_loop_step(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("comparison"),
                                args.get("left_value"),
                                args.get("right_value"),
                                args.get("steps"),
                            ),
                        )
                    case "add_subtest_step":
                        return check_result_error(
                            span,
                            await step_manager.add_subtest_step(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("test_uuid"),
                                args.get("trigger_token"),
                                args.get("environment_uuid"),
                                args.get("subtest_bucket_key"),
                                args.get("use_parent_environment"),
                                args.get("params"),
                            ),
                        )
                    case "update_step":
                        return check_result_error(
                            span,
                            await step_manager.update_step(
                                args["bucket_key"],
                                args["test_id"],
                                args["step_id"],
                                args.get("updates"),
                            ),
                        )
                    case "reorder_steps":
                        return check_result_error(
                            span,
                            await step_manager.reorder_steps(
                                args["bucket_key"],
                                args["test_id"],
                                args.get("step_order"),
                            ),
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in steps manager tool")
            except httpx.TimeoutException:
                record_span_error(span, "timeout")
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "tool_error")
                logger.exception("Unexpected error in steps tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
