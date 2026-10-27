# Tasks: Extend blazemeter_apitest_steps — new step types, update, reorder (MOB-55587)

**Feature dir**: `specs/mob-55587` | **Branch**: `ai-mob-55587`
**Tech**: Python 3.11+, MCP (FastMCP), httpx, pydantic, pytest (+asyncio auto). Test-First is NON-NEGOTIABLE (constitution III): each builder gets a failing test first.

All tests mock `src.tools.step_manager.api_request`; no task verifies contracts against live/dev/stage/prod endpoints. Dependency-contract conformance is proven statically against the radar-input shapes documented in `brownfield-context.md`, not by network calls.

Each `T###` id appears on exactly one line. "Depends on / unblocks" relationships are in the Dependencies section, not inline, to keep task ids unique.

## Phase 1: Setup

- [ ] T001 Confirm the dev environment installs test deps and the suite runs green on a clean worktree in the repo root (`make install && make test`), establishing the pre-change baseline.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 [P] Add sample API step responses (inbound, condition start+end, conditional-loop start+end, subtest) as fixtures in `tests/conftest.py`, each including realistic per-type fields so the formatter is exercised.
- [ ] T013 Static contract-verification task (AC-1): assert each new builder's request body exactly matches the required radar-input fields documented in `specs/mob-55587/brownfield-context.md` (Dependency Contract Facts) via assertions on the mocked `api_request` call args in `tests/test_step_manager.py`; no live endpoint calls.

## Phase 3: User Story 1 — Add the remaining step types (P1)

**Goal**: add inbound, conditional-if, conditional-loop, and subtest steps. **Independent test**: call each new add action and see the step returned with the correct `step_type`. ACs: AC-1.

### Tests first (red)

- [ ] T101 [P] [US1] Write failing `test_add_inbound_step` in `tests/test_step_manager.py` (AC-1) asserting the POST body is `{step_type:"inbound", token, isDynamicUrl}` and `result.error is None`.
- [ ] T102 [P] [US1] Write failing `test_add_condition_step` in `tests/test_step_manager.py` (AC-1) asserting the POST body uses `step_type:"condition"` (NOT `"conditional"`) + `condition_type:"start"` + comparison/left_value/right_value, that NO explicit end block is sent, and that a mocked response returning start+end round-trips (auto-end falsification: an explicit end block or `"conditional"` wire key fails this test).
- [ ] T103 [P] [US1] Write failing `test_add_conditional_loop_step` in `tests/test_step_manager.py` (AC-1) asserting the POST body uses `step_type:"conditional-loop"` + `condition_type:"start"` and sends no explicit end block.
- [ ] T104 [P] [US1] Write failing `test_add_subtest_step` in `tests/test_step_manager.py` (AC-1) asserting the POST body carries the required subtest fields and that the builder does NOT pre-validate `test_uuid` (lazy-validation falsification: assert `api_request` is called exactly once as a POST — a pre-POST existence read fails this test).
- [ ] T105 [P] [US1] Write failing `test_teststep_model_roundtrip_inbound_subtest` in `tests/test_step_manager.py` (AC-1) asserting an inbound response (`token`, `isDynamicUrl`) and a subtest response (`trigger_token`, `environment_id`, `use_parent_environment`, `params`) survive `format_steps` without dropping fields (falsification: the current model drops these, so the test fails until the model is extended).
- [ ] T106 [P] [US1] Write failing negative tests `test_add_inbound_step_missing_field` and `test_add_condition_step_invalid_comparison` in `tests/test_step_manager.py` (AC-1) asserting a mocked API error surfaces as a categorized message.

### Implementation (green)

