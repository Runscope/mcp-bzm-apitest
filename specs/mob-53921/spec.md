# Feature Specification: Usage-retrieval MCP tools (consumer)

**Feature Branch**: `ai-mob-53921`
**Created**: 2026-10-06
**Status**: Draft
**Input**: Jira MOB-53921 — API Monitoring (Runscope) MCP: add usage-data tools. This spec is scoped to the `mcp-bzm-apim` repo (consumer). Jira: https://perforce.atlassian.net/browse/MOB-53921

## Background / Overview

MOB-53921 extends the API Monitoring (Runscope) MCP server with read-only usage tools (team, bucket, and test-level request consumption over the last 90 days), closing a gap deferred from the parent MCP epic MOB-43615.

The work spans two repos in this shard:

- **`api` (separate spec — PRODUCER):** owns the public usage REST endpoints. Team-level (`/team/<team_uuid>/requests`) and bucket-level (`/buckets/<bucket_key>/requests`) already exist; test-level (`/buckets/<bucket_key>/tests/<test_uuid>/requests`) is added in the same ticket. **Out of scope for this `mcp-bzm-apim` spec.**
- **`mcp-bzm-apim` (this spec — CONSUMER):** adds new read-only MCP tools that call api's public usage endpoints and present the counts to the agent/user in natural language. The MCP server is a thin read-only wrapper over api's REST surface; existing tools (`ResultManager`, `BucketManager`, `TeamManager`, `TestManager`) already follow this pattern.

The usage API returns a single usage metric — request count — over a date window. `api` owns all auth, AI-consent, and date-range semantics; this consumer wraps, formats, and presents.

### In Scope

- New endpoint constants in `src/config/defaults.py`: `TEAM_USAGE_ENDPOINT = "/team/{}/requests"`, `BUCKET_USAGE_ENDPOINT = "/buckets/{}/requests"`, `TEST_USAGE_ENDPOINT = "/buckets/{}/tests/{}/requests"`.
- New usage models in `src/models/usage.py` (`TeamUsage`, `BucketUsage`, `TestUsage`): `requests_count: int`, `from_date: str`, `to_date: str`, plus the resource identifier.
- New formatters in `src/formatters/usage.py` (`format_team_usage`, `format_bucket_usage`, `format_test_usage`) mirroring `format_results`.
- New manager + three read-only usage tool registrations in `src/tools/usage_manager.py` (under `TOOLS_PREFIX` `blazemeter_apitest`), each calling `api_request` with the endpoint constant and formatter, wrapped in a telemetry span.
- Wire `register` into `src/server.py` `register_tools`.
- Tests in `tests/test_usage_manager.py`: mock `api_request`; assert correct `requests_count` mapping; error cases; default-window (today); falsification (faithful pass-through).

### Out of Scope

- Any change to `api` (the public usage endpoints — separate producer repo in this shard).
- Any change to `scorekeeper`.
- Enforcing the 90-day retention or window bounding (api/scorekeeper own that; this consumer documents the limit and passes date params through).
- Companion doc update to the MCP server's tool list (explicitly out of scope per the ticket).
- Any UI change.

## Field Semantics (BINDING)

> Source: brownfield semantic disambiguation (brownfield-context.md § Semantic Disambiguation).
> These decisions are NON-NEGOTIABLE. Every downstream artifact — plan.md, tasks.md, tests, and the implementation — must honor them.

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|---|---|---|---|---|
| usage data retrieval | (none in mcp-bzm-apim) | — | NEW — no usage tools exist | no matches in `src/tools/` |
| team/bucket/test usage tools | (none) | MCP tools to fetch request counts | NEW | ticket AC; api endpoints (`api/resources/radar_results.py:777-986`; new test endpoint `api/specs/mob-53921`) |
| `requests_count` | `tests_count` (`src/models/bucket.py:27`, a COUNT OF TESTS — different); `requests` (`src/models/result.py`, per-request sub-object — different) | aggregate HTTP request count over a window | NEW field; do NOT conflate with `tests_count`/`requests` | `src/models/bucket.py:27`; `src/models/result.py` |
| `UsageManager` / `get_team_usage` / `get_bucket_usage` / `get_test_usage` | (none) | usage manager + methods | NEW (no collision) | `src/tools/` has no usage manager |
| `TeamUsage` / `BucketUsage` / `TestUsage` | (none) | usage response models | NEW | `src/models/` has no usage models |
| `TEAM_USAGE_ENDPOINT` / `BUCKET_USAGE_ENDPOINT` / `TEST_USAGE_ENDPOINT` | `TEAMS_ENDPOINT`, `BUCKETS_ENDPOINT`, `RESULTS_ENDPOINT` (different suffixes) | endpoint path constants | NEW | `src/config/defaults.py` |

