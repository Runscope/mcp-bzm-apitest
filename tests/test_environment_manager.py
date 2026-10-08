"""
Unit tests for EnvironmentManager
"""
import pytest
from unittest.mock import Mock, patch

import httpx

from src.tools.environment_manager import EnvironmentManager
from src.models import BaseResult


@pytest.mark.asyncio
class TestEnvironmentManager:
    """Test cases for EnvironmentManager"""

    async def test_list_environments(self, mock_token, mock_context):
        """Test listing environments"""
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "env_1", "name": "Development"},
                    {"id": "env_2", "name": "Production"}
                ],
                total=2
            )

            result = await manager.list("bucket_abc", "test_123")

            assert result.error is None
            assert len(result.result) == 2

    async def test_read_environment(self, mock_token, mock_context):
        """Test reading an environment"""
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "env_123",
                    "name": "Production",
                    "initial_variables": {"API_KEY": "secret"}
                }],
                total=1
            )

            result = await manager.read("bucket_abc", "test_123", "env_123")

            assert result.error is None
            assert result.result[0]["name"] == "Production"

    async def test_list_local_environments_regression(self, mock_token, mock_context):
        """Covers T001, T028. Scenario S6 (positive / regression). AC-2, FR-001.

        Named regression guard required by spec.md's Requirement Traceability
        Matrix (AC-2): proves the EXISTING local (test-level) list behavior is
        unaffected by this ticket's shared-scope and create/modify additions.
        Falsification: if shared-scope routing (added for AC-1/AC-3/AC-4/AC-6/
        AC-7) accidentally changed the local-scope endpoint or dropped the
        test_id parameter, this test (which pins the original two-arg call
        signature and endpoint shape) would fail.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "env_1", "name": "Development"},
                    {"id": "env_2", "name": "Production"},
                ],
                total=2,
            )

            result = await manager.list("bucket_abc", "test_123")

        assert result.error is None
        assert len(result.result) == 2

        endpoint = mock_api.call_args.args[2]
        assert endpoint == "/buckets/bucket_abc/tests/test_123/environments", (
            f"Local-scope list must still hit the test-level endpoint "
            f"unchanged by the shared-scope additions, got: {endpoint}"
        )


def _register_and_get_tool(token=None):
    """Harness helper: register the environments MCP tool and return the underlying
    async function, mirroring tests/test_version_manager.py::_register_and_get_tool.

    Used by negative-path tests that must exercise the register()-level try/except
    ladder (http_error_message conversion), since EnvironmentManager methods
    themselves do not catch HTTPStatusError -- only the @mcp.tool wrapper does.
    """
    from src.tools.environment_manager import register

    captured = []

    def mock_tool_decorator(name=None, description=None):
        def decorator(func):
            captured.append(func)
            return func

        return decorator

    mcp = Mock()
    mcp.tool = mock_tool_decorator
    register(mcp, token)
    return captured[0]


def _http_status_error(status_code):
    """Build a real httpx.HTTPStatusError the way tests/test_api_client.py does
    (Mock response, no live request) -- repo convention for simulating API errors.
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    return httpx.HTTPStatusError(f"{status_code} error", request=Mock(), response=mock_response)


