import logging
from typing import Any, Dict, Optional

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
from src.config.defaults import TEST_ENVIRONMENT_ENDPOINT, TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.formatters.environment import format_environments
from src.models import BaseResult

logger = logging.getLogger(__name__)


class EnvironmentManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str, test_id: str, environment_id: str) -> BaseResult:
        bucket_result = await api_request(
            self.token,
            "GET",
            f"{TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)}/{environment_id}",
            result_formatter=format_environments,
        )
        return bucket_result

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_environments,
        )


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_environments",
        description="""
        Operations on test environments. Environments define execution settings for a test such as
        regions, variables, headers, SSL verification, and notification settings.
        Actions:
        - list: List all the environments for a given test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose environments are to be
                 listed.
        - read: Read a test environment. Get the detailed information of a test environment.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test where the environment resides.
                environment_id(str): The required parameter. The id of the environment to read.
        Examples:
            - List environments: action="list",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456"}
            - Get environment details: action="read",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "environment_id": "abc123def456"}
        """,
    )
    async def environments(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        environment_manager = EnvironmentManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_environments", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span,
                            await environment_manager.read(
                                args["bucket_key"], args["test_id"], args["environment_id"]
                            ),
                        )
                    case "list":
                        return check_result_error(
                            span, await environment_manager.list(args["bucket_key"], args["test_id"])
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in environments manager tool")
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "unexpected_error")
                logger.exception("Unexpected error in environments tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
