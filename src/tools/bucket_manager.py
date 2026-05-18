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
from src.config.defaults import BUCKETS_ENDPOINT, TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.formatters.bucket import format_buckets
from src.models import BaseResult

logger = logging.getLogger(__name__)


class BucketManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str) -> BaseResult:
        bucket_result = await api_request(
            self.token, "GET", f"{BUCKETS_ENDPOINT}/{bucket_key}", result_formatter=format_buckets
        )
        return bucket_result

    async def create(self, bucket_name: str, team_id: int) -> BaseResult:
        parameters = {"name": bucket_name, "team_uuid": team_id}
        return await api_request(
            self.token, "POST", f"{BUCKETS_ENDPOINT}", result_formatter=format_buckets, params=parameters
        )

    async def list(self) -> BaseResult:
        return await api_request(self.token, "GET", f"{BUCKETS_ENDPOINT}", result_formatter=format_buckets)


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_buckets",
        description="""
        Operations on buckets. These buckets reside within teams which is represented by team_id and
        contains tests represented by test_id.
        Actions:
        - read: Read a bucket. Get the detailed information of a bucket.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket to read.
        - create: Create a new bucket. This will create a empty bucket to which new tests can be added by
        creating them in this bucket.
            args(dict): Dictionary with the following required parameters:
                bucket_name (str): The required name of the bucket to create.
                team_id (str): The id of the team where this bucket will be created.
        - list: List all the buckets user has access to.
            args(dict): '{}' empty dictionary as no arguments are required.
        Examples:
            - List all buckets: action="list", args={}
            - Get bucket details: action="read", args={"bucket_key": "abc123def456"}
            - Create a bucket: action="create",
              args={"bucket_name": "My API Tests", "team_id": "abc123def456"}
        """,
    )
    async def buckets(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        bucket_manager = BucketManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_buckets", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(span, await bucket_manager.read(args["bucket_key"]))
                    case "create":
                        return check_result_error(
                            span, await bucket_manager.create(args["bucket_name"], args["team_id"])
                        )
                    case "list":
                        return check_result_error(span, await bucket_manager.list())
                    case _:
                        return BaseResult(error=f"Action {action} not found in buckets manager tool")
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "unexpected_error")
                logger.exception("Unexpected error in buckets tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
