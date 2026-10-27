# Feature Specification: Extend blazemeter_apitest_steps to support remaining test step types, step update, and reorder

**Feature Branch**: `ai-mob-55587`
**Created**: 2026-10-27
**Status**: Draft
**Input**: Jira MOB-55587 — API Monitoring (Runscope) MCP: Extend steps tool to support remaining test steps.

## Background

The `blazemeter_apitest_steps` MCP tool in the BlazeMeter API Test MCP Server (`mcp-bzm-apim`) lets AI agents manage the steps of a Runscope/BlazeMeter API test. Today the tool can **add** only two step types — Request and Pause — and can modify a request step only through narrow, request-specific helpers (add body / headers / assertion / variable / script). It cannot add the other test step types the platform supports, cannot generically update an arbitrary existing step, and cannot change the order of steps within a test.

This feature extends the same tool so an AI agent can build a complete, realistic API test: adding Inbound, conditional-if, conditional-loop, and subtest steps; updating any existing step; and reordering steps. Ghost Inspector / UI-integration steps are explicitly out of scope.

The tool is a thin stateless adapter over the Runscope public API. Per the ticket's R&D note, the authoritative payload shapes for each step type come from the public API code (the tea-service "radar" parser); those shapes are proven in `brownfield-context.md` and carried into this spec as binding dependency facts.

## In Scope

- Adding new step types: Inbound, conditional-if, conditional-loop, and subtest.
- Modifying/updating any existing test step (generic single-step update).
- Changing test step order within a test (reorder).

## Out of Scope

- Ghost Inspector / UI-test-integration steps.

## Current Implementation

> Source: brownfield codebase research (`brownfield-context.md`).

### What exists today

| Capability | Status |
|---|---|
| Add Request step | exists (`add_request_step`) |
| Add Pause step | exists (`add_pause_step`) |
| Modify a request step (body/headers/assertion/variable/script) | exists (request-only helpers) |
| Add Inbound / conditional-if / conditional-loop / subtest step | missing |
| Generic update of any existing step | missing |
| Change step order (reorder) | missing |

### Key files

- `src/tools/step_manager.py` — `StepManager` builders + `register()` match/case dispatch + tool description.
- `src/models/step.py` — `TestStep` Pydantic response model.
- `src/formatters/step.py` — `format_steps` round-trip.
- `src/common/api_client.py` — single `api_request()` HTTP call site.
- `tests/test_step_manager.py` — existing `test_add_request_step` / `test_add_pause_step` patterns.

### Root cause / gap

`step_manager.py` has no builder methods, dispatch cases, or tool-description entries for the four new step types, no generic `update_step` action, and no `reorder_steps` action.

## Field Semantics (BINDING)

> Source: brownfield semantic disambiguation (`brownfield-context.md` § Semantic Disambiguation). NON-NEGOTIABLE for every downstream artifact.

### Approved identifiers (USE these)

- `inbound` — new step type; radar input `{step_type: "inbound", token, isDynamicUrl}`.
- `condition` — radar input wire key for the conditional-**if** step. The `step_type` MUST be `"condition"` (singular), **NOT** `"conditional"`; carries `condition_type: "start"`.
- `conditional-loop` — radar input wire key for the loop step; carries `condition_type: "start"`.
- `subtest` — new step type; radar input `{step_type: "subtest", test_uuid, trigger_token, environment_uuid, bucket_key, use_parent_environment, params?}`.
- `update_step` — generic single-step update via `PUT /steps/{step_id}`.
- `reorder_steps` — change step order via `PUT /steps` with a `template_order` list.

### Forbidden identifiers (DO NOT USE)

none

### Negative constraints

- The conditional-**if** step's radar input `step_type` is `"condition"` (singular). Sending `"conditional"` as the radar input `step_type` for the if-step is wrong and will not parse. (The internal template type the API stores becomes `"conditional"`, but the tool MUST send `"condition"` on the wire.) The loop step's wire key IS `"conditional-loop"`.
- The tool MUST NOT send an explicit conditional/loop `end` block — the parser auto-appends it.

## Runtime Data Availability (BINDING)

> Source: `brownfield-context.md` § Runtime Data Availability Proof.

None. The tool is a stateless request/response adapter: add/modify/reorder are single API round-trips against the live API, and the API validates the full step set server-side. No runtime data is cached or read that could be stale.

## Cross-Repo Capability Analysis (BINDING)

> Source: `brownfield-context.md` § Cross-Repo Capability Analysis.

