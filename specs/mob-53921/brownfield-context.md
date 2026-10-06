# Brownfield Context: mcp-bzm-apim — MOB-53921

## Semantic Disambiguation

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|---|---|---|---|---|
| usage data retrieval (capability) | (none in mcp-bzm-apim) | — | NEW — no usage tools exist | no matches in src/tools/ |
| team-level usage tool | (none) | MCP tool to fetch team request counts | NEW | ticket AC; api endpoint `/team/<team_uuid>/requests` exists (api/resources/radar_results.py:777-872) |
| bucket-level usage tool | (none) | MCP tool to fetch bucket request counts | NEW | ticket AC; api endpoint `/buckets/<bucket_key>/requests` exists (api/resources/radar_results.py:875-986) |
| test-level usage tool | (none) | MCP tool to fetch test request counts | NEW | ticket AC; api endpoint `/buckets/<bucket_key>/tests/<test_uuid>/requests` NEW (api/specs/mob-53921/spec.md FR-001) |
| requests_count | `tests_count` (models/bucket.py:27 — count of tests, DIFFERENT domain); `requests` (models/result.py — per-request sub-object, DIFFERENT) | aggregate HTTP request count over a window | NEW (field name for usage models) | no existing usage-count field; `tests_count`/`requests` are unrelated concepts |
| get_team_usage / get_bucket_usage / get_test_usage | (none) | usage tool method names | NEW | no method naming collision in src/tools/ |
| TeamUsage / BucketUsage / TestUsage | (none) | Pydantic models for usage responses | NEW | no existing usage models in src/models/ |
| TEAM_USAGE_ENDPOINT / BUCKET_USAGE_ENDPOINT / TEST_USAGE_ENDPOINT | `TEAMS_ENDPOINT`, `BUCKETS_ENDPOINT`, `RESULTS_ENDPOINT` (different suffixes) | endpoint path constants | NEW | src/config/defaults.py has resource constants but none for usage |
| 90-day max lookback | (none) | maximum historical window | NEW (documented in tool descriptions) | api enforces; api spec FR-004/FR-005 |

## Code Search Coverage

| Search Target | Patterns Used | Files Matched | Files Read | Omitted/Reason |
|---|---|---|---|---|
| existing tool managers (analog) | `*_manager.py`, `class .*Manager`, `@mcp.tool`, `TOOLS_PREFIX` | 8 managers in src/tools/ | result_manager.py, team_manager.py, bucket_manager.py, test_manager.py, __init__.py | others (schedule/step/environment/version) are the same pattern — not re-read |
| usage identifiers | `usage`, `requests_count`, `request_count`, `get_.*_usage`, `Usage` | 0 in src/ (2 unrelated: tests_count, result.requests) | models/bucket.py, models/result.py | confirmed no usage concept exists |
| endpoint constants | `_ENDPOINT`, `defaults.py` | src/config/defaults.py | defaults.py | no usage endpoint constants |
| api_request client | `api_request`, `src/common/api_client` | api_client.py + all managers | api_client.py (23-72) | — |
| formatters / models | `format_`, `src/formatters/`, `src/models/` | formatters + models dirs | result.py, team.py, bucket.py formatters; result.py/team.py/__init__.py models | others same pattern |
| api usage endpoints (cross-repo) | `TeamRequestCount`, `BucketRequestCount`, `/requests` | api/resources/radar_results.py, api/routes.py | radar_results.py:729-986, routes.py:64-65 | — |
| api test endpoint (new, cross-repo) | `TestRequestCount`, api planner artifacts | api/specs/mob-53921/spec.md, plan.md | spec.md, plan.md | — |

## Negative Constraints

None. No symbols are forbidden. The change is purely additive — three new tools, no refactor of existing managers. (Note: `tests_count` in models/bucket.py and `requests` in models/result.py are unrelated domains; do not conflate the new `requests_count` usage field with them.)

## Binding Decisions

