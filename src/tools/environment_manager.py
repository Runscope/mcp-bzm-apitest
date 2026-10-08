import logging
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import Context
from pydantic import ValidationError

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
from src.config.defaults import (
    BUCKET_LEVEL_ENVIRONMENT_ENDPOINT,
    TEST_ENVIRONMENT_ENDPOINT,
    TOOLS_PREFIX,
)
from src.config.token import BzmApimToken
from src.formatters.environment import format_environments
from src.models import BaseResult
from src.models.environment import CreateEnvironment, ModifyEnvironment

logger = logging.getLogger(__name__)


def _environments_endpoint(bucket_key: str, test_id: Optional[str]) -> str:
    """Return the collection endpoint for the requested scope.

    Local (test-level) scope when test_id is supplied, shared (bucket-level) scope otherwise.
    """
    if test_id:
        return TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)
    return BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)


def _invalid_arguments(error: ValidationError) -> BaseResult:
    """Turn a request-model validation error into a clear, actionable tool error."""
    problems = []
    for err in error.errors():
        field = ".".join(str(part) for part in err["loc"]) or "arguments"
        if err["type"] == "extra_forbidden":
            problems.append(f"'{field}' is not a supported field")
        elif err["type"] == "missing":
            problems.append(f"'{field}' is required")
        else:
            problems.append(f"'{field}': {err['msg']}")
    return BaseResult(error="Invalid environment arguments: " + "; ".join(problems))


class EnvironmentManager:

    def __init__(self, token: Optional[BzmApimToken], ctx: Context):
        self.token = token
        self.ctx = ctx

    async def read(self, bucket_key: str, test_id: Optional[str], environment_id: str) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            f"{_environments_endpoint(bucket_key, test_id)}/{environment_id}",
            result_formatter=format_environments,
        )

    async def list(self, bucket_key: str, test_id: Optional[str] = None) -> BaseResult:
        return await api_request(
            self.token,
            "GET",
            _environments_endpoint(bucket_key, test_id),
            result_formatter=format_environments,
        )

    async def create_test_environment(self, bucket_key: str, test_id: str, **fields: Any) -> BaseResult:
        try:
            environment_data = CreateEnvironment(**fields)
        except ValidationError as e:
            return _invalid_arguments(e)
        body = environment_data.model_dump(by_alias=True, exclude_none=True)
        return await api_request(
            self.token,
            "POST",
            TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id),
            result_formatter=format_environments,
            json=body,
        )

    async def create_shared_environment(self, bucket_key: str, **fields: Any) -> BaseResult:
        try:
            environment_data = CreateEnvironment(**fields)
        except ValidationError as e:
            return _invalid_arguments(e)
        body = environment_data.model_dump(by_alias=True, exclude_none=True)
        return await api_request(
            self.token,
            "POST",
            BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key),
            result_formatter=format_environments,
            json=body,
        )

    async def modify_environment(
        self,
        bucket_key: str,
        environment_id: str,
        test_id: Optional[str] = None,
        **fields: Any,
    ) -> BaseResult:
        try:
            environment_data = ModifyEnvironment(**fields)
        except ValidationError as e:
            return _invalid_arguments(e)
        body = environment_data.model_dump(by_alias=True, exclude_none=True)
        if not body:
            # Nothing to change: no write, return the environment as it currently is.
            return await self.read(bucket_key, test_id, environment_id)
        return await api_request(
            self.token,
            "PATCH",
            f"{_environments_endpoint(bucket_key, test_id)}/{environment_id}",
            result_formatter=format_environments,
            json=body,
        )


