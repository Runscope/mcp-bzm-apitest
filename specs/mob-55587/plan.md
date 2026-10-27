# Implementation Plan: Extend blazemeter_apitest_steps — new step types, update, reorder

**Branch**: `ai-mob-55587` | **Date**: 2026-10-27 | **Spec**: `specs/mob-55587/spec.md`
**Input**: Feature specification from `specs/mob-55587/spec.md`; brownfield facts from `specs/mob-55587/brownfield-context.md`

## Summary

Extend the existing `blazemeter_apitest_steps` MCP tool so an AI agent can (1) add the four remaining step types — Inbound, conditional-if, conditional-loop, subtest; (2) update any existing step generically; and (3) reorder a test's steps. The implementation adds six new builder methods to `StepManager`, wires them into the `register()` match/case dispatch and tool description, and extends the `TestStep` response model with inbound/subtest fields. Every builder mirrors the existing `add_request_step` / `add_pause_step` pattern (a flat body dict with a literal `step_type` → single `api_request()` call). No new service, endpoint, or storage is introduced.

## Non-Goals

- Ghost Inspector / UI-test-integration steps are out of scope.
- No change to the existing request/pause step behavior, token resolution, or the single `api_request()` call site.
- No new service, endpoint, storage, or external dependency.
- Not fixing the server-side conditional-loop reorder-nesting limitation (API-side; documented only).

## Technical Context

**Language/Version**: Python 3.11+ (CI matrix 3.11 and 3.12)
**Primary Dependencies**: `mcp` (FastMCP), `httpx` (async HTTP), `pydantic` (models), `defusedxml`, `nh3`
**Storage**: N/A — stateless adapter; all state lives in the Runscope public API
**Testing**: pytest + pytest-asyncio (auto mode) + pytest-cov; `make test` / `make test-unit`; mocks via `unittest.mock.AsyncMock`
**Target Platform**: Linux / stdio MCP server (also Docker image)
**Project Type**: single project (MCP server library) — `src/` + `tests/`
**Performance Goals**: each tool action is a single API round-trip; no nested/N×M external-call pattern
**Constraints**: line length 108; max complexity 10 (flake8); LLM-friendly categorized errors; token never logged; single `api_request()` HTTP call site
**Scale/Scope**: ~6 new `StepManager` methods + 6 new dispatch cases + tool-description entries + `TestStep` model extension + tests; test step count capped at 100 by the API

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Repo constitution v1.0.0 principles:

| Principle | Compliance | Evidence |
|---|---|---|
| I. Domain-Scoped MCP Tools | PASS | All new actions live in the existing `StepManager` (step domain) under `src/tools/step_manager.py`; no cross-domain leakage; registered via `register()` + `@mcp.tool()`. |
| II. Single API Client | PASS | Every new builder calls `api_request()` from `src/common/api_client.py`; no direct HTTP. |
| III. Test-First (NON-NEGOTIABLE) | PASS (enforced downstream) | task-test-author authors failing tests before implementation; tasks.md orders a failing test before each builder. |
| IV. LLM-Friendly Error Handling | PASS | New actions reuse the `steps()` handler's try/except that routes through `http_error_message` / `UNEXPECTED_ERROR_MESSAGE`; builders return `BaseResult(error=...)` for input problems; no raw status/trace/token leakage. |
| V. Structured Pydantic Responses | PASS | All builders return `BaseResult` via `format_steps`; the `TestStep` model is extended (not bypassed); formatters still own JSON→model transform. |
| Code Quality & Style | PASS | 108-char lines, complexity ≤10, `make lint`/`make format` with `--target-version py311`. |
| Security & Token Handling | PASS | No change to token resolution or auth; auth stays inside `api_request()`; no token in responses. |

**Result: PASS — no violations. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/mob-55587/
├── spec.md
├── brownfield-context.md
├── plan.md                 # this file
├── research.md             # Phase 0
├── data-model.md           # Phase 1
├── quickstart.md           # Phase 1
├── contracts/
│   └── steps-tool-actions.md   # Phase 1 — MCP action contracts
├── design-contract.json    # structured design contract
├── evidence-index.json
├── tasks.md                # Phase 2 (/speckit-tasks)
└── test-scenarios.md       # test-author
```

### Source Code (repository root)

```text
src/
├── tools/
│   └── step_manager.py     # ADD builders + dispatch cases + tool description
├── models/
│   └── step.py             # EXTEND TestStep with inbound + subtest fields
├── formatters/
│   └── step.py             # unchanged (permissive round-trip)
└── common/
    └── api_client.py       # unchanged (single api_request call site)

