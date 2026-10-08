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
from src.config.defaults import (
    BUCKET_USAGE_ENDPOINT,
    TEAM_USAGE_ENDPOINT,
    TEST_USAGE_ENDPOINT,
    TOOLS_PREFIX,
)
from src.config.token import BzmApimToken
from src.formatters.usage import (
    format_bucket_usage,
    format_team_usage,
    format_test_usage,
)
from src.models import BaseResult

logger = logging.getLogger(__name__)


def _date_params(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    days: Optional[Any] = None,
    date: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the optional date-window query params for a usage request.

    Only keys explicitly provided are included; api defaults to today when none
    are passed, so the tool must not force any default of its own.
    """
    params: Dict[str, Any] = {}
    if from_date is not None:
        params["from"] = from_date
    if to_date is not None:
        params["to"] = to_date
    if days is not None:
        params["days"] = days
    if date is not None:
        params["date"] = date
    return params


class UsageManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Optional[Context] = None):
        self.token = token
        self.ctx = ctx

    async def get_team_usage(
        self,
        team_uuid: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        days: Optional[Any] = None,
        date: Optional[str] = None,
    ) -> BaseResult:
        try:
            return await api_request(
                self.token,
                "GET",
                TEAM_USAGE_ENDPOINT.format(team_uuid),
                result_formatter=format_team_usage,
                params=_date_params(from_date, to_date, days, date),
            )
        except httpx.HTTPStatusError as e:
            return BaseResult(error=http_error_message(e))

    async def get_bucket_usage(
        self,
        bucket_key: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        days: Optional[Any] = None,
        date: Optional[str] = None,
    ) -> BaseResult:
        try:
            return await api_request(
                self.token,
                "GET",
                BUCKET_USAGE_ENDPOINT.format(bucket_key),
                result_formatter=format_bucket_usage,
                result_formatter_params={"bucket_key": bucket_key},
                params=_date_params(from_date, to_date, days, date),
            )
        except httpx.HTTPStatusError as e:
            return BaseResult(error=http_error_message(e))

    async def get_test_usage(
        self,
        bucket_key: str,
        test_uuid: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        days: Optional[Any] = None,
        date: Optional[str] = None,
    ) -> BaseResult:
        try:
            return await api_request(
                self.token,
                "GET",
                TEST_USAGE_ENDPOINT.format(bucket_key, test_uuid),
                result_formatter=format_test_usage,
                params=_date_params(from_date, to_date, days, date),
            )
        except httpx.HTTPStatusError as e:
            return BaseResult(error=http_error_message(e))


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_team_usage",
        description="""
        Read-only. Retrieve the total number of API Monitoring requests consumed by a team over a
        window. Default window is today when no date params are given.
        Actions:
        - read: Get the team's request count.
            args(dict):
                team_uuid(str): Required. The team whose usage is requested.
                from(str): Optional. Window start date (YYYY-MM-DD).
                to(str): Optional. Window end date (YYYY-MM-DD).
                days(int): Optional. Number of days to look back.
                date(str): Optional. Window start date (YYYY-MM-DD); counts from this date through today.
        Examples:
            - action="read", args={"team_uuid": "abc123"}
            - action="read", args={"team_uuid": "abc123", "from": "2026-01-01", "to": "2026-01-08"}
        """,
    )
    async def team_usage(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        return await _dispatch_usage(token, ctx, f"{TOOLS_PREFIX}_team_usage", action, args, "team")

    @mcp.tool(
        name=f"{TOOLS_PREFIX}_bucket_usage",
        description="""
        Read-only. Retrieve the total number of API Monitoring requests consumed by a bucket over a
        window. Default window is today when no date params are given.
        Actions:
        - read: Get the bucket's request count.
            args(dict):
                bucket_key(str): Required. The bucket whose usage is requested.
                from(str): Optional. Window start date (YYYY-MM-DD).
                to(str): Optional. Window end date (YYYY-MM-DD).
                days(int): Optional. Number of days to look back.
                date(str): Optional. Window start date (YYYY-MM-DD); counts from this date through today.
        Examples:
            - action="read", args={"bucket_key": "abc123"}
            - action="read", args={"bucket_key": "abc123", "from": "2026-01-01", "to": "2026-01-08"}
        """,
    )
    async def bucket_usage(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        return await _dispatch_usage(token, ctx, f"{TOOLS_PREFIX}_bucket_usage", action, args, "bucket")

    @mcp.tool(
        name=f"{TOOLS_PREFIX}_test_usage",
        description="""
        Read-only. Retrieve the total number of API Monitoring requests consumed by a test over a
        window. Default window is today when no date params are given. Test-level usage is retained for
        about 90 days, so older data may be unavailable.
        Actions:
        - read: Get the test's request count.
            args(dict):
                bucket_key(str): Required. The bucket where the test resides.
                test_uuid(str): Required. The test whose usage is requested.
                from(str): Optional. Window start date (YYYY-MM-DD).
                to(str): Optional. Window end date (YYYY-MM-DD).
                days(int): Optional. Number of days to look back.
                date(str): Optional. Window start date (YYYY-MM-DD); counts from this date through today.
        Examples:
            - action="read", args={"bucket_key": "abc123", "test_uuid": "def456"}
            - action="read", args={"bucket_key": "abc123", "test_uuid": "def456", "days": 7}
        """,
    )
    async def test_usage(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        return await _dispatch_usage(token, ctx, f"{TOOLS_PREFIX}_test_usage", action, args, "test")


async def _dispatch_usage(
    token: Optional[BzmApimToken],
    ctx: Context,
    tool_name: str,
    action: str,
    args: Dict[str, Any],
    resource: str,
) -> BaseResult:
    manager = UsageManager(token, ctx)
    meta = get_meta_from_ctx(ctx)
    parent_context = extract_trace_context(meta)
    async with tool_span(tool_name, action, parent_context) as span:
        try:
            if action != "read":
                return BaseResult(error=f"Action {action} not found in {resource} usage tool")
            date_kwargs = {
                "from_date": args.get("from"),
                "to_date": args.get("to"),
                "days": args.get("days"),
                "date": args.get("date"),
            }
            if resource == "team":
                result = await manager.get_team_usage(args["team_uuid"], **date_kwargs)
            elif resource == "bucket":
                result = await manager.get_bucket_usage(args["bucket_key"], **date_kwargs)
            else:
                result = await manager.get_test_usage(args["bucket_key"], args["test_uuid"], **date_kwargs)
            return check_result_error(span, result)
        except httpx.TimeoutException:
            record_span_error(span, "timeout")
            return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
        except httpx.HTTPStatusError as e:
            record_span_error(span, http_status_to_error_type(e.response.status_code))
            return BaseResult(error=http_error_message(e))
        except Exception as e:
            record_span_error(span, "tool_error")
            logger.exception("Unexpected error in %s usage tool: %s", resource, e)
            return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