def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_environments",
        description="""
        Operations on environments. Environments define execution settings for a test such as
        regions, variables, headers, SSL verification, and remote agents. Notification settings
        (emails, webhooks, integrations) and authentication are returned when reading but cannot
        be set through create or modify.
        Environments have two scopes: local (test-level, scoped to a single test) and shared
        (bucket-level, reusable across tests). Supply test_id for the local scope; omit it for the
        shared scope. Delete is not supported.
        Actions:
        - list: List environments. With test_id: the test's local environments. Without test_id:
          the bucket's shared environments.
            args(dict):
                bucket_key(str): Required. The id of the bucket.
                test_id(str): Optional. The id of the test. Omit for shared (bucket-level) scope.
        - read: Read a single environment.
            args(dict):
                bucket_key(str): Required. The id of the bucket.
                environment_id(str): Required. The id of the environment to read.
                test_id(str): Optional. The id of the test. Omit for shared (bucket-level) scope.
        - create: Create an environment. With test_id: a local (test-level) environment. Without
          test_id: a shared (bucket-level) environment.
            args(dict):
                bucket_key(str): Required. The id of the bucket.
                name(str): Required. The name of the new environment.
                test_id(str): Optional. The id of the test. Omit to create a shared environment.
                initial_variables(dict): Optional. Environment variables.
                regions(list): Optional. Execution regions.
                remote_agents(list): Optional. Remote agents configuration.
        - modify: Partially update an environment via PATCH. Only the supplied fields are changed;
          all other fields (including remote_agents when not supplied) are preserved server-side.
          Use this for the agent-swap path: supply only remote_agents to swap the private agent
          while keeping every other setting intact. Each supplied field replaces that field's whole
          value (e.g. initial_variables and remote_agents are replaced, not merged key by key), so
          send the complete new value. Unsupported fields are rejected with an error. With no
          fields supplied, nothing is changed and the current environment is returned.
            args(dict):
                bucket_key(str): Required. The id of the bucket.
                environment_id(str): Required. The id of the environment to modify.
                test_id(str): Optional. The id of the test. Omit for shared (bucket-level) scope.
                remote_agents(list): Optional. New remote agents (agent-swap).
                name(str): Optional. New environment name.
                initial_variables(dict): Optional. New environment variables.
                regions(list): Optional. New execution regions.
        Examples:
            - List local environments: action="list",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456"}
            - List shared environments: action="list", args={"bucket_key": "abc123def456"}
            - Get environment details: action="read",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "environment_id": "abc123def456"}
            - Read a shared environment: action="read",
              args={"bucket_key": "abc123def456", "environment_id": "abc123def456"}
            - Create a local environment: action="create",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456", "name": "Staging"}
            - Create a shared environment: action="create",
              args={"bucket_key": "abc123def456", "name": "Shared Staging"}
            - Swap the private agent (agent-swap): action="modify",
              args={"bucket_key": "abc123def456", "test_id": "abc123def456",
                    "environment_id": "abc123def456", "remote_agents": [{"uuid": "new-agent"}]}
        """,
    )
    async def environments(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        environment_manager = EnvironmentManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_environments", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span,
                            await environment_manager.read(
                                args["bucket_key"], args.get("test_id"), args["environment_id"]
                            ),
                        )
                    case "list":
                        return check_result_error(
                            span,
                            await environment_manager.list(args["bucket_key"], args.get("test_id")),
                        )
                    case "create":
                        fields = {
                            k: v
                            for k, v in args.items()
                            if k not in ("bucket_key", "test_id", "environment_id")
                        }
                        if args.get("test_id"):
                            result = await environment_manager.create_test_environment(
                                args["bucket_key"], args["test_id"], **fields
                            )
                        else:
                            result = await environment_manager.create_shared_environment(
                                args["bucket_key"], **fields
                            )
                        return check_result_error(span, result)
                    case "modify":
                        fields = {
                            k: v
                            for k, v in args.items()
                            if k not in ("bucket_key", "test_id", "environment_id")
                        }
                        return check_result_error(
                            span,
                            await environment_manager.modify_environment(
                                args["bucket_key"],
                                args["environment_id"],
                                test_id=args.get("test_id"),
                                **fields,
                            ),
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in environments manager tool")
            except httpx.TimeoutException:
                record_span_error(span, "timeout")
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "tool_error")
                logger.exception("Unexpected error in environments tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
