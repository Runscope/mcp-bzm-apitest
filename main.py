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

BLAZEMETER_APIM_KEY_FILE_PATH = os.getenv('BZM_APIM_TOKEN')

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
    # print("**************")
    # print(f"BLAZEMETER_APIM_KEY_FILE_PATH: {BLAZEMETER_APIM_KEY_FILE_PATH}")
    # Verify if running inside Docker container
    is_docker = os.getenv('MCP_DOCKER', 'false').lower() == 'true'
    token = None

    local_api_key_file = os.path.join(
        os.path.dirname(__executable__), "bzm_apim_token.json")

    if BLAZEMETER_APIM_KEY_FILE_PATH:
        token = BLAZEMETER_APIM_KEY_FILE_PATH.strip()
        return token

    if not BLAZEMETER_APIM_KEY_FILE_PATH and os.path.exists(local_api_key_file):
        BLAZEMETER_APIM_KEY_FILE_PATH = local_api_key_file

    if BLAZEMETER_APIM_KEY_FILE_PATH:
        try:
            token = BzmApimToken.from_file(BLAZEMETER_APIM_KEY_FILE_PATH)
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
        - If you have the information needed to call a tool action with its arguments, do so.
        - Read action always get more information about a particular item than the list action, list only display minimal information.
        - Read the current user information at startup to learn the username, default account, workspace and project, and other important information.
        - Dependencies:
            accounts: It doesn't depend on anyone. In user you can access which is the default account, and in the list of accounts, you can see the accounts available to the user.
            workspaces: Workspaces belong to a particular account.
            projects: Projects belong to a particular workspace.
            tests: Tests belong to a particular project.
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
    # else:
    #
    #     logo_ascii = (
    #         "  ____  _                __  __      _            \n"
    #         " | __ )| | __ _ _______ |  \/  | ___| |_ ___ _ __ \n"
    #         " |  _ \| |/ _` |_  / _ \| .  . |/ _ \ __/ _ \ '__|\n"
    #         " | |_) | | (_| |/ /  __/| |\/| |  __/ ||  __/ |   \n"
    #         " |____/|_|\__,_/___\___||_|  |_|\___|\__\___|_|   \n"
    #         "                                                    \n"
    #         f" BlazeMeter APIM MCP Server v{__version__} \n"
    #     )
    #     print(logo_ascii, file=sys.stderr)
    #
    #     config_dict = {
    #         "BlazeMeter APIM MCP": {
    #             "command": f"{__executable__}",
    #             "args": ["--mcp"],
    #         }
    #     }
    #
    #     print(" MCP Server Configuration:\n", file=sys.stderr)
    #     print(" In your tool with MCP server support, locate the MCP server configuration file", file=sys.stderr)
    #     print(" and add the following server to the server list.\n", file=sys.stderr)
    #
    #     json_str = json.dumps(config_dict, ensure_ascii=False, indent=4)
    #     print("\n".join(json_str.split("\n")[1:-1]) + "\n", file=sys.stderr)
    #
    #     if not get_api_token():
    #         print(" [X] BlazeMeter APIM token not configured.")
    #         print(" ")
    #         print(
    #             " Copy the BlazeMeter APIM Token file (bzm_apim_token.json) to the same location of this executable.")
    #         print(" ")
    #         print(" How to obtain the bzm_apim_token file:")
    #         print(" https://help.blazemeter.com/docs/guide/api-blazemeter-api-keys.html")
    #     else:
    #         print(" [OK] BlazeMeter APIM token configured correctly.", file=sys.stderr)
    #     print(" ", file=sys.stderr)
    #     print(" There are configuration alternatives, if you want to know more:", file=sys.stderr)
    #     print(" https://github.com/Blazemeter/bzm-mcp/", file=sys.stderr)
    #     print(" ", file=sys.stderr)
    #     input("Press Enter to exit...")


if __name__ == "__main__":
    main()