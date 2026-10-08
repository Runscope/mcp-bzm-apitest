# Test Scenarios: Environment Management MCP Tools (MOB-54638)

> **Planner seed.** This file is seeded by task-planner to anchor the Requirement Traceability
> Matrix and the design contract. `task-test-author` (stage 4.5) owns the full authoring: it may add
> scenarios, refine assertions, and assign final S# ids, but it MUST preserve the `test_*` names
> referenced by spec.md's RTM. All API calls are mocked (`unittest.mock.AsyncMock`); no live calls.

**Total scenarios: 15**
**Negative-path coverage: 46% negative (7 of 15)** — target ≥30%.

| S# | Test | Type | Given | When | Then | Covers |
|----|------|------|-------|------|------|--------|
| S1 | test_modify_environment_agent_swap_preserves_fields | positive | a local env with agent A + variables | modify with only remote_agents=[B] | PATCH body contains ONLY remote_agents; result shows agent B; other fields preserved | AC-6, AC-7 |
| S2 | test_modify_environment_name_only_preserves_remote_agents | positive | a local env with remote_agents set | modify with only name="X" | PATCH body contains ONLY name; remote_agents absent from body (preserved server-side) | AC-7 |
| S3 | test_create_local_environment | positive | a valid bucket + test | create local env with name + initial_variables | POST hits /buckets/{key}/tests/{id}/environments with serialized body; created env returned | AC-5 |
| S4 | test_create_shared_environment | positive | a valid bucket | create shared env with name (no test_id) | POST hits /buckets/{key}/environments; created env returned | AC-4 |
| S5 | test_list_shared_environments | positive | a valid bucket | list with no test_id | GET /buckets/{key}/environments; shared envs returned | AC-1 |
| S6 | test_list_local_environments_regression | positive | a valid bucket + test | list with test_id | existing GET /buckets/{key}/tests/{id}/environments still works | AC-2 |
| S7 | test_read_shared_environment | positive | a valid bucket + shared env id | read with no test_id | GET /buckets/{key}/environments/{env_id}; single env returned | AC-3 |
| S8 | test_create_modify_request_models_serialize_by_alias_exclude_none | positive | CreateEnvironment/ModifyEnvironment models | model_dump(by_alias=True, exclude_none=True) | omitted fields absent from the serialized body; aliases applied | AC-10 |
| S9 | test_modify_environment_invalid_id_returns_not_found | negative | an invalid environment_id | modify called, API returns 404 | result error is the http_error_message not-found category; no stack trace | AC-11 |
| S10 | test_modify_environment_validation_error_surfaced | negative | a modify the server rejects | API returns 4xx validation | categorized validation error surfaced | AC-11 |
| S11 | test_modify_environment_empty_payload_returns_current_unchanged | negative | an empty modify payload | modify called with no changed fields | current environment returned unchanged; no API write, no error | AC-6 |
| S12 | test_create_local_environment_limit_reached_surfaces_api_message | negative | a test at the 100-env limit | create called, API returns 400 "Cannot create more than 100 …" | the API's limit message is surfaced via http_error_message; no hardcoded cap | AC-9 |
| S13 | test_create_local_environment_invalid_ids_return_error | negative | an invalid bucket_key/test_id | create called, API returns 404 | categorized not-found error surfaced | AC-11 |
| S14 | test_insufficient_permission_surfaces_auth_error | negative | a caller lacking permission/consent | a write action, API returns 401/403 | http_error_message auth category surfaced; tool adds no consent check and no bypass | AC-8 |
| S15 | test_create_shared_environment_limit_reached_surfaces_api_message | negative | a bucket at the 100 shared-env limit | create shared called, API returns 400 | the API's limit message is surfaced via http_error_message; no hardcoded cap | AC-9 |

## Planner hard-gate scenarios (mandatory — carried for task-test-author)

- **Runtime lifecycle**: N/A — no runtime data is deleted/expired between read and write within a
  single MCP action; the api PATCH reads-and-merges server-side (brownfield Runtime Data Availability
  Proof: all rows available). No lifecycle falsification test required.
- **Static contract**: S1/S2 (PATCH partial-merge body shape) + S8 (request-model serialization) are
  the contract tests proving the create/modify wire body matches the `api` service's expected shape.
- **Forbidden identifier (negative/contrast)**: the modify method MUST be `modify_environment`, not
  `patch_environment`; task-test-author asserts the manager exposes `modify_environment` and no
  `patch_environment`. Covered conceptually by S1 (exercises `modify_environment`).
- **Mock reality**: S1/S2 must NOT mock away the preserved fields — the mocked `api_request` must
  receive and expose the actual PATCH body so the assertion "only the changed field is in the body"
  is meaningful. A mock that discards the body is invalid.
- **No-delete guard**: test_environments_tool_has_no_delete_action — enumerate tool actions; assert
  no delete action exists and an unknown action returns the not-found BaseResult.

## AC coverage map

| AC | Scenarios |
|----|-----------|
| AC-1 | S5 |
| AC-2 | S6 |
| AC-3 | S7 |
| AC-4 | S4 |
| AC-5 | S3 |
| AC-6 | S1, S11 |
| AC-7 | S1, S2 |
| AC-8 | S14 |
| AC-9 | S12, S15 |
| AC-10 | S8 |
| AC-11 | S9, S10, S13 |
| AC-12 | test_environments_tool_has_no_delete_action |
