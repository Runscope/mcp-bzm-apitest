"""
Failing (red) tests for MOB-55587 — extend blazemeter_apitest_steps with
Inbound, conditional-if, conditional-loop, and subtest step types, plus
generic update_step and reorder_steps actions.

All tests mock src.tools.step_manager.api_request; none call live/dev/stage/
prod endpoints (see specs/mob-55587/brownfield-context.md, Test Validity
Strategy). Maps to specs/mob-55587/test-scenarios.md S1-S13 plus two harness
validity checks (S_HARNESS_1, S_HARNESS_2) that prove the invocation/
assertion pattern against the existing add_pause_step/add_request_step
analogs before trusting it for the new, not-yet-implemented builders.
"""

import httpx
import pytest
from unittest.mock import patch

from src.tools.step_manager import StepManager
from src.models import BaseResult


async def _invoke_add(manager, method_name, *args, **kwargs):
    """
    Harness helper: call an add_<type>_step builder the same way the existing
    add_pause_step/add_request_step tests do, and return (result, mock_api).
    Centralizing this means every red test below reads the POST/PUT body via
    the SAME call-args access pattern proven by the harness tests.
    """
    with patch("src.tools.step_manager.api_request") as mock_api:
        mock_api.return_value = kwargs.pop("_mock_return", BaseResult(result=[{"id": "new_step"}], total=1))
        method = getattr(manager, method_name)
        result = await method(*args, **kwargs)
        return result, mock_api


@pytest.mark.asyncio
class TestStepManagerHarnessValidity:
    """
    S_HARNESS_1 / S_HARNESS_2 -- prove the mock_api.call_args.kwargs["json"] POST-body-access
    pattern and the mocked-api_request/BaseResult round-trip pattern (the exact pattern every red
    test above relies on) against ScheduleManager.create/read -- a DIFFERENT tool manager this
    ticket does not touch (this ticket only changes src/tools/step_manager.py and
    src/models/step.py). Proving the pattern against an un-touched analog, rather than against
    add_pause_step/add_request_step in the very file the implementer will edit, means these
    harness tests cannot be invalidated by the implementer's changes to step_manager.py. These
    must PASS now, before any new StepManager builder exists.
    """

    async def test_harness_schedule_manager_create_post_body_pattern(self, mock_token, mock_context):
        """Harness check: mock_api.call_args.kwargs["json"] POST-body pattern against ScheduleManager.create (analog, untouched file)."""
        from src.tools.schedule_manager import ScheduleManager

        manager = ScheduleManager(mock_token, mock_context)
        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "new_schedule", "interval": "6h", "environment_id": "env_123"}],
                total=1,
            )
            result = await manager.create("bucket_abc", "test_123", "env_123", "6h")

            assert result.error is None
            sent_body = mock_api.call_args.kwargs["json"]
            assert sent_body["interval"] == "6h"
            assert sent_body["environment_id"] == "env_123"
            assert result.result[0]["interval"] == "6h"

    async def test_harness_schedule_manager_read_result_pattern(self, mock_token, mock_context):
        """Harness check: BaseResult.result[0] read-after-mock pattern against ScheduleManager.read (analog, untouched file)."""
        from src.tools.schedule_manager import ScheduleManager

        manager = ScheduleManager(mock_token, mock_context)
        with patch("src.tools.schedule_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[{"id": "schedule_123", "interval": "1h", "environment_id": "env_123"}],
                total=1,
            )
            result = await manager.read("bucket_abc", "test_123", "schedule_123")

            assert result.error is None
            assert result.result[0]["id"] == "schedule_123"
            assert result.result[0]["interval"] == "1h"