@pytest.mark.asyncio
class TestHarnessCreateAnalogSchedule:
    """Harness validity check (step 2f.5). Analog: ScheduleManager.create
    (src/tools/schedule_manager.py), the brownfield-cited CREATE analog
    ("mirror schedule_manager.create") for EnvironmentManager's not-yet-written
    create_test_environment/create_shared_environment methods.

    This test exercises the EXISTING, ALREADY-WORKING create path through the
    exact invocation + result-accessor pattern the new create_* red tests will
    use (manager method call -> BaseResult -> result.result[0][<alias field>]).
    It must PASS today, proving the harness (not the not-yet-existing code) is
    correct. Not a red test -- excluded from the scenarios list and from the
    negative-quota calculation.
    """

    async def test_harness_schedule_create_analog_returns_serialized_fields(self, mock_token, mock_context):
        """Harness. Analog: ScheduleManager.create. Pattern: typed-model POST + BaseResult read.

        Proves: (1) calling a manager's create-style method with a mocked api_request
        returns a BaseResult whose .result[0][<field>] accessor exposes the created
        payload, and (2) the manager-level call site never needs to catch
        HTTPStatusError itself (confirmed by this test using the same bare manager
        call the red tests will use, no try/except around it).
        """
        from src.tools.schedule_manager import ScheduleManager

        manager = ScheduleManager(mock_token, mock_context)

        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "new_schedule", "interval": "6h", "environment_id": "env_123"}],
                total=1,
            )

            result = await manager.create("bucket_abc", "test_123", "env_123", "6h")

        assert result.error is None
        assert result.result[0]["interval"] == "6h"
        assert mock_api.call_args.kwargs["json"] == {
            "note": "Schedule created via MCP tool",
            "interval": "6h",
            "environment_id": "env_123",
        }


@pytest.mark.asyncio
class TestHarnessRegisterErrorLadderAnalog:
    """Harness validity check (step 2f.5). Analog: version_manager's
    _register_and_get_tool pattern (tests/test_version_manager.py), the only
    existing example in this repo of invoking a register()-wrapped MCP tool
    function directly (rather than the bare manager class).

    Proves the _register_and_get_tool helper (copied above as
    _register_and_get_tool for environment_manager) correctly captures and
    invokes the tool function, and that an unknown action ALREADY returns a
    BaseResult error through the existing environments register() ladder.
    This is the harness the negative-path (http_error_message /
    no-delete-action) red tests below read results through.
    """

    async def test_harness_register_unknown_action_returns_error_result(self, mock_context):
        """Harness. Analog: existing environments register() match/case default arm.

        Calls the ALREADY-EXISTING environments tool (today only read/list are
        wired) with a bogus action and asserts the existing `case _:` arm
        returns a BaseResult with a non-None .error -- proving the
        _register_and_get_tool + result.error accessor pattern is valid before
        it's reused by test_environments_tool_has_no_delete_action below.
        """
        environments_tool = _register_and_get_tool()

        result = await environments_tool(action="bogus_action_xyz", args={}, ctx=mock_context)

        assert result.error is not None
        assert "bogus_action_xyz" in result.error


@pytest.mark.asyncio
class TestModifyEnvironmentAgentSwap:
    """Covers T004, T009, T010. US1 AC "Modify an environment via PATCH (partial)",
    AC "Agent-swap path works end to end". FR-006, FR-007, SC-001.

    Scenario S1 (positive / static-contract / mock-reality hard-gate): modifying
    only remote_agents must send a PATCH body containing ONLY remote_agents (not
    a full-body PUT-style replace), and the manager must expose the method as
    `modify_environment` (never `patch_environment` -- Forbidden Identifier).
    """

    async def test_modify_environment_agent_swap_preserves_fields(self, mock_token, mock_context):
        """Covers T004, T009. Scenario S1 (positive / static-contract).

        Falsification: a full-body PUT-style call (one that includes name,
        regions, etc. in the PATCH body) fails this test, because the body
        equality assertion below only allows the single changed field.
        The mocked api_request's json kwarg is read directly (mock-reality
        rule: the mock must receive and expose the actual body for this
        assertion to be meaningful) rather than patched away.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006). "
            "Forbidden Identifier note: the method must be named "
            "'modify_environment', never 'patch_environment'."
        )
        assert not hasattr(manager, "patch_environment"), (
            "EnvironmentManager must not expose a method literally named "
            "'patch_environment' -- PATCH is the HTTP verb, not the method "
            "name (brownfield-context.md Forbidden Identifiers)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{
                    "id": "env_123",
                    "name": "Production",
                    "remote_agents": [{"uuid": "agent-b"}],
                    "initial_variables": {"API_KEY": "secret"},
                }],
                total=1,
            )

            result = await manager.modify_environment(
                "bucket_abc", "env_123", test_id="test_123", remote_agents=[{"uuid": "agent-b"}]
            )

        assert result.error is None
        assert result.result[0]["remote_agents"] == [{"uuid": "agent-b"}]

        _, call_kwargs = mock_api.call_args
        assert call_kwargs["json"] == {"remote_agents": [{"uuid": "agent-b"}]}, (
            f"PATCH body must contain ONLY remote_agents, got: {call_kwargs.get('json')}. "
            "A full-body PUT-style payload would reintroduce the MOB-49921 wipe risk."
        )
        assert mock_api.call_args.args[1] == "PATCH"

    async def test_modify_environment_name_only_preserves_remote_agents(self, mock_token, mock_context):
        """Covers T005, T009. Scenario S2 (positive / static-contract / partial-merge falsification).

        Modifying only name must NOT include remote_agents in the PATCH body --
        proving the partial-merge contract from the other direction (S1 proves
        a remote_agents-only change excludes other fields; this proves a
        name-only change excludes remote_agents).
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "env_123", "name": "X", "remote_agents": [{"uuid": "agent-a"}]}],
                total=1,
            )

            await manager.modify_environment("bucket_abc", "env_123", test_id="test_123", name="X")

        _, call_kwargs = mock_api.call_args
        assert call_kwargs["json"] == {"name": "X"}, (
            f"PATCH body for a name-only change must contain ONLY name, got: "
            f"{call_kwargs.get('json')}. remote_agents must be absent so the "
            f"server preserves it (partial-merge, not a full-body replace)."
        )
        assert "remote_agents" not in call_kwargs["json"]


