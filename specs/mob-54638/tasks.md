---
description: "Task list for MOB-54638 — Environment Management MCP Tools"
---

# Tasks: Environment Management MCP Tools (MOB-54638)

**Input**: Design documents from `/specs/mob-54638/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/environments-tool.md, brownfield-context.md

**Tests**: REQUIRED. Constitution III (Test-First) is NON-NEGOTIABLE. Each new action and error/edge
path has a failing test (mocked `AsyncMock`) authored BEFORE its implementation. All API calls are
mocked; no live calls.

**Binding constraints** (from brownfield-context.md — enforced across all tasks):
- modify method is named `modify_environment` (NOT `patch_environment`); PATCH is the verb.
- PATCH is the primary modify verb (partial-merge preserves `remote_agents`); no PUT required.
- Inherit server-side ai_consent/PAT/RBAC — NO new MCP-layer consent check.
- Surface the API's 400 limit message via `http_error_message()` — do NOT hardcode 100/100 caps.
- NO delete action.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / independent).
- **[Story]**: US1 (modify/agent-swap), US2 (create local), US3 (shared scope), US4 (safe/consistent surface).

## Path Conventions

Single-package MCP server. `src/`, `tests/` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Brownfield repo already set up; only the shared endpoint constant + request model are
prerequisites for all stories.

- [ ] T001 Add `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT = "/buckets/{}/environments"` to `src/config/defaults.py` (alongside `TEST_ENVIRONMENT_ENDPOINT`).
- [ ] T002 [P] Add `CreateEnvironment` and `ModifyEnvironment` Pydantic request models to `src/models/environment.py` (writable fields only: name, initial_variables, regions, remote_agents, common optional toggles; alias-mapped; dumped with `by_alias=True, exclude_none=True`; `ModifyEnvironment` fields all optional). Mirror `CreateSchedule` in `src/models/schedule.py:10-28`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Request-model contract test that all create/modify stories depend on.

- [ ] T003 [US4] Write FAILING contract test in `tests/test_environment_manager.py` asserting `CreateEnvironment`/`ModifyEnvironment` serialize with `by_alias=True, exclude_none=True` (omitted fields absent from the body) for both scopes. (Red before the request models are added; validates FR-013.)

---

## Phase 3: User Story 1 — Modify a local environment to swap its private agent (P1) 🎯 MVP

**Goal**: `modify` action performs a PATCH partial update that preserves unspecified fields; agent-swap works end to end.
**Independent test**: modify only `remote_agents` → agent changes, other fields preserved.

### Tests (write first — must fail)

- [ ] T004 [US1] Write FAILING test `test_modify_environment_agent_swap_preserves_fields` in `tests/test_environment_manager.py`: mock `api_request` for PATCH; call modify with only `{"remote_agents": [new]}`; assert the PATCH body contains ONLY `remote_agents` (other fields omitted so server preserves them) and the result reflects the new agent. (Falsification: a PUT-style full-body call fails this test.) Maps AC "Agent-swap path works end to end", "Modify via PATCH".
- [ ] T005 [US1] Write FAILING test `test_modify_environment_name_only_preserves_remote_agents`: modify only `{"name": "X"}`; assert PATCH body contains only `name` and NOT `remote_agents`. (Partial-merge falsification.)
- [ ] T006 [P] [US1] Write FAILING test `test_modify_environment_invalid_id_returns_not_found`: mock PATCH → 404 `HTTPStatusError`; assert result error is the `http_error_message` not-found category. Maps AC "Clear error messages for invalid … env ID".
- [ ] T007 [P] [US1] Write FAILING test `test_modify_environment_validation_error_surfaced`: mock PATCH → 4xx validation; assert categorized error surfaced.
- [ ] T008 [P] [US1] Write FAILING test `test_modify_environment_empty_payload_returns_current_unchanged`: modify with no changed fields → returns current environment, no error.

### Implementation

- [ ] T009 [US1] Implement `modify_environment(self, bucket_key, environment_id, test_id=None, **fields)` in `EnvironmentManager` (`src/tools/environment_manager.py`): build `ModifyEnvironment`, dump `by_alias=True, exclude_none=True`, call `api_request(self.token, "PATCH", f"{endpoint}/{environment_id}", result_formatter=format_environments, json=body)` where endpoint routes shared vs local by `test_id`. Empty body → read-and-return current env. Method named `modify_environment` (NOT `patch_environment`).
- [ ] T010 [US1] Add the `modify` case to the `environments` `@mcp.tool` match-action router in `register()`; wrap in the existing `tool_span` + `try/except` ladder (timeout/HTTPStatusError/Exception → existing error helpers). Confirm this story's red tests now pass (green).

---

## Phase 4: User Story 2 — Create a local (test-level) environment (P1)

**Goal**: `create` action for a test-level environment via POST.
**Independent test**: create local env with name+variables → new env returned with a new id.

### Tests (write first — must fail)

- [ ] T011 [US2] Write FAILING test `test_create_local_environment` in `tests/test_environment_manager.py`: mock `api_request` POST; call create with `bucket_key`+`test_id`+name+initial_variables; assert POST hits `/buckets/{key}/tests/{id}/environments` with the serialized body and returns the created env. Maps AC "Create a local (test-level) environment".
- [ ] T012 [P] [US2] Write FAILING test `test_create_local_environment_limit_reached_surfaces_api_message`: mock POST → 400 "Cannot create more than 100 …"; assert the API's message is surfaced via `http_error_message` (NOT a hardcoded cap). Maps AC "Surface API-enforced limits clearly".
- [ ] T013 [P] [US2] Write FAILING test `test_create_local_environment_invalid_ids_return_error`: mock POST → 404; assert categorized not-found error.

### Implementation

- [ ] T014 [US2] Implement `create_test_environment(self, bucket_key, test_id, **fields)` in `EnvironmentManager`: build `CreateEnvironment`, dump `by_alias/exclude_none`, `api_request(..., "POST", TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id), result_formatter=format_environments, json=body)`. Mirror `schedule_manager.create`.
- [ ] T015 [US2] Add the `create` (local-scope) case to the match-action router; route to `create_test_environment` when `test_id` present. Confirm this story's red tests now pass.

---

## Phase 5: User Story 3 — Create and manage shared (bucket-level) environments (P2)

**Goal**: list/read/create/modify on the bucket-level scope.
**Independent test**: list shared, create shared, read shared by id.

### Tests (write first — must fail)

- [ ] T016 [US3] Write FAILING test `test_list_shared_environments`: mock GET `/buckets/{key}/environments`; assert shared envs returned (no `test_id` in args). Maps AC "List shared (bucket-level) environments".
- [ ] T017 [P] [US3] Write FAILING test `test_read_shared_environment`: mock GET `/buckets/{key}/environments/{env_id}`; assert single env returned. Maps AC "Retrieve a single environment by ID (shared …)".
- [ ] T018 [P] [US3] Write FAILING test `test_create_shared_environment`: mock POST `/buckets/{key}/environments`; assert created shared env returned. Maps AC "Create a shared (bucket-level) environment".
- [ ] T019 [P] [US3] Write FAILING test `test_create_shared_environment_limit_reached_surfaces_api_message`: mock POST → 400; assert API limit message surfaced.
- [ ] T020 [P] [US3] Write FAILING test `test_modify_shared_environment`: mock PATCH `/buckets/{key}/environments/{env_id}`; assert partial update on bucket-level scope.

### Implementation

- [ ] T021 [US3] Implement shared-scope list (`list` with no `test_id` → GET `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)`) and shared read (`read` with no `test_id`) in `EnvironmentManager`.
- [ ] T022 [US3] Implement `create_shared_environment(self, bucket_key, **fields)` → POST `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)`.
- [ ] T023 [US3] Extend the match-action router so `list`/`read`/`create`/`modify` route to the shared-scope path when `test_id` is absent. Confirm this story's red tests now pass.

---

## Phase 6: User Story 4 — Consistent, safe, auditable tool surface (P2)

**Goal**: conventions, no-delete, no new consent check, auditability.
**Independent test**: enumerate tool actions → create/modify present for both scopes, no delete.

### Tests (write first — must fail)

- [ ] T024 [US4] Write FAILING test `test_environments_tool_has_no_delete_action`: enumerate the `environments` tool actions; assert there is NO `delete` action and an unknown action returns the "not found" `BaseResult`. Maps AC "Delete stays out of scope", FR-012.
- [ ] T025 [P] [US4] Write FAILING test `test_insufficient_permission_surfaces_auth_error`: mock a write call → 401/403 `HTTPStatusError`; assert the `http_error_message` auth category is surfaced (confirms the tool relies on server-side gating and does not add/ bypass consent). Maps AC "respect existing PAT auth, RBAC, AI-consent gating".

### Implementation

- [ ] T026 [US4] Update the `environments` `@mcp.tool` docstring to document the new actions (create local/shared, modify, list/read shared) with args and examples, in the existing schedule/bucket manager docstring style. Confirm no `ai_consent` check and no `delete` action exist in the manager. Confirm this story's red tests now pass.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T027 Run `make lint` (black `--target-version py311`, flake8, isort) and fix any style issues in changed files; ensure max-complexity ≤ 10.
- [ ] T028 Run `make test` (full suite with coverage) and confirm all new + existing tests pass with `src/` coverage maintained.

---

## Dependencies

- Setup (endpoint constant + request models) blocks all stories.
- The request-model contract test depends on the request models existing.
- User Story 1 (agent-swap modify) is the MVP; independently testable after setup.
- User Stories 2, 3, 4 each depend only on setup plus their own story tests.
- Within each story: write the failing tests first (red), then implement (green).
- Polish (lint + full suite) runs last.

## Parallel Execution Examples

- After the request models are added, the contract test and the US1 modify tests can be written in
  parallel; the `[P]`-marked negative-path tests within each story are independent (distinct test
  functions in the same file, authored together).
- The US2, US3, and US4 test-writing tasks marked `[P]` are independent of each other.

## Implementation Strategy

MVP = User Story 1 (agent-swap modify) — the primary customer driver. Deliver US1 first, then US2
(create local), then US3 (shared scope) and US4 (surface polish). Each story is an independently
testable increment.

## AC → Task Coverage

See the Requirement Traceability Matrix in `spec.md` for the authoritative AC → task → test mapping.
Each Jira AC maps to at least one task above and at least one scenario in `test-scenarios.md`.
