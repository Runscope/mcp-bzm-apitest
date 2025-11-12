"""
Test or Bucket Result tools for BlazeMeter API Monitoring
"""
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
from src.config.defaults import TOOLS_PREFIX, RESULTS_ENDPOINT, BUCKET_LEVEL_RESULTS_ENDPOINT
from src.models import BaseResult
from src.formatters.result import format_triggered_runs, format_results, format_bucket_level_results
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ResultManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def start(self, trigger_url: str) -> BaseResult:
        return await api_request(
	        self.token,
	        "GET",
	        trigger_url,
	        result_formatter=format_triggered_runs
        )

    async def read(self, bucket_key: str, test_id: str, test_run_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{RESULTS_ENDPOINT.format(bucket_key, test_id)}/{test_run_id}",
            result_formatter=format_results
        )

    async def read_bucket_level_test_run(self, bucket_key: str, bucket_level_test_run_id: str) -> BaseResult:
        return await api_request(
		    self.token,
		    "GET",
		    f"{BUCKET_LEVEL_RESULTS_ENDPOINT.format(bucket_key)}/{bucket_level_test_run_id}",
		    # result_formatter=format_bucket_level_results
	    )


    async def list(self, bucket_key: str, test_id: str, limit: int) -> BaseResult:
        parameters = {"count": limit}

        return await api_request(
	        self.token,
	        "GET",
	        f"{RESULTS_ENDPOINT.format(bucket_key, test_id)}",
	        result_formatter=format_results,
	        params=parameters
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
			trigger_url(str): The required parameter. The trigger URL of the test, present in test details, to start the run.
		- start_bucket_level_run: Start a bucket-level test run. This will trigger a new test run for all tests present
		in the specified bucket via API.
			args(dict): Dictionary with the following required parameters:
			trigger_url(str): The required parameter. The trigger URL of the bucket, present in bucket details, to start the bucket-level run.
        - read: Read an individual test run's result. Get the detailed information of a result.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose result is to be read.
                test_run_id(str): The required parameter. The id of the test run whose result is to be read.
        - read_bucket_level_run: Read a bucket-level test run's result. Get the detailed information of a result.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                bucket_level_test_run_id(str): The required parameter. The id of the bucket-level run whose result is to be read.
        - list: List all the test runs. This will list all the test runs for the specified test.
            args(dict): Dictionary with the following required parameters:
                bucket_key(str): The required parameter. The id of the bucket where the test resides.
                test_id(str): The required parameter. The id of the test whose result is to be read
                limit(int): Optional parameter. Number of results to return. Default is 10, maximum is 50.
        """
    )
    async def results(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        result_manager = ResultManager(token, ctx)
        try:
            match action:
                case "start" | "start_bucket_level_run":
                    return await result_manager.start(args["trigger_url"])
                case "read":
                    return await result_manager.read(args["bucket_key"], args["test_id"], args["test_run_id"])
                case "read_bucket_level_run":
                    return await result_manager.read_bucket_level_test_run(args["bucket_key"], args['bucket_level_test_run_id'])
                case "list":
                    return await result_manager.list(args["bucket_key"], args["test_id"], args.get("limit", 10))
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in results manager tool"
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

