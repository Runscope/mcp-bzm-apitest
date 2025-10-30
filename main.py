"""
BlazeMeter API Monitoring MCP Server

This MCP server provides tools for managing BlazeMeter API Monitoring (formerly Runscope)
resources including teams, buckets, tests, and results.
"""

import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.tools.teams import handle_team_tool
from src.tools.buckets import handle_bucket_tool
from src.tools.tests import handle_test_tool
from src.tools.results import handle_result_tool

# Configure logging
def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.CRITICAL)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        stream=sys.stdout,
        force=True
    )
    logger = logging.getLogger(__name__)