tests/
├── test_step_manager.py    # ADD test classes for the 6 new actions + model round-trips
└── conftest.py             # ADD sample inbound/condition/loop/subtest API responses
```

**Structure Decision**: Single-project MCP-server layout. All production change concentrates in `src/tools/step_manager.py` (new builders + registration) and `src/models/step.py` (model extension); tests extend `tests/test_step_manager.py` and `tests/conftest.py`.

## Technical Approach

### §Add builders (AC-1)

Add four async builder methods to `StepManager`, each constructing a flat radar-input body with a literal `step_type` and calling `api_request(self.token, "POST", STEPS_ENDPOINT.format(bucket_key, test_id), result_formatter=format_steps, json=body)` — the exact shape of `add_pause_step`/`add_request_step`.

Runnable pseudocode (field names/wire keys from Dependency Contract Facts):

```python
async def add_inbound_step(self, bucket_key, test_id, token, is_dynamic_url):
    body = {"step_type": "inbound", "token": token, "isDynamicUrl": bool(is_dynamic_url)}
    return await api_request(self.token, "POST",
        f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
        result_formatter=format_steps, json=body)

async def add_condition_step(self, bucket_key, test_id, comparison,
                             left_value, right_value, steps=None):
    # WIRE KEY IS "condition" (NOT "conditional"); condition_type "start";
    # do NOT send an explicit end block — tea-service parser auto-appends it.
    body = {"step_type": "condition", "condition_type": "start",
            "comparison": comparison, "left_value": left_value,
            "right_value": right_value}
    if steps is not None:
        body["steps"] = steps
    return await api_request(self.token, "POST",
        f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
        result_formatter=format_steps, json=body)

async def add_conditional_loop_step(self, bucket_key, test_id, comparison,
                                    left_value, right_value, steps=None):
    body = {"step_type": "conditional-loop", "condition_type": "start",
            "comparison": comparison, "left_value": left_value,
            "right_value": right_value}
    if steps is not None:
        body["steps"] = steps
    return await api_request(self.token, "POST",
        f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
        result_formatter=format_steps, json=body)

async def add_subtest_step(self, bucket_key, test_id, test_uuid, trigger_token,
                           environment_uuid, subtest_bucket_key,
                           use_parent_environment, params=None):
    # Lazy validation: do NOT pre-check that test_uuid exists (matches
    # add_request_step, which does not pre-validate url). API errors surface unchanged.
    body = {"step_type": "subtest", "test_uuid": test_uuid,
            "trigger_token": trigger_token, "environment_uuid": environment_uuid,
            "bucket_key": subtest_bucket_key,
            "use_parent_environment": bool(use_parent_environment)}
    if params is not None:
        body["params"] = params
    return await api_request(self.token, "POST",
        f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
        result_formatter=format_steps, json=body)
```

Note the subtest `bucket_key` field is the *subtest's* bucket (distinct from the path `bucket_key`), so the builder parameter is named `subtest_bucket_key` and mapped to the `bucket_key` body key.

### §Update (AC-2)

Generic single-step update. Read the current step (`self.read(..., result_formatter=None)` returns the raw dict), merge caller updates, PUT the full step to `/steps/{step_id}` via the existing `_put_step` helper:

```python
async def update_step(self, bucket_key, test_id, step_id, updates):
    if not isinstance(updates, dict) or not updates:
        return BaseResult(error="updates must be a non-empty object of fields to change.")
    step = await self.read(bucket_key, test_id, step_id, result_formatter=None)
    if not step:
        return BaseResult(error=f"Step {step_id} not found.")
    step.update(updates)                       # shallow merge of caller fields
    return await self._put_step(bucket_key, test_id, step_id, step)  # PUT /steps/{step_id}
```

This reuses `_put_step` (PUT /steps/{step_id} with `format_steps`) — the same call `add_body_to_step`/`add_headers_to_step` already use.

### §Reorder (AC-3)

Pass a caller-supplied `template_order` list to `PUT /steps`:

```python
async def reorder_steps(self, bucket_key, test_id, step_order):
    if not isinstance(step_order, list) or not step_order:
        return BaseResult(error="step_order must be a non-empty list of step ids.")
    return await api_request(self.token, "PUT",
        f"{STEPS_ENDPOINT.format(bucket_key, test_id)}",
        result_formatter=format_steps, json=step_order)
