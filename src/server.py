from src.tools.test_manager import register as register_test_manager
from src.tools.bucket_manager import register as register_bucket_manager
from src.tools.team_manager import register as register_team_manager
# from tools.test_manager import register as register_test_manager
# from tools.execution_manager import register as register_execution_manager
# from tools.account_manager import register as register_account_manager
from src.config.token import BzmApimToken
from typing import Optional


def register_tools(mcp, token: Optional[BzmApimToken]):
	"""
	Register all available tools with the MCP server.

	Args:
		mcp: The MCP server instance
		token: Optional BlazeMeter APIM token (can be None if not configured)
	"""
	# register_user_manager(mcp, token)
	register_team_manager(mcp, token)
	register_bucket_manager(mcp, token)
	register_test_manager(mcp, token)
	# register_execution_manager(mcp, token)
	# register_account_manager(mcp, token)
