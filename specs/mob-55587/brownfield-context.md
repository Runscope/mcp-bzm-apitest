# Brownfield Context: mcp-bzm-apim — MOB-55587

> Authoritative payload shapes below are taken from the Runscope public API parser
> (`tea-service/parsers/radar.py`) per the ticket's R&D note ("verify the public api
> code in the api service to come up with the payloads"). The MCP tool POSTs the
> *radar input* shape; tea-service translates it to internal templates.

## Semantic Disambiguation

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|---|---|---|---|---|
| `inbound` step | `step_type: "inbound"` (radar input) | Inbound HTTP webhook step | NEW (no MCP method yet) | tea-service/parsers/radar.py:_parse_inbound_template; src/tools/step_manager.py (no add_inbound_step) |
| `conditional-if` step | `step_type: "condition"` + `condition_type: "start"` (radar input) | If/else branching step | NEW (no MCP method yet) | tea-service/parsers/radar.py:647-656, :873-898 (_parse_condition_template default step_type="conditional") |
| `conditional-loop` step | `step_type: "conditional-loop"` + `condition_type: "start"` | Loop/while step | NEW (no MCP method yet) | tea-service/parsers/radar.py:657-666, :873 (_parse_condition_template step_type="conditional-loop") |
| `subtest` step | `step_type: "subtest"` (radar input) | Nested test execution step | NEW (no MCP method yet) | tea-service/parsers/radar.py:_parse_subtest_template |
| `modify/update step` | `PUT /buckets/{}/tests/{}/steps/{step_id}` | Update a single existing step | USE | api/resources/tests.py (TestStepInstance.put); src/tools/step_manager.py:_put_step |
| `change step order` / `reorder` | `PUT /buckets/{}/tests/{}/steps` (template_order list) | Reorder steps within a test | USE | api/resources/tests.py (TestStepList.put) |
| `add step` | `POST /buckets/{}/tests/{}/steps` | Append a new step to end of list | USE | api/resources/tests.py (TestStepList.post); src/tools/step_manager.py:add_request_step/add_pause_step |
| `condition` vs `conditional` | parser dispatch key is `"condition"` for if-branch | Wire key for if-step is `condition`, NOT `conditional` | USE (`condition`) | tea-service/parsers/radar.py:693 (`if step_type == "condition"`) |

## Code Search Coverage

| Search Target | Patterns Used | Files Matched | Files Read | Omitted / Reason |
|---|---|---|---|---|
| Step type enumeration (mcp-bzm-apim) | `step_type\|pause\|request\|inbound\|condition\|subtest` | ~8 in mcp-bzm-apim | src/tools/step_manager.py, src/models/step.py, src/formatters/step.py, tests/test_step_manager.py, src/common/api_client.py | integration/deploy configs — not load-bearing |
| Existing MCP step actions | `add_pause_step\|add_request_step\|add_.*_to_step\|_put_step` | step_manager.py | step_manager.py (full) | n/a |
| API step endpoints | `TestStepList\|TestStepInstance\|/steps` | api/resources/tests.py | api/resources/tests.py:502-700 (post/put/reorder) | other resources |
| Radar step-type input shapes | `_parse_.*_template\|condition_type\|flattened_steps` | tea-service/parsers/radar.py | radar.py:640-760, parser fns for condition/loop/inbound/subtest/pause | other parsers (websocket/mcp/ghost — out of scope) |
| conditional-loop reorder handling | `conditional-loop\|end_condition` in reorder | api/resources/tests.py | TestStepList.put region | n/a |

## Negative Constraints

None. All four new step types are NEW capability (no partial code, no colliding unrelated symbols). The existing `blazemeter_apitest_steps` tool already supports request + pause; the new types extend the same tool.

One naming caution (not a prohibition): the if-branch step's **radar input wire key is `step_type: "condition"`** (singular, no `-al`), while the ticket uses "conditional-if". The internal template `step_type` becomes `"conditional"`. New code MUST send `"condition"` as the radar input `step_type` for the if-step. The loop step's wire key IS `"conditional-loop"`.

## Binding Decisions

