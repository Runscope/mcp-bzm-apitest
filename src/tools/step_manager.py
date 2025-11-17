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

    async def read(self, bucket_key: str, test_id: str, step_id: str) -> BaseResult:
        step_result = await api_request(
            self.token,
            "GET",
            f"{STEPS_ENDPOINT.format(bucket_key, test_id)}/{step_id}",
            result_formatter=format_steps
        )
        return step_result

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        steps_result = await api_request(
            self.token,
            "GET",
            STEPS_ENDPOINT.format(bucket_key, test_id),
            result_formatter=format_steps
        )
        return steps_result


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
                           https://github.com/BlazeMeter/bzm-mcp/issues"""
            )