```yaml
approved_identifiers:
  - name: UsageManager (or TeamUsageManager/BucketUsageManager/TestUsageManager)
    reason: "new manager(s) for usage tools; mirror ResultManager/BucketManager class pattern"
    files:
      - path: "src/tools/usage_manager.py"
        usage: "new manager class(es) with get_team_usage/get_bucket_usage/get_test_usage methods"
    source: "src/tools/result_manager.py (analog); ticket MOB-53921"
  - name: "TEAM_USAGE_ENDPOINT / BUCKET_USAGE_ENDPOINT / TEST_USAGE_ENDPOINT"
    reason: "endpoint path constants for the three api usage endpoints; mirror existing *_ENDPOINT constants"
    files:
      - path: "src/config/defaults.py"
        usage: "new endpoint constants matching api route paths"
    source: "api/routes.py:64-65 (team/bucket paths); api/specs/mob-53921 (test path)"
  - name: "TeamUsage / BucketUsage / TestUsage"
    reason: "Pydantic models for usage responses; fields requests_count/from_date/to_date + identifier"
    files:
      - path: "src/models/usage.py"
        usage: "new model classes mirroring models/result.py pattern"
    source: "api response contract {data:{<id>, requests_count, from_date, to_date}, meta, error}"
  - name: "format_team_usage / format_bucket_usage / format_test_usage"
    reason: "formatters mirroring src/formatters/result.py format_* pattern"
    files:
      - path: "src/formatters/usage.py"
        usage: "format api usage response into List[UsageModel]"
    source: "src/formatters/result.py:6-26"
forbidden_identifiers: []
ambiguous_identifiers:
  - name: "one parameterized UsageManager vs three separate managers"
    reason: "existing code has separate single-resource managers; a parameterized manager has no precedent"
    resolution: "SELECTED three separate usage tools (matching existing Team/Bucket/Test/Result granularity); may share one UsageManager class file but expose three distinct MCP tools"
    risk: "LOW — design choice; both are implementable; separate tools match conventions and MCP discoverability"
    source: "src/tools/*_manager.py (separate single-resource managers); CLAUDE.md tool list"
```

## Runtime Data Availability Proof

