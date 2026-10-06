# Phase 0 Research: Usage-retrieval MCP tools (consumer) — MOB-53921

All unknowns were resolved during the brownfield semantic-disambiguation gate (see `brownfield-context.md`). No open clarification markers remain; every item below is a settled decision.

## Decision: Three separate read-only usage tools wiring to api
- **Decision**: Add `blazemeter_apitest_team_usage`, `_bucket_usage`, `_test_usage` tools in a new `UsageManager`, each calling the respective api public usage endpoint via `api_request`.
- **Rationale**: The MCP server is a thin read-only wrapper over api's REST surface; usage counts are served by api (team/bucket exist; test is added in the same shard). Separate tools match the existing Team/Bucket/Test/Result granularity and MCP discoverability.
- **Alternatives considered**: one parameterized usage tool (rejected — no precedent, worse discoverability); extend existing CRUD managers (rejected — mixes analytics with resource ops); compute locally (rejected — api/scorekeeper own aggregation). See brownfield-context.md § Design Alternatives.

## Decision: Mirror ResultManager in every respect
- **Decision**: New endpoint constants in `defaults.py`; new Pydantic models in `models/usage.py`; new formatters in `formatters/usage.py` mirroring `format_results`; `register(mcp, token)` + `@mcp.tool` + `action`/`args`/`ctx` + `tool_span`; wire into `src/server.py`.
- **Rationale**: Reusing the proven pattern satisfies all five constitution principles and minimizes risk.

## Decision: Faithful pass-through of requests_count
- **Decision**: `requests_count` = api response `data.requests_count`; the formatter maps it directly; no re-aggregation/re-validation in the consumer.
- **Rationale**: api/scorekeeper are the source of truth; the consumer is a thin wrapper. A 0 count is a legitimate value.

## Decision: Default window = today, 90-day = max lookback
- **Decision**: No date params → the tool passes none; api defaults to today. 90 days is the maximum selectable lookback (documented in each tool description), not a default.
- **Rationale**: Inherited directly from api's default-window behavior (BucketRequestCount `if not args_dict: # today`); consistency across team/bucket/test.

## Decision: No new auth path
- **Decision**: Pass `BzmApimToken` (PAT) to `api_request`; api enforces RBAC and the AI-consent gate.
- **Rationale**: Existing tools do the same; the AI-consent gate lives in api. No consumer-side auth logic.

## Decision: Single synchronous call — no N×M
- **Decision**: Each tool invocation makes exactly one `api_request`; no loop/fan-out.
- **Rationale**: api/scorekeeper aggregate server-side; latency identical to existing read tools. No call-budget math required.

## Decision: Tests mock api_request (no live calls)
- **Decision**: Mock `api_request` via `AsyncMock`; assert count mapping, errors, default-window, and a faithful-passthrough falsification test.
- **Rationale**: Constitution III (test-first, no live calls); the api/test endpoint ships in the same shard, so runtime wiring is validated at integration time.
