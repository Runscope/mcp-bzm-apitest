import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx
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
from src.config.defaults import (
    BUCKET_LEVEL_RESULTS_ENDPOINT,
    RESULTS_ENDPOINT,
    TOOLS_PREFIX,
)
from src.config.token import BzmApimToken
from src.formatters.result import (
    format_bucket_level_results,
    format_results,
    format_triggered_runs,
)
from src.models import BaseResult

logger = logging.getLogger(__name__)


class ResultManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    @staticmethod
    def _validate_trigger_url(trigger_url: Optional[str]) -> Optional[str]:
        """
        Validate trigger_url is a safe relative path.
        Returns an error message string if invalid, None if valid.
        """
        if not trigger_url or not isinstance(trigger_url, str):
            return "trigger_url must be a non-empty string."
        parsed = urlparse(trigger_url)
        if parsed.scheme or parsed.netloc:
            return (
                "trigger_url must be a relative path (e.g. '/radar/trigger/abc123'), "
                "not an absolute URL. Absolute URLs are not permitted."
            )
        if not trigger_url.startswith("/"):
            return "trigger_url must start with '/'."
        return None

    @staticmethod
    def _append_source_param(trigger_url: str) -> str:
        parsed = urlparse(trigger_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        if "runscope_source" in params:
            return trigger_url
        params["runscope_source"] = ["bzm-apim-mcp"]
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    async def start(self, trigger_url: Optional[str]) -> BaseResult:
        error = self._validate_trigger_url(trigger_url)
        if error:
            return BaseResult(error=error)
        url_with_source = self._append_source_param(trigger_url)
        return await api_request(self.token, "GET", url_with_source, result_formatter=format_triggered_runs)

    async def read(self, bucket_key: str, test_id: str, test_run_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{RESULTS_ENDPOINT.format(bucket_key, test_id)}/{test_run_id}",
            params={"subtests": "true"},
            result_formatter=format_results,
        )

    async def read_bucket_level_test_run(
        self, bucket_key: str, bucket_level_test_run_id: str
    ) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"/v1{BUCKET_LEVEL_RESULTS_ENDPOINT.format(bucket_key)}/{bucket_level_test_run_id}",
            result_formatter=format_bucket_level_results,
        )

    async def list(self, bucket_key: str, test_id: str, limit: int) -> BaseResult:
        parameters = {"count": limit}

        return await api_request(
            self.token,
            "GET",
            f"{RESULTS_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_results,
            params=parameters,
        )


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_results",
        description="""
        Operations on the results(executions). Results could be an individual test result or a
        bucket-level test result. A bucket-level test run is like a test-suite run which executes all the
        tests present in the bucket via a single API call.
        Actions:
        - start: Start a test run. This will trigger a new test run for the specified test via API.
            args(dict): Dictionary with the following required parameters:
                trigger_url(str): The required parameter. The trigger URL of the test, present in test
                 details, to start the run.
        - start_bucket_level_run: Start a bucket-level test run. This will trigger a new test run for all
             tests present in the specified bucket via API.
            args(dict): Dictionary with the following required parameters:
                trigger_url(str): The required parameter. The trigger URL of the bucket, present in bucket
                 details, to start the bucket-level run.
        - read: Read an individual test run's result. Get the detailed information of a result.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose result is to be read.
                test_run_id(str): The required parameter. The id of the test run whose result is to be read.
        - read_bucket_level_run: Read a bucket-level test run's result. Get the detailed information of a
         result.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                bucket_level_test_run_id(str): The required parameter. The id of the bucket-level run whose
                 result is to be read.
        - list: List all the test runs. This will list all the test runs for the specified test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose result is to be read
                limit(int): Optional parameter. Number of results to return. Default is 10, maximum is 50.
        Examples:
            - Start a test run: action="start",
              args={"trigger_url": "/radar/trigger/abc123?runscope_environment=abc123"}
            - Start a bucket-level run: action="start_bucket_level_run",
              args={"trigger_url": "/radar/trigger/abc123"}
            - List recent runs: action="list",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "limit": 10}
            - Get a specific run result: action="read",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "test_run_id": "abc123def456"}
            - Read bucket-level run: action="read_bucket_level_run",
              args={"bucket_key": "abc123def456", "bucket_level_test_run_id": "abc123def456"}
        """,
    )
    async def results(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        result_manager = ResultManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_results", action, parent_context) as span:
            try:
                match action:
                    case "start" | "start_bucket_level_run":
                        return check_result_error(span, await result_manager.start(args["trigger_url"]))
                    case "read":
                        return check_result_error(
                            span,
                            await result_manager.read(
                                args["bucket_key"], args["test_id"], args["test_run_id"]
                            ),
                        )
                    case "read_bucket_level_run":
                        return check_result_error(
                            span,
                            await result_manager.read_bucket_level_test_run(
                                args["bucket_key"], args["bucket_level_test_run_id"]
                            ),
                        )
                    case "list":
                        return check_result_error(
                            span,
                            await result_manager.list(
                                args["bucket_key"], args["test_id"], args.get("limit", 10)
                            ),
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in results manager tool")
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "unexpected_error")
                logger.exception("Unexpected error in results tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
