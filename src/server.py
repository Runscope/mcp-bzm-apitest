from typing import Optional

from src.config.token import BzmApimToken
from src.tools.bucket_manager import register as register_bucket_manager
from src.tools.environment_manager import register as register_environment_manager
from src.tools.result_manager import register as register_result_manager
from src.tools.schedule_manager import register as register_schedule_manager
from src.tools.step_manager import register as register_step_manager
from src.tools.team_manager import register as register_team_manager
from src.tools.test_manager import register as register_test_manager


def register_tools(mcp, token: Optional[BzmApimToken]):
    """
    Register all available tools with the MCP server.

    Args:
            mcp: The MCP server instance
            token: Optional BlazeMeter API Test token (can be None if not configured)
    """
    register_result_manager(mcp, token)
    register_team_manager(mcp, token)
    register_bucket_manager(mcp, token)
    register_test_manager(mcp, token)
    register_schedule_manager(mcp, token)
    register_step_manager(mcp, token)
    register_environment_manager(mcp, token)