@pytest.mark.asyncio
class TestModifyEnvironmentErrorPaths:
    """Covers T006, T007, T008. US1. FR-010, FR-006.

    Negative paths for modify: invalid id (404), validation error (4xx), and
    empty payload (no-op, no error).
    """

    async def test_modify_environment_invalid_id_returns_not_found(self, mock_token, mock_context):
        """Covers T006. Scenario S9 (negative). AC "Clear error messages for invalid ... env ID".

        The manager method itself re-raises HTTPStatusError (api_request's
        documented behavior -- see src/common/api_client.py, "except
        httpx.HTTPStatusError: raise"); categorization into a clear message
        happens in the register() try/except ladder. This test exercises the
        full registered tool (via the harness-proven _register_and_get_tool),
        not the bare manager call, so it reads the error the way the real MCP
        client will receive it.
        """
        manager = EnvironmentManager(mock_token, mock_context)
        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006); "
            "the 'modify' action cannot yet route to it."
        )

        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(404),
        ):
            result = await environments_tool(
                action="modify",
                args={"bucket_key": "bucket_abc", "test_id": "test_123", "environment_id": "nonexistent", "remote_agents": []},
                ctx=mock_context,
            )

        assert result.error is not None
        assert "not found" in result.error.lower() or "404" in result.error
        assert "not found in environments manager tool" not in result.error, (
            f"The 'modify' action is not routed yet -- got the generic "
            f"unknown-action error instead of a categorized 404, got: {result.error}"
        )

    async def test_modify_environment_validation_error_surfaced(self, mock_token, mock_context):
        """Covers T007. Scenario S10 (negative). AC "Clear error messages for ... validation errors"."""
        manager = EnvironmentManager(mock_token, mock_context)
        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006); "
            "the 'modify' action cannot yet route to it."
        )

        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(422),
        ):
            result = await environments_tool(
                action="modify",
                args={"bucket_key": "bucket_abc", "test_id": "test_123", "environment_id": "env_123", "name": ""},
                ctx=mock_context,
            )

        assert result.error is not None
        assert "not found in environments manager tool" not in result.error, (
            f"The 'modify' action is not routed yet -- got the generic "
            f"unknown-action error instead of a categorized validation error, got: {result.error}"
        )

    async def test_modify_environment_empty_payload_returns_current_unchanged(self, mock_token, mock_context):
        """Covers T008. Scenario S11 (negative / edge). AC-6.

        A modify call with no changed fields must return the CURRENT environment (not just its
        id) with no write and no error (spec.md Edge Cases: "Empty modify payload"). It reads the
        environment with a GET; a PATCH would be a write.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "env_123", "name": "Production"}],
                total=1,
            )

            result = await manager.modify_environment("bucket_abc", "env_123", test_id="test_123")

        assert result.error is None
        assert result.result[0]["name"] == "Production"
        mock_api.assert_called_once()
        call_args, _ = mock_api.call_args
        assert call_args[1] == "GET"
        assert call_args[2] == "/buckets/bucket_abc/tests/test_123/environments/env_123"


@pytest.mark.asyncio
class TestEnvironmentArgumentValidation:
    """Unsupported or missing fields must produce a clear error, never a silent success."""

    async def test_modify_unsupported_field_is_rejected(self, mock_token, mock_context):
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            result = await manager.modify_environment(
                "bucket_abc", "env_123", webhooks=["https://example.com/hook"]
            )

        assert result.error is not None
        assert "webhooks" in result.error
        assert "not a supported field" in result.error
        mock_api.assert_not_called()

    async def test_create_unsupported_field_is_rejected(self, mock_token, mock_context):
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            result = await manager.create_shared_environment("bucket_abc", name="Shared", emails={})

        assert result.error is not None
        assert "emails" in result.error
        mock_api.assert_not_called()

    async def test_create_without_name_reports_missing_name(self, mock_token, mock_context):
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            result = await manager.create_test_environment("bucket_abc", "test_123")

        assert result.error is not None
        assert "'name' is required" in result.error
        mock_api.assert_not_called()


class TestSharedEnvironmentFormatting:
    """api_request is mocked in the manager tests, so these run the real formatter against the
    producer's shared-environment payload, where test_id is null (it belongs to no test)."""

    def test_shared_environment_with_null_test_id_formats(self):
        from src.formatters.environment import format_environments

        payload = {
            "id": "env-uuid-1",
            "test_id": None,
            "name": "Shared Production",
            "parent_environment_id": None,
            "initial_variables": {"base_url": "https://example.com"},
            "retry_on_failure": False,
            "script": None,
            "webhooks": [],
            "integrations": [],
            "emails": {"recipients": []},
            "preserve_cookies": True,
            "stop_on_failure": False,
            "verify_ssl": True,
            "http_version_support": "http1.1",
            "force_h2c": False,
            "regions": ["us1"],
            "remote_agents": [],
            "headers": {},
        }

        result = format_environments([payload])

        assert result[0]["environment_id"] == "env-uuid-1"
        assert result[0]["test_id"] is None


