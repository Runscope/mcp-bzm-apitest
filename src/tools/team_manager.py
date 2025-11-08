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
from src.config.defaults import TOOLS_PREFIX, ACCOUNTS_ENDPOINT, TEAMS_ENDPOINT
from src.models import BaseResult
from src.formatters.team import format_teams, format_accounts, format_team_users
from src.common.api_client import api_request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TeamManager:

	def __init__(self, token: Optional[BzmApimToken], ctx: Context):
		self.token = token
		self.ctx = ctx

	async def list(self) -> BaseResult:
		# if control_ai_consent:
		#     # Check if it's valid or allowed
		#     project_result = await bridge.read_project(self.token, self.ctx, project_id)
		#     if project_result.error:
		#         return project_result

		# parameters = {
		#     "count": limit,
		#     "offset": offset
		# }

		return await api_request(
			self.token,
			"GET",
			f"{ACCOUNTS_ENDPOINT}",
			result_formatter=format_accounts,
			params={"include_owner": True}
		)

	async def get_team_users(self, team_id: str) -> BaseResult:
		return await api_request(
			self.token,
			"GET",
			f"{TEAMS_ENDPOINT}/{team_id}/people",
			result_formatter=format_team_users
		)


def register(mcp, token: Optional[BzmApimToken]):
	@mcp.tool(
		name=f"{TOOLS_PREFIX}_teams",
		description="""
        Operations on teams. A user can be part of multiple teams, and each team can have multiple buckets
        and buckets can have multiple tests.
        Actions:
        - list: List all the teams user is part of. User is determined from the provided API token.
            args(dict): '{}' empty dictionary as no arguments are required.
        - get_team_users: List all users in a specific team.
            args(dict): Dictionary with the following required parameters:
                - team_id (str): The ID of the team to get users for.
        """
	)
	async def teams(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
		team_manager = TeamManager(token, ctx)
		try:
			match action:
				case "list":
					return await team_manager.list()
				case "get_team_users":
					return await team_manager.get_team_users(args["team_id"])
				case _:
					return BaseResult(
						error=f"Action {action} not found in teams manager tool"
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
