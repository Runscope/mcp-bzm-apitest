# Implementation Plan: Environment Management MCP Tools (MOB-54638)

**Branch**: `ai-mob-54638` | **Date**: 2026-10-08 | **Spec**: `specs/mob-54638/spec.md`
**Input**: Feature specification from `specs/mob-54638/spec.md`

## Summary

Extend the existing `environments` MCP tool (`src/tools/environment_manager.py`) — today read/list
only — with **create** (shared + local) and **modify** (PATCH partial-merge) actions, plus
shared-scope list/read. The modify action enables the primary driver: bulk-swapping a private agent
across a customer's per-test environments while preserving every other field. The technical approach
mirrors the existing manager pattern exactly: typed Pydantic request model → `api_request()` with the
right verb → `format_environments` response → `BaseResult`. All endpoints, caps, and PATCH
partial-merge semantics are confirmed from the `api` service source (binding Dependency Contract Facts
in `brownfield-context.md`).

## Technical Context

**Language/Version**: Python `>=3.11` (CI matrix 3.11, 3.12) — `pyproject.toml:10`
**Primary Dependencies**: `mcp[cli]>=1.19.0,<2` (FastMCP/stdio), `httpx>=0.27.0`, `pydantic>=2.12.3` — `pyproject.toml:20-23`
**Storage**: N/A — stateless MCP client; proxies the Runscope `api` service over HTTPS
**Testing**: `pytest` + `pytest-asyncio` (auto mode); API mocked via `unittest.mock.AsyncMock`; `make test` → `pytest -v --cov=src`
**Target Platform**: CLI / Docker — FastMCP server on stdio (`main.py --mcp`)
**Project Type**: Single-package MCP server (`src/tools`, `src/models`, `src/formatters`, `src/common`, `src/config`)
**Performance Goals**: Not latency-sensitive; every action is exactly one upstream API call. No nested external-call fan-out (no N×M) → no Performance Strategy section required.
**Constraints**: line length 108; max complexity 10 (flake8); no live API calls in tests — `CLAUDE.md` Code Style
**Scale/Scope**: one tool module extended; one new request model; one new endpoint constant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Scoped MCP Tools | PASS | New actions stay inside `EnvironmentManager` / the `environments` tool; no cross-domain absorption. Registered via existing `register()` + `@mcp.tool()`. |
| II. Single API Client | PASS | All new calls go through `api_request()` with the correct verb (GET/POST/PATCH); no direct HTTP, no new auth layer. |
| III. Test-First (NON-NEGOTIABLE) | PASS | task-test-author authors failing tests first; API mocked via `AsyncMock`; tests mirror `tests/test_environment_manager.py`. |
| IV. LLM-Friendly Error Handling | PASS | All errors routed through `http_error_message()` / `UNEXPECTED_ERROR_MESSAGE`; limit (400), not-found (404), auth (401/403), validation surfaced as categorized messages; no stack traces/tokens leak. |
| V. Structured Pydantic Responses | PASS | Every action returns `BaseResult`; responses pass through `format_environments`; a typed create/modify request model validates input. No raw JSON parsing in the tool. |

**Result**: No violations. Complexity Tracking table is empty (below).

## Project Structure

### Documentation (this feature)

```text
specs/mob-54638/
├── spec.md                  # Feature spec (authored)
├── brownfield-context.md    # Binding research (semantic, contract, alternatives — all PROVEN)
├── plan.md                  # This file
├── research.md              # Phase 0 output
├── data-model.md            # Phase 1 output
├── quickstart.md            # Phase 1 output
├── contracts/               # Phase 1 output (MCP action contracts)
├── design-contract.json     # Structured design/evidence contract
├── evidence-index.json      # Evidence IDs
└── tasks.md                 # Phase 2 output (speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── tools/
│   └── environment_manager.py   # MODIFY: add create/modify + shared list/read actions to EnvironmentManager and the match-action router
├── models/
│   └── environment.py           # MODIFY: add CreateEnvironment / ModifyEnvironment request model(s)
├── formatters/
│   └── environment.py           # REUSE: format_environments (no change expected)
├── common/
│   ├── api_client.py            # REUSE: api_request() (no change)
│   └── errors.py                # REUSE: http_error_message / UNEXPECTED_ERROR_MESSAGE (no change)
└── config/
    └── defaults.py              # MODIFY: add BUCKET_LEVEL_ENVIRONMENT_ENDPOINT constant

tests/
└── test_environment_manager.py  # MODIFY: add create/modify/shared/error-path tests (mocked)
```

**Structure Decision**: Single-project MCP server. The change is additive and localized to the
environment domain: extend `EnvironmentManager` with new methods and extend the existing `environments`
tool's `match action` router with the new action cases. No new modules, no architectural change.

## Technical Approach

### Endpoints (confirmed from `api` service source — binding)

| Action | Endpoint | Verb | api evidence |
|--------|----------|------|--------------|
| list local | `/buckets/{key}/tests/{id}/environments` | GET | environment_manager.py:40 (existing); api tests.py:779 |
| list shared | `/buckets/{key}/environments` | GET | api tests.py:745 (SharedEnvironmentList.get) |
| read single | `/buckets/{key}/environments/{env_id}` or `/buckets/{key}/tests/{id}/environments/{env_id}` | GET | api tests.py:1131; routes.py:142-144 |
| create local | `/buckets/{key}/tests/{id}/environments` | POST | api tests.py:756 (TestEnvironmentList.post) |
| create shared | `/buckets/{key}/environments` | POST | api tests.py:721 (SharedEnvironmentList.post) |
| modify (both) | `.../environments/{env_id}` | PATCH | api tests.py:1068-1126 (EnvironmentInstance.patch) |