USE the Runscope public API step endpoints (owned by the `api` service, validated by `tea-service`): `POST /steps` to add, `PUT /steps/{step_id}` to modify, `PUT /steps` to reorder. The tool already uses `POST /steps` for request/pause; no new service is required.

## Dependency Contract Facts (BINDING)

> Source: `brownfield-context.md` § Dependency Contract Facts (runscope/api + runscope/tea-service).

**Endpoints the step tool calls**

| Endpoint | Method | Input (radar) shape | Response |
|---|---|---|---|
| `/buckets/{bucket}/tests/{test}/steps` | POST | one step dict (see per-type shapes) | 201 + full steps list |
| `/buckets/{bucket}/tests/{test}/steps/{step_id}` | PUT | full step dict | 200 + updated step(s) |
| `/buckets/{bucket}/tests/{test}/steps` | PUT | `template_order`: list of `{id}` (or `{id, steps:[...]}` for a conditional start) | 200 + reordered steps; 400 on missing ids; 100-step cap |

**Required radar-input fields per NEW step type** (parser-enforced in `tea-service/parsers/radar.py`)

| Step type (radar `step_type`) | Required fields | Optional |
|---|---|---|
| `inbound` | `token` (str), `isDynamicUrl` (bool) | — |
| `condition` (conditional-if) | `condition_type: "start"`, `comparison` (must be a valid assert def), `left_value`, `right_value` | `steps` (nested) |
| `conditional-loop` | `condition_type: "start"`, `comparison`, `left_value`, `right_value` | `steps` (nested) |
| `subtest` | `test_uuid`, `trigger_token`, `environment_uuid`, `bucket_key`, `use_parent_environment` | `params` (list) |
| `pause` (existing) | `duration` (int, seconds, 1–180) | — |

**Behavioral facts**

- POST appends a step to the end of the step list.
- For `condition` / `conditional-loop`, the parser auto-flattens a `start` entry + its nested `steps` + an auto-generated `end` marker. The tool MUST send only the start (with optional `steps`) and MUST NOT send an explicit end step.
- `comparison` is validated server-side; the tool passes the user's token through (lazy validation — matches the existing request-step precedent that does not pre-validate `url`).
- Reorder auto-pairs conditional end-blocks, but the pairing branch matches only the internal template `step_type == "conditional"`. Nesting a `conditional-loop`'s children under a reorder `template_order` entry is therefore a **known API limitation**; flat-id reordering of every step type is supported.
- Tests are capped at 100 total steps (POST and reorder return 400 beyond that).

## Response model note (BINDING)

`src/models/step.py`'s `TestStep` currently lacks fields for the inbound step (`token`, `isDynamicUrl`) and several subtest fields (`trigger_token`, `environment_uuid` / `environment_id`, `use_parent_environment`, `params`). Pydantic drops unknown keys by default, so those fields would be silently dropped from the tool's response. The implementation MUST extend `TestStep` with these fields so inbound and subtest responses round-trip through `format_steps` without data loss.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add the remaining step types (Priority: P1)

An AI agent building an API test needs to add Inbound, conditional-if, conditional-loop, and subtest steps — not just Request and Pause — so it can author tests that mirror what a human can build in the UI.

**Why this priority**: This is the core of the ticket (AC-1) and the largest capability gap. Without it the tool cannot construct realistic tests.

**Independent Test**: Call `blazemeter_apitest_steps` with `action="add_inbound_step"` / `"add_condition_step"` / `"add_conditional_loop_step"` / `"add_subtest_step"` against a test and confirm the new step appears in the returned step list with the correct `step_type`.

**Acceptance Scenarios**:

1. **Given** a test, **When** the agent adds an inbound step with a token and `isDynamicUrl`, **Then** the step list returns a step of type `inbound` carrying those values.
2. **Given** a test, **When** the agent adds a conditional-if step with a comparison and left/right values, **Then** the returned step list contains a conditional start step and its auto-created end step, and the tool did not send an explicit end step.
3. **Given** a test, **When** the agent adds a conditional-loop step, **Then** the returned step list contains a `conditional-loop` start step and its auto-created end step.
4. **Given** a test, **When** the agent adds a subtest step with `test_uuid`, `trigger_token`, `environment_uuid`, `bucket_key`, and `use_parent_environment`, **Then** the returned step list contains a `subtest` step with those values.
5. **Given** a subtest step, **When** the agent supplies a `test_uuid` that does not exist, **Then** the tool still submits the step (lazy validation) and surfaces any API error unchanged — it does not pre-validate existence.