```

The API validates the order list server-side (400 on missing ids; 100-step cap). **Known API limitation (A-LOOP-REORDER)**: the API's reorder end-block pairing matches only internal template `step_type == "conditional"`, so nesting a conditional-loop's children under a `template_order` entry is unsupported. The tool passes the list through; flat-id reordering of every step type works. This limitation is documented in the tool description and the subtest/loop reorder is not exercised with nesting.

### §Model (AC-1)

Extend `src/models/step.py` `TestStep` with the inbound and subtest response fields that the API returns but the model currently drops:

- `token: Optional[str]` (inbound)
- `is_dynamic_url: Optional[bool]` with `alias="isDynamicUrl"` (inbound)
- `trigger_token: Optional[str]` (subtest)
- `environment_id: Optional[str]` (subtest; API returns `environment_id`)
- `use_parent_environment: Optional[bool]` (subtest)
- `params: Optional[List[Any]]` (subtest)

(`test_uuid`, `bucket_key`, `steps`, `comparison`, `left_value`, `right_value` already exist.) `format_steps` calls `model_dump(by_alias=False)`, so aliased fields round-trip under their python names; add fields as `Optional` with `default=None` to preserve request/pause compatibility.

### §Registration (FR-008)

For each of the six new actions: (a) the builder method above, (b) a new `case "<action>":` in the `register()` `match action:` block that unpacks `args` and calls the builder through `check_result_error(span, ...)`, and (c) a new entry in the tool `description` string documenting the action, its args, and an example. All three are required for the action to be reachable — mirrors how `add_pause_step`/`add_request_step` are wired.

## Performance Strategy

Each action (`add_*`, `update_step`, `reorder_steps`) is a **single** API round-trip (`update_step` is a read-then-PUT = 2 sequential calls, still constant, no loop). There is no outer-loop-with-inner-API-call (N×M) pattern anywhere in this feature, so no call-budget math, concurrency cap, or degradation contract is required. The existing `api_request()` timeout and categorized-error handling apply unchanged.

## Failure Modes

- Missing required field (inbound `token`/`isDynamicUrl`; condition/loop `comparison`/`left_value`/`right_value`; subtest required fields) → tea-service parser returns a missing-field error → surfaced via `http_error_message` as a categorized message.
- Invalid `comparison` → parser 400 → categorized message (lazy validation).
- Unknown step id on `update_step` → `read` returns empty → `BaseResult(error="Step {id} not found.")`; or API not-found → categorized message.
- Reorder with a non-list / missing ids → builder guard or API 400 → categorized message.
- Exceeding the 100-step cap → API 400 → categorized message.

## Requirement Traceability

| Jira AC | Spec FR/SC | Plan section | Task IDs | Test names | Impl files |
|---|---|---|---|---|---|
| AC-1 add new step types | FR-001..FR-005, FR-009, SC-001 | §Add builders, §Model | T003, T004, T005, T006, T011 | `test_add_inbound_step`, `test_add_condition_step`, `test_add_conditional_loop_step`, `test_add_subtest_step`, `test_teststep_model_roundtrip_inbound_subtest` | src/tools/step_manager.py, src/models/step.py |
| AC-2 modify existing step | FR-006, SC-002 | §Update | T007 | `test_update_step` | src/tools/step_manager.py |
| AC-3 change step order | FR-007, SC-003 | §Reorder | T008 | `test_reorder_steps` | src/tools/step_manager.py |
| cross-cutting registration | FR-008 | §Registration | T009 | `test_steps_dispatch_new_actions` | src/tools/step_manager.py |
| cross-cutting errors + no regression | FR-010, SC-004 | §Failure Modes | T010, T012 | `test_new_actions_error_handling`, N/A — full suite (`make test`) | src/tools/step_manager.py, tests/ |

## Design Alternatives Considered

| Option | Decision | Reason |
|---|---|---|
| Per-step-type builders + generic update + reorder | SELECTED | Mirrors existing `add_request_step`/`add_pause_step`; typed, self-documenting actions for the LLM. |
| Single generic `add_step` raw-dict passthrough | REJECTED | Loses per-type LLM affordance and typed args; harder to document. |
| Full test-steps PUT replace for modify | REJECTED | API offers per-step `PUT /steps/{id}`; full-list replace adds a race window and latency. |
| Per-step `move_up`/`move_down` reorder | REJECTED | API's canonical op is a full-list `template_order`; only adjacent swaps otherwise. |

## Complexity Tracking

No constitution violations — not applicable.