```yaml
approved_identifiers:
  - name: "inbound"
    reason: "new step type; radar input {step_type: inbound, token, isDynamicUrl}"
    source: "tea-service/parsers/radar.py:_parse_inbound_template"
  - name: "condition"
    reason: "radar input wire key for conditional-if step (condition_type: start/end)"
    source: "tea-service/parsers/radar.py:693"
  - name: "conditional-loop"
    reason: "radar input wire key for loop step (condition_type: start/end)"
    source: "tea-service/parsers/radar.py:657-666"
  - name: "subtest"
    reason: "new step type; radar input {step_type: subtest, test_uuid, trigger_token, environment_uuid, bucket_key, use_parent_environment, params?}"
    source: "tea-service/parsers/radar.py:_parse_subtest_template"
  - name: "update_step"
    reason: "generic single-step update via PUT /steps/{step_id}"
    source: "src/tools/step_manager.py:_put_step"
  - name: "reorder_steps"
    reason: "change step order via PUT /steps with template_order list"
    source: "api/resources/tests.py:TestStepList.put"
forbidden_identifiers: []
ambiguous_identifiers: []
```

## Runtime Data Availability Proof

None — the tool reads no runtime/cache/db/queue data whose lifecycle could invalidate a read. The one read path (`update_step` read-then-PUT) reads the current step from the live API immediately before writing it back; there is no cached or deleted intermediate.

| Runtime data | Written | Updated | Deleted / Expired | Planned read | Available at read time? | Evidence |
|---|---|---|---|---|---|---|
| N/A — no runtime/cache/db/queue reads | N/A | N/A | N/A | N/A — only a live API read in `update_step` | yes (read immediately precedes the PUT) | Source: src/tools/step_manager.py:255 (`_put_step`); FILE:src/tools/step_manager.py:84 (`read`) |

No row is marked unavailable or unproven; the tool is a stateless adapter (Source: src/tools/step_manager.py:78).

## Reference Implementation Trace

### Behavioral portrait (identifier-free)
A thin stateless adapter that: accepts an action + typed args → builds a JSON body keyed by a literal `step_type` → calls a single shared async HTTP function (`api_request`) with POST (append) or PUT (update/reorder) → returns a uniform structured envelope (`BaseResult`) produced by a formatter over the API response list. No execution, no persistence beyond the API call, no derived fields.

### Chosen analog — existing request + pause step support
Property-by-property: same protocol (HTTPS to Runscope API via `api_request`), same IO shape (request→response), same data (step config), same auth (Bearer, in `api_request` only), same lifecycle (per-call), same producer/consumer (MCP action → API). The 4 new step types are the closest cousins of request/pause; they differ only in the body dict's keys.

### Per-layer trace (file:line)

| Layer | File | Evidence |
|---|---|---|
| Tool registration + action dispatch | `src/tools/step_manager.py` | `register(mcp, token)` decorates one `steps()` handler `@mcp.tool(name="blazemeter_apitest_steps")`; dispatches on `action` via match/case; each case calls an `async def add_<type>_step(...)` |
| Builder methods | `src/tools/step_manager.py:add_pause_step`, `add_request_step` | Build a `*_step_body` dict with literal `step_type`; call `api_request(token, "POST", STEPS_ENDPOINT, result_formatter=format_steps, json=body)` |
| Update builder | `src/tools/step_manager.py:_put_step` | `api_request(token, "PUT", f"{STEPS_ENDPOINT}/{step_id}", result_formatter=format_steps, json=step)` |
| Model (response) | `src/models/step.py:TestStep` | Polymorphic `TestStep` with Optional fields for all step types incl. `step_type`, `method`, `url`, `duration`, `steps`, `comparison`, `left_value`, `right_value`, `test_uuid`, `bucket_key`; `step_type` description already lists request/pause/conditional/conditional-loop/subtest/inbound |
| Formatter | `src/formatters/step.py:format_steps` | `for step in steps: TestStep(**step).model_dump(by_alias=False)` — permissive, returns list of dicts |
| API client | `src/common/api_client.py:api_request` | Single async HTTP call site; Bearer auth; passes `json=body` via `**kwargs`; calls formatter on `response["data"]`; returns `BaseResult` |
| Tests | `tests/test_step_manager.py` | `test_add_pause_step`, `test_add_request_step` patch `src.tools.step_manager.api_request`, assert `result.error is None` and `result.result[0]` fields |

