# Implementation Plan: Usage-retrieval MCP tools (consumer)

**Branch**: `ai-mob-53921` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/mob-53921/spec.md`; brownfield research from `specs/mob-53921/brownfield-context.md`

## Summary

Add three new read-only MCP tools — team usage, bucket usage, and test usage — to the API Monitoring (Runscope) MCP server. Each tool calls one of api's public usage REST endpoints via the existing `api_request` client and formats the returned request count for the agent. The design mirrors the existing `ResultManager` tool pattern exactly (registration, api_request, formatter, Pydantic model, telemetry span, error helpers) and is purely additive. `api` owns all auth, AI-consent, aggregation, and date-range semantics; this consumer is a thin read-only wrapper.

## Non-Goals

- No change to `api` (the public usage endpoints live in the separate producer repo in this shard).
- No change to `scorekeeper`.
- No enforcement of the 90-day retention or window bounding (api/scorekeeper own that; this consumer documents the limit and passes date params through).
- No companion doc update to the MCP server's tool list (explicitly out of scope per the ticket).
- No UI change, no new auth path, no new HTTP client (reuse `api_request`), and no modification to existing tool managers/models/formatters.

## Technical Context

**Language/Version**: Python 3.11+ (MCP server; FastMCP via `mcp.server.fastmcp`)
**Primary Dependencies**: `mcp` (FastMCP), `httpx` (inside `api_request`), `pydantic` (response models); internal: `src/common/api_client.api_request`, `src/common/errors`, `src/common/telemetry`, `src/config/token.BzmApimToken`
**Storage**: N/A — no storage; usage counts fetched synchronously from api public REST
**Testing**: `pytest` + `unittest.mock` (`AsyncMock`); `pytest-asyncio` auto mode; `make test` / `make test-unit`; no live API calls
**Target Platform**: MCP server (stdio); distributed as a PyInstaller binary / Docker image
**Project Type**: MCP server (tool-manager architecture)
**Performance Goals**: one synchronous `api_request` per tool invocation; latency bounded by that single upstream call (same as existing read tools)
**Constraints**: read-only; no mutation; no new auth path; default window = today (inherited from api); 90-day maximum lookback; line length 108; max complexity 10
**Scale/Scope**: one new manager file (three tools), three endpoint constants, three models, three formatters, plus tests. No storage, no schema change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Domain-Scoped MCP Tools | PASS | New usage domain gets its own `UsageManager` under `src/tools/`; registers via `register()` + `@mcp.tool()`; existing managers untouched |
| II. Single API Client | PASS | All HTTP goes through `api_request` (`src/common/api_client.py`); the manager/formatter never call the API directly |
| III. Test-First (NON-NEGOTIABLE) | PASS | tasks.md writes failing tests first (mock `api_request` via `AsyncMock`); test files mirror source (`tests/test_usage_manager.py`); no live calls |
| IV. LLM-Friendly Error Handling | PASS | Errors via `http_error_message` / `UNEXPECTED_ERROR_MESSAGE` (`src/common/errors.py`); no raw status/trace/token in responses |
| V. Structured Pydantic Responses | PASS | Each tool returns `BaseResult`; formatters (`src/formatters/usage.py`) build `TeamUsage`/`BucketUsage`/`TestUsage` Pydantic models before returning |
| Security & Token Handling | PASS | `BzmApimToken` passed to `api_request`; Bearer applied only in `api_request`; no token in logs/responses |
| Code Quality & Style | PASS | new code under line length 108, complexity ≤ 10; `make lint`/`make format` |

**Result: PASS — no violations. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/mob-53921/
├── spec.md
├── brownfield-context.md
├── brownfield-context.meta.json
├── plan.md                  # This file
├── research.md              # Phase 0
├── data-model.md            # Phase 1
├── quickstart.md            # Phase 1
├── contracts/               # Phase 1 (tool contract)
├── checklists/requirements.md
└── tasks.md                 # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── config/
│   └── defaults.py          # ADD: TEAM_USAGE_ENDPOINT, BUCKET_USAGE_ENDPOINT, TEST_USAGE_ENDPOINT
├── models/
│   └── usage.py             # ADD (new file): TeamUsage, BucketUsage, TestUsage (extend BaseResult domain models)
├── formatters/
│   └── usage.py             # ADD (new file): format_team_usage, format_bucket_usage, format_test_usage
├── tools/
│   └── usage_manager.py     # ADD (new file): UsageManager + register(mcp, token) with 3 @mcp.tool usage tools
└── server.py                # MODIFY: register_tools() calls usage_manager.register(mcp, token)

tests/
└── test_usage_manager.py    # ADD (new file): mock api_request; count mapping, errors, default-window, falsification
```

**Structure Decision**: MCP server tool-manager architecture. All production changes are a new manager/model/formatter file trio plus three endpoint constants and one registration line in `src/server.py`. No existing files beyond `defaults.py` and `server.py` are modified; those two edits are additive.

## Design

