# Feature Specification: API Monitoring (Runscope) MCP — Environment Management Tools

**Feature Branch**: `ai-mob-54638`
**Created**: 2026-10-08
**Status**: Draft
**Input**: MOB-54638 — Extend the Runscope (API Monitoring) MCP server's environment tool with create (shared + local) and modify (PATCH) actions on top of the existing read/list actions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Modify a local environment to swap its private agent (Priority: P1)

A platform engineer (acting on behalf of a customer like Deloitte) needs to change the private
agent used by a per-test (local) environment. Today the MCP environment tool is read/list only,
so the only recourse is manual UI edits across hundreds of tests. With a `modify` action, the
engineer can, through natural language to the MCP client, update a single environment's
`remote_agents` while every other setting (name, variables, regions, notifications) stays intact.
Repeating this across the customer's 631 per-test environments becomes a scriptable MCP workflow.

**Why this priority**: This is the primary customer driver (Deloitte agent swap). It is the single
most valuable new capability and the reason the story exists. It is independently valuable even if
create and shared-scope support were deferred.

**Independent Test**: Call the environments tool with `action="modify"`, a known
`bucket_key`/`test_id`/`environment_id`, and `{"remote_agents": [<new agent>]}`. Verify the
returned environment shows the new agent AND that unspecified fields (name, initial_variables,
regions) are unchanged from before the call.

**Acceptance Scenarios**:

1. **Given** an existing local environment with agent A and a set of variables, **When** the user
   modifies only `remote_agents` to agent B, **Then** the environment returns agent B and the
   original variables, name, and regions are preserved (partial update via PATCH).
2. **Given** an invalid `environment_id`, **When** the user calls modify, **Then** a clear
   not-found error message is returned (no silent failure).
3. **Given** a modify request the server rejects (validation error), **When** the call is made,
   **Then** the API's error is surfaced to the user as a clear, LLM-friendly message.

---

### User Story 2 - Create a local (test-level) environment (Priority: P1)

An engineer sets up a new per-test environment for a test — defining its name, initial variables,
regions, and (optionally) a private agent — directly through the MCP client, instead of the UI.

**Why this priority**: Creating local environments is a first-class part of the environment
management gap this story closes, and is a prerequisite for a full "manage environments via MCP"
workflow. Equal priority to modify for the core local-environment use case.

**Independent Test**: Call `action="create"` with scope local, a `bucket_key`, a `test_id`, and a
name + variables. Verify a new environment is returned with the supplied values and a new id.

**Acceptance Scenarios**:

1. **Given** a valid bucket and test, **When** the user creates a local environment with a name and
   initial variables, **Then** a new environment is returned with those values and a generated id.
2. **Given** a test already at the per-test environment limit, **When** the user creates another,
   **Then** the API-enforced limit error (e.g. "Cannot create more than 100 …") is surfaced clearly.
3. **Given** an invalid `bucket_key` or `test_id`, **When** create is called, **Then** a clear
   not-found/validation error is returned.

---

### User Story 3 - Create and manage shared (bucket-level) environments (Priority: P2)

An engineer lists, reads, and creates shared (bucket-level) environments that apply across a
bucket's tests, and can modify them the same way as local environments.

**Why this priority**: Shared environments round out the capability so the tool covers both scopes
the ticket requires. It is lower priority than the local-environment path only because the primary
customer driver (Deloitte) uses per-test local environments exclusively.

**Independent Test**: Call `action="list"` (shared scope) for a bucket, `action="create"` (shared
scope) with a name, and `action="read"` of the created shared environment by id. Verify list, create,
and read all operate on the bucket-level scope.

**Acceptance Scenarios**:

1. **Given** a valid bucket, **When** the user lists shared environments, **Then** the bucket's
   shared environments are returned.
2. **Given** a valid bucket, **When** the user creates a shared environment with a name, **Then** a
   new bucket-level environment is returned with a generated id.
