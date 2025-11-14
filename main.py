import argparse
import json
import logging
import os
import sys
from typing import Literal, cast

from mcp.server.fastmcp import FastMCP

from src.config.token import BzmApimToken, BzmApimTokenError
from src.config.version import __version__, __executable__
from src.server import register_tools

BLAZEMETER_APIM_KEY_FILE_PATH = os.getenv('BZM_APIM_TOKEN_FILE')

LOG_LEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


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
    is_docker = os.getenv('MCP_DOCKER', 'false').lower() == 'true'
    token = None

    # Option1: If token is provided directly in the mcp.json file
    if os.getenv('BZM_APIM_TOKEN'):
        token = BzmApimToken(os.getenv('BZM_APIM_TOKEN')).token
        return token

    # Option2: Token is provided in the .env file
    # 2.a - User sets BZM_APIM_TOKEN_FILE environment variable to point to the file location
    # 2.b - If not set, we look for the file in the same location as the executable
    local_api_key_file = os.path.join(
        os.path.dirname(__executable__), "bzm_apim_token.env")

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
        token = BzmApimToken(os.getenv('API_KEY_ID'))
    return token


def run(log_level: str = "CRITICAL"):
    token = get_api_token()
    instructions = """
    # BlazeMeter APIM MCP Server
    This MCP server provides AI assistants with programmatic access to BlazeMeter's
    API Monitoring platform via the BlazeMeter APIM API.
    It enables AI assistants to perform various operations related to API monitoring or testing,
    such as creating, managing, and analyzing API tests and their executions.
    The server transforms BlazeMeter's API Monitoring capabilities into an AI-accessible service,
    allowing intelligent automation of complex API monitoring tasks.

    General rules:
        - Invoke the 'list' action on teams tools to get a list of all the teams current user has access to. This should be the first action to perform as all further actions depend on teams.
        - You can use list_buckets to get all buckets the user has access to. Each bucket object contains the team_id it belongs to. You do not need to call list_teams first unless you explicitly need team metadata.
        - If you have the information needed to call a tool action with its arguments, do so.
        - Read action always get more information about a particular item than the list action, list only display minimal information.
        - Dependencies:
            teams: It doesn't depend on anyone. A user can be part of multiple teams.
            buckets: Buckets belong to a particular team. Each team has a default bucket which can be identified by 'default': bool property in the bucket object.
            tests: Tests belong to a particular bucket.
            schedules: Schedules belong to a particular test.
            executions: Executions belong to a particular test.
    """
    mcp = FastMCP("blazemeter-apim-mcp", instructions=instructions,
                  log_level=cast(LOG_LEVELS, log_level))
    register_tools(mcp, token)
    mcp.run(transport="stdio")


def main():
    parser = argparse.ArgumentParser(prog="mcp-bzm-apim")

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Execute MCP Server"
    )

    parser.add_argument(
        "--log-level",
        default="CRITICAL",  # By default, only critical errors
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: CRITICAL = critical errors only)"
    )

    args = parser.parse_args()
    init_logging(args.log_level)

    if args.mcp:
        run(log_level=args.log_level.upper())
    else:

        logo_ascii = (
            "  ____  _                __  __      _            \n"
            " | __ )| | __ _ _______ |  \\/  | ___| |_ ___ _ __ \n"
            " |  _ \\| |/ _` |_  / _ \\| .  . |/ _ \\ __/ _ \\ '__|\n"
            " | |_) | | (_| |/ /  __/| |\\/| |  __/ ||  __/ |   \n"
            " |____/|_|\\__,_/___\\___||_|  |_|\\___|\\__\\___|_|   \n"
            "                                                    \n"
            f" BlazeMeter APIM MCP Server v{__version__} \n"
        )
        print(logo_ascii)

        config_dict = {
            "BlazeMeter APIM MCP": {
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
            print(" [X] BlazeMeter APIM token not configured.")
            print(" ")
            print(
                " Copy the BlazeMeter APIM Token file (bzm_apim_token.json) to the same location of this"
                " executable.")
            print(" ")
            print(" How to obtain the bzm_apim_token file:")
            print(" https://help.blazemeter.com/docs/guide/api-blazemeter-api-keys.html")
        else:
            print(" [OK] BlazeMeter APIM token configured correctly.")
        print(" ")
        print(" There are configuration alternatives, if you want to know more:")
        print(" https://github.com/Blazemeter/bzm-mcp/")
        print(" ")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