### Tool surface (three read-only tools)

Three separate tools under `TOOLS_PREFIX` `blazemeter_apitest`, mirroring the existing `Team`/`Bucket`/`Test`/`Results` granularity (Design Alternatives SELECTED):

- `blazemeter_apitest_team_usage` — action `read`; args `{team_uuid, from?, to?, days?, date?}` → `GET /team/<team_uuid>/requests`
- `blazemeter_apitest_bucket_usage` — action `read`; args `{bucket_key, from?, to?, days?, date?}` → `GET /buckets/<bucket_key>/requests`
- `blazemeter_apitest_test_usage` — action `read`; args `{bucket_key, test_uuid, from?, to?, days?, date?}` → `GET /buckets/<bucket_key>/tests/<test_uuid>/requests`

Each tool description states: read-only; 90-day maximum lookback (older data unavailable); default window = today when no date params are given.

### Endpoint constants (BINDING — mirror defaults.py pattern)

```python
# src/config/defaults.py (ADD — match api route paths exactly)
TEAM_USAGE_ENDPOINT: str = "/team/{}/requests"
BUCKET_USAGE_ENDPOINT: str = "/buckets/{}/requests"
TEST_USAGE_ENDPOINT: str = "/buckets/{}/tests/{}/requests"
```

### Models (BINDING — extend BaseResult domain models, mirror src/models/result.py)

`TeamUsage`/`BucketUsage`/`TestUsage` Pydantic models with fields: `requests_count: int`, `from_date: str`, `to_date: str`, plus the identifier (`team_uuid` / `bucket_key` / `test_uuid`). The tool returns a `BaseResult` whose `result` is the formatted usage model (per Constitution Principle V).

### Manager + registration (BINDING — mirror ResultManager src/tools/result_manager.py)

```python
# src/tools/usage_manager.py (new) — shape mirrors result_manager.py
class UsageManager:
    def __init__(self, token, ctx):
        self.token = token
        self.ctx = ctx

    async def get_team_usage(self, team_uuid, params):
        return await api_request(self.token, "GET",
                                 TEAM_USAGE_ENDPOINT.format(team_uuid),
                                 result_formatter=format_team_usage, params=params)
    # get_bucket_usage(bucket_key, params) -> BUCKET_USAGE_ENDPOINT.format(bucket_key)
    # get_test_usage(bucket_key, test_uuid, params) -> TEST_USAGE_ENDPOINT.format(bucket_key, test_uuid)

def register(mcp, token):
    @mcp.tool(name=f"{TOOLS_PREFIX}_team_usage", description="...read-only; 90-day max lookback; default=today...")
    async def team_usage(action, args, ctx):
        mgr = UsageManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_team_usage", action, parent) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span, await mgr.get_team_usage(args["team_uuid"], _date_params(args)))
                    case _:
                        return BaseResult(error=f"Unknown action: {action}")
            except Exception as e:
                record_span_error(span, e)
                return BaseResult(error=http_error_message(e))
    # ...bucket_usage and test_usage registered the same way
```

`_date_params(args)` extracts the optional `from`/`to`/`days`/`date` keys and passes them through to api (api parses + defaults to today). Wire `register` into `src/server.py` `register_tools`.

### Faithful pass-through (BINDING — Field/Metric Provenance)

`requests_count` in the tool output = api response `data.requests_count` (the formatter maps it directly). The consumer does NOT re-aggregate, re-validate, or compute the count. A missing/0 count from api is surfaced as-is (0 is a legitimate value). scorekeeper's internal list-typed `test_id` is NOT exposed to the tool user.

### Data flow (single synchronous api call — NOT an N×M pattern)

Each tool invocation makes **exactly one** `api_request` to the corresponding api endpoint. There is **no loop and no nested fan-out** — api/scorekeeper do all aggregation server-side and return a single count. This is structurally identical to the existing read tools (e.g. `ResultManager.read`). **No N×M external-call pattern exists**, so no call-budget fan-out math is required.

```python
# single call, no loop:
params = _date_params(args)                       # optional from/to/days/date; omitted -> api defaults to today
resp = await api_request(token, "GET", ENDPOINT.format(ids),
                         result_formatter=format_resource_usage, params=params)
# resp.result[*].requests_count is api's data.requests_count, mapped faithfully by the formatter
```

## Performance Strategy

**No N×M external-call pattern is present.** Each usage tool issues a single `api_request` to api for the one requested resource; N=1, M=1, no nesting. api/scorekeeper perform the aggregation server-side. Latency/throughput match the existing read tools (e.g. ResultManager).

- **Call budget**: a single api call per tool invocation; no fan-out across days, tests, or buckets.
- **Timeout / deadline**: inherits `api_request`'s existing httpx timeout behavior (same as all existing tools); a multi-call deadline is not applicable.
- **Degradation**: on api error/unreachable, the tool returns a `BaseResult` with a clear `error` via `http_error_message` — never a fabricated or zero count masking the failure. A legitimate api `requests_count: 0` (no data) is surfaced as `0`.
- **No scaling concern**: the design adds no scaling or latency surface beyond the existing read tools; all performance characteristics are handled within this change, with nothing deferred.
- **Observability**: each tool invocation is wrapped in a `tool_span` (`src/common/telemetry.py`); errors recorded via `record_span_error` — on-call can observe failures/latency via existing telemetry.