### Approved Identifiers (USE these for this ticket)
- `UsageManager` + `get_team_usage`/`get_bucket_usage`/`get_test_usage` — mirror `ResultManager` (`src/tools/result_manager.py`).
- `TEAM_USAGE_ENDPOINT`/`BUCKET_USAGE_ENDPOINT`/`TEST_USAGE_ENDPOINT` — new `defaults.py` constants matching api route paths.
- `TeamUsage`/`BucketUsage`/`TestUsage` — Pydantic models (`src/models/usage.py`) mirroring `src/models/result.py`.
- `format_team_usage`/`format_bucket_usage`/`format_test_usage` — formatters (`src/formatters/usage.py`) mirroring `src/formatters/result.py`.
- `BzmApimToken` + `api_request` + `tool_span` + `http_error_message` — existing auth/client/telemetry/error helpers; no new auth path.

### Forbidden Identifiers (DO NOT USE — belong to a different feature or risk collision)
None. The change is purely additive. Note: `tests_count` (`src/models/bucket.py:27`, a count of tests) and `result.requests` (per-request sub-object) are UNRELATED domains — do not conflate the new usage `requests_count` with them.

### Negative Constraints
The design is purely additive — three new tools, no refactor of existing managers. Existing tool managers, models, formatters, and registrations MUST remain unchanged.

## Current Implementation

> Source: brownfield codebase research (brownfield-context.md)

### What exists today
| What | File | Status |
|---|---|---|
| Read-only tool-manager pattern (primary analog) | `src/tools/result_manager.py` (ResultManager) | exists; registration + `api_request` + formatter + model + telemetry + errors |
| Simpler single-resource managers | `src/tools/team_manager.py`, `bucket_manager.py`, `test_manager.py` | exist; mirror for granularity |
| Tool wiring | `src/server.py` `register_tools` (called from `main.py:104`) | exists; add usage registration here |
| api_request client | `src/common/api_client.py:23-72` | exists; reuse |
| Error helpers | `src/common/errors.py` (`http_error_message`, `UNEXPECTED_ERROR_MESSAGE`) | exist; reuse |
| Telemetry | `src/common/telemetry.py` (`tool_span`, `check_result_error`, `record_span_error`) | exist; reuse |
| Endpoint constants | `src/config/defaults.py` (`TOOLS_PREFIX`, resource `*_ENDPOINT`) | exists; add usage constants |
| Formatter pattern | `src/formatters/result.py` | exists; mirror |
| Model pattern | `src/models/__init__.py` (BaseResult), `src/models/result.py` | exists; mirror |
| Usage tools | — | DO NOT EXIST; this spec adds them |

### Key files the planner/implementer must read
- api contract (cross-repo): `api/specs/mob-53921/spec.md`, `api/specs/mob-53921/plan.md`; `api/resources/radar_results.py:729-986`; `api/routes.py:64-65`
- mcp (to mirror): `CLAUDE.md`, `README.md`, `src/tools/result_manager.py`, `src/server.py`, `src/common/api_client.py`, `src/common/errors.py`, `src/common/telemetry.py`, `src/config/defaults.py`, `src/formatters/result.py`, `src/models/__init__.py` + `result.py`, `tests/conftest.py`

## Runtime Data Availability (BINDING)

> Source: brownfield-context.md § Runtime Data Availability Proof.