@pytest.mark.asyncio
class TestAddInboundStep:
    """S1 (AC-1) / S6 (AC-1, negative). Covers T003, T101, T106."""

    async def test_add_inbound_step(self, mock_token, mock_context):
        """Covers T003, T101. Scenario: POST body is {step_type:"inbound", token, isDynamicUrl}; step round-trips."""
        manager = StepManager(mock_token, mock_context)
        result, mock_api = await _invoke_add(
            manager,
            "add_inbound_step",
            "bucket_abc",
            "test_123",
            "inbound_token_xyz",
            True,
            _mock_return=BaseResult(
                result=[
                    {
                        "id": "new_step",
                        "step_type": "inbound",
                        "token": "inbound_token_xyz",
                        "isDynamicUrl": True,
                    }
                ],
                total=1,
            ),
        )
        assert result.error is None
        sent_body = mock_api.call_args.kwargs["json"]
        assert sent_body == {
            "step_type": "inbound",
            "token": "inbound_token_xyz",
            "isDynamicUrl": True,
        }
        assert result.result[0]["step_type"] == "inbound"

    async def test_add_inbound_step_missing_field(self, mock_token, mock_context):
        """Covers T106. Scenario: a categorized API error surfaces when a required inbound field is missing."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                error="Not found (HTTP 404): The requested resource does not exist. "
                "Check that the IDs you provided are correct."
            )
            result = await manager.add_inbound_step("bucket_abc", "test_123", None, True)
            assert result.error is not None
            assert "HTTP 404" in result.error
            assert "Traceback" not in result.error


@pytest.mark.asyncio
class TestAddConditionStep:
    """S2 (AC-1), assumption-challenge A-AUTO-END / wire-format. Covers T004, T102."""

    async def test_add_condition_step(self, mock_token, mock_context):
        """Covers T004, T102. Scenario: condition POST uses wire key "condition" (not "conditional"), no explicit end block, auto-end round-trips."""
        manager = StepManager(mock_token, mock_context)
        result, mock_api = await _invoke_add(
            manager,
            "add_condition_step",
            "bucket_abc",
            "test_123",
            comparison="equals",
            left_value="{{status}}",
            right_value="200",
            _mock_return=BaseResult(
                result=[
                    {
                        "id": "cond_start",
                        "step_type": "conditional",
                        "condition_type": "start",
                        "comparison": "equals",
                        "left_value": "{{status}}",
                        "right_value": "200",
                    },
                    {"id": "cond_end", "step_type": "conditional", "condition_type": "end"},
                ],
                total=2,
            ),
        )
        assert result.error is None
        sent_body = mock_api.call_args.kwargs["json"]
        # Falsification: the radar wire key MUST be "condition" singular, never "conditional".
        assert sent_body["step_type"] == "condition"
        assert sent_body["condition_type"] == "start"
        assert sent_body["comparison"] == "equals"
        assert sent_body["left_value"] == "{{status}}"
        assert sent_body["right_value"] == "200"
        # Falsification: tool must NOT construct or send an explicit end block.
        assert "end" not in sent_body
        assert not any(isinstance(v, dict) and v.get("condition_type") == "end" for v in sent_body.values())
        # The mocked response (simulating the parser's auto-appended end) still round-trips both entries.
        assert len(result.result) == 2
        assert result.result[1]["condition_type"] == "end"

    async def test_add_condition_step_invalid_comparison(self, mock_token, mock_context):
        """Covers T106. Scenario: an invalid comparison surfaces as a categorized parser error (lazy validation)."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = httpx.HTTPStatusError(
                "400 Bad Request",
                request=httpx.Request("POST", "https://api.example.com"),
                response=httpx.Response(400, request=httpx.Request("POST", "https://api.example.com")),
            )
            with pytest.raises(httpx.HTTPStatusError):
                await manager.add_condition_step(
                    "bucket_abc",
                    "test_123",
                    comparison="not_a_real_comparison",
                    left_value="x",
                    right_value="y",
                )
            # Falsification: the tool must NOT pre-validate comparison values itself (lazy validation
            # precedent) — it only forwards whatever the server rejects.
            sent_body = mock_api.call_args.kwargs["json"]
            assert sent_body["comparison"] == "not_a_real_comparison"


@pytest.mark.asyncio
class TestAddConditionalLoopStep:
    """S3 (AC-1). Covers T005, T103."""

    async def test_add_conditional_loop_step(self, mock_token, mock_context):
        """Covers T005, T103. Scenario: conditional-loop POST uses wire key "conditional-loop", no explicit end block."""
        manager = StepManager(mock_token, mock_context)
        result, mock_api = await _invoke_add(
            manager,
            "add_conditional_loop_step",
            "bucket_abc",
            "test_123",
            comparison="is_greater_than",
            left_value="{{counter}}",
            right_value="10",
            _mock_return=BaseResult(
                result=[
                    {
                        "id": "loop_start",
                        "step_type": "conditional-loop",
                        "condition_type": "start",
                    },
                    {"id": "loop_end", "step_type": "conditional-loop", "condition_type": "end"},
                ],
                total=2,
            ),
        )
        assert result.error is None
        sent_body = mock_api.call_args.kwargs["json"]
        assert sent_body["step_type"] == "conditional-loop"
        assert sent_body["condition_type"] == "start"
        assert sent_body["comparison"] == "is_greater_than"
        assert "end" not in sent_body
        assert not any(isinstance(v, dict) and v.get("condition_type") == "end" for v in sent_body.values())