### User Story 2 - Update an existing step (Priority: P2)

An AI agent needs to modify any existing step (not just request-specific attributes) — e.g. change a pause duration or a conditional's comparison — without recreating the step.

**Why this priority**: AC-2. Builds on the add capability; valuable but secondary to being able to add the steps at all.

**Independent Test**: Add a step, then call `action="update_step"` with the step id and a set of field updates, and confirm the returned step reflects the update.

**Acceptance Scenarios**:

1. **Given** an existing step, **When** the agent calls `update_step` with the step id and updated fields, **Then** the tool reads the current step, merges the updates, PUTs the full step to `/steps/{step_id}`, and returns the updated step.
2. **Given** a non-existent step id, **When** the agent calls `update_step`, **Then** the tool surfaces the API's not-found error as a categorized, LLM-friendly message.

### User Story 3 - Change step order (Priority: P3)

An AI agent needs to reorder the steps of a test so the sequence matches the intended flow.

**Why this priority**: AC-3. The smallest, most self-contained capability.

**Independent Test**: Given a test with several steps, call `action="reorder_steps"` with a `template_order` list of step ids and confirm the returned step list reflects the new order.

**Acceptance Scenarios**:

1. **Given** a test with multiple flat (non-conditional) steps, **When** the agent calls `reorder_steps` with a `template_order` list of all step ids in the desired order, **Then** the returned step list is in that order.
2. **Given** a `template_order` list that omits an existing step id, **When** the agent calls `reorder_steps`, **Then** the tool surfaces the API's 400 error as a categorized message.
3. **Given** a test containing a conditional-loop block, **When** the agent reorders, **Then** flat-id reordering succeeds; nesting the loop's children under a reorder entry is a documented, unsupported API behavior and is not exercised.

### Edge Cases

