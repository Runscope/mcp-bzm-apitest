from typing import Optional

from mcp.server.fastmcp import Context

from src.config.defaults import TOOLS_PREFIX
from src.config.token import BzmApimToken
from src.config.version import __version__
from src.models import BaseResult


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_version",
        description=(
            "Returns the current version of the BlazeMeter API Test MCP server. "
            "Use this to identify which server version is running so you can match it against "
            "the correct product documentation. Call this first if you are unsure whether a "
            "feature is available in the installed version."
        ),
    )
    async def version(ctx: Context) -> BaseResult:
        return BaseResult(
            result=[
                {
                    "version": __version__,
                    "changelog": f"https://github.com/Runscope/mcp-bzm-apitest/releases/tag/v{__version__}",
                }
            ]
        )
