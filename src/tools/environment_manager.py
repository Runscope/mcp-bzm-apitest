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
from src.config.defaults import TOOLS_PREFIX, TEST_ENVIRONMENT_ENDPOINT
from src.models import BaseResult
from src.formatters.environment import format_environments
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
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
            result_formatter=format_environments
        )
        return bucket_result

    async def list(self, bucket_key: str, test_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)}",
            result_formatter=format_environments
        )


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_environments",
        description="""
        Operations on buckets. These buckets reside within teams which is represented by team_id and
        contains tests represented by test_id.
        Actions:
        - list: List all the environments for a given test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose environments are to be listed.
        - read: Read a test environment. Get the detailed information of a test environment.
			args(dict): Dictionary with the following required parameters:
				bucket_key(str): The required parameter. The id of the bucket where the test resides.
				test_id(str): The required parameter. The id of the test where the environment resides.
				environment_id(str): The required parameter. The id of the environment to read.
        """
    )
    async def environments(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        environment_manager = EnvironmentManager(token, ctx)
        try:
            match action:
                case "read":
                    return await environment_manager.read(args["bucket_key"], args["test_id"],
                                                          args['environment_id'])
                case "list":
                    return await environment_manager.list(args["bucket_key"], args["test_id"])
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in environments manager tool"
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