### SHAPE records (radar input the MCP tool POSTs)

Existing (analog):
- **request**: `{step_type: "request", method: str, url: str, headers?: Dict, note?: str, ...}`
- **pause**: `{step_type: "pause", duration: int}` — duration in **seconds, validated 1–180** (`_parse_pause_template`)

New (required, from tea-service parsers):
- **inbound**: `{step_type: "inbound", token: str, isDynamicUrl: bool}` — both required (`_parse_inbound_template`)
- **conditional-if**: `{step_type: "condition", condition_type: "start", comparison: str, left_value: str, right_value: str, steps?: [ ...nested steps... ]}` — `comparison` MUST be a key in `VALID_ASSERT_DEFS`; parser auto-appends `{step_type:"condition", condition_type:"end"}` (`radar.py:647-656`, `_parse_condition_template`)
- **conditional-loop**: `{step_type: "conditional-loop", condition_type: "start", comparison: str, left_value: str, right_value: str, steps?: [...]}` — same assertion contract; parser auto-appends `{step_type:"conditional-loop", condition_type:"end"}` (`radar.py:657-666`)
- **subtest**: `{step_type: "subtest", test_uuid: str, trigger_token: str, environment_uuid: str, bucket_key: str, use_parent_environment: bool, params?: List}` — first five required; `params` optional list (`_parse_subtest_template`)

### Pattern extractions — BINDING

