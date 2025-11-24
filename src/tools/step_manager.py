import asyncio
import logging
import os
import traceback
import json
import nh3
from pathlib import Path
import defusedxml.ElementTree as DET
from typing import Any, Dict, Union
from typing import Optional
from html import escape

import httpx
from mcp.server.fastmcp import Context

from src.config.token import BzmApimToken
from src.config.defaults import TOOLS_PREFIX, STEPS_ENDPOINT
from src.models import BaseResult
from src.formatters.step import format_steps
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class StepManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str, test_id: str, step_id: str,
                   result_formatter=format_steps) -> Union[BaseResult, dict]:
        step_result = await api_request(
            self.token,
            "GET",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=result_formatter
        )
        if result_formatter:
            return step_result
        return step_result.result[0] if step_result else {}

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        steps_result = await api_request(
            self.token,
            "GET",
            STEPS_ENDPOINT.format(bucket_key, test_id),
            result_formatter=format_steps
        )
        return steps_result

    async def add_pause_step(self, bucket_key: str, test_id: str, duration: int) -> BaseResult:
        pause_step_body = {
            "step_type": "pause",
            "duration": duration or 5
        }
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=pause_step_body
        )

    async def add_request_step(self, bucket_key: str, test_id: str, method: str, url: str) -> BaseResult:
        request_step_body = {
            "step_type": "request",
            "method": method or "GET",
            "url": url or "https://yourapihere.com"
        }
        return await api_request(
            self.token,
            "POST",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_steps,
            json=request_step_body
        )

    async def add_body_to_step(self, bucket_key: str, test_id: str, step_id: str,
                               body_type: str, body_content: str) -> BaseResult:
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
                request_headers["Content-Type"] = "application/json"

            case "xml":
                try:
                    parsed_xml = DET.fromstring(body_content)   # Validate XML content using defusedxml (prevents XXE)
                    safe_xml = DET.tostring(parsed_xml, encoding='unicode')
                    request_step_body["body"] = safe_xml
                except DET.ParseError as e:
                    return BaseResult(error=f"Invalid XML content provided for body_content: {str(e)}")
                except Exception as e:
                    return BaseResult(error=f"Error processing XML content: {str(e)}")
                request_headers["Content-Type"] = "application/xml"

            case "html":
                try:
                    safe_html = nh3.clean(body_content)  # Sanitize HTML content (prevents XSS)
                    request_step_body["body"] = safe_html
                except Exception as e:
                    return BaseResult(error=f"Error processing HTML content: {str(e)}")
                request_headers["Content-Type"] = "text/html"

            case "text":
                # Remove any null bytes and control characters except newlines/tabs
                try:
                    safe_text = ''.join(char for char in body_content
                                      if char.isprintable() or char in '\n\r\t')
                    request_step_body["body"] = safe_text
                except Exception as e:
                    return BaseResult(error=f"Error processing text content: {str(e)}")
                request_headers["Content-Type"] = "text/plain"
            case _:
                BaseResult(error=f"Unsupported body_type {body_type}. Supported types are: json, xml, html, text")

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
            json=request_result
        )

    async def add_assertion_to_step(self, bucket_key: str, test_id: str, step_id: str,
                                    assertion_source: str, assertion_comparison: str,
                                    assertion_property: Optional[str],
                                    assertion_value: Optional[str]) -> BaseResult:
        request_result = await self.read(bucket_key, test_id, step_id, result_formatter=None)
        if not request_result or request_result.get("step_type") != "request":
            return BaseResult(error=f"Step {step_id} is not a request step and cannot have a body added.")
        if "assertions" not in request_result or not isinstance(request_result["assertions"], list):
            request_result["assertions"] = []
        new_assertion = {
            "source": assertion_source,
            "comparison": assertion_comparison
        }
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
            json=request_result
        )


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
                test_id (str): The required parameter. The id of the test to which the pause step will be added.
                duration (int): The required parameter. Duration of the pause in seconds.
        - add_request_step: Add a request step to a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test to which the request step will be added.
                method (str): The optional parameter. HTTP method for the request step.
                url (str): The optional parameter. URL for the request step. If not provided, use the default value: "https://yourapihere.com".
        - add_body_to_step: Add body to an existing request step in a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the body will be added.
                body_type (str): The required parameter. The type of the body to add. Possible values are 'json', 'xml', 'html', 'text'.
                    - 'json': Validates JSON format and sets Content-Type to 'application/json'
                    - 'xml': Validates XML format and sets Content-Type to 'application/xml'
                    - 'html': Sets Content-Type to 'text/html'
                    - 'text': Sets Content-Type to 'text/plain'
                body_content (str): The required parameter. The body content to add to the request step.
                 - For 'json' body_type: Provide valid JSON string (e.g., '{"key": "value"}')
                 - For 'xml' body_type: Provide valid XML string (e.g., '<?xml version="1.0"?><root><element>value</element></root>')
                 - For 'html' body_type: Provide HTML string (e.g., '<html><body><h1>Hello</h1></body></html>')
                 - For 'text' body_type: Provide any plain text string
        - add_assertion_to_step: Add an assertion to an existing request, Ghost Inspector, subtest, or conditional step in a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the step resides.
                step_id (str): The required parameter. The id of the request step to which the assertion will be added.
                assertion_source (str): The required parameter. The location of the data to extract for comparison. Possible values are
                    -  'response_status': Assert on the value of the HTTP status code from the Response
                    -  'response_time': Assert on the execution time of the response in milliseconds
                    -  'response_size': Assert on the size of the Response body in bytes
                    -  'response_text': Parse the response body as plain text. This source does not specify a Property
                    -  'response_json': Parse the response body as JSON. You must include a Property with the JSON path to assert on
                    -  'response_xml': Parse the response body as XML. You must include a Property with the XPath to assert on
                assertion_comparison (str): The required parameter. The comparison operator for the assertion. Possible values are
                    -  'equals': A string equality check on the given property and value
                    -  'greater_than': Asserts that the actual value is greater than the expected value
                    -  'is_less_than': The given property is numerically less than the given value
                    -  'is_less_than_or_equal': The given property is numerically less than or equal to the given value
                    -  'is_greater_than': The given property is numerically greater than the given value
                    -  'is_greater_than_or_equal': The given property is numerically greater than or equal to the given value
                    -  'has_key': The JSON property evaluates to an object and contains the given value as a key. Source must be response_json
                    -  'has_value': The JSON property evaluates to an array and contains the given value as an element. Source must be response_json
                    -  'is_null': The JSON property has a NULL value. Source must be response_json
                    -  'contains': Asserts that the actual value contains the expected value
                    -  'not_contains': Asserts that the actual value does not contain the expected value
                    -  'empty': The given value is an empty string
                    -  'not_empty': The given value is not an empty string
                    -  'not_equal': The given string property is not equal to the given string value
                    -  'contains': The given string value is found in the given property
                    -  'does_not_contain': The given string value is not found in the given property
                    -  'is_a_number': The source property can be converted to a numeric value. This comparison does not take a value
                    -  'equal_number': The source property is numerically equal to the given value. This comparison ensures the values are able to be converted to numbers
                assertion_property (str): The optional parameter. The property of the source data to retrieve.
                    - response_json: JSON path notation (e.g., "headers.Host", "data.items[0].name")
                    - response_xml: XPath expression
                    - response_headers: Header name (e.g., "Server", "Content-Type", "Content-Length")
                    - Not required for response_status, response_time, response_size, response_text
                assertion_value (str): The optional parameter. The expected value used to compare against the actual value.
                    - Set to null for comparisons like 'is_a_number', 'not_empty', 'is_null' that don't require a value
                    - Provide the expected value for other comparisons (e.g., "200", "yourapihere.com", "application")
        """
    )
    async def steps(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        step_manager = StepManager(token, ctx)
        try:
            match action:
                case "read":
                    return await step_manager.read(args["bucket_key"], args["test_id"],
                                                   args["step_id"])
                case "list":
                    return await step_manager.list(args["bucket_key"], args["test_id"])
                case "add_pause_step":
                    return await step_manager.add_pause_step(args["bucket_key"], args["test_id"],
                                                             args["duration"])
                case "add_request_step":
                    return await step_manager.add_request_step(args["bucket_key"], args["test_id"],
                                                              args.get("method"), args.get("url"))
                case "add_body_to_step":
                    return await step_manager.add_body_to_step(args["bucket_key"], args["test_id"],
                                                               args["step_id"], args.get("body_type"),
                                                               args.get("body_content"))
                case "add_assertion_to_step":
                    return await step_manager.add_assertion_to_step(args["bucket_key"], args["test_id"],
                                                                    args["step_id"],
                                                                    args.get("assertion_source"),
                                                                    args.get("assertion_comparison"),
                                                                    args.get("assertion_property"),
                                                                    args.get("assertion_value"))
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in steps manager tool"
                    )
        except httpx.HTTPStatusError:
            return BaseResult(
                error=f"HTTP Error: {traceback.format_exc()}"
            )
        except Exception:
            return BaseResult(
                error=f"""Error: {traceback.format_exc()}
                          If you think this is a bug, please contact BlazeMeter support or report issue at
                           https://github.com/Runscope/mcp-bzm-apitest/issues"""
            )