3. **Given** a bucket at the shared-environment limit, **When** the user creates another, **Then**
   the API-enforced limit error is surfaced clearly.
4. **Given** a shared environment id, **When** the user reads or modifies it, **Then** the operation
   targets the bucket-level resource correctly.

---

### User Story 4 - Consistent, safe, auditable tool surface (Priority: P2)

Every new action follows the existing Runscope MCP tool conventions: one `environments` tool with
action routing, structured `BaseResult` responses, clear error messages, and telemetry spans. The
new write actions respect the platform's existing authentication (PAT), RBAC, and AI-consent gating
with no new bypass, and all actions remain auditable. Deletion is intentionally NOT offered.

**Why this priority**: Convention-consistency, safety (no delete), and auditability are
cross-cutting quality requirements that make the feature mergeable and operable, but they are not a
standalone user journey.

**Independent Test**: Inspect the registered tool: one `environments` tool exposes read/list/create/
modify for both scopes via action routing; no delete action exists; errors route through the shared
error helper; each action is wrapped in a telemetry span.

**Acceptance Scenarios**:

1. **Given** the environments tool, **When** its actions are enumerated, **Then** create and modify
   are present for both scopes and NO delete action exists.
2. **Given** a request lacking permission/consent at the platform layer, **When** a write action is
   attempted, **Then** the platform's auth/RBAC/consent decision is honored and its error surfaced
   (the MCP tool adds no new enforcement of its own and performs no bypass).

### Edge Cases

- **Invalid identifiers**: invalid `bucket_key`, `test_id`, or `environment_id` → surface the API's
  404/validation error as a clear message; never a silent success.
- **Limit reached**: creating beyond 100 shared/bucket or 100 local/test → surface the API's HTTP 400
  limit message unchanged.
- **Partial-update preservation**: modifying one field must not wipe `remote_agents` or other
  unspecified fields (the MOB-49921 wipe must not reoccur; PATCH partial-merge prevents it).
- **Insufficient permission / consent**: platform returns 401/403 → surface a clear auth error.
- **Empty modify payload**: a modify call with no changed fields returns the current environment
  unchanged (no error).
- **Timeout / unexpected error**: surface the shared unexpected-error message; never leak a stack
  trace to the MCP client.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The environments MCP tool MUST support a `list` action for **local (test-level)**
  environments, scoped by `bucket_key` + `test_id` (existing behavior; retained).
- **FR-002**: The environments MCP tool MUST support a `list` action for **shared (bucket-level)**
  environments, scoped by `bucket_key`.
- **FR-003**: The environments MCP tool MUST support a `read` action to retrieve a single
  environment by `environment_id` for both shared and local scopes.
- **FR-004**: The environments MCP tool MUST support a `create` action for a **local (test-level)**
  environment, accepting at least a name and initial variables, and returning the created
  environment.
- **FR-005**: The environments MCP tool MUST support a `create` action for a **shared
  (bucket-level)** environment, accepting at least a name, and returning the created environment.
- **FR-006**: The environments MCP tool MUST support a `modify` action that performs a **partial
  update (PATCH)**: only the fields supplied in the request are changed; all other fields —
  including `remote_agents` — MUST be preserved.
- **FR-007**: The `modify` action MUST support the agent-swap path end to end: updating only
  `remote_agents` on a local environment leaves every other field intact and returns the updated
  environment.
- **FR-008**: All create/modify actions MUST rely on the platform's existing PAT authentication,
  server-side RBAC, and server-side AI-consent gating. The MCP tool MUST NOT add a new consent
  bypass and MUST NOT implement a redundant MCP-layer consent check.
- **FR-009**: The tool MUST surface API-enforced environment limits (100 shared per bucket, 100
  local per test) by relaying the platform's limit error as a clear, LLM-friendly message; it MUST
  NOT hardcode or pre-validate the numeric caps itself.
- **FR-010**: The tool MUST return clear, LLM-friendly error messages for invalid bucket/test/
  environment id, validation errors, insufficient permission/consent, and limit-reached conditions,
  using the existing error-message helper.
