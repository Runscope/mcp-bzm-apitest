import asyncio
import logging
import os
import traceback
from pathlib import Path
from typing import Any, Dict
from typing import Optional

import httpx
from mcp.server.fastmcp import Context

from src.config.token import BzmApimToken
from src.config.defaults import TOOLS_PREFIX, SCHEDULES_ENDPOINT
from src.models import BaseResult
from src.models.schedule import CreateSchedule
from src.formatters.schedule import format_schedules
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
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
            result_formatter=format_schedules
        )
        return schedule_result

    async def create(self, bucket_key: str, test_id: str, environment_id: str, interval: str) -> BaseResult:
        # Validate input using the Pydantic model
        schedule_data = CreateSchedule(
            environment_id=environment_id,
            interval=interval,
            note="Schedule created via MCP tool"
        )
        body = schedule_data.model_dump(by_alias=True, exclude_none=True)

        return await api_request(
            self.token,
            "POST",
            f"/v1{SCHEDULES_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_schedules,
            json=body
        )

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{SCHEDULES_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_schedules
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
        """
    )
    async def schedules(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        schedule_manager = ScheduleManager(token, ctx)
        try:
            match action:
                case "read":
                    return await schedule_manager.read(args["bucket_key"], args["test_id"],
                                                       args["schedule_id"])
                case "create":
                    return await schedule_manager.create(args["bucket_key"], args["test_id"],
                                                         args["environment_id"], args["interval"])
                case "list":
                    return await schedule_manager.list(args["bucket_key"], args["test_id"])
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in schedules manager tool"
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
