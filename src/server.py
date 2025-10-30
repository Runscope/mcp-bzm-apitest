from mcp.server.fastmcp import FastMCP

def load_tools(mcp: FastMCP) -> None:
	"""Load all tool handlers into the FastMCP server."""
	from src.tools.teams import handle_team_tool
	from src.tools.buckets import handle_bucket_tool
	from src.tools.tests import handle_test_tool
	from src.tools.results import handle_result_tool