- **Schema invariant**: each builder constructs a flat dict with a literal `step_type` key plus exactly the type-specific fields the tea-service parser reads; no extra keys. Mirror the `add_pause_step`/`add_request_step` body-building style. (`src/tools/step_manager.py:add_pause_step/add_request_step`)
- **Validator invariant**: server-side validation lives in the tea-service parser (missing-required-field errors, `comparison` ∈ `VALID_ASSERT_DEFS`, pause 1–180s). The MCP tool need not re-validate but MUST pass through all required fields; follow the existing lazy-validation precedent (request steps don't pre-validate URL). (`tea-service/parsers/radar.py` parser fns)
- **Wire-format invariant**: the if-step wire key is `step_type: "condition"` (not `"conditional"`); the loop wire key is `"conditional-loop"`; conditional/loop blocks carry `condition_type: "start"` and an optional `steps` array (end marker is auto-added by the parser — the tool MUST NOT send an explicit end block). (`tea-service/parsers/radar.py:647-666, 693`)
- **Registration invariant**: a new step type is wired end-to-end only when BOTH (a) a new `async def add_<type>_step(...)` builder exists AND (b) a new `case` is added to the `register()` match statement AND (c) the action appears in the tool's `description` string so the LLM can discover it. Missing any one leaves the action unreachable. (`src/tools/step_manager.py:register()`)
- **Endpoint invariant**: add → `POST /steps`; single-step modify → `PUT /steps/{step_id}` (full step dict); reorder → `PUT /steps` with a `template_order` list of `{id}` (nested `{id, steps:[...]}` only for `conditional` start blocks). (`api/resources/tests.py:TestStepList.post/put`, `TestStepInstance.put`)

## Cross-Repo Capability Analysis

| Candidate Service/API | Capability | Evidence | Decision | Rationale |
|---|---|---|---|---|
| Runscope public API (`api` service) step endpoints | add / modify / reorder test steps for all step types | api/resources/tests.py:TestStepList.post/put, TestStepInstance.put | USE | Canonical owner of test-step mutations; the MCP tool already uses it for request/pause and must continue to for the new types |
| tea-service radar parser | authoritative input shape + validation for every step type | tea-service/parsers/radar.py (parser fns) | USE (as contract reference) | Defines exactly which fields each step type requires; the MCP tool's payloads must conform |
| Local-only payload construction in the MCP tool | build and send bodies without a new service | src/tools/step_manager.py:add_pause_step | USE | No new service needed — this is the existing pattern; the tool just adds builders for the new types |

## Cross-Service Contract Verification

Static source evidence only; no live/dev/stage/prod endpoint was probed. Sibling-repo paths (`api/`, `tea-service/`) resolve in `$CODE_ROOT`, not in this worktree.

| API / Capability | Route / method / path evidence | Schema / serializer / response-fields evidence | Query / filter / ownership evidence | Client / auth / timeout / fallback evidence | Test / fixture evidence | Decision |
|---|---|---|---|---|---|---|
| Add step (POST) | route `POST /buckets/{}/tests/{}/steps` — Source: api/resources/tests.py:502 (`TestStepList.post`) | serializer: step dict parsed by the radar parser; required fields per type — Source: tea-service/parsers/radar.py:687 (`parse_radar_template`) | ownership: `api` owns the route; data owner is identity service — Source: api/resources/tests.py:519 | client: Bearer auth + httpx timeout inside `api_request`; error-handling fallback via `http_error_message` — Source: src/common/api_client.py:23 | existing contract tests/fixtures: FILE:tests/test_step_manager.py:51 (`test_add_pause_step`), tests/test_step_manager.py:70 (`test_add_request_step`) | USE |
| Modify step (PUT) | route `PUT /buckets/{}/tests/{}/steps/{step_id}` — Source: api/resources/tests.py:653 (`TestStepInstance.put`) | serializer: full step dict re-parsed by the radar parser — Source: tea-service/parsers/radar.py:687 | ownership: `api` owns the route — Source: api/resources/tests.py:653 | client: `api_request` PUT, Bearer auth, timeout, categorized-error fallback — Source: src/common/api_client.py:23 | new fixture to add — Source: tests/test_step_manager.py:51 (pattern to mirror) | USE |
| Reorder steps (PUT) | route `PUT /buckets/{}/tests/{}/steps` with a `template_order` list; 100-step cap; 400 on missing ids — Source: api/resources/tests.py:555 (`TestStepList.put`) | schema: list of `{id}` or `{id, steps:[...]}`; response is the reordered step fields — Source: api/resources/tests.py:589 | query/filter: reorder owns step `rank` ordering; data owner identity — Source: api/resources/tests.py:618 | client: `api_request` PUT, Bearer auth, timeout, fallback — Source: src/common/api_client.py:23 | new fixture to add — Source: tests/test_step_manager.py:70 (pattern to mirror) | USE |

## Dependency Contract Facts: runscope/api (public API) + runscope/tea-service (parser)

**Endpoints used by the step tool**

| Endpoint | Method | Input (radar) shape | Response | Evidence |
|---|---|---|---|---|
| `/buckets/{bucket}/tests/{test}/steps` | POST | one step dict (see SHAPE records) | 201 + full steps list | api/resources/tests.py:TestStepList.post |
| `/buckets/{bucket}/tests/{test}/steps/{step_id}` | PUT | full step dict | 200 + updated step(s) | api/resources/tests.py:TestStepInstance.put |
| `/buckets/{bucket}/tests/{test}/steps` | PUT | `template_order`: list of `{id}` (or `{id, steps:[...]}` for conditional start) | 200 + reordered steps | api/resources/tests.py:TestStepList.put |
| `/buckets/{bucket}/tests/{test}/steps/{step_id}` | GET | — | single step dict | src/tools/step_manager.py:read |
| `/buckets/{bucket}/tests/{test}/steps` | GET | — | list of step dicts | src/tools/step_manager.py (list) |

**Required fields per step type (parser-enforced)**

| Step Type (radar `step_type`) | Required fields | Optional | Evidence |
|---|---|---|---|
| request | method, url | headers, note, body, assertions, ... | tea-service/parsers/radar.py:_parse_request_template (REQUIRED_REQUEST_ATTRIBUTES = ["method","url"]) |
| pause | duration (int, 1–180 seconds) | — | tea-service/parsers/radar.py:_parse_pause_template |
| inbound | token, isDynamicUrl | — | tea-service/parsers/radar.py:_parse_inbound_template |
| condition (conditional-if) | condition_type; for "start": comparison, left_value, right_value | steps (nested) | tea-service/parsers/radar.py:_parse_condition_template |
| conditional-loop | condition_type; for "start": comparison, left_value, right_value | steps (nested) | tea-service/parsers/radar.py:_parse_condition_template(step_type="conditional-loop") |
| subtest | test_uuid, trigger_token, environment_uuid, bucket_key, use_parent_environment | params (list) | tea-service/parsers/radar.py:_parse_subtest_template |

**Behavioral facts**
- POST appends to the end of the step list; the parser auto-flattens a conditional/loop `start` + its `steps` + an auto-generated `end` marker (`radar.py:647-666`). The tool MUST NOT send an explicit `end` step.
- `comparison` is validated against `VALID_ASSERT_DEFS`; numeric comparisons set an `is_numeric` flag internally. The tool should pass the user's comparison token through and let the parser 400 on an invalid one (lazy validation).
- Reorder pairs conditional end-blocks automatically but the pairing branch matches only `step_type == "conditional"` (internal template type), so `conditional-loop` nesting in the reorder `template_order` is a KNOWN API limitation — see Assumption A-LOOP-REORDER.
- Total steps capped at 100 (both POST and reorder return 400 beyond that).

## Field/Metric Provenance Matrix

None applicable — the tool derives, aggregates, and renders no new downstream output field or metric; every response field passes through the `TestStep` model and `format_steps` formatter unchanged (Source: src/formatters/step.py:6). The matrix below is intentionally N/A.

| Output field / metric | Required semantics | Source of truth and object level | Endpoint / function | Source field path | Drill-down / nesting proof | Aggregation rule | Evidence | Falsification test |
|---|---|---|---|---|---|---|---|---|
| N/A — no derived output field or metric | N/A — no business meaning is computed | N/A — pass-through object level (step row) | N/A — `format_steps` formatter, no endpoint-derived metric | N/A — no source field path (fields copied verbatim) | N/A — no drill-down / nested read | N/A — no aggregation | Source: src/formatters/step.py:6 (`format_steps` copies fields 1:1) | N/A — no metric to falsify |

## Assumption Ledger

| ID | Assumption / Claim | Type | Evidence For | Evidence Against / Unknowns | Risk | Validation / Challenge Required | Decision |
|---|---|---|---|---|---|---|---|
| A-SHAPE | Radar input shapes for inbound/condition/conditional-loop/subtest are exactly the parser-read fields above | shape contract | tea-service/parsers/radar.py parser fns (read in full) | parser could change; version drift | medium | Contract-verification tasks in tasks.md assert each builder sends exactly the required keys | PROVEN |
| A-PAUSE-UNITS | Pause duration is seconds, 1–180 | unit/contract | _parse_pause_template validates `1 <= duration <= 180` | — | low | existing behavior; covered by existing tests | PROVEN |
| A-AUTO-END | Conditional/loop end block is auto-created by the parser; tool sends only the start + nested steps | API behavior | radar.py:647-666 appends end marker | — | low | test asserts a POSTed condition returns start+end in the steps list | PROVEN |
| A-LOOP-REORDER | Reorder's conditional end-pairing matches only `step_type=="conditional"`, so nesting a conditional-loop's children in the reorder list is unsupported by the API | API limitation | api/resources/tests.py TestStepList.put pairs only `conditional` | loop steps still reorderable as flat entries (by id), just not with nested `steps` | medium | Document limitation in plan; reorder_steps passes template_order through; test asserts flat-id reorder works | VALIDATE (documented constraint, not a tool defect) |
| A-SUBTEST-LAZY | subtest test_uuid/bucket_key are NOT validated at step-creation time by the tool | validation policy | existing add_request_step does not validate url; parser only checks presence, not existence | invalid uuid surfaces only at run time | low | Follow existing lazy-validation precedent; document in plan | PROVEN (matches brownfield precedent) |
| A-NO-MODEL-CHANGE | `TestStep` model + `format_steps` already handle all 6 step types | shape | src/models/step.py step_type description already lists all 6; Optional fields cover condition/subtest fields | some response fields (e.g. inbound token) may lack a model field → dropped from output, not an error | low | add a formatter round-trip test per new type; extend model only if a needed field is missing | VALIDATE |

## Boundary Compatibility Analysis

| Boundary | Producer / Source Shape | Consumer / Expected Shape | Compatibility Proof | Adapter / Mapping | Decision |
|---|---|---|---|---|---|
| MCP action args → builder (producer: typed kwargs; consumer: builder body dict) | producer/source shape: typed kwargs (token, isDynamicUrl, comparison, ...) | consumer contract: builder body dict with a literal step_type | compatible — builder maps kwargs→body keys 1:1 per SHAPE records — Source: src/tools/step_manager.py:113 (`add_request_step`) | adapter: none needed (direct mapping) | USE |
| builder body → API POST (producer: builder; consumer: parser) | producer/source shape: radar input dict the builder emits | consumer contract: tea-service parser required fields | compatible — parser reads exactly those keys; builder sends them — Source: src/tools/step_manager.py:104 (`add_pause_step` body) | adapter: none (pass-through) | USE |
| API response list → format_steps (producer: API; consumer: model) | producer/source shape: list of step dicts the API returns | consumer contract: `TestStep(**dict).model_dump()` | compatible but lossy for inbound/subtest — Pydantic drops unknown keys, so new fields need the model extension (equivalence via adapter = model extension) — Source: src/formatters/step.py:6; src/models/step.py:10 | adapter/mapping: extend `TestStep` (model change) | USE WITH ADAPTER (model extension) |

Context mapping: cross-service boundary MCP-tool → api service is **Conformist** — the api/tea-service owns the step contract and the MCP tool adopts it as-is; no anti-corruption layer is warranted because the tool is a thin adapter and the contract is already the tool's native shape.

## Design Alternatives Considered

| Option | What changes | Pros | Cons/Risks | Evidence | Decision |
|---|---|---|---|---|---|
| Per-step-type builder methods (add_inbound_step, add_condition_step, add_conditional_loop_step, add_subtest_step) + generic update_step + reorder_steps | 6 new async methods + register cases + description entries | Mirrors existing add_request_step/add_pause_step; self-documenting for the LLM; type-specific signatures | More methods + tests | Source: src/tools/step_manager.py:103 (`add_pause_step`), src/tools/step_manager.py:113 (`add_request_step`) | SELECTED |
| Single generic `add_step` accepting a raw step dict | one action, raw passthrough | Less code; future step types need no new action | Loses per-type LLM affordance; no typed args; harder to document; parser errors are the only guard | Source: src/tools/step_manager.py:331 (no existing generic action in `register`) | REJECTED |
| Modify via full test-steps PUT replace | read all steps, mutate one, PUT whole list | fewer endpoints | race window; higher latency; API already offers per-step PUT | Source: api/resources/tests.py:653 (`TestStepInstance.put`); src/tools/step_manager.py:255 (`_put_step`) | REJECTED |
| Reorder via per-step move_up/move_down | convenience swap actions | easier for simple cases | only adjacent moves; not arbitrary reorder; API's canonical op is full-list | Source: api/resources/tests.py:555 (`TestStepList.put` full list) | REJECTED (may add later) |

## Test Validity Strategy

- **Required test shape**: unit tests per new builder (mock `src.tools.step_manager.api_request`, assert the POST/PUT body sent and `result.error is None`), plus a formatter round-trip test per new type (ensure `TestStep(**resp)` doesn't drop required fields).
- **Mock-reality rule**: mocked API responses MUST include the fields the real API returns for each step type (`id`, `step_type`, and type-specific keys), so the formatter is exercised against a realistic shape — do NOT mock away `format_steps`.
- **Assumption-challenge cases**:
  - A-AUTO-END: `test_add_condition_step_returns_start_and_end` — POSTed condition yields both start and end entries (parser auto-end).
  - A-SHAPE (condition): `test_add_condition_step_sends_condition_wire_key` — asserts the body uses `step_type: "condition"` (NOT "conditional") and carries `condition_type: "start"`, comparison/left/right.
  - A-LOOP-REORDER: `test_reorder_steps_flat_ids` — flat-id reorder succeeds; a nested conditional-loop reorder is documented as unsupported (no test claims it works).
  - A-SUBTEST-LAZY: `test_add_subtest_step_does_not_prevalidate_test_uuid` — builder sends an arbitrary test_uuid without an extra existence check.
- **Evidence files to extend**: `tests/test_step_manager.py` (new test classes), `tests/conftest.py` (sample inbound/condition/loop/subtest API responses).

## Current State

### Relevant files
- `src/tools/step_manager.py` — `add_pause_step`/`add_request_step` builders, `_put_step`, `register()` match/case + tool description. No methods for inbound/condition/conditional-loop/subtest; no generic `update_step`; no `reorder_steps`.
- `src/models/step.py` — `TestStep` already enumerates all 6 step types in its `step_type` description and has Optional fields for condition/subtest.
- `src/formatters/step.py` — `format_steps` permissive round-trip.
- `src/common/api_client.py` — `api_request` single HTTP call site.
- `tests/test_step_manager.py` — existing `test_add_pause_step`, `test_add_request_step` patterns.
- `api/resources/tests.py` (sibling) — POST/PUT/reorder endpoints.
- `tea-service/parsers/radar.py` (sibling) — authoritative per-step-type input shapes.

### Root cause / gap
`blazemeter_apitest_steps` supports only `add_request_step` and `add_pause_step`. There are no builders, dispatch cases, or tool-description entries for the 4 new step types, no generic single-step update action, and no reorder action.

## Desired State Delta

| What | File | Change |
|------|------|--------|
| Add inbound step builder | src/tools/step_manager.py | `async def add_inbound_step(bucket_key, test_id, token, is_dynamic_url)` → body `{step_type:"inbound", token, isDynamicUrl}` POST |
| Add conditional-if builder | src/tools/step_manager.py | `async def add_condition_step(bucket_key, test_id, comparison, left_value, right_value, steps=None)` → body `{step_type:"condition", condition_type:"start", comparison, left_value, right_value, steps?}` POST |
| Add conditional-loop builder | src/tools/step_manager.py | `async def add_conditional_loop_step(...)` → body `{step_type:"conditional-loop", condition_type:"start", comparison, left_value, right_value, steps?}` POST |
| Add subtest builder | src/tools/step_manager.py | `async def add_subtest_step(bucket_key, test_id, test_uuid, trigger_token, environment_uuid, subtest_bucket_key, use_parent_environment, params=None)` → body with those keys POST |
| Add generic update action | src/tools/step_manager.py | `async def update_step(bucket_key, test_id, step_id, updates)` → read step, merge updates, `_put_step` |
| Add reorder action | src/tools/step_manager.py | `async def reorder_steps(bucket_key, test_id, step_order)` → `api_request("PUT", STEPS_ENDPOINT, json=step_order)` |
| Register new actions | src/tools/step_manager.py | new `case` branches + tool `description` entries for all 6 new actions |
| Extend tests | tests/test_step_manager.py | new test classes per builder + reorder + update + formatter round-trips |
| conftest fixtures | tests/conftest.py | sample API responses for inbound/condition/loop/subtest |
| Model (if needed) | src/models/step.py | extend `TestStep` only if a new-type response field is missing (e.g. inbound token/isDynamicUrl) |

## Files the planner must read for spec.md

- src/tools/step_manager.py
- src/models/step.py
- src/formatters/step.py
- tests/test_step_manager.py
- /home/jenkins/runscope/api/api/resources/tests.py (TestStepList/TestStepInstance)
- /home/jenkins/runscope/tea-service/tea_service/parsers/radar.py (parser fns)

## Planner Blockers

None blocking. Two items resolved confidence-first and recorded as assumptions:
- Conditional-loop reorder nesting is an API limitation (A-LOOP-REORDER) — documented as a known constraint; reorder_steps still supports flat-id reordering of all step types.
- Subtest existence validation is lazy (A-SUBTEST-LAZY) — matches the existing request-step precedent.

## overall_finding
brownfield