@pytest.mark.asyncio
class TestAddSubtestStep:
    """S4 (AC-1), assumption-challenge A-SUBTEST-LAZY. Covers T006, T104."""

    async def test_add_subtest_step(self, mock_token, mock_context):
        """Covers T006, T104. Scenario: subtest POST carries required fields; builder does not pre-validate test_uuid (single POST call, lazy validation)."""
        manager = StepManager(mock_token, mock_context)
        result, mock_api = await _invoke_add(
            manager,
            "add_subtest_step",
            "bucket_abc",
            "test_123",
            test_uuid="does-not-exist-uuid",
            trigger_token="trig_abc",
            environment_uuid="env_abc",
            subtest_bucket_key="bucket_other",
            use_parent_environment=False,
            _mock_return=BaseResult(
                result=[
                    {
                        "id": "new_step",
                        "step_type": "subtest",
                        "test_uuid": "does-not-exist-uuid",
                        "trigger_token": "trig_abc",
                        "environment_id": "env_abc",
                        "bucket_key": "bucket_other",
                        "use_parent_environment": False,
                    }
                ],
                total=1,
            ),
        )
        assert result.error is None
        sent_body = mock_api.call_args.kwargs["json"]
        assert sent_body["step_type"] == "subtest"
        assert sent_body["test_uuid"] == "does-not-exist-uuid"
        assert sent_body["trigger_token"] == "trig_abc"
        assert sent_body["environment_uuid"] == "env_abc"
        assert sent_body["bucket_key"] == "bucket_other"
        assert sent_body["use_parent_environment"] is False
        # Falsification (A-SUBTEST-LAZY): exactly one API call (the POST) — no pre-existence
        # read/validation call for test_uuid before submitting.
        assert mock_api.call_count == 1
        assert mock_api.call_args.args[1] == "POST"


@pytest.mark.asyncio
class TestStepModelRoundtrip:
    """S5 (AC-1), Boundary Compatibility (model extension). Covers T011, T105."""

    async def test_teststep_model_roundtrip_inbound_subtest(self, mock_token, mock_context):
        """Covers T011, T105. Scenario: inbound and subtest response fields survive format_steps without being dropped."""
        from src.formatters.step import format_steps

        inbound_raw = {
            "id": "step_inbound",
            "step_type": "inbound",
            "skipped": False,
            "token": "inbound_token_xyz",
            "isDynamicUrl": True,
        }
        subtest_raw = {
            "id": "step_subtest",
            "step_type": "subtest",
            "skipped": False,
            "test_uuid": "sub_test_uuid",
            "trigger_token": "trig_abc",
            "environment_id": "env_abc",
            "use_parent_environment": True,
            "params": [{"name": "foo", "value": "bar"}],
        }
        formatted = format_steps([inbound_raw, subtest_raw])

        # Falsification: today's TestStep model has no fields for token/isDynamicUrl/trigger_token/
        # environment_id/use_parent_environment/params, so Pydantic silently drops them. This test
        # fails until the model is extended (T011) to carry these fields through model_dump().
        assert formatted[0]["token"] == "inbound_token_xyz"
        assert formatted[0]["is_dynamic_url"] is True
        assert formatted[1]["trigger_token"] == "trig_abc"
        assert formatted[1]["environment_id"] == "env_abc"
        assert formatted[1]["use_parent_environment"] is True
        assert formatted[1]["params"] == [{"name": "foo", "value": "bar"}]