@pytest.mark.asyncio
class TestCreateLocalEnvironment:
    """Covers T011, T014, T015. US2 AC "Create a local (test-level) environment".
    FR-004, SC-002.
    """

    async def test_create_local_environment(self, mock_token, mock_context):
        """Covers T011, T014. Scenario S3 (positive / static-contract).

        Harness proven by TestHarnessCreateAnalogSchedule above (same
        typed-model POST + BaseResult.result[0][field] accessor pattern as
        ScheduleManager.create). Falsification: a call that hits the shared
        (bucket-level) endpoint instead of the test-level endpoint fails the
        endpoint assertion.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "create_test_environment"), (
            "EnvironmentManager has no create_test_environment method yet (FR-004)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "env_new", "name": "Staging", "initial_variables": {"K": "V"}}],
                total=1,
            )

            result = await manager.create_test_environment(
                "bucket_abc", "test_123", name="Staging", initial_variables={"K": "V"}
            )

        assert result.error is None
        assert result.result[0]["name"] == "Staging"

        call_args, call_kwargs = mock_api.call_args
        assert call_args[1] == "POST"
        assert "/buckets/bucket_abc/tests/test_123/environments" in call_args[2]
        assert call_kwargs["json"]["name"] == "Staging"

    async def test_create_local_environment_limit_reached_surfaces_api_message(
        self, mock_token, mock_context
    ):
        """Covers T012. Scenario S12 (negative). AC "Surface API-enforced limits clearly", FR-009.

        Falsification: an implementation that hardcodes/pre-validates the 100
        cap client-side (rejected design alternative) would never reach this
        mocked 400, and the test would fail with no error surfaced; this test
        requires the 400 to flow through to http_error_message.
        """
        manager = EnvironmentManager(mock_token, mock_context)
        assert hasattr(manager, "create_test_environment"), (
            "EnvironmentManager has no create_test_environment method yet (FR-004); "
            "the local 'create' action cannot yet route to it."
        )

        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(400),
        ):
            result = await environments_tool(
                action="create",
                args={"bucket_key": "bucket_abc", "test_id": "test_123", "name": "One Too Many"},
                ctx=mock_context,
            )

        assert result.error is not None
        assert "not found in environments manager tool" not in result.error, (
            f"The local 'create' action is not routed yet -- got the generic "
            f"unknown-action error instead of a categorized 400 limit message, got: {result.error}"
        )

    async def test_create_local_environment_invalid_ids_return_error(self, mock_token, mock_context):
        """Covers T013. Scenario S13 (negative). AC "Clear error messages for invalid bucket/test ... ID"."""
        manager = EnvironmentManager(mock_token, mock_context)
        assert hasattr(manager, "create_test_environment"), (
            "EnvironmentManager has no create_test_environment method yet (FR-004); "
            "the local 'create' action cannot yet route to it."
        )

        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(404),
        ):
            result = await environments_tool(
                action="create",
                args={"bucket_key": "nonexistent_bucket", "test_id": "nonexistent_test", "name": "X"},
                ctx=mock_context,
            )

        assert result.error is not None
        assert "not found in environments manager tool" not in result.error, (
            f"The local 'create' action is not routed yet -- got the generic "
            f"unknown-action error instead of a categorized 404, got: {result.error}"
        )


@pytest.mark.asyncio
class TestSharedEnvironments:
    """Covers T016-T023. US3 ACs: list shared, read shared, create shared, shared
    limit. FR-002, FR-003, FR-005, SC-002, SC-003, SC-004.
    """

    async def test_list_shared_environments(self, mock_token, mock_context):
        """Covers T016, T021, T023. Scenario S5 (positive / static-contract).

        Falsification: a call that targets the test-level endpoint (with a
        test_id segment) instead of the bucket-level endpoint fails the
        endpoint assertion -- proving list correctly branches shared vs local.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "shared_1", "name": "Shared A"}, {"id": "shared_2", "name": "Shared B"}],
                total=2,
            )

            result = await manager.list("bucket_abc", test_id=None)

        assert result.error is None
        assert len(result.result) == 2

        call_args = mock_api.call_args.args
        endpoint = call_args[2]
        assert endpoint == "/buckets/bucket_abc/environments", (
            f"Shared-scope list must hit the bucket-level endpoint, got: {endpoint}"
        )
        assert "/tests/" not in endpoint

    async def test_read_shared_environment(self, mock_token, mock_context):
        """Covers T017, T021. Scenario S7 (positive / static-contract). AC-3."""
        manager = EnvironmentManager(mock_token, mock_context)

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "shared_1", "name": "Shared A"}],
                total=1,
            )

            result = await manager.read("bucket_abc", test_id=None, environment_id="shared_1")

        assert result.error is None
        assert result.result[0]["id"] == "shared_1"

        endpoint = mock_api.call_args.args[2]
        assert endpoint == "/buckets/bucket_abc/environments/shared_1"
        assert "/tests/" not in endpoint

    async def test_create_shared_environment(self, mock_token, mock_context):
        """Covers T018, T022, T023. Scenario S4 (positive / static-contract). AC-4.

        Harness proven by TestHarnessCreateAnalogSchedule. Falsification: a
        call that includes a test_id segment in the endpoint fails the
        bucket-level-only assertion.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "create_shared_environment"), (
            "EnvironmentManager has no create_shared_environment method yet (FR-005)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "shared_new", "name": "Shared C"}],
                total=1,
            )

            result = await manager.create_shared_environment("bucket_abc", name="Shared C")

        assert result.error is None
        assert result.result[0]["name"] == "Shared C"

        call_args, call_kwargs = mock_api.call_args
        assert call_args[1] == "POST"
        assert call_args[2] == "/buckets/bucket_abc/environments"
        assert "/tests/" not in call_args[2]
        assert call_kwargs["json"]["name"] == "Shared C"

    async def test_create_shared_environment_limit_reached_surfaces_api_message(
        self, mock_token, mock_context
    ):
        """Covers T019. Scenario S15 (negative). AC-9, FR-009.

        Mirrors test_create_local_environment_limit_reached_surfaces_api_message
        but for the shared (bucket-level) scope -- the 100-shared-per-bucket cap.
        """
        manager = EnvironmentManager(mock_token, mock_context)
        assert hasattr(manager, "create_shared_environment"), (
            "EnvironmentManager has no create_shared_environment method yet (FR-005); "
            "the shared 'create' action cannot yet route to it."
        )

        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(400),
        ):
            result = await environments_tool(
                action="create",
                args={"bucket_key": "bucket_at_limit", "name": "One Too Many Shared"},
                ctx=mock_context,
            )

        assert result.error is not None
        assert "not found in environments manager tool" not in result.error, (
            f"The shared 'create' action is not routed yet -- got the generic "
            f"unknown-action error instead of a categorized 400 limit message, got: {result.error}"
        )

    async def test_modify_shared_environment(self, mock_token, mock_context):
        """Covers T020. Scenario (positive / static-contract, additional beyond
        the planner's 15-scenario seed -- shared-scope modify was named in
        tasks.md T020 but not separately enumerated in test-scenarios.md's
        table). AC-6, AC-7 (shared-scope variant).

        Proves modify_environment routes to the bucket-level (no /tests/)
        endpoint when test_id is None/absent, mirroring the local-scope
        assertions in TestModifyEnvironmentAgentSwap but for shared scope.
        """
        manager = EnvironmentManager(mock_token, mock_context)

        assert hasattr(manager, "modify_environment"), (
            "EnvironmentManager has no modify_environment method yet (FR-006)."
        )

        with patch("src.tools.environment_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "shared_1", "name": "Renamed Shared"}],
                total=1,
            )

            result = await manager.modify_environment("bucket_abc", "shared_1", test_id=None, name="Renamed Shared")

        assert result.error is None
        assert result.result[0]["name"] == "Renamed Shared"

        call_args, call_kwargs = mock_api.call_args
        assert call_args[1] == "PATCH"
        endpoint = call_args[2]
        assert endpoint == "/buckets/bucket_abc/environments/shared_1"
        assert "/tests/" not in endpoint
        assert call_kwargs["json"] == {"name": "Renamed Shared"}


@pytest.mark.asyncio
class TestRequestModelSerialization:
    """Covers T002, T003. US4 AC "Tool naming/inputs/output follow conventions". FR-013.

    Foundational contract test: CreateEnvironment/ModifyEnvironment must
    serialize with by_alias=True, exclude_none=True so omitted fields are
    absent from the wire body (required for modify's partial-merge contract
    and for create's clean payload).
    """

    def test_create_modify_request_models_serialize_by_alias_exclude_none(self):
        """Covers T002, T003. Scenario S8 (positive / static-contract).

        Falsification: a model that serializes None fields (no
        exclude_none=True) would include them in the dumped dict, failing the
        "omitted fields absent" assertions below -- and for modify, would
        reintroduce the full-body-replace risk this ticket exists to avoid.
        """
        import src.models.environment as environment_module

        assert hasattr(environment_module, "CreateEnvironment"), (
            "src.models.environment has no CreateEnvironment model yet (FR-013, T002)."
        )
        assert hasattr(environment_module, "ModifyEnvironment"), (
            "src.models.environment has no ModifyEnvironment model yet (FR-013, T002)."
        )

        CreateEnvironment = environment_module.CreateEnvironment
        ModifyEnvironment = environment_module.ModifyEnvironment

        create_model = CreateEnvironment(name="Only Name")
        create_body = create_model.model_dump(by_alias=True, exclude_none=True)
        assert create_body == {"name": "Only Name"}, (
            f"CreateEnvironment with only name set must serialize to exactly "
            f"{{'name': 'Only Name'}} with all other fields omitted, got: {create_body}"
        )

        modify_model = ModifyEnvironment(remote_agents=[{"uuid": "agent-b"}])
        modify_body = modify_model.model_dump(by_alias=True, exclude_none=True)
        assert modify_body == {"remote_agents": [{"uuid": "agent-b"}]}, (
            f"ModifyEnvironment with only remote_agents set must serialize to "
            f"exactly {{'remote_agents': [...]}} with all other fields omitted, "
            f"got: {modify_body}"
        )

        empty_modify_body = ModifyEnvironment().model_dump(by_alias=True, exclude_none=True)
        assert empty_modify_body == {}, (
            f"An empty ModifyEnvironment (no fields set) must serialize to an "
            f"empty dict, got: {empty_modify_body}"
        )


@pytest.mark.asyncio
class TestAuthAndConsentGating:
    """Covers T025. US4 AC "respect existing PAT auth, RBAC, AI-consent gating". FR-008.

    Proves a write action surfaces the platform's 401/403 decision via the
    existing http_error_message auth category, and (per the Forbidden
    Identifier) that the tool adds no redundant MCP-layer ai_consent check of
    its own.
    """

    async def test_insufficient_permission_surfaces_auth_error(self, mock_token, mock_context):
        """Covers T025. Scenario S14 (negative). AC-8.

        Falsification: if the tool added its own ai_consent/permission check
        (forbidden per brownfield-context.md), this test would still pass
        coincidentally -- the real proof is in
        test_environment_manager_has_no_redundant_consent_check below, which
        this test complements.
        """
        environments_tool = _register_and_get_tool(mock_token)

        with patch(
            "src.tools.environment_manager.api_request",
            side_effect=_http_status_error(403),
        ):
            result = await environments_tool(
                action="modify",
                args={"bucket_key": "bucket_abc", "test_id": "test_123", "environment_id": "env_123", "name": "X"},
                ctx=mock_context,
            )

        assert result.error is not None
        assert (
            "auth" in result.error.lower()
            or "permission" in result.error.lower()
            or "403" in result.error
        )

    def test_environment_manager_has_no_redundant_consent_check(self):
        """Covers T025. Scenario (negative constraint — forbidden identifier).

        brownfield-context.md Forbidden Identifiers: a new MCP-layer
        ai_consent enforcement block is forbidden (ai_consent is enforced
        server-side by the api service). Scans the environment_manager source
        for any local ai_consent check the implementation might add.
        """
        import inspect

        import src.tools.environment_manager as env_manager_module

        source = inspect.getsource(env_manager_module)
        assert "ai_consent" not in source, (
            "src/tools/environment_manager.py must not implement a local "
            "ai_consent check -- it is enforced server-side by the api "
            "service for the bzm-apitest-mcp user-agent (brownfield-context.md "
            "Forbidden Identifiers)."
        )


@pytest.mark.asyncio
class TestNoDeleteAction:
    """Covers T024. US4 AC "Delete stays out of scope". FR-012, AC-12.

    No-delete guard (planner hard-gate scenario). Enumerates the registered
    environments tool's handled actions and asserts delete is absent, using
    the existing-today unknown-action arm (harness-proven above) as the probe.
    """

    async def test_environments_tool_has_no_delete_action(self, mock_context):
        """Covers T024. Scenario (no-delete guard, planner hard-gate).

        Falsification: if a `delete` action were wired into the match/case
        router, this call would route to it instead of falling through to the
        existing not-found arm, and the assertion on the not-found message
        would fail.
        """
        environments_tool = _register_and_get_tool()

        result = await environments_tool(action="delete", args={}, ctx=mock_context)

        assert result.error is not None
        assert "delete" in result.error, (
            f"Expected the 'delete' action to fall through to the existing "
            f"not-found arm (no delete action is ever wired in), got: {result.error}"
        )