## Failure Modes

| Condition | Behavior | Fallback value | Source of rule |
|---|---|---|---|
| api returns 401/403 (auth/permission) | `BaseResult.error` with a clear auth/permission message | no count | `http_error_message` (errors.py); api `@validate_authentication` |
| api returns 404 (unknown id) | `BaseResult.error` with a clear not-found message | no count | `http_error_message` |
| api unreachable / 5xx | `BaseResult.error` via `http_error_message`; never a fabricated/zero count | no count | Constitution IV; `src/common/errors.py` |
| api returns success with `requests_count: 0` (no data in window) | `BaseResult` with `requests_count == 0` (legitimate) | `0` | Field/Metric Provenance; faithful pass-through |
| unexpected non-HTTP error | `BaseResult.error = UNEXPECTED_ERROR_MESSAGE` | no count | Constitution IV |
| unknown action | `BaseResult.error = "Unknown action: <action>"` | no count | existing manager pattern |
| no date params | pass none; api defaults to today | window=today | api default-window behavior |

## Change Map

| ID | Path | Symbols | Change type | Reason | Requirement IDs |
|---|---|---|---|---|---|
| C-1 | `src/config/defaults.py` | `src/config/defaults.py::TEAM_USAGE_ENDPOINT`, `src/config/defaults.py::BUCKET_USAGE_ENDPOINT`, `src/config/defaults.py::TEST_USAGE_ENDPOINT` | add | endpoint constants matching api route paths | FR-003 |
| C-2 | `src/models/usage.py` | `src/models/usage.py::TeamUsage`, `src/models/usage.py::BucketUsage`, `src/models/usage.py::TestUsage` | add | Pydantic usage models (requests_count/from_date/to_date + identifier) | FR-007, SC-002 |
| C-3 | `src/formatters/usage.py` | `src/formatters/usage.py::format_team_usage`, `src/formatters/usage.py::format_bucket_usage`, `src/formatters/usage.py::format_test_usage` | add | map api `data.*` into usage models | FR-007 |
| C-4 | `src/tools/usage_manager.py` | `src/tools/usage_manager.py::UsageManager`, `src/tools/usage_manager.py::register` | add | manager + three read-only usage tools calling api_request | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-008, FR-009 |
| C-5 | `src/server.py` | `src/server.py::register_tools` | modify | wire `usage_manager.register(mcp, token)` | FR-009 |
| C-6 | `tests/test_usage_manager.py` | `tests/test_usage_manager.py::usage tests` | add | mock api_request; count mapping, errors, default-window, falsification, read-only | SC-001, SC-002, SC-003 |

No `delete` changes. Existing managers, models, formatters, and registrations are UNCHANGED (FR-010).

## Requirement Traceability Matrix

| AC / Requirement | Spec FR/SC | Change Map | Task (tasks.md) | Test | Impl files |
|---|---|---|---|---|---|
| Three read-only usage tools wired to api | FR-001, FR-003, FR-009 | C-1, C-4, C-5 | (tasks.md) | `test_team_usage_returns_api_count`, `test_bucket_usage_returns_api_count`, `test_test_usage_returns_api_count` | `src/tools/usage_manager.py`, `src/config/defaults.py`, `src/server.py` |
| Read-only, no mutation | FR-002 | C-4 | (tasks.md) | `test_usage_tools_are_read_only` | `src/tools/usage_manager.py` |
| Date params + default=today + 90-day max | FR-004, FR-005 | C-4 | (tasks.md) | `test_usage_default_window_today` | `src/tools/usage_manager.py` |
| PAT auth / no new auth path | FR-006 | C-4 | (tasks.md) | `test_usage_passes_token_no_new_auth` | `src/tools/usage_manager.py` |
| Output formatting/model | FR-007, SC-002 | C-2, C-3 | (tasks.md) | `test_usage_response_shape` | `src/formatters/usage.py`, `src/models/usage.py` |
| Clear errors; count 0 valid | FR-008, SC-003 | C-4 | (tasks.md) | `test_usage_api_error_surfaces_message`, `test_usage_no_data_returns_zero` | `src/tools/usage_manager.py` |
| requests_count faithful pass-through | FR-003, SC-001 | C-3, C-4 | (tasks.md) | `test_usage_faithful_passthrough` | `src/formatters/usage.py`, `src/tools/usage_manager.py` |
| Existing tools unchanged | FR-010, SC-004 | (none — additive) | (tasks.md) | N/A — full test suite (pytest) | existing files unchanged |

## Complexity Tracking

> No Constitution Check violations. This section intentionally left empty.
