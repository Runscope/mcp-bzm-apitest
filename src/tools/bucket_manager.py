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
from src.config.defaults import TOOLS_PREFIX, BUCKETS_ENDPOINT
from src.models.bucket import Bucket
from src.models import BaseResult
from src.formatters.bucket import format_buckets
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class BucketManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str) -> BaseResult:
        bucket_result = await api_request(
            self.token,
            "GET",
            f"{BUCKETS_ENDPOINT}/{bucket_key}",
            result_formatter=format_buckets
        )
        return bucket_result

    async def create(self, bucket_name: str, team_id: int) -> BaseResult:
        parameters = {
            "name": bucket_name,
            "team_uuid": team_id
        }
        return await api_request(
            self.token,
            "POST",
            f"{BUCKETS_ENDPOINT}",
            result_formatter=format_buckets,
            params=parameters
        )

    async def list(self) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{BUCKETS_ENDPOINT}",
            result_formatter=format_buckets
        )


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
        """
    )
    async def buckets(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        bucket_manager = BucketManager(token, ctx)
        try:
            match action:
                case "read":
                    return await bucket_manager.read(args["bucket_key"])
                case "create":
                    return await bucket_manager.create(args["bucket_name"], args["team_id"])
                case "list":
                    return await bucket_manager.list()
                case _:
                    return BaseResult(
                        error=f"Action {action} not found in buckets manager tool"
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