@pytest.mark.asyncio
class TestUpdateStep:
    """S8 (AC-2) / S9 (AC-2, negative). Covers T007, T107."""

    async def test_update_step(self, mock_token, mock_context):
        """Covers T007, T107. Scenario: update_step reads the current step, merges updates, PUTs the full step dict."""
        manager = StepManager(mock_token, mock_context)
        with (
            patch.object(manager, "read") as mock_read,
            patch("src.tools.step_manager.api_request") as mock_api,
        ):
            mock_read.return_value = {
                "id": "step_123",
                "step_type": "pause",
                "duration": 5,
            }
            mock_api.return_value = BaseResult(
                result=[{"id": "step_123", "step_type": "pause", "duration": 30}], total=1
            )

            result = await manager.update_step("bucket_abc", "test_123", "step_123", {"duration": 30})

            assert result.error is None
            put_payload = mock_api.call_args.kwargs["json"]
            # Falsification: the PUT must carry the FULL merged step dict (id + step_type preserved),
            # not just the caller-supplied partial update.
            assert put_payload["id"] == "step_123"
            assert put_payload["step_type"] == "pause"
            assert put_payload["duration"] == 30
            assert result.result[0]["duration"] == 30

    async def test_update_step_unknown_id(self, mock_token, mock_context):
        """Covers T107. Scenario: update_step on an unknown step_id yields a BaseResult(error=...) not-found."""
        manager = StepManager(mock_token, mock_context)
        with (
            patch.object(manager, "read") as mock_read,
            patch("src.tools.step_manager.api_request") as mock_api,
        ):
            mock_read.return_value = {}

            result = await manager.update_step(
                "bucket_abc", "test_123", "step_does_not_exist", {"duration": 10}
            )

            assert result.error is not None
            mock_api.assert_not_called()


@pytest.mark.asyncio
class TestReorderSteps:
    """S10 (AC-3), assumption-challenge A-LOOP-REORDER / S11 (AC-3, negative). Covers T008, T108."""

    async def test_reorder_steps(self, mock_token, mock_context):
        """Covers T008, T108. Scenario: flat-id template_order PUT to /steps; reordered list returned."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.return_value = BaseResult(
                result=[
                    {"id": "step_2", "step_type": "request"},
                    {"id": "step_1", "step_type": "pause"},
                ],
                total=2,
            )

            step_order = [{"id": "step_2"}, {"id": "step_1"}]
            result = await manager.reorder_steps("bucket_abc", "test_123", step_order)

            assert result.error is None
            call_args, call_kwargs = mock_api.call_args.args, mock_api.call_args.kwargs
            # Falsification: reorder is a PUT to the collection endpoint (no /{step_id} suffix),
            # carrying the flat template_order list as the body.
            assert call_args[1] == "PUT"
            assert not call_args[2].endswith(tuple(f"/{s['id']}" for s in step_order))
            assert call_kwargs["json"] == step_order
            assert result.result[0]["id"] == "step_2"
            assert result.result[1]["id"] == "step_1"

    async def test_reorder_steps_missing_id(self, mock_token, mock_context):
        """Covers T108. Scenario: a non-list / missing-id reorder input yields an error without calling the API."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            result = await manager.reorder_steps("bucket_abc", "test_123", "not-a-list")

            assert result.error is not None
            mock_api.assert_not_called()


def _locate_error(template_id: str) -> httpx.HTTPStatusError:
    """A 400 whose body is the reorder API's matches-all-templates complaint (MOB-55673)."""
    request = httpx.Request("PUT", "https://api.runscope.com/buckets/b/tests/t/steps")
    response = httpx.Response(
        400,
        text='{"data": {}, "meta": {"status": "error"}, "error": {"error": '
        f'"Must provide a list of template ids that matches all templates in the test. '
        f'Unable to locate template {template_id} in updated list"}}}}',
        request=request,
    )
    return httpx.HTTPStatusError("400 error", request=request, response=response)