All three usage data sources are available synchronously via `api` REST at tool-invocation time (api proxies scorekeeper's aggregated counters). There is NO deleted-before-read hazard in the consumer: the tool makes a blocking `api_request` and formats whatever api returns. 90-day retention is an api/scorekeeper ops concern (documented in the api planner artifacts); from the consumer's perspective availability is YES.

| Runtime Data | Available at Read Time? | Evidence | Safer Alternative |
|---|---|---|---|
| Team usage counts | YES (synchronous api call) | `api/resources/radar_results.py:777-872` (TeamRequestCount) | None — synchronous upstream |
| Bucket usage counts | YES (synchronous api call) | `api/resources/radar_results.py:875-986` (BucketRequestCount) | None — synchronous upstream |
| Test usage counts | YES (synchronous api call) | `api/specs/mob-53921/spec.md` (new TestRequestCount) | None — synchronous upstream; a missing day contributes 0 (ops dependency, not a redesign blocker) |

## Dependency Contract Facts (BINDING)

### Dependency Contract Facts: api
All three endpoints return the standard `{data, meta, error}` envelope (via `@api_marshal`):

| Endpoint | Method / Path | `data` fields | Status |
|---|---|---|---|
| Team usage | `GET /team/<team_uuid>/requests` | `team_uuid`, `requests_count` (int), `from_date` (str "YYYY-MM-DD"), `to_date` (str) | EXISTS (`api/resources/radar_results.py:777-872`) |
| Bucket usage | `GET /buckets/<bucket_key>/requests` | `bucket_key`, `requests_count` (int), `from_date`, `to_date` | EXISTS (`api/resources/radar_results.py:875-986`) |
| Test usage | `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` | `test_uuid`, `requests_count` (int), `from_date`, `to_date` | NEW (`api/specs/mob-53921/spec.md` FR-001) |

- **Date params (all three):** optional `from`/`to`/`days`/`date`; no params → TODAY (NOT a 90-day default); 90-day maximum lookback.
- **Auth (all three):** PAT via `@validate_authentication`; `bucket_for_user` for bucket/test; existing AI-consent gate; no new auth path.
- **Binding:** the consumer reads `data.requests_count` (int), `data.from_date`, `data.to_date`, and the resource identifier. It does NOT re-aggregate or re-validate counts — api is the source of truth. scorekeeper's internal list-typed `test_id` is NOT exposed to the MCP tool user; the tool takes `team_uuid`/`bucket_key`/`test_uuid` + optional date params.

## Field/Metric Provenance Matrix (BINDING)

| Output Field | Required Semantics | Source of Truth | Object Level | Source Endpoint | Source Field Path | 90-day Window |
|---|---|---|---|---|---|---|
| team `requests_count` | total HTTP requests for the team in window | api TeamRequestCount (proxies scorekeeper) | team aggregate | `GET /team/<team_uuid>/requests` | `data.requests_count` | default=today; 90-day max |
| bucket `requests_count` | total HTTP requests for the bucket in window | api BucketRequestCount | bucket aggregate | `GET /buckets/<bucket_key>/requests` | `data.requests_count` | default=today; 90-day max |
| test `requests_count` | total HTTP requests for the test in window | api TestRequestCount (NEW) | test aggregate | `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` | `data.requests_count` | default=today; 90-day max |
| `from_date` / `to_date` | the window the count spans | api query-param parsing | request context | all three | `data.from_date` / `data.to_date` | default=today; 90-day max |
| resource identifier | which resource the count belongs to | api route param echoed in response | identifier | all three | `data.<identifier>` | n/a |

**Falsification test (mandatory):** mocking `api_request` to return a specific `requests_count` MUST produce exactly that value in the tool output (no placeholder / non-empty-only assertion); a non-matching mock MUST NOT fabricate a value. The "requests_count maps to the requested test only" invariant is proven in api's own test suite; the consumer's test asserts faithful pass-through of `data.requests_count`.

## Reference Implementation Trace (BINDING)

**Behavioral portrait:** read-only MCP tool (FastMCP), fetches aggregate usage counts from an api public REST endpoint via a synchronous `api_request` call, PAT auth + team AI-consent (enforced upstream by api), per-invocation lifecycle, upstream = api public REST, result destination = formatted MCP tool response.

**Chosen analog:** `ResultManager` (`src/tools/result_manager.py`) — same protocol (MCP tool), IO shape (request→response), auth (BzmApimToken + api_request), lifecycle, and data source (api public REST). `TeamManager`/`BucketManager`/`TestManager` are secondary analogs for single-resource granularity.

**Pattern extractions (BINDING — mirror unless a Design Alternatives row justifies divergence with evidence):**
- **Tool-registration invariant:** a `register(mcp, token)` function with `@mcp.tool(name=f"{TOOLS_PREFIX}_<resource>")`, an `async def <resource>(action, args, ctx)` signature dispatching via `match action`, wrapped in `tool_span`. Register three usage tools (team/bucket/test) and wire into `src/server.py` `register_tools`.
- **api_request/endpoint-constant invariant:** add the three endpoint constants to `src/config/defaults.py`; call `api_request(token, "GET", ENDPOINT.format(ids), <formatter>, params=date_params)` exactly as `ResultManager` does.
- **Formatter invariant:** add `format_*_usage` in `src/formatters/usage.py` mirroring `format_results` (`src/formatters/result.py:6-26`): build the Pydantic model and `model_dump(by_alias=False)`.
- **Model invariant:** add `TeamUsage`/`BucketUsage`/`TestUsage` in `src/models/usage.py` mirroring `src/models/result.py`.
- **Error-handling invariant:** reuse `http_error_message` / `UNEXPECTED_ERROR_MESSAGE` (`src/common/errors.py`) — never fabricate a count on error.
- **Auth/consent invariant:** pass `BzmApimToken` to `api_request`; api enforces `@validate_authentication` + the existing AI-consent gate. No new auth path.
- **Naming invariant:** tool names consistent with existing `Team`/`Bucket`/`Test`/`Results` tools under `TOOLS_PREFIX`.

## Design Alternatives Considered (BINDING)

| Option | Decision | Rationale |
|---|---|---|
| Three separate usage tools (team/bucket/test) | **SELECTED** | matches existing tool granularity (separate Team/Bucket/Test/Result tools); best MCP discoverability (`src/tools/*_manager.py`) |
| One parameterized usage tool (resource_type arg) | REJECTED | no precedent in the codebase; worse discoverability; higher cognitive load |
| Extend existing TeamManager/BucketManager/TestManager with usage methods | REJECTED | mixes analytics with resource CRUD; violates separation of concerns |
| Compute usage locally in mcp | REJECTED | mcp is a thin read-only wrapper; api/scorekeeper own aggregation |

## Test Validity Strategy (BINDING)

- Mock `api_request` (and thus api/scorekeeper) — NO live api/stage/dev/prod calls (CLAUDE.md testing convention).
- Per tool: assert the formatter maps `data.requests_count`/`from_date`/`to_date` into the model correctly; assert the echoed identifier matches the requested one.
- Error cases: mock `api_request` to raise / return 401/403/404/500; assert the tool surfaces a clear error via `http_error_message`, never a fabricated count.
- Default window: omit date params; assert the tool surfaces api's returned window (today).
- **Mock-reality rule:** do NOT mock away the api→formatter mapping being proven; a mock returning a specific int MUST produce exactly that `requests_count` in the tool output.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retrieve usage counts via natural language (Priority: P1)

As an API Monitoring user, I want to ask (through the MCP server) for my team, bucket, or test request usage over a date range, so I can understand my consumption in natural language without leaving the chat.

**Why this priority**: This is the entire purpose of the mcp change — the three new tools that surface usage to the agent. Without them the ticket delivers nothing on the consumer side.

**Independent Test**: Invoke each usage tool with a valid PAT and ids, mocking `api_request` to return a known `{data: {<id>, requests_count, from_date, to_date}, meta, error}`; assert the tool returns the exact `requests_count` and window.

**Acceptance Scenarios**:

1. **Given** a valid PAT and `team_uuid` for a team with 42 requests today, **When** the team usage tool is invoked with no date params, **Then** it returns `requests_count == 42` and `from_date`/`to_date` = today (api's default).
2. **Given** a valid PAT and `bucket_key`, **When** the bucket usage tool is invoked with `from`/`to`, **Then** it returns the api-provided `requests_count` for that bucket over the custom window.
3. **Given** a valid PAT, `bucket_key`, and `test_uuid`, **When** the test usage tool is invoked, **Then** it returns the api-provided `requests_count` for that test (sourced from the new api endpoint).

### User Story 2 - Clear, consistent errors (Priority: P2)

As a consumer of the tools, I want invalid requests and upstream failures to surface clear messages, so the agent/user understands what went wrong.

**Why this priority**: Required by the ticket AC on error handling; without it the agent cannot distinguish "no access" from "no data".

**Independent Test**: Mock `api_request` to return 401/403/404/500 or raise; assert each tool returns a clear error via `http_error_message`, never a fabricated count.

**Acceptance Scenarios**:

1. **Given** api returns 401/403 (auth/permission), **When** a usage tool is invoked, **Then** it surfaces a clear error message (not a count).
2. **Given** api is unreachable or returns 5xx, **When** a usage tool is invoked, **Then** it surfaces a clear error via `http_error_message`, never a fabricated/zero count masking the failure.
3. **Given** api returns a success envelope with `requests_count: 0` (no data in window), **When** a usage tool is invoked, **Then** it returns `requests_count == 0` (a legitimate value, not an error).

### User Story 3 - Existing tools and safety model unaffected (Priority: P2)

As an operator, I want the existing MCP tools and the read-only safety model to be unchanged, so adding usage tools is a safe, additive change.

**Why this priority**: Regression protection for a shipped MCP server.

**Independent Test**: Run the full `pytest` suite + `make lint`; confirm existing tools/managers are unchanged and the new tools are read-only.

**Acceptance Scenarios**:

1. **Given** the new usage tools are added, **When** the full test suite runs, **Then** all existing tool tests pass unchanged and the new usage tools expose no mutating action.

### Edge Cases

- **No data in window** → `requests_count` is `0` (api returns it; not an error).
- **Invalid/unknown team/bucket/test id** → api returns an error; the tool surfaces it via `http_error_message`.
- **Insufficient permission / AI-consent not granted** → api returns 403; the tool surfaces a clear message (no new auth path in mcp).
- **No date params** → window = today (api's default, inherited).
- **Range beyond 90 days** → api bounds it; the tool documents the 90-day max limit.
- **api/test endpoint not yet deployed** → tests mock `api_request`; runtime wiring is validated at integration time (the api endpoint ships in the same shard).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MCP server MUST add three new read-only tools — team usage, bucket usage, and test usage — that retrieve request counts via api's public usage endpoints.
- **FR-002**: The tools MUST be strictly read-only and MUST NOT expose any mutating action or mutate data.
- **FR-003**: Each tool MUST call api via the existing `api_request` client using a new endpoint constant in `src/config/defaults.py`, and MUST read the count from `data.requests_count` of api's response envelope (no re-aggregation or re-validation).
- **FR-004**: The tools MUST support the same optional date-range params as the api endpoints (`from`/`to`/`days`/`date`) and MUST inherit api's default-window behavior (no params → today, NOT a 90-day window); the maximum selectable lookback is 90 days.
- **FR-005**: Each tool's description MUST make the 90-day maximum lookback explicit so the agent/user understands older data is unavailable.
- **FR-006**: The tools MUST authenticate using the existing `BzmApimToken` (PAT) passed to `api_request`; api enforces RBAC and the AI-consent gate. The consumer MUST NOT add a new auth path.
- **FR-007**: Output formatting MUST follow existing conventions — a new formatter (`src/formatters/usage.py`) building a Pydantic model (`src/models/usage.py`), consistent with `format_results`/`TestResult`.
- **FR-008**: Error cases MUST surface clear messages via the existing `http_error_message` helper: invalid id, no data (count 0 is a valid success value), insufficient permission, and upstream (api) failure — never a fabricated count.
- **FR-009**: Tool naming and registration MUST follow the existing pattern (`register(mcp, token)` + `@mcp.tool(name=f"{TOOLS_PREFIX}_<resource>")`, `action`/`args`/`ctx` signature, telemetry span) and MUST be wired into `src/server.py` `register_tools`.
- **FR-010**: The change MUST be purely additive — existing tool managers, models, formatters, and registrations MUST remain unchanged.

### Key Entities

- **Usage count**: the integer number of API requests executed for a given team/bucket/test over a date window. Owned by scorekeeper, served by api, consumed read-only by the MCP tool. Keyed by the resource identifier.
- **Date window**: the `(from_date, to_date)` the count spans; default = today, max 90-day lookback (both governed by api).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can retrieve team, bucket, or test request usage through the MCP server in a single tool invocation, with the returned count matching api's response exactly.
- **SC-002**: 100% of the three usage tools present the same `requests_count`/`from_date`/`to_date` shape, consistent with the existing tool output conventions.
- **SC-003**: All error conditions (invalid id, no data, insufficient permission, api failure) return a clear message or a legitimate `0`, never a fabricated count — verified by dedicated tests.
- **SC-004**: The existing MCP tools and read-only safety model show zero change — verified by the full `pytest` suite and `make lint` passing.

## Assumptions

- api's three usage endpoints return identical field names (`requests_count`/`from_date`/`to_date`); the test endpoint ships in the same shard. (Risk: LOW; PROVEN by api spec FR-007 + existing marshal dicts.)
- The MCP tools reuse `BzmApimToken` + `api_request` with no new auth logic; api enforces the AI-consent gate. (Risk: LOW; PROVEN by existing tools + api/CLAUDE.md.)
- Three separate usage tools match existing granularity better than one parameterized tool. (Risk: LOW; PROCEED — matches `src/tools/*_manager.py`.)
- The 90-day max lookback is documented in tool descriptions; api enforces the bound. (Risk: MEDIUM; PROCEED — document in tool text, api is the enforcement point.)
- No-params default window = today, inherited from api. (Risk: LOW; PROVEN by api default-window behavior.)
- The api/test endpoint ships in the same shard; mcp tests mock `api_request` so they do not depend on the live endpoint; runtime wiring validated at integration time. (Risk: LOW; PROCEED.)

## Requirement Traceability Matrix

| AC / Requirement | Spec FR/SC | Plan section | Task IDs | Test | Impl files |
|---|---|---|---|---|---|
| Three read-only usage tools wired to api | FR-001, FR-003, FR-009 | plan §Design / §Change Map | (tasks) | `test_team_usage_returns_api_count`, `test_bucket_usage_returns_api_count`, `test_test_usage_returns_api_count` | `src/tools/usage_manager.py`, `src/config/defaults.py`, `src/server.py` |
| Read-only, no mutation | FR-002 | plan §Design | (tasks) | `test_usage_tools_are_read_only` | `src/tools/usage_manager.py` |
| Date params + default=today + 90-day max | FR-004, FR-005 | plan §Design | (tasks) | `test_usage_default_window_today` | `src/tools/usage_manager.py` |
| PAT auth / no new auth path | FR-006 | plan §Design | (tasks) | `test_usage_passes_token_no_new_auth` | `src/tools/usage_manager.py` |
| Output formatting/model | FR-007, SC-002 | plan §Design | (tasks) | `test_usage_response_shape` | `src/formatters/usage.py`, `src/models/usage.py` |
| Clear errors; count 0 valid | FR-008, SC-003 | plan §Failure Modes | (tasks) | `test_usage_api_error_surfaces_message`, `test_usage_no_data_returns_zero` | `src/tools/usage_manager.py` |
| requests_count faithful pass-through | FR-003, SC-001 | plan §Design | (tasks) | `test_usage_faithful_passthrough` (falsification) | `src/tools/usage_manager.py`, `src/formatters/usage.py` |
| Existing tools unchanged | FR-010, SC-004 | plan §Design | (tasks) | N/A — full test suite (pytest) | existing files unchanged |

## AC Verification Strategy

- AC "three read-only usage tools wired to api" (FR-001, FR-003, FR-009) → test_scenarios: test_team_usage_returns_api_count, test_bucket_usage_returns_api_count, test_test_usage_returns_api_count
- AC "read-only, no mutation" (FR-002) → test_scenarios: test_usage_tools_are_read_only
- AC "date params + default=today + 90-day max" (FR-004, FR-005) → test_scenarios: test_usage_default_window_today ; documentation: each tool description states the 90-day max lookback
- AC "PAT auth / no new auth path" (FR-006) → test_scenarios: test_usage_passes_token_no_new_auth
- AC "output formatting/model" (FR-007, SC-002) → test_scenarios: test_usage_response_shape
- AC "clear errors; count 0 valid" (FR-008, SC-003) → test_scenarios: test_usage_api_error_surfaces_message, test_usage_no_data_returns_zero
- AC "requests_count faithful pass-through" (FR-003, SC-001) → test_scenarios: test_usage_faithful_passthrough (falsification)
- AC "existing tools unchanged" (FR-010, SC-004) → not_verifiable: by a single unit test — verified by the full pytest suite + make lint passing with no change to existing managers/models/formatters