- **FR-011**: The new actions MUST follow existing Runscope MCP tool conventions: a single
  `environments` tool with action routing, structured result objects, and telemetry spans per action
  for auditability.
- **FR-012**: The tool MUST NOT offer an environment deletion action (destructive operations remain
  out of scope, consistent with the server's safety model).
- **FR-013**: Input to create/modify MUST be validated against a typed request model before the API
  call so malformed requests fail fast with a clear message.

### Key Entities *(include if feature involves data)*

- **Environment**: An execution-settings container for tests. Key attributes include `id`, `name`,
  `initial_variables`, `regions`, `remote_agents` (the private/public agents used — central to the
  agent-swap use case), plus notification, SSL, cookie, and script settings. An environment is
  either **shared** (bucket-level, applies across the bucket) or **local** (test-level, bound to one
  test). Deletion is out of scope.
- **Bucket**: The container that owns tests and shared environments; identified by `bucket_key`.
- **Test**: Owns local environments; identified by `test_id` within a bucket.
- **Remote agent**: An entry within an environment's `remote_agents` list identifying the private
  or public agent location; the subject of the primary (swap) use case.

## Scope

### In Scope

- List shared (bucket-level) environments for a bucket.
- List local (test-level) environments for a test.
- Retrieve a single environment by ID (shared or test-level).
- Create a shared (bucket-level) environment.
- Create a local (test-level) environment.
- Modify an environment via PATCH (partial update), preferred over PUT.
- Agent-swap path works end to end via the MCP tool.
- Create/modify tools respect existing PAT auth, RBAC, and AI-consent gating; all actions auditable.
- Surface API-enforced limits clearly.
- Tool naming/inputs/output formatting follow existing Runscope MCP tool conventions.
- Clear error messages for invalid bucket/test/env ID, validation errors, insufficient permissions, limit reached.

### Out of Scope

- Delete environment capability (no destructive operations, consistent with the server's safety model).
- UI changes (MCP / natural-language interface only; no mock-up).
- Companion MCP tool-list documentation update (likely warranted post-ship, but out of scope for this story).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can swap a local environment's private agent through the MCP tool in a single
  `modify` call, with 100% of unspecified fields preserved (verified by before/after comparison).
- **SC-002**: A user can create both a local and a shared environment through the MCP tool and
  immediately read each back by id.
- **SC-003**: All six environment operations (list local, list shared, read, create local, create
  shared, modify) are available as actions on a single environments tool, with zero delete action.
- **SC-004**: Every failure mode (invalid id, limit reached, insufficient permission/consent,
  validation error) returns a clear, actionable message rather than a silent failure or raw stack
  trace — verified by negative-path tests for each.
- **SC-005**: The agent-swap workflow is repeatable across many per-test environments without manual
  UI edits, eliminating the current no-bulk-path gap for the customer use case.

## Assumptions

- The public Runscope environment APIs the MCP tool wraps live in the `api` service; its route and
  resource definitions are the authoritative contract (confirmed with the assignee). All contract
  facts below were read from that source — no live endpoint was called during planning.
- The existing `Environment` Pydantic model and `format_environments` formatter already cover the
  fields needed for create/modify (including `remote_agents` and `initial_variables`); only a typed
  **create/modify request** model needs to be added.
- PAT authentication, RBAC, and AI-consent are enforced by the `api` service for MCP requests; the
  MCP tool inherits them and adds no new enforcement.
- Environment caps are 100 shared/bucket and 100 local/test, enforced and messaged by the API; the
  tool surfaces those messages rather than hardcoding the numbers.
- `modify` uses PATCH (partial merge) as the primary verb; PUT is not required for correctness and
  is retained, if at all, only as a defensive fallback.

## Requirement Traceability Matrix

Every AC carries an `AC-N` id, at least one `T###` task, and at least one `test_*` name that exists
in `test-scenarios.md`.

| AC | Statement | FR / SC | Tasks | Test | Impl file |
|----|-----------|---------|-------|------|-----------|
| AC-1 | List shared (bucket-level) environments | FR-002, SC-003 | T016, T021, T023 | test_list_shared_environments | src/tools/environment_manager.py |
| AC-2 | List local (test-level) environments | FR-001, SC-003 | T001, T028 | test_list_local_environments_regression | src/tools/environment_manager.py |
| AC-3 | Retrieve a single environment by ID | FR-003, SC-002 | T017, T021 | test_read_shared_environment | src/tools/environment_manager.py |
| AC-4 | Create a shared (bucket-level) environment | FR-005, SC-002 | T018, T022, T023 | test_create_shared_environment | src/tools/environment_manager.py |
| AC-5 | Create a local (test-level) environment | FR-004, SC-002 | T011, T014, T015 | test_create_local_environment | src/tools/environment_manager.py |
| AC-6 | Modify an environment via PATCH (partial) | FR-006, SC-001 | T004, T009, T010 | test_modify_environment_agent_swap_preserves_fields | src/tools/environment_manager.py |
| AC-7 | Agent-swap path works end to end | FR-007, SC-001, SC-005 | T004, T005, T009 | test_modify_environment_name_only_preserves_remote_agents | src/tools/environment_manager.py |
| AC-8 | Respect PAT auth, RBAC, AI-consent; auditable | FR-008, FR-011 | T025, T026 | test_insufficient_permission_surfaces_auth_error | src/tools/environment_manager.py |
| AC-9 | Surface API-enforced limits clearly | FR-009, SC-004 | T012, T019 | test_create_local_environment_limit_reached_surfaces_api_message | src/tools/environment_manager.py |
| AC-10 | Tool naming/inputs/output follow conventions | FR-011, FR-013, SC-003 | T002, T003, T026 | test_create_modify_request_models_serialize_by_alias_exclude_none | src/tools/environment_manager.py, src/models/environment.py |
| AC-11 | Clear error messages for invalid/limit/perm | FR-010, SC-004 | T006, T013, T025 | test_modify_environment_invalid_id_returns_not_found | src/tools/environment_manager.py |
| AC-12 | Delete stays out of scope | FR-012, SC-003 | T024, T026 | test_environments_tool_has_no_delete_action | src/tools/environment_manager.py |

## Technical Context

- **Language/Version**: Python `>=3.11` (CI matrix 3.11, 3.12). `pyproject.toml:10`.
- **Primary Dependencies**: `mcp[cli]>=1.19.0,<2` (FastMCP server over stdio), `httpx>=0.27.0`
  (async HTTP client used by `src/common/api_client.py`), `pydantic>=2.12.3` (models + request
  validation). `pyproject.toml:20-23`.
- **Storage**: None local — this is a stateless MCP client; it proxies the Runscope/BlazeMeter
  public API (`api` service) over HTTPS. No DB/Redis in this repo.
- **Testing**: `pytest` with `pytest-asyncio` in `auto` mode, `unittest.mock`/`AsyncMock` (API
  calls are mocked, never live). `make test` → `pytest -v --cov=src`. `pytest.ini`, `Makefile:21`.
- **Target Platform**: CLI / Docker — a FastMCP server started on stdio from `main.py` (`--mcp`);
  packaged as a standalone binary (PyInstaller) or Docker image.
- **Project Type**: Single-package MCP server (`src/tools`, `src/models`, `src/formatters`,
  `src/common`, `src/config`).
- **Performance Goals**: Not latency-sensitive; each action is one upstream API call. No N×M fan-out
  (create/modify/read each hit exactly one endpoint). No performance strategy section is required
  (no nested external-call loops).
- **Constraints**: Line length 108; max complexity 10 (flake8); async test mode auto; no live API
  calls in tests. `CLAUDE.md` Code Style.
- **Scale/Scope**: One tool module (`environment_manager.py`) extended with create/modify actions;
  one new request model; one new endpoint constant for bucket-level environments.

## Field Semantics (BINDING)

> Source: brownfield semantic disambiguation (brownfield-context.md § Semantic Disambiguation).
> These decisions are NON-NEGOTIABLE. Every downstream artifact — plan.md, tasks.md, tests, and the
> implementation — must honor them.

### Approved Identifiers (USE these for this ticket)
- `EnvironmentManager` class — extend with create()/modify() methods (existing pattern).
- `Environment` Pydantic model (`src/models/environment.py`) — already has `remote_agents`,
  `initial_variables`, `name`, `regions`.
- CREATE via POST + typed request model + `model_dump(by_alias=True, exclude_none=True)` +
  `api_request(..., json=body)` — mirror `schedule_manager.create` (`schedule_manager.py:41-54`).
- `modify_environment` via PATCH partial-merge (preserves `remote_agents`) — api confirms at
  `api/api/resources/tests.py:1068-1126`.
- Shared endpoint `/buckets/{key}/environments`; test-level `/buckets/{key}/tests/{id}/environments`;
  single/modify via `.../environments/{env_id}`.
- `format_environments` formatter; `http_error_message()` / `UNEXPECTED_ERROR_MESSAGE`; `@mcp.tool`
  + match-action routing; `tool_span` / `check_result_error` / `record_span_error` telemetry.
- Inherit server-side PAT + RBAC + ai_consent gating; surface API 400 limit errors via
  `http_error_message()`.

### Forbidden Identifiers (DO NOT USE — belong to a different feature / wrong design)
- A method literally named `patch_environment` — name the modify method `modify_environment`
  (PATCH is the verb, not the method name). Reason: avoid locking the public action name to a verb;
  keep naming consistent with existing managers.
- A new MCP-layer `ai_consent` enforcement block — ai_consent is enforced server-side by the `api`
  service for the `bzm-apitest-mcp` user-agent; a redundant MCP-layer check is forbidden. Evidence:
  `api/CLAUDE.md` Request Lifecycle; no current tool manager enforces ai_consent.

### Negative Constraints
- DO NOT add a delete/destructive environment action (FR-012).
- DO NOT hardcode the 100/100 environment caps or pre-validate counts client-side; relay the API's
  400 message (FR-009).
- DO NOT use PUT (wholesale replace) as the primary modify verb — it risks the MOB-49921
  `remote_agents` wipe; use PATCH partial-merge.
- DO NOT implement a redundant MCP-layer ai_consent check (inherited from the api service).

## Current Implementation

> Source: brownfield codebase research (brownfield-context.md)

### What exists today
- `src/tools/environment_manager.py` exposes exactly two actions — `read` and `list` — both GET,
  both scoped to test-level `TEST_ENVIRONMENT_ENDPOINT = /buckets/{}/tests/{}/environments`
  (`environment_manager.py:31-46`). No create, no modify, no shared (bucket-level) scope.
- `src/models/environment.py:14-95` defines the full `Environment` model including
  `remote_agents` (54-56), `initial_variables` (25-27), `name` (19), `regions` (53).
- `src/formatters/environment.py:6` provides `format_environments`.
- `src/config/defaults.py:15` defines `TEST_ENVIRONMENT_ENDPOINT`; there is NO bucket-level
  environment endpoint constant yet.
- `src/common/api_client.py:23-71` provides generic `api_request(token, method, endpoint,
  result_formatter=…, json=…, params=…)` supporting any HTTP verb.
- Analog for CREATE: `schedule_manager.create` (`schedule_manager.py:41-54`) — typed model →
  `model_dump(by_alias=True, exclude_none=True)` → POST with `json=`.

### Key files the implementer will touch
- `src/tools/environment_manager.py` (add create/modify actions + list_shared/read-shared routing)
- `src/models/environment.py` (add a create/modify request model)
- `src/config/defaults.py` (add `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT`)
- `tests/test_environment_manager.py` (extend with create/modify/error-path tests)

## Runtime Data Availability (BINDING)

> Source: brownfield-context.md § Runtime Data Availability Proof. All inputs (bucket_key, test_id,
> environment_id) are supplied by the MCP caller; invalid ids are rejected by the API (404). For
> modify, the `api` service's PATCH itself reads the current environment and merges — the MCP tool
> does not need a separate client-side read-merge. No runtime data is deleted/expired between read
> and write within a single MCP action. No row is `no`/`unknown`.

## Cross-Repo / API Contract (BINDING)

> Source: brownfield-context.md § Dependency Contract Facts: runscope-env-api. Confirmed from the
> `api` service source (read-only). Boundary pattern: **Conformist** — the MCP tool consumes the
> `api` service's published environment contract as-is; it marshals responses through the existing
> `Environment` model (a light adapter), and adds no new contract of its own.

| Operation | Endpoint | Verb | api evidence |
|-----------|----------|------|--------------|
| List shared | `/buckets/{key}/environments` | GET | tests.py:745 (SharedEnvironmentList.get) |
| List local | `/buckets/{key}/tests/{id}/environments` | GET | environment_manager.py:40; tests.py:779 |
| Read single | `/buckets/{key}/environments/{env_id}` or `/buckets/{key}/tests/{id}/environments/{env_id}` | GET | tests.py:1131 (EnvironmentInstance.get); routes.py:142-144 |
| Create shared | `/buckets/{key}/environments` | POST | tests.py:721 (SharedEnvironmentList.post) |
| Create local | `/buckets/{key}/tests/{id}/environments` | POST | tests.py:756 (TestEnvironmentList.post) |
| Modify (both scopes) | `.../environments/{env_id}` | PATCH | tests.py:1068-1126 (EnvironmentInstance.patch, partial-merge, preserves remote_agents) |

Caps: `SHARED_ENVIRONMENT_LIMIT = 100`, `TEST_ENVIRONMENT_LIMIT = 100` (`api/api/config.py:112-113`),
API-enforced with HTTP 400 — surfaced via `http_error_message()`, not hardcoded in the MCP tool.

## Design Alternatives Considered (BINDING)

> Source: brownfield-context.md § Design Alternatives Considered.

| Option | Decision | Reason |
|--------|----------|--------|
| Modify via PATCH (partial merge) | SELECTED | api PATCH preserves `remote_agents`; agent-swap safe; no MOB-49921 wipe. |
| Modify via PUT (wholesale) + client read-merge | REJECTED | Unnecessary — api PATCH already merges server-side; PUT risks the wipe. |
| Extend the single `environments` tool with new actions | SELECTED | Mirrors every other manager; preserves naming/convention consistency. |
| Add a separate new MCP tool for writes | REJECTED | Breaks the one-tool-per-domain convention. |
| Add MCP-layer ai_consent enforcement | REJECTED | Enforced server-side by api for the MCP user-agent; redundant and a divergence from existing managers. |
| Hardcode 100/100 caps and pre-validate | REJECTED | API already enforces and messages; hardcoding risks drift if the limit changes. |

## Test Validity Strategy (BINDING)

> Source: brownfield-context.md § Test Validity Strategy. Tests MUST challenge the partial-update
> contract, not merely assert non-empty output:
> - **Partial-merge falsification**: modify only `remote_agents` → assert all other fields unchanged;
>   and modify only `name` → assert `remote_agents` unchanged. A test that mocks away the preserved
>   fields is invalid.
> - **Contract shape**: create/modify request body is the typed request model serialized with
>   `by_alias=True, exclude_none=True`; verify the mocked `api_request` is called with the right
>   verb + endpoint + json body for each scope (shared vs local).
> - **Negative paths**: invalid id (404), limit reached (400), insufficient permission/consent
>   (401/403), validation error — each surfaced via `http_error_message()`.
> - **No-delete guard**: assert the tool exposes no delete action.
> - All API calls are mocked (`unittest.mock`/`AsyncMock`); no live calls (repo convention).
