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
from src.config.defaults import SCHEDULES_ENDPOINT, TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.formatters.schedule import format_schedules
from src.models import BaseResult
from src.models.schedule import CreateSchedule

logger = logging.getLogger(__name__)


class ScheduleManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str, test_id: str, schedule_id: str) -> BaseResult:
        schedule_result = await api_request(
            self.token,
            "GET",
            f"{SCHEDULES_ENDPOINT.format(bucket_key, test_id)}/{schedule_id}",
            result_formatter=format_schedules,
        )
        return schedule_result

    async def create(self, bucket_key: str, test_id: str, environment_id: str, interval: str) -> BaseResult:
        # Validate input using the Pydantic model
        schedule_data = CreateSchedule(
            environment_id=environment_id, interval=interval, note="Schedule created via MCP tool"
        )
        body = schedule_data.model_dump(by_alias=True, exclude_none=True)

        return await api_request(
            self.token,
            "POST",
            f"/v1{SCHEDULES_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_schedules,
            json=body,
        )

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{SCHEDULES_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_schedules,
        )


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_schedules",
        description="""
        Operations on test schedules. Schedules allow to run tests periodically at defined intervals.
        Actions:
        - read: Read a schedule. Get the detailed information of a schedule.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the schedule resides.
                schedule_id (str): The required parameter. The id of the schedule to read.
        - create: Create a new schedule for the test.
            args(dict): Dictionary with the following required parameters:
                bucket_key (str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the schedule resides.
                environment_id (str): The required parameter. The id of the environment to associate with
                the schedule.
                interval (str): The required parameter. The interval at which the schedule should run
                 Allowed values are: -
                    1m — every minute
                    5m — every 5 minutes
                    15m — every 15 minutes
                    30m — every 30 minutes
                    1h — every hour
                    6h — every 6 hours
                    1d — every day.
        - list: List all schedules for a test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id (str): The required parameter. The id of the test where the schedules reside
        Examples:
            - List schedules: action="list",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456"}
            - Get schedule details: action="read",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "schedule_id": "abc123def456"}
            - Create a daily schedule: action="create",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "environment_id": "abc123def456", "interval": "1d"}
        """,
    )
    async def schedules(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        schedule_manager = ScheduleManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_schedules", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span,
                            await schedule_manager.read(
                                args["bucket_key"], args["test_id"], args["schedule_id"]
                            ),
                        )
                    case "create":
                        return check_result_error(
                            span,
                            await schedule_manager.create(
                                args["bucket_key"],
                                args["test_id"],
                                args["environment_id"],
                                args["interval"],
                            ),
                        )
                    case "list":
                        return check_result_error(
                            span, await schedule_manager.list(args["bucket_key"], args["test_id"])
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in schedules manager tool")
            except httpx.TimeoutException:
                record_span_error(span, "timeout")
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "tool_error")
                logger.exception("Unexpected error in schedules tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