- [ ] T011 [US1] Extend `TestStep` in `src/models/step.py` (AC-1) with Optional fields `token`, `is_dynamic_url` (alias `isDynamicUrl`), `trigger_token`, `environment_id`, `use_parent_environment`, `params` (default None) so inbound/subtest responses round-trip.
- [ ] T003 [US1] Implement `add_inbound_step(bucket_key, test_id, token, is_dynamic_url)` in `src/tools/step_manager.py` (AC-1) → POST `{step_type:"inbound", token, isDynamicUrl}` via `api_request`.
- [ ] T004 [US1] Implement `add_condition_step(bucket_key, test_id, comparison, left_value, right_value, steps=None)` in `src/tools/step_manager.py` (AC-1) → POST `{step_type:"condition", condition_type:"start", comparison, left_value, right_value, steps?}`; never send an explicit end block.
- [ ] T005 [US1] Implement `add_conditional_loop_step(bucket_key, test_id, comparison, left_value, right_value, steps=None)` in `src/tools/step_manager.py` (AC-1) → POST `{step_type:"conditional-loop", condition_type:"start", ...}`; no explicit end block.
- [ ] T006 [US1] Implement `add_subtest_step(bucket_key, test_id, test_uuid, trigger_token, environment_uuid, subtest_bucket_key, use_parent_environment, params=None)` in `src/tools/step_manager.py` (AC-1) → POST subtest body (map `subtest_bucket_key`→`bucket_key`); no `test_uuid` pre-validation.

## Phase 4: User Story 2 — Update an existing step (P2)

**Goal**: generically update any existing step. **Independent test**: add a step, call `update_step`, see the change returned. ACs: AC-2.

- [ ] T107 [P] [US2] Write failing `test_update_step` and negative `test_update_step_unknown_id` in `tests/test_step_manager.py` (AC-2) asserting read→merge→`PUT /steps/{step_id}` with the merged full step dict, and that an unknown `step_id` yields a `BaseResult(error=...)`.
- [ ] T007 [US2] Implement `update_step(bucket_key, test_id, step_id, updates)` in `src/tools/step_manager.py` (AC-2) — read current step (`result_formatter=None`), shallow-merge `updates`, call `_put_step`; guard non-dict/empty `updates` and not-found step.

## Phase 5: User Story 3 — Change step order (P3)

**Goal**: reorder a test's steps. **Independent test**: call `reorder_steps` with an ordered id list, see the new order. ACs: AC-3.

- [ ] T108 [P] [US3] Write failing `test_reorder_steps` and negative `test_reorder_steps_missing_id` in `tests/test_step_manager.py` (AC-3) asserting a flat-id `template_order` list is PUT to `/steps`, the reordered list is returned, and a non-list / missing-id input yields an error.
- [ ] T008 [US3] Implement `reorder_steps(bucket_key, test_id, step_order)` in `src/tools/step_manager.py` (AC-3) → guard non-list/empty, then `PUT /steps` with `step_order` as the body.

## Phase 6: Cross-cutting — registration & errors

- [ ] T109 [P] Write failing `test_steps_dispatch_new_actions` in `tests/test_step_manager.py` (AC-1, AC-2, AC-3) asserting the `steps()` handler routes each of the 6 new `action` values to its builder (patch the builder, assert it is called with the unpacked args).
- [ ] T110 [P] Write failing `test_new_actions_error_handling` in `tests/test_step_manager.py` asserting an `httpx.HTTPStatusError` raised inside a new action surfaces as a categorized `http_error_message` (no raw status/trace/token in the response).
- [ ] T009 Add a `case` for each of the 6 new actions in `register()`'s `match action:` block AND a documenting entry (args + example) in the tool `description` string in `src/tools/step_manager.py`; document the conditional-loop reorder-nesting limitation.
- [ ] T010 Verify the new actions inherit the `steps()` try/except categorized error handling in `src/tools/step_manager.py` (no code change expected beyond registration); adjust if any builder path bypasses it.

## Phase 7: Polish & non-regression

- [ ] T012 Run the full suite + lint non-regression gate in the repo root (`make test && make lint`); confirm all new tests pass and the existing request/pause tests are unaffected. (N/A — quality gate: make test / make lint)

## Dependencies

- Phase 1 → Phase 2 → Phases 3/4/5 (US1 before US2 before US3 by priority; builders share `step_manager.py`) → Phase 6 (registration depends on all builders existing) → Phase 7.
- The model-extension implementation task must land before the inbound/subtest model round-trip test can pass.
- The registration task depends on the six builder implementation tasks existing.
- Each red test task precedes its matching green implementation task within the same user story.

## Parallel opportunities

- The User Story 1 test-authoring tasks are parallel-safe (`[P]` — independent assertions in the same file; author together then stage).
- The US2/US3 test tasks and the cross-cutting dispatch/error test tasks are parallel-safe relative to US1 work.

## MVP scope

User Story 1 (add the four new step types) plus the model extension is the MVP — it closes the largest capability gap (AC-1). User Story 2 (update) and User Story 3 (reorder) are incremental.