| Runtime Data | Written | Updated | Deleted / Expired | Planned Read | Available at Read Time? | Evidence | Safer Alternative |
|---|---|---|---|---|---|---|---|
| Team usage counts | scorekeeper worker increments per-team daily Redis counters on every request (via api) | counters incremented in place | governed by Redis TTL ops config; not deleted within read window | mcp tool calls api `GET /team/<team_uuid>/requests` synchronously at tool-invocation time | YES | api/resources/radar_results.py:777-872 (TeamRequestCount) + 353-374 (_get_bucket_usage proxy) | None — synchronous upstream call |
| Bucket usage counts | scorekeeper worker increments per-bucket counters (via api) | counters incremented in place | Redis TTL ops config | mcp tool calls api `GET /buckets/<bucket_key>/requests` synchronously | YES | api/resources/radar_results.py:875-986 (BucketRequestCount) | None — synchronous upstream call |
| Test usage counts | scorekeeper worker increments per-test daily counters (via api's NEW TestRequestCount) | counters incremented in place | Redis TTL ops config (ops dependency; a missing day contributes 0) | mcp tool calls api `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` synchronously | YES | api/specs/mob-53921/spec.md § Dependency Contract Facts; api/specs/mob-53921/plan.md Change Map | None — synchronous upstream call |

All three are available synchronously via api REST at tool-invocation time — there is NO deleted-before-read hazard in the consumer: the consumer makes a blocking HTTP call and formats whatever api returns. The 90-day retention is an api/scorekeeper ops concern already documented in the api planner artifacts (api degrades gracefully, a missing day → 0). From the consumer's perspective availability is YES.

## Cross-Repo Capability Analysis

| Candidate | Capability | Evidence | Decision | Rationale |
|---|---|---|---|---|
| api `GET /team/<team_uuid>/requests` (TeamRequestCount) | team-level request count over a window | api/resources/radar_results.py:777-872; api/routes.py:64-65 | USE | already public; the team usage tool wires directly to it |
| api `GET /buckets/<bucket_key>/requests` (BucketRequestCount) | bucket-level request count over a window | api/resources/radar_results.py:875-986; api/routes.py:64-65 | USE | already public; the bucket usage tool wires directly to it |
| api `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` (TestRequestCount, NEW) | test-level request count over a window | api/specs/mob-53921/spec.md FR-001; api/specs/mob-53921/plan.md Change Map C-2/C-3 | USE | the new public endpoint the sibling api repo adds in this same ticket; the test usage tool wires to it |
| compute usage inside mcp from other data | — | — | DO NOT USE | the MCP server is a thin read-only wrapper; api/scorekeeper own aggregation |

## Cross-Service Contract Verification

All three endpoints are verified STATICALLY (no live probes):

- **Route/method:** team `GET /team/<team_uuid>/requests` + bucket `GET /buckets/<bucket_key>/requests` registered at api/routes.py:64-65; test `GET /buckets/<bucket_key>/tests/<uuid:test_uuid>/requests` added per api/specs/mob-53921/plan.md Change Map C-3.
- **Response schema:** all three via `@api_marshal` → `{data: {...}, meta: {status}, error}`. Field names requests_count/from_date/to_date confirmed in bucket_count_fields/team_count_fields (api/resources/radar_results.py:729-746) and the new test_request_count_fields (api/specs/mob-53921/plan.md C-1).
- **Date params:** `from`/`to`/`days`/`date`; no params → today (NOT 90 days); 90-day maximum lookback (api/resources/radar_results.py:895-945; api/specs/mob-53921/spec.md FR-004).
- **Query/filter/ownership:** scorekeeper OWNS the usage counters (source of truth); api is the query/filter owner for the public usage surface — it parses the `from`/`to`/`days`/`date` filters and owns the routes. The consumer neither filters nor owns data; it passes the identifier + date filters through. Evidence: api/resources/radar_results.py:895-945 (query-param filtering); scorekeeper/activity/resources.py:129-152 (counter ownership).
- **Client/auth:** mcp passes `BzmApimToken` (PAT) via `api_request` (src/common/api_client.py:23-72); api enforces `@validate_authentication` + `bucket_for_user` + the existing `bzm-apitest-mcp` AI-consent gate — no new auth path in the consumer (api/specs/mob-53921/spec.md FR-006; api/CLAUDE.md).
- **Tests/fixtures:** mcp tests mock `api_request` (tests/test_*_manager.py pattern; tests/conftest.py); no live api calls.

## Dependency Contract Facts: api

**Consumed endpoints (all return the standard `{data, meta, error}` envelope):**

| Endpoint | Method / Path | Response `data` fields | Status |
|---|---|---|---|
| Team usage | `GET /team/<team_uuid>/requests` | `team_uuid`, `requests_count` (int), `from_date` (str "YYYY-MM-DD"), `to_date` (str) (+ team metadata not needed) | EXISTS — api/resources/radar_results.py:777-872 |
| Bucket usage | `GET /buckets/<bucket_key>/requests` | `bucket_key`, `requests_count` (int), `from_date`, `to_date` | EXISTS — api/resources/radar_results.py:875-986 |
| Test usage | `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` | `test_uuid`, `requests_count` (int), `from_date`, `to_date` | NEW — api/specs/mob-53921/spec.md FR-001/FR-007 |

**Date-param contract (all three):** optional `from`/`to`/`days`/`date`; no params → TODAY (not 90 days); 90-day maximum lookback (older data unavailable).
**Auth contract (all three):** PAT via `@validate_authentication`; `bucket_for_user` for bucket/test; existing AI-consent gate; no new auth path.
**Binding:** the consumer reads `data.requests_count` (int), `data.from_date`, `data.to_date`, and the resource identifier from the envelope. It does NOT re-aggregate or re-validate counts — api is the source of truth. `test_id` (scorekeeper's internal list-typed param) is NOT exposed to the MCP tool user; the tool takes `team_uuid` / `bucket_key` / `test_uuid` + optional date params.

## Field/Metric Provenance Matrix

| Output Field / Metric | Required Semantics | Source of Truth | Object Level | Source Endpoint | Source Field Path | Drill-down / Nesting | Aggregation Rule | 90-day Window | Evidence | Falsification Test |
|---|---|---|---|---|---|---|---|---|---|---|
| team usage `requests_count` | total HTTP requests for the team in window | api TeamRequestCount (proxies scorekeeper) | team aggregate | `GET /team/<team_uuid>/requests` | `data.requests_count` | none — flat single-level response, no nested drill-down | done by api/scorekeeper (consumer does not aggregate) | default=today; 90-day max | api/resources/radar_results.py:777-872 | mock api_request → `data.requests_count: 0`; assert tool reports 0, not another team's count |
| bucket usage `requests_count` | total HTTP requests for the bucket in window | api BucketRequestCount | bucket aggregate | `GET /buckets/<bucket_key>/requests` | `data.requests_count` | none — flat single-level response, no nested drill-down | done by api/scorekeeper (consumer does not aggregate) | default=today; 90-day max | api/resources/radar_results.py:875-986 | mock api_request → specific int; assert tool reports exactly that |
| test usage `requests_count` | total HTTP requests for the test in window | api TestRequestCount (NEW) | test aggregate | `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` | `data.requests_count` | none — flat single-level response, no nested drill-down | done by api/scorekeeper (consumer does not aggregate) | default=today; 90-day max | api/specs/mob-53921/spec.md FR-001 | mock api_request → `data.requests_count: 42` for the requested test; assert tool reports 42 (the requested-test-only mapping is proven in api's own test suite, not re-done here) |
| `from_date` / `to_date` (all tools) | the window the count spans | api query-param parsing | request context | all three endpoints | `data.from_date` / `data.to_date` | none — flat single-level | N/A | default=today; 90-day max | api/resources/radar_results.py:895-945 | omit date params; assert tool surfaces api's returned from_date/to_date (today) |
| resource identifier (team_uuid/bucket_key/test_uuid) | which resource the count belongs to | api route param echoed in response | identifier | all three endpoints | `data.<identifier>` | none — flat single-level | identifier only | n/a | api/routes.py:64-65 | assert echoed identifier matches the requested one |

Falsification note: the "requests_count maps to the requested test only" invariant is proven in api's own test suite (api's `test_test_request_count_maps_requested_test_only`). The consumer's falsification tests assert the tool faithfully surfaces `data.requests_count` from the mocked api response (no silent drop/placeholder), and that a non-matching mock does not fabricate a value.

## Assumption Ledger

| ID | Assumption | Type | Evidence For | Evidence Against / Unknowns | Risk | Validation Required | Decision |
|---|---|---|---|---|---|---|---|
| A1 | Three separate usage tools match existing tool granularity better than one parameterized tool | Design pattern | existing Team/Bucket/Test/Result managers are separate single-resource classes (src/tools/) | a parameterized tool would be more compact | LOW | confirm no parameterized multi-resource precedent | PROCEED — three separate tools |
| A2 | api's three usage endpoints return identical field names (requests_count/from_date/to_date) | API contract | api/specs/mob-53921/spec.md FR-007 + Field Semantics; bucket_count_fields/team_count_fields (api/resources/radar_results.py:729-746) | field names could drift per endpoint | LOW | read the api marshal dicts + the new test_request_count_fields in the api plan | PROVEN — api spec guarantees consistency |
| A3 | mcp usage tools reuse BzmApimToken + api_request with no new auth logic | Auth architecture | all existing tools use BzmApimToken + api_request; api enforces ai_consent (api/CLAUDE.md) | — | LOW | confirm api side enforces the gate; mcp just passes the PAT | PROVEN — no new auth path |
| A4 | usage formatters follow the existing `format_<resource>` → List[Model] pattern | Code pattern | src/formatters/result.py:6-26; team.py; bucket.py | — | LOW | mirror an existing formatter | PROVEN |
| A5 | new endpoint constants in defaults.py match api route paths exactly | Config | api/routes.py:64-65 (team/bucket paths); new test path from api plan | constant paths could diverge | LOW | copy the exact api route paths into defaults.py | PROVEN — route paths are the public contract |
| A6 | 90-day max lookback is documented in tool descriptions; not enforced in mcp (api gates it) | Operational boundary | api enforces via date-range logic (api spec FR-004/FR-005) | mcp could allow unbounded input | MEDIUM | document "90-day max lookback" in each tool description, matching api wording | PROCEED — document in tool text; api is the enforcement point |
| A7 | no-params default window = today (not 90 days), inherited from api | Date default | api/resources/radar_results.py:895-945 (`if not args_dict: # today`); api spec FR-004 | — | LOW | document default=today in tool descriptions | PROVEN |
| A8 | the test endpoint will exist in api by implementation time (same shard) | Cross-repo sequencing | api repo is the producer in this same ticket; api plan Change Map C-2/C-3 add it | api work could lag | LOW | task-decomposer/implementer sequence api before/with mcp; mcp tests mock api so they do not depend on the live endpoint | PROCEED — mcp tests mock api; runtime wiring validated at integration time |

No HIGH/CRITICAL risks. All MEDIUM items are documentation/sequencing, resolved by PROCEED with a concrete action.

## Boundary Compatibility Analysis

**Shape table — producer (api) → consumer (mcp formatter):**

| Boundary | Producer / Source Shape | Consumer / Helper Expected Shape | Compatibility Decision | Adapter / Mapping | Evidence |
|---|---|---|---|---|---|
| api response → mcp usage formatter | `{data: {<id>, requests_count:int, from_date, to_date}, meta:{status}, error}` | formatter reads `data.requests_count`/`data.from_date`/`data.to_date`/`data.<id>` → `List[UsageModel]` | compatible (direct field map) | `format_*_usage` maps `data.*` into a Pydantic model, mirroring `format_results` | src/formatters/result.py:6-26; api/specs/mob-53921/spec.md FR-007 |
| mcp request → api | tool params team_uuid/bucket_key/test_uuid + optional from/to/days/date | api route path params + query params | compatible | `api_request(token, "GET", ENDPOINT.format(ids), params={date params})` | src/common/api_client.py:23-72; api/routes.py:64-65 |

**Context-mapping table (cross-service):**

| Upstream service | Downstream service | Pattern | Contract owner | Translation needed | Failure mode |
|---|---|---|---|---|---|
| api (public usage endpoints) | mcp-bzm-apim (usage tools) | Open Host Service / Published Language | api publishes the `{data, meta, error}` usage contract; mcp conforms | none — mcp conforms to the published envelope and field names | if api/test endpoint is unavailable, `api_request` surfaces the HTTP error via `http_error_message`; the tool returns a clear error, never a fabricated count |

The consumer is a **Conformist / Published-Language** consumer of api's Open Host Service — it adopts api's envelope and field names as-is, with a thin formatter adapter into Pydantic models. No ACL needed; api is a stable published interface.

## Design Alternatives Considered

| Option | What changes | Decision | Rationale / Evidence |
|---|---|---|---|
| Three separate usage tools (team/bucket/test), each a focused MCP tool | add 3 tool registrations + 3 manager methods | **SELECTED** | matches existing granularity (separate Team/Bucket/Test/Result tools); best MCP discoverability. Evidence: src/tools/*_manager.py; CLAUDE.md tool list |
| One parameterized usage tool (resource_type arg) | single tool dispatching on type | REJECTED | no precedent in the codebase; worse discoverability; higher cognitive load. Evidence: existing managers are single-resource |
| Extend existing TeamManager/BucketManager/TestManager with usage methods | add usage to CRUD managers | REJECTED | mixes analytics with resource CRUD; violates separation of concerns. Evidence: existing managers scoped to resource ops |
| Compute usage locally in mcp | aggregate from other data | REJECTED | mcp is a thin read-only wrapper; api/scorekeeper own aggregation. Evidence: all existing tools proxy api |

## Test Validity Strategy

- Mock `api_request` (and thus api/scorekeeper) — NO live api/stage/dev/prod calls (CLAUDE.md testing convention).
- Per tool: assert the formatter maps `data.requests_count`/`from_date`/`to_date` into the model correctly; assert the echoed identifier matches the requested one.
- Error cases: mock api_request to raise / return 401/403/404/500; assert the tool surfaces a clear error via `http_error_message`, never a fabricated count.
- Date defaults: omit date params; assert the tool surfaces api's returned window (today) — consistent with api's default=today.
- Mock-reality rule: do NOT mock away the api→formatter mapping being proven; a mock returning a specific int must produce exactly that `requests_count` in the tool output (no placeholder/non-empty-only assertions).

## Current State

### Relevant files (the tool-manager pattern to mirror)
- `src/tools/result_manager.py` (ResultManager — primary read-only analog: registration, api_request call, formatter, model, telemetry, errors)
- `src/tools/team_manager.py`, `src/tools/bucket_manager.py`, `src/tools/test_manager.py` (simpler single-resource managers)
- `src/tools/__init__.py` (register_tools — where managers are wired)
- `src/common/api_client.py` (`api_request` signature + error handling)
- `src/common/errors.py` (`http_error_message`, `UNEXPECTED_ERROR_MESSAGE`)
- `src/common/telemetry.py` (`tool_span`, `check_result_error`, `record_span_error`)
- `src/config/defaults.py` (endpoint constants + `TOOLS_PREFIX`)
- `src/formatters/result.py` (formatter pattern)
- `src/models/__init__.py` (BaseResult), `src/models/result.py` (model pattern)
- `tests/test_*_manager.py`, `tests/conftest.py` (test + mock fixtures)

### Root cause / gap
No usage tools exist in mcp-bzm-apim. The capability is entirely new; nothing to refactor. Three new tools must be added mirroring the proven ResultManager pattern.

## Desired State Delta

| What | File | Change |
|---|---|---|
| New endpoint constants | `src/config/defaults.py` | add `TEAM_USAGE_ENDPOINT`, `BUCKET_USAGE_ENDPOINT`, `TEST_USAGE_ENDPOINT` matching api route paths |
| New usage models | `src/models/usage.py` (new) | `TeamUsage`, `BucketUsage`, `TestUsage` Pydantic models: `requests_count` (int), `from_date` (str), `to_date` (str), + identifier |
| New formatters | `src/formatters/usage.py` (new) | `format_team_usage`, `format_bucket_usage`, `format_test_usage` mirroring `format_results` |
| New manager + tools | `src/tools/usage_manager.py` (new) | `UsageManager` with `get_team_usage`/`get_bucket_usage`/`get_test_usage`; register 3 MCP tools via `TOOLS_PREFIX` |
| Tool registration | `src/tools/__init__.py` | import + call `register_usage_manager` in `register_tools()` |
| Tests | `tests/test_usage_manager.py` (new) | unit tests mocking `api_request`; error cases; falsification (faithful `requests_count` pass-through) |

## Files the planner must read for spec.md
- api contract (cross-repo): api/specs/mob-53921/spec.md, api/specs/mob-53921/plan.md; api/resources/radar_results.py:729-986; api/routes.py:64-65
- mcp (to mirror): CLAUDE.md, README.md, src/tools/result_manager.py, src/tools/__init__.py, src/common/api_client.py, src/common/errors.py, src/common/telemetry.py, src/config/defaults.py, src/formatters/result.py, src/models/__init__.py + result.py, tests/conftest.py

## Planner Blockers

None. All three api endpoints are available or committed in the same shard; naming is clear (zero collisions); token auth is reusable; formatter/model/telemetry patterns are proven.

## overall_finding

brownfield
