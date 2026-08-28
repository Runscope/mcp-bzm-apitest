import argparse
import json
import logging
import os
import sys
from typing import Literal, cast

from mcp.server.fastmcp import FastMCP

from src.common.telemetry import init_telemetry
from src.config.auth import run_streamable_http
from src.config.token import BzmApimToken, BzmApimTokenError
from src.config.version import __executable__, __version__
from src.server import register_tools

BLAZEMETER_APIM_KEY_FILE_PATH = os.getenv("BZM_API_TEST_TOKEN_FILE")

LOG_LEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
MCP_TRANSPORTS = ("stdio", "http")


def init_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.CRITICAL)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )


def get_api_token():
    global BLAZEMETER_APIM_KEY_FILE_PATH

    # Verify if running inside Docker container
    is_docker = os.getenv("MCP_DOCKER", "false").lower() == "true"
    token = None

    # Option1: If token is provided directly in the mcp.json file
    if os.getenv("BZM_API_TEST_TOKEN"):
        token = BzmApimToken(os.getenv("BZM_API_TEST_TOKEN")).token
        return token

    # Option2: Token is provided in the .env file
    # 2.a - User sets BZM_APIM_TOKEN_FILE environment variable to point to the file location
    # 2.b - If not set, we look for the file in the same location as the executable
    local_api_key_file = os.path.join(os.path.dirname(__executable__), "bzm_api_test_token.env")

    if not BLAZEMETER_APIM_KEY_FILE_PATH and os.path.exists(local_api_key_file):
        BLAZEMETER_APIM_KEY_FILE_PATH = local_api_key_file

    if BLAZEMETER_APIM_KEY_FILE_PATH:
        try:
            token = BzmApimToken.from_file(BLAZEMETER_APIM_KEY_FILE_PATH).token
        except BzmApimTokenError:
            # Token file exists but is invalid - this will be handled by individual tools
            pass
        except Exception:
            # Other errors (file not found, permissions, etc.) - also handled by tools
            pass
    elif is_docker:
        token = BzmApimToken(os.getenv("BZM_API_TEST_TOKEN")).token
    return token


def resolve_mcp_transport(raw_cli_transport: str) -> str:
    """Resolve the MCP transport from CLI, environment, then stdio default."""
    candidate = raw_cli_transport.strip() or os.getenv("BZM_API_TEST_MCP_TRANSPORT", "").strip()
    if not candidate:
        return "stdio"

    transport = candidate.lower()
    if transport not in MCP_TRANSPORTS:
        allowed = ", ".join(MCP_TRANSPORTS)
        raise ValueError(f"Invalid MCP transport '{candidate}'. Valid values: {allowed}.")
    return transport


def build_mcp_server(log_level: str = "CRITICAL", transport: str = "stdio") -> tuple[FastMCP, str]:
    """Build an API Test MCP server for local stdio or hosted HTTP transport."""
    init_telemetry("mcp-bzm-apitest", __version__)
    instructions = """
    # BlazeMeter API Test MCP Server
    This MCP server provides AI assistants with programmatic access to BlazeMeter's
    API Monitoring platform via the BlazeMeter API test APIs.
    It enables AI assistants to perform various operations related to API monitoring or testing,
    such as creating, managing, and analyzing API tests and their executions.
    The server transforms BlazeMeter's API Monitoring capabilities into an AI-accessible service,
    allowing intelligent automation of complex API monitoring tasks.

    General rules:
        - Invoke the 'list' action on teams tools to get a list of all the teams current user has access to.
           This should be the first action to perform as all further actions depend on teams. All further 
           operations can be done if the 'ai_consent' for a particular team is true/given otherwise return an
           error message or tool call result itself will have the error field populated.
        - You can use list_buckets to get all buckets the user has access to. Each bucket object contains 
           the team_id it belongs to.
        - If you have the information needed to call a tool action with its arguments, do so.
        - Read action always get more information about a particular item than the list action, 
           list only display minimal information.
        - Tool results may have 'hint' field in the result object, use it to guide your next actions.
        - Dependencies:
            teams: It doesn't depend on anyone. A user can be part of multiple teams.
            buckets: Buckets belong to a particular team. Each team has a default bucket which can be identified by 'default': bool property in the bucket object.
            tests: Tests belong to a particular bucket.
            schedules: Schedules belong to a particular test.
            environments: Test Environments belong to a particular test.
            steps: Test steps belong to a particular test.
            results: Test execution results belong to a particular test.
    """
    host = "127.0.0.1"
    port = 8000
    if transport == "http":
        host = os.getenv("FASTMCP_HOST", "127.0.0.1").strip() or "127.0.0.1"
        port = int((os.getenv("FASTMCP_PORT") or os.getenv("PORT") or "8000").strip() or "8000")

    wire_transport = "streamable-http" if transport == "http" else "stdio"
    mcp = FastMCP(
        "blazemeter-apitest-mcp",
        instructions=instructions,
        log_level=cast(LOG_LEVELS, log_level),
        host=host,
        port=port,
        streamable_http_path=os.getenv("FASTMCP_STREAMABLE_HTTP_PATH", "/mcp").strip() or "/mcp",
        stateless_http=True,
    )
    register_tools(mcp, get_api_token() if wire_transport == "stdio" else None, hosted=transport == "http")
    return mcp, wire_transport