- Adding an inbound step with a missing required field (`token` or `isDynamicUrl`) → the API/parser returns a missing-field error, surfaced as a categorized message.
- Adding a conditional/loop with an invalid `comparison` → surfaced as a categorized parser error (lazy validation).
- Adding any step to a test that already has 100 steps → API returns 400, surfaced as a categorized message.
- Updating a step with an unknown step id → categorized not-found message.
- Reorder `template_order` that is not a list or omits ids → categorized 400 message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `blazemeter_apitest_steps` tool MUST expose an `add_inbound_step` action that POSTs `{step_type: "inbound", token, isDynamicUrl}` to `/steps` and returns the updated step list. (AC-1)
- **FR-002**: The tool MUST expose an `add_condition_step` action that POSTs `{step_type: "condition", condition_type: "start", comparison, left_value, right_value, steps?}` to `/steps`; it MUST send the radar wire key `"condition"` (not `"conditional"`) and MUST NOT send an explicit end step. (AC-1)
- **FR-003**: The tool MUST expose an `add_conditional_loop_step` action that POSTs `{step_type: "conditional-loop", condition_type: "start", comparison, left_value, right_value, steps?}` to `/steps` and MUST NOT send an explicit end step. (AC-1)
- **FR-004**: The tool MUST expose an `add_subtest_step` action that POSTs `{step_type: "subtest", test_uuid, trigger_token, environment_uuid, bucket_key, use_parent_environment, params?}` to `/steps`. (AC-1)
- **FR-005**: The new add actions MUST follow the existing lazy-validation precedent — they MUST NOT pre-validate referenced resources (e.g. a subtest's `test_uuid`); server-side errors are surfaced unchanged. (AC-1)
- **FR-006**: The tool MUST expose a generic `update_step` action that reads the current step, merges caller-supplied field updates, and PUTs the full step dict to `/steps/{step_id}`, returning the updated step. (AC-2)
- **FR-007**: The tool MUST expose a `reorder_steps` action that PUTs a caller-supplied `template_order` list to `/steps` and returns the reordered step list. (AC-3)
- **FR-008**: Each new action MUST be reachable end-to-end: a builder method on `StepManager`, a `case` in the `register()` match statement, and an entry in the tool `description` string. (AC-1, AC-2, AC-3)
- **FR-009**: The `TestStep` response model MUST carry the inbound fields (`token`, `isDynamicUrl`) and subtest fields (`trigger_token`, `environment_uuid`/`environment_id`, `use_parent_environment`, `params`) so inbound and subtest responses round-trip through `format_steps` without silently dropping data. (AC-1)
- **FR-010**: All errors MUST be surfaced through the existing categorized, LLM-friendly error handling (`http_error_message` / `UNEXPECTED_ERROR_MESSAGE`); raw status codes, stack traces, and token values MUST NOT appear in responses. (constitution IV)

### Key Entities

- **Test Step (radar input)**: the dict the tool POSTs/PUTs. Keyed by `step_type`; carries type-specific fields (see Dependency Contract Facts).
- **Test Step (response)**: `TestStep` model instance returned to the agent via `BaseResult`.
- **template_order**: an ordered list of `{id}` (or `{id, steps:[...]}` for conditional starts) used by reorder.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An AI agent can add all four new step types (inbound, conditional-if, conditional-loop, subtest) and see each returned with the correct `step_type` — 4/4 new types supported. (AC-1)
- **SC-002**: An AI agent can update any existing step's fields via a single `update_step` call and observe the change in the returned step. (AC-2)
- **SC-003**: An AI agent can reorder a test's flat steps via a single `reorder_steps` call and observe the new order. (AC-3)
- **SC-004**: Every new action and the model change is covered by unit tests that assert the exact request payload and a formatter round-trip; the full suite passes with no regression to the existing request/pause actions.

## Assumptions

- **A-SHAPE**: The radar input shapes above are exactly the fields the tea-service parser reads (proven in `brownfield-context.md`; contract-verification tasks assert each builder sends exactly those keys).
- **A-AUTO-END**: The conditional/loop end block is auto-created by the parser; the tool sends only the start (+ optional nested `steps`).
- **A-LOOP-REORDER**: Nesting a conditional-loop's children in a reorder `template_order` entry is an API limitation; `reorder_steps` supports flat-id reordering of all step types and documents the limitation.
- **A-SUBTEST-LAZY**: Subtest `test_uuid`/`bucket_key` are not validated at step-creation time (matches the request-step precedent).
- The existing `api_request()` single-call-site and `BaseResult` envelope are reused unchanged.
- No new service, endpoint, or external dependency is introduced; only the existing Runscope public API step endpoints are used.

## Performance

Each action (add / update / reorder) is a single API round-trip. There is no nested or N×M external-call pattern, so no call-budget / latency-envelope performance strategy is required.

## AC Verification Strategy

Each acceptance criterion is verified by the test scenarios declared in `test-scenarios.md` (marker syntax: `test_scenarios: [S#, ...]`). No AC is manual-only; all are covered by mocked unit tests.

- **AC-1** (add Inbound, conditional-if, conditional-loop, subtest step types) — `test_scenarios: [S1, S2, S3, S4, S5, S6, S7]`
- **AC-2** (modify/update an existing test step) — `test_scenarios: [S8, S9]`
- **AC-3** (change test step order) — `test_scenarios: [S10, S11]`
- **FR-008** (registration dispatch for the 6 new actions) — `test_scenarios: [S12]`
- **FR-010** (categorized error handling for the new actions) — `test_scenarios: [S13]`

Each `S#` maps to a concrete `test_*` name and a positive/negative type in `test-scenarios.md`. The non-regression gate (SC-004) is verified by the full suite + lint (`make test` / `make lint`), which is a tooling gate, not a unit test.

## Requirement Traceability Matrix

| Jira AC | Spec FR / SC | Plan section | Task IDs | Test | Impl location |
|---|---|---|---|---|---|
| AC-1 add new step types | FR-001..FR-005, FR-009, SC-001 | Plan Add builders, Model | T003, T004, T005, T006, T011 | `test_add_inbound_step`, `test_add_condition_step`, `test_add_conditional_loop_step`, `test_add_subtest_step`, `test_teststep_model_roundtrip_inbound_subtest` | step_manager builders + step model |
| AC-2 modify existing step | FR-006, SC-002 | Plan Update | T007 | `test_update_step` | step_manager update builder |
| AC-3 change step order | FR-007, SC-003 | Plan Reorder | T008 | `test_reorder_steps` | step_manager reorder builder |
| cross-cutting registration | FR-008, SC-004 | Plan Registration | T009 | `test_steps_dispatch_new_actions` | step_manager register dispatch |
| cross-cutting errors | FR-010 | Plan Failure Modes | T010 | `test_new_actions_error_handling` | step_manager error handling |
| non-regression gate | SC-004 | Plan Performance | T012 | N/A — full suite (make test / make lint) | whole suite |