@pytest.mark.asyncio
class TestReorderHiddenEndblocks:
    """MOB-55673: conditional blocks carry a hidden end-block companion template that
    GET /steps never returns but the reorder API requires. reorder_steps discovers
    the missing ids from the API's own 400 and inserts each one immediately after
    its owning block (end-position placement would nest the following steps inside
    the block — verified live), bounded."""

    UUID1 = "ea3588fa-19c4-4efe-ab48-df36b26ea2dd"
    UUID2 = "c3135c57-de80-4085-ad10-54b389bb2696"

    # The visible listing reorder_steps fetches first: one request step, one
    # condition block, one pause. blocks = [step_2] (the condition).
    CURRENT = BaseResult(
        result=[
            {"id": "step_1", "step_type": "request"},
            {"id": "step_2", "step_type": "condition"},
            {"id": "33333333-3333-4333-8333-333333333333", "step_type": "pause"},
            {"id": "step_4", "step_type": "conditional-loop"},
        ],
        total=4,
    )

    @staticmethod
    def _puts(mock_api):
        return [c for c in mock_api.await_args_list if c.args[1] == "PUT"]

    async def test_reorder_two_phase_discovery_and_placement(self, mock_token, mock_context):
        """Scenario: two blocks, two hidden ends. Phase A appends the revealed ids at
        the end until the PUT is accepted; phase B re-PUTs once with each end placed
        immediately after its owning block (reveal order pairs with block order)."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [
                self.CURRENT,
                _locate_error(self.UUID1),   # phase A PUT #1: 400
                _locate_error(self.UUID2),   # phase A PUT #2: 400
                BaseResult(result=[{"id": "ok_phase_a"}], total=1),  # phase A PUT #3: 200
                BaseResult(result=[{"id": "ok_phase_b"}], total=1),  # phase B PUT #4: 200
            ]
            result = await manager.reorder_steps(
                "bucket_abc", "test_123",
                [{"id": "step_4"}, {"id": "step_1"}, {"id": "step_2"},
                 {"id": "33333333-3333-4333-8333-333333333333"}],
            )

            assert result.error is None
            puts = self._puts(mock_api)
            assert len(puts) == 4
            # Phase A's accepted payload had the ends appended at the end.
            assert puts[2].kwargs["json"][-1] == {"id": self.UUID2}
            # Phase B's payload places each end right after its owning block:
            # UUID1 pairs with the condition (step_2), UUID2 with the loop (step_4).
            assert puts[3].kwargs["json"] == [
                {"id": "step_4"}, {"id": self.UUID2},
                {"id": "step_1"},
                {"id": "step_2"}, {"id": self.UUID1},
                {"id": "33333333-3333-4333-8333-333333333333"},
            ]
            assert result.info and "2" in " ".join(result.info) and self.UUID1 in " ".join(result.info)

    async def test_reorder_phase_b_failure_warns_but_succeeds(self, mock_token, mock_context):
        """Scenario: phase A applies, phase B's corrective PUT 400s — the applied order
        stands, reported with a warning instead of failing the whole action."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [
                self.CURRENT,
                _locate_error(self.UUID1),   # phase A PUT #1: 400
                BaseResult(result=[{"id": "ok_phase_a"}], total=1),  # phase A PUT #2: 200
                _locate_error(self.UUID1),   # phase B PUT: 400 (API unhappy with placement)
            ]
            result = await manager.reorder_steps(
                "bucket_abc", "test_123", [{"id": "step_1"}, {"id": "step_2"}]
            )

            assert result.error is None  # phase A's reorder stands
            assert result.warning and "could not be structurally placed" in " ".join(result.warning)
            assert result.info and self.UUID1 in " ".join(result.info)

    async def test_reorder_rejects_missing_visible_step(self, mock_token, mock_context):
        """Scenario: the API reveals a VISIBLE step the caller omitted — targeted error, not pairing."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [self.CURRENT, _locate_error("33333333-3333-4333-8333-333333333333")]
            result = await manager.reorder_steps(
                "bucket_abc", "test_123", [{"id": "step_1"}, {"id": "step_2"}]
            )

            assert result.error is not None and "missing from your step_order" in result.error
            assert len(self._puts(mock_api)) == 1

    async def test_reorder_surfaces_actionable_error_on_unrelated_400(self, mock_token, mock_context):
        """Scenario: a 400 that does not match the reveal pattern returns a targeted error, not the generic one."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            request = httpx.Request("PUT", "https://api.runscope.com/x")
            response = httpx.Response(400, text='{"error": "different problem"}', request=request)
            mock_api.side_effect = [
                self.CURRENT,
                httpx.HTTPStatusError("400", request=request, response=response),
            ]
            result = await manager.reorder_steps("bucket_abc", "test_123", [{"id": "step_1"}])

            assert result.error is not None and "hidden end-block" in result.error.lower()
            assert len(self._puts(mock_api)) == 1

    async def test_reorder_stops_when_api_keeps_requiring_known_template(self, mock_token, mock_context):
        """Scenario: the API names a template already in the list — inconsistent template set, stop."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [self.CURRENT, _locate_error(self.UUID1)]
            result = await manager.reorder_steps(
                "bucket_abc", "test_123", [{"id": "step_1"}, {"id": self.UUID1}]
            )

            assert result.error is not None and "inconsistent" in result.error
            assert len(self._puts(mock_api)) == 1

    async def test_reorder_bounded_after_too_many_reveals(self, mock_token, mock_context):
        """Scenario: more distinct hidden ids than the cap — refuse instead of looping forever."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [self.CURRENT] + [
                _locate_error(f"{i:08x}-0000-4000-8000-{i:012x}") for i in range(20)
            ]
            result = await manager.reorder_steps("bucket_abc", "test_123", [{"id": "step_1"}])

            assert result.error is not None and "refusing" in result.error
            assert len(self._puts(mock_api)) <= 14  # 12 reveals + repeat/idempotence attempts

    async def test_reorder_normalizes_bare_id_strings(self, mock_token, mock_context):
        """Scenario: a caller passing bare id strings still sends the documented flat objects."""
        manager = StepManager(mock_token, mock_context)
        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = [
                self.CURRENT,
                BaseResult(result=[{"id": "step_2"}], total=1),
            ]
            result = await manager.reorder_steps("bucket_abc", "test_123", ["step_2", "step_1"])

            assert result.error is None
            assert self._puts(mock_api)[-1].kwargs["json"] == [{"id": "step_2"}, {"id": "step_1"}]


