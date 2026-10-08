# Test Scenarios: Environment Management MCP Tools (MOB-54638)

> **Planner seed, finalized by task-test-author.** Originally seeded by task-planner with 15
> scenarios anchoring the Requirement Traceability Matrix. task-test-author (stage 4.5) authored,
> red-verified, and committed all tests below to `tests/test_environment_manager.py`. All
> `test_*` names referenced by spec.md's RTM are preserved. All API calls are mocked
> (`unittest.mock`/`AsyncMock`); no live calls (repo convention, CLAUDE.md Testing Conventions).

**Total scenarios: 16** (plus 2 planner hard-gate scenarios and 2 harness checks, tracked in
separate tables below and excluded from this total per the 50-row-cap/negative-quota convention)
**Negative-path coverage: 7/16 = 43%** — target ≥30%.

| S# | Test | Type | Given | When | Then | Covers | Status |
|----|------|------|-------|------|------|--------|--------|
| S1 | test_modify_environment_agent_swap_preserves_fields | positive | a local env with agent A + variables | modify with only remote_agents=[B] | PATCH body contains ONLY remote_agents; result shows agent B; other fields preserved | AC-6, AC-7 | RED |
| S2 | test_modify_environment_name_only_preserves_remote_agents | positive | a local env with remote_agents set | modify with only name="X" | PATCH body contains ONLY name; remote_agents absent from body (preserved server-side) | AC-7 | RED |
| S3 | test_create_local_environment | positive | a valid bucket + test | create local env with name + initial_variables | POST hits /buckets/{key}/tests/{id}/environments with serialized body; created env returned | AC-5 | RED |
| S4 | test_create_shared_environment | positive | a valid bucket | create shared env with name (no test_id) | POST hits /buckets/{key}/environments; created env returned | AC-4 | RED |
| S5 | test_list_shared_environments | positive | a valid bucket | list with no test_id | GET /buckets/{key}/environments; shared envs returned | AC-1 | RED |
| S6 | test_list_local_environments_regression | positive | a valid bucket + test | list with test_id | existing GET /buckets/{key}/tests/{id}/environments still works (named regression guard per spec.md RTM) | AC-2 | GREEN (regression guard; local-scope list unaffected by shared-scope additions) |
| S7 | test_read_shared_environment | positive | a valid bucket + shared env id | read with no test_id | GET /buckets/{key}/environments/{env_id}; single env returned | AC-3 | RED |
| S8 | test_create_modify_request_models_serialize_by_alias_exclude_none | positive | CreateEnvironment/ModifyEnvironment models | model_dump(by_alias=True, exclude_none=True) | omitted fields absent from the serialized body; aliases applied | AC-10 | RED |
| S9 | test_modify_environment_invalid_id_returns_not_found | negative | an invalid environment_id | modify called, API returns 404 | result error is the http_error_message not-found category; no stack trace | AC-11 | RED |
| S10 | test_modify_environment_validation_error_surfaced | negative | a modify the server rejects | API returns 4xx validation | categorized validation error surfaced | AC-11 | RED |
| S11 | test_modify_environment_empty_payload_returns_current_unchanged | negative/edge | an empty modify payload | modify called with no changed fields | current environment returned unchanged; no API write, no error | AC-6 | RED |
| S12 | test_create_local_environment_limit_reached_surfaces_api_message | negative | a test at the 100-env limit | create called, API returns 400 "Cannot create more than 100 …" | the API's limit message is surfaced via http_error_message; no hardcoded cap | AC-9 | RED |
| S13 | test_create_local_environment_invalid_ids_return_error | negative | an invalid bucket_key/test_id | create called, API returns 404 | categorized not-found error surfaced | AC-11 | RED |
| S14 | test_insufficient_permission_surfaces_auth_error | negative | a caller lacking permission/consent | a write action, API returns 401/403 | http_error_message auth category surfaced; tool adds no consent check and no bypass | AC-8 | RED |
| S15 | test_create_shared_environment_limit_reached_surfaces_api_message | negative | a bucket at the 100 shared-env limit | create shared called, API returns 400 | the API's limit message is surfaced via http_error_message; no hardcoded cap | AC-9 | RED |
| S16 | test_modify_shared_environment | positive | a shared (bucket-level) env | modify with only name="X", no test_id | PATCH hits bucket-level endpoint (no /tests/ segment); partial-merge body | AC-6, AC-7 | RED |

