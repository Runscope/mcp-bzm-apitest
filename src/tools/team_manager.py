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
from src.config.defaults import ACCOUNTS_ENDPOINT, TEAMS_ENDPOINT, TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.formatters.team import format_accounts, format_team_users, format_teams
from src.models import BaseResult

logger = logging.getLogger(__name__)


class TeamManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def list(self) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{ACCOUNTS_ENDPOINT}",
            result_formatter=format_accounts,
            params={"include_owner": True},
        )

    async def read(self, team_id: str) -> BaseResult:
        return await api_request(
            self.token, "GET", f"{TEAMS_ENDPOINT}/{team_id}", result_formatter=format_teams
        )

    async def get_team_users(self, team_id: str) -> BaseResult:
        return await api_request(
            self.token, "GET", f"{TEAMS_ENDPOINT}/{team_id}/people", result_formatter=format_team_users
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
        - read: Read a team. Get details of a specific team.
            args(dict): Dictionary with the following required parameters:
                - team_id (str): The ID of the team to get details for.
        - get_team_users: List all users in a specific team.
            args(dict): Dictionary with the following required parameters:
                - team_id (str): The ID of the team to get users for.
        Examples:
            - List all teams: action="list", args={}
            - Get team details: action="read", args={"team_id": "abc123def456"}
            - List team members: action="get_team_users", args={"team_id": "abc123def456"}
        """,
    )
    async def teams(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        team_manager = TeamManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_teams", action, parent_context) as span:
            try:
                match action:
                    case "list":
                        return check_result_error(span, await team_manager.list())
                    case "read":
                        return check_result_error(span, await team_manager.read(args["team_id"]))
                    case "get_team_users":
                        return check_result_error(span, await team_manager.get_team_users(args["team_id"]))
                    case _:
                        return BaseResult(error=f"Action {action} not found in teams manager tool")
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "unexpected_error")
                logger.exception("Unexpected error in teams tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