def run(log_level: str = "CRITICAL", base_url: str = None, transport: str = "stdio"):
    if base_url:
        import src.config.defaults as defaults

        defaults.BZM_APIM_BASE_URL = base_url

    mcp, wire_transport = build_mcp_server(log_level=log_level, transport=transport)
    if wire_transport == "stdio":
        mcp.run(transport="stdio")
    else:
        run_streamable_http(mcp)


def main():
    parser = argparse.ArgumentParser(prog="mcp-bzm-apitest")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument(
        "--mcp",
        nargs="?",
        const="",
        metavar="TRANSPORT",
        help="Execute MCP Server. Optional TRANSPORT values: stdio or http.",
    )

    parser.add_argument(
        "--log-level",
        default="CRITICAL",  # By default, only critical errors
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: CRITICAL = critical errors only)",
    )

    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for the API (default: https://api.runscope.com). "
        "Can also be set via BZM_API_TEST_BASE_URL env var. "
        "Example: https://api.staging.runscope.com",
    )

    args = parser.parse_args()
    init_logging(args.log_level)

    if args.mcp is not None:
        run(
            log_level=args.log_level.upper(),
            base_url=args.base_url,
            transport=resolve_mcp_transport(args.mcp),
        )
    else:

        logo_ascii = (
            "  ____  _                __  __      _            \n"
            " | __ )| | __ _ _______ |  \\/  | ___| |_ ___ _ __ \n"
            " |  _ \\| |/ _` |_  / _ \\| .  . |/ _ \\ __/ _ \\ '__|\n"
            " | |_) | | (_| |/ /  __/| |\\/| |  __/ ||  __/ |   \n"
            " |____/|_|\\__,_/___\\___||_|  |_|\\___|\\__\\___|_|   \n"
            "                                                    \n"
            f" BlazeMeter API Test MCP Server v{__version__} \n"
        )
        print(logo_ascii)

        config_dict = {
            "BlazeMeter API Test MCP": {
                "command": f"{__executable__}",
                "args": ["--mcp"],
            }
        }

        print(" MCP Server Configuration:\n")
        print(" In your tool with MCP server support, locate the MCP server configuration file")
        print(" and add the following server to the server list.\n")

        json_str = json.dumps(config_dict, ensure_ascii=False, indent=4)
        print("\n".join(json_str.split("\n")[1:-1]) + "\n")

        if not get_api_token():
            print(" [X] BlazeMeter API Test token not configured.")
            print(" ")
            print(
                " Copy the BlazeMeter API Test Token file (bzm_api_test_token.env) to the same location of"
                " this executable."
            )
            print(" ")
            print(" How to obtain the BZM API Test Access Token:")
            print(
                "https://help.blazemeter.com/apidocs/api-monitoring/authentication.htm?tocpath=API%20Monitoring%7CAuthentication%20Process%7C_____0#applications"
            )
        else:
            print(" [OK] BlazeMeter API Test token configured correctly.")
        print(" ")
        print(" There are configuration alternatives, if you want to know more:")
        print(" https://github.com/Runscope/mcp-bzm-apitest")
        print(" ")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