## Planner hard-gate scenarios (tracked outside the 50-row cap, mandatory)

| S# | Test | Type | Covers | Status |
|----|------|------|--------|--------|
| S_NEG_1 | test_environment_manager_has_no_redundant_consent_check | negative-constraint (forbidden identifier) | AC-8 | GREEN (constraint already holds; guards against future regression) |
| S_NODELETE | test_environments_tool_has_no_delete_action | no-delete guard | AC-12 | GREEN (constraint already holds; guards against future regression) |

- **Runtime lifecycle**: N/A — confirmed no runtime data is deleted/expired between read and write
  within a single MCP action (brownfield Runtime Data Availability Proof). No lifecycle
  falsification test required or authored.
- **Static contract**: S1, S2, S16 (PATCH partial-merge body shape) + S8 (request-model
  serialization) + S3/S4/S5/S7 (endpoint routing) prove the create/modify/list/read wire shapes
  match the `api` service's expected contract, read directly from checked-in route evidence
  (brownfield-context.md Cross-Repo/API Contract table). No live/dev/stage/prod call made.
- **Forbidden identifier (negative/contrast)**: S1 asserts the manager exposes `modify_environment`
  and explicitly asserts `patch_environment` does NOT exist (`not hasattr`) — the Forbidden
  Identifier from brownfield-context.md.
- **Mock reality**: S1/S2/S16's mocked `api_request` is read directly via `mock_api.call_args` (not
  patched away) so the "only the changed field is in the body" assertion is meaningful against the
  real call arguments the implementation will pass.
- **No-delete guard**: S_NODELETE enumerates the registered `environments` tool's routed actions via
  the existing not-found arm and asserts `delete` is not wired in.

## AC coverage map

| AC | Scenarios |
|----|-----------|
| AC-1 | S5 |
| AC-2 | S6 |
| AC-3 | S7 |
| AC-4 | S4 |
| AC-5 | S3 |
| AC-6 | S1, S11, S16 |
| AC-7 | S1, S2, S16 |
| AC-8 | S14, S_NEG_1 |
| AC-9 | S12, S15 |
| AC-10 | S8 |
| AC-11 | S9, S10, S13 |
| AC-12 | S_NODELETE |

Every AC (AC-1 through AC-12) has at least one mapped scenario — zero coverage gaps.

## Harness validity checks

| Scenario | Analog | Pattern | Helper |
|----------|--------|---------|--------|
| S_HARNESS_1 | ScheduleManager.create (src/tools/schedule_manager.py) | typed-model POST + BaseResult.result[0][field] accessor | inline manager call in test_harness_schedule_create_analog_returns_serialized_fields |
| S_HARNESS_2 | version_manager's register()-wrapped tool invocation (tests/test_version_manager.py::_register_and_get_tool) | register() match/case unknown-action arm -> BaseResult.error accessor | `_register_and_get_tool` helper (copied into test_environment_manager.py), proven in test_harness_register_unknown_action_returns_error_result |

Both harness tests PASS today (verified against already-shipped analog code), proving the
invocation + result-accessor patterns the 16 red tests above read through are correct before any
implementation code exists.

## Red-verification summary

- 16 standard scenarios (S1-S16): all RED by `AssertionError` (hasattr/endpoint/body-shape
  assertions), zero collection errors, zero vacuous passes. Verified via
  `.venv/bin/pytest tests/test_environment_manager.py -v --no-cov`.
- 2 planner hard-gate scenarios (S_NEG_1, S_NODELETE): GREEN today — both assert a constraint that
  already holds in the current (pre-implementation) codebase, and will continue to guard against
  regression once create/modify land.
- 2 harness scenarios (S_HARNESS_1, S_HARNESS_2): GREEN today, proving the test harness is valid.
- Pre-existing suite (133 tests outside this file) plus the 2 originally-authored
  `test_list_environments`/`test_read_environment` tests and the new S6 regression guard, all
  inside the modified file: 136 passed, 0 regressions, confirmed via
  `.venv/bin/pytest tests/ --no-cov -q --ignore=tests/test_environment_manager.py` (133 passed)
  plus the 3 pre-existing/regression tests passing inside the modified file.