@pytest.mark.asyncio
class TestStepsDispatchNewActions:
    """S12 (FR-008). Covers T009, T109."""

    async def test_steps_dispatch_new_actions(self, mock_token, mock_context):
        """Covers T009, T109. Scenario: each of the 6 new action values routes to its builder with unpacked args."""
        from src.tools import step_manager as step_manager_module
        from mcp.server.fastmcp import FastMCP

        mcp = FastMCP("test")
        step_manager_module.register(mcp, mock_token)

        tools = await mcp.list_tools()
        steps_tool = next(t for t in tools if t.name.endswith("_steps"))

        new_actions = (
            "add_inbound_step",
            "add_condition_step",
            "add_conditional_loop_step",
            "add_subtest_step",
            "update_step",
            "reorder_steps",
        )
        for action in new_actions:
            # Falsification: today's tool description string documents only the pre-existing
            # actions (read/list/add_pause_step/add_request_step/add_*_to_step); none of the
            # 6 new action names appear until FR-008's registration work lands.
            assert action in steps_tool.description, f"{action} missing from tool description (FR-008)"


@pytest.mark.asyncio
class TestNewActionsErrorHandling:
    """S13 (FR-010, negative). Covers T010, T110."""

    async def test_new_actions_error_handling(self, mock_token, mock_context):
        """Covers T010, T110. Scenario: an httpx.HTTPStatusError in a new action surfaces as a categorized http_error_message (no raw status/trace/token)."""
        from src.tools.step_manager import register
        from mcp.server.fastmcp import FastMCP, Context

        mcp = FastMCP("test")
        register(mcp, mock_token)

        with patch("src.tools.step_manager.api_request") as mock_api:
            mock_api.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=httpx.Request("POST", "https://api.example.com"),
                response=httpx.Response(500, request=httpx.Request("POST", "https://api.example.com")),
            )
            tool_fn = mcp._tool_manager._tools[
                [n for n in mcp._tool_manager._tools if n.endswith("_steps")][0]
            ].fn

            result = await tool_fn(
                action="add_inbound_step",
                args={
                    "bucket_key": "bucket_abc",
                    "test_id": "test_123",
                    "token": "tok_secret_value",
                    "is_dynamic_url": True,
                },
                ctx=mock_context,
            )

            assert result.error is not None
            # Falsification: the error must be the categorized 5xx message from http_error_message()
            # (proves the httpx.HTTPStatusError actually propagated out of add_inbound_step and was
            # caught by the steps() dispatcher's except clause) -- not the generic "Action ... not
            # found" message the dispatcher returns today because no "add_inbound_step" case exists.
            assert "BlazeMeter API server error" in result.error
            assert "HTTP 500" in result.error
            assert "not found in steps manager tool" not in result.error
            assert "Traceback" not in result.error
            assert "tok_secret_value" not in result.error