A new `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT = "/buckets/{}/environments"` constant is added to
`src/config/defaults.py` (alongside the existing `TEST_ENVIRONMENT_ENDPOINT`).

### Modify = PATCH partial-merge (binding; agent-swap safe)

The `api` service's `EnvironmentInstance.patch` (tests.py:1068-1126) fetches the full current
environment, overlays ONLY the fields present in the request body, re-validates, and persists the
merged object. Therefore the MCP tool's `modify_environment` sends **only the fields the caller wants
to change** as the PATCH `json=` body. For the agent-swap path, that is `{"remote_agents": [<new
agent>]}` — the server preserves name, variables, regions, etc. No client-side read-merge is needed,
and the MOB-49921 wipe does not occur because PUT (wholesale replace) is not used.

> **Binding naming**: the method is `modify_environment` (and the MCP action is `modify`). A method
> literally named `patch_environment` is FORBIDDEN (brownfield Negative Constraints).

### Create = POST + typed request model (mirror schedule_manager)

Following `schedule_manager.create` (schedule_manager.py:41-54): build a typed request model
(e.g. `CreateEnvironment`), serialize with `model_dump(by_alias=True, exclude_none=True)`, and pass
as `json=body` to `api_request(..., "POST", <endpoint>, result_formatter=format_environments)`. The
endpoint is `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)` for shared or
`TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)` for local.

### Tool surface (extend, don't fork)

Extend the single `environments` `@mcp.tool` registered in `register()` with new `match action`
cases: `create` (routes to shared vs local by presence of `test_id`/a `scope` arg), `modify`, and a
shared-scope `list`/`read` (routed the same way). No separate tool. Update the tool `description`
docstring to document the new actions and their args (follow the existing schedule/bucket manager
docstring style). Keep the existing `read`/`list` behavior intact.

### Auth / consent / limits (inherit; surface)

- PAT auth is applied in `api_request()` (constitution II); unchanged.
- AI-consent + RBAC are enforced server-side by the `api` service for the `bzm-apitest-mcp`
  user-agent (api/CLAUDE.md Request Lifecycle). The MCP tool adds NO new consent check (binding
  Negative Constraint).
- Caps (100 shared/bucket, 100 local/test — api/api/config.py:112-113) are enforced by the API with
  HTTP 400; the tool surfaces that 400 via `http_error_message()` and does NOT hardcode the numbers
  (FR-009).

### Error handling (constitution IV)

Wrap each new action in the existing `tool_span` and the `try/except` ladder already present in
`environment_manager.register()` (timeout → `UNEXPECTED_ERROR_MESSAGE`; `HTTPStatusError` →
`http_error_message(e)`; other → `UNEXPECTED_ERROR_MESSAGE`). No new error paths are invented.

## Non-Goals

- No environment delete/destructive action (FR-012).
- No UI changes — MCP / natural-language interface only.
- No new MCP-layer ai_consent enforcement — gating is inherited from the `api` service.
- No hardcoded environment caps — the API enforces and messages 100/100; the tool surfaces the error.
- No PUT-based wholesale modify — PATCH partial-merge is the primary (and sufficient) verb.
- No change to the `Environment` response model or `format_environments` formatter (reused as-is).

## Failure Modes

| Condition | Behavior | Fallback value |
|-----------|----------|----------------|
| Invalid bucket/test/env id | API 404 → `http_error_message` not-found category | `BaseResult(error=<not-found message>)` |
| Limit reached (100/100) | API 400 → `http_error_message` | `BaseResult(error=<API limit message>)` |
| Insufficient permission/consent | API 401/403 → `http_error_message` auth category | `BaseResult(error=<auth message>)` |
| Validation error on create/modify | request-model validation (pre-call) OR API 4xx | `BaseResult(error=<validation message>)` |
| Timeout | `httpx.TimeoutException` | `BaseResult(error=UNEXPECTED_ERROR_MESSAGE)` |
| Empty modify payload | return current env unchanged (no error) | the current environment |
| Unexpected exception | logged (no token), span error recorded | `BaseResult(error=UNEXPECTED_ERROR_MESSAGE)` |

## Phase 0 — Research (research.md)

All decisions are PROVEN from source (see brownfield-context.md). No open clarification items. Key
decisions carried into research.md:
- Decision: PATCH partial-merge for modify. Rationale: api PATCH preserves remote_agents; agent-swap
  safe. Alternatives: PUT wholesale + client read-merge (rejected — redundant, risks wipe).
- Decision: extend the single environments tool via action routing. Rationale: convention
  consistency. Alternatives: separate write tool (rejected).
- Decision: inherit server-side ai_consent/PAT/RBAC. Rationale: enforced by api for the MCP
  user-agent. Alternatives: MCP-layer consent check (rejected — redundant).
- Decision: surface API 400 limit error; no hardcoded caps. Rationale: API enforces + messages.

## Phase 1 — Design & Contracts

- **data-model.md**: the `Environment` entity (existing, reused) and a new `CreateEnvironment` /
  `ModifyEnvironment` request model (writable fields only: name, initial_variables, regions,
  remote_agents, and the common optional toggles; alias-mapped, exclude_none).
- **contracts/**: MCP action contracts for `environments` — `list` (local+shared), `read`,
  `create` (local+shared), `modify` — documenting args, routing (scope by `test_id`/`scope`), the
  upstream verb+endpoint, and the `BaseResult` response.
- **quickstart.md**: a worked agent-swap example (modify only remote_agents) and a create example.
- **Agent context**: the CLAUDE.md SPECKIT markers point to this plan.

## Complexity Tracking

> No constitution violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
