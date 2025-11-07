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
from src.config.defaults import TOOLS_PREFIX, TESTS_ENDPOINT
from src.models.test import Test
from src.models import BaseResult
from src.formatters.test import format_tests, format_test_scehdules, format_test_environments
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str, test_id: int) -> BaseResult:
        test_result = await api_request(
            self.token,
            "GET",
            f"{TESTS_ENDPOINT.format(bucket_key)}/{test_id}",
            result_formatter=format_tests
        )
        return test_result
        # if test_result.error:
        #     return test_result
        # else:
        #     # Check if it's valid or allowed
        #     project_result = await bridge.read_project(self.token, self.ctx, test_result.result[0].project_id)
        #     if project_result.error:
        #         return project_result
        #     else:
        #         return test_result

    async def create(self, test_name: str, bucket_key: int) -> BaseResult:
        # Check if it's valid or allowed
        # project_result = await bridge.read_project(self.token, self.ctx, project_id)
        # if project_result.error:
        #     return project_result

        test_body = {
            "name": test_name,
            "description": f"Test {test_name} created via MCP tool"
        }
        return await api_request(
            self.token,
            "POST",
            f"{TESTS_ENDPOINT.format(bucket_key)}",
            result_formatter=format_tests,
            json=test_body
        )

    async def list(self, bucket_key: str, limit: int, offset: int) -> BaseResult:
        # if control_ai_consent:
        #     # Check if it's valid or allowed
        #     project_result = await bridge.read_project(self.token, self.ctx, project_id)
        #     if project_result.error:
        #         return project_result

        parameters = {
            "count": limit,
            "offset": offset
        }

        return await api_request(
            self.token,
            "GET",
            f"{TESTS_ENDPOINT.format(bucket_key)}",
            result_formatter=format_tests,
            params=parameters
        )

    async def get_test_schedules(self, bucket_key: str, test_id: int) -> BaseResult:
        test_result = await api_request(
            self.token,
            "GET",
            f"{TESTS_ENDPOINT.format(bucket_key)}/{test_id}/schedules",
            result_formatter=format_test_scehdules
        )
        return test_result

    async def get_test_environments(self, bucket_key: str, test_id: int) -> BaseResult:
        test_result = await api_request(
            self.token,
            "GET",
            f"{TESTS_ENDPOINT.format(bucket_key)}/{test_id}/environments",
            result_formatter=format_test_environments
        )
        return test_result


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_tests",
        description="""
        Operations on tests. These tests reside within buckets which is represented by bucket_key.
        Actions:
        - read: Read a test. Get the detailed information of a test.
            args(dict): Dictionary with the following required parameters:
                test_id (int): The required parameter. The id of the test to read.
                bucket_key(str): The bucket key where the test resides.
        - create: Create a new test.
            args(dict): Dictionary with the following required parameters:
                test_name (str): The required name of the test to create.
                bucket_key (str): The key of the bucket where the test will be created.
        - list: List all tests. 
            args(dict): Dictionary with the following required parameters:
                bucket_key (str): The key of the bucket to list tests from.
                limit (int, default=10, valid=[1 to 50]): The number of tests to list.
                offset (int, default=0): Number of tests to skip.
        - get_test_schedules: Get all the schedules defined for a test.
            args(dict): Dictionary with the following required parameters:
                test_id (int): The required parameter. The id of the test to get schedules for.
                bucket_key(str): The bucket key where the test resides.
        - get_test_environments: Get all the environments defined in a test.
            args(dict): Dictionary with the following required parameters:
                test_id (int): The required parameter. The id of the test to get schedules for.
                bucket_key(str): The bucket key where the test resides.
        """
    )
    async def tests(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        test_manager = TestManager(token, ctx)
        try:
            match action:
                case "read":
                    return await test_manager.read(args["bucket_key"], args["test_id"])
                case "create":
                    return await test_manager.create(args["test_name"], args["bucket_key"])
                case "list":
                    return await test_manager.list(args["bucket_key"], args.get("limit", 50),
                                                   args.get("offset", 0))
                case "get_test_schedules":
                    return await test_manager.get_test_schedules(args["bucket_key"], args["test_id"])
                case "get_test_environments":
                    return await test_manager.get_test_environments(args["bucket_key"], args["test_id"])
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in tests manager tool"
                    )
        except httpx.HTTPStatusError:
            return BaseResult(
                error=f"HTTP Error: {traceback.format_exc()}"
            )
        except Exception:
            return BaseResult(
                error=f"""Error: {traceback.format_exc()}
                          If you think this is a bug, please contact BlazeMeter support or report issue at https://github.com/BlazeMeter/bzm-mcp/issues"""
                )
