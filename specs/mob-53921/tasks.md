# Tasks: Usage-retrieval MCP tools (consumer) — MOB-53921

**Feature dir**: `specs/mob-53921` | **Branch**: `ai-mob-53921`
**Tech**: Python 3.11+, FastMCP; `pytest` + `unittest.mock` (`AsyncMock`), `pytest-asyncio` auto mode; lint flake8 + black + isort (`make lint`). Test-first per Constitution III (mock `api_request`; no live calls).

All production changes: new `src/tools/usage_manager.py`, `src/models/usage.py`, `src/formatters/usage.py`, additive edits to `src/config/defaults.py` and `src/server.py`; tests in `tests/test_usage_manager.py`. Existing managers/models/formatters MUST remain unchanged. Each task names the acceptance criteria it serves.

## Phase 1: Setup

- [ ] T001 (baseline) Confirm the worktree is green BEFORE changes: run `make lint` and `make test-unit` to establish a passing baseline. Serves: FR-010, SC-004.

## Phase 2: Foundational (blocking prerequisites)

- [ ] T002 (AC: FR-003) Read the api dependency contract: `specs/mob-53921/brownfield-context.md` Dependency Contract Facts and the api planner artifacts (`api/specs/mob-53921/spec.md`, `plan.md`) + `api/resources/radar_results.py:729-986` + `api/routes.py:64-65`. Confirm the three endpoint paths, the `{data:{<id>, requests_count, from_date, to_date}, meta, error}` envelope, the `from`/`to`/`days`/`date` params with default=today and 90-day max. Do not call live api. Serves: FR-003, FR-004.
- [ ] T003 (AC: FR-001) Read the reference analog `src/tools/result_manager.py`, `src/common/api_client.py`, `src/common/errors.py`, `src/common/telemetry.py`, `src/formatters/result.py`, `src/models/__init__.py`, and `src/server.py` register_tools to lock the manager/formatter/model/registration pattern the new tools must mirror. Serves: FR-007, FR-009.
- [ ] T004 (AC: FR-003) Add the three endpoint constants to `src/config/defaults.py`: `TEAM_USAGE_ENDPOINT = "/team/{}/requests"`, `BUCKET_USAGE_ENDPOINT = "/buckets/{}/requests"`, `TEST_USAGE_ENDPOINT = "/buckets/{}/tests/{}/requests"` (match api route paths exactly). Serves: FR-003.

## Phase 3: User Story 1 — Retrieve usage counts (Priority: P1)

**Goal**: three read-only usage tools (team/bucket/test) return the api-provided request count.
**Independent test criteria**: invoking each tool with mocked `api_request` returns the exact `requests_count` from the mocked api response.

### Tests for User Story 1 (write first — red before green; mock api_request via AsyncMock)

- [ ] T005 [P] [US1] (AC: FR-001, FR-003, SC-001) Add `test_team_usage_returns_api_count` in `tests/test_usage_manager.py`: mock `api_request` to return a `BaseResult` whose result has `requests_count=42`; invoke the team usage tool with a valid token and `team_uuid`; assert the tool output `requests_count == 42` and the echoed `team_uuid` matches.
- [ ] T006 [P] [US1] (AC: FR-001, FR-003, SC-001) Add `test_bucket_usage_returns_api_count` in `tests/test_usage_manager.py`: same shape for the bucket usage tool via `bucket_key`.
- [ ] T007 [P] [US1] (AC: FR-001, FR-003, SC-001) Add `test_test_usage_returns_api_count` in `tests/test_usage_manager.py`: same shape for the test usage tool via `bucket_key` + `test_uuid`.
- [ ] T008 [P] [US1] (AC: FR-007, SC-002) Add `test_usage_response_shape` in `tests/test_usage_manager.py`: assert each tool returns a `BaseResult` whose result carries exactly `requests_count`/`from_date`/`to_date` + identifier (no fabricated fields; no `tests_count`/`result.requests` conflation).
- [ ] T009 [P] [US1] (AC: FR-003, SC-001) Add `test_usage_faithful_passthrough` (FALSIFICATION) in `tests/test_usage_manager.py`: mock `api_request` to return `requests_count=7`; assert the tool reports exactly 7 (not a placeholder/non-empty-only assertion); a mock returning a different value must produce that exact different value — the tool must NOT re-aggregate or fabricate.
- [ ] T010 [P] [US1] (AC: FR-004) Add `test_usage_default_window_today` in `tests/test_usage_manager.py`: invoke a usage tool with no date params; assert no date params are forced by the tool (api defaults to today); invoke with `from`/`to` and assert they are passed through to `api_request` params.
- [ ] T011 [P] [US1] (AC: FR-006) Add `test_usage_passes_token_no_new_auth` in `tests/test_usage_manager.py`: assert the tool passes the provided `BzmApimToken` to `api_request` and adds no auth header/logic itself.

### Implementation for User Story 1

- [ ] T012 [US1] (AC: FR-007, SC-002) Add `src/models/usage.py`: `TeamUsage`, `BucketUsage`, `TestUsage` Pydantic models with `requests_count: int`, `from_date: str`, `to_date: str` + identifier, mirroring `src/models/result.py`.
- [ ] T013 [US1] (AC: FR-007) Add `src/formatters/usage.py`: `format_team_usage`, `format_bucket_usage`, `format_test_usage` mapping api `data.*` into the usage models (mirror `format_results`); `requests_count` = api `data.requests_count` (direct map, no re-aggregation).
- [ ] T014 [US1] (AC: FR-001, FR-002, FR-003, FR-006, FR-009) Add `src/tools/usage_manager.py`: `UsageManager` with `get_team_usage`/`get_bucket_usage`/`get_test_usage` calling `api_request(token, "GET", ENDPOINT.format(ids), result_formatter=format_*_usage, params=_date_params(args))`; `register(mcp, token)` exposing three `@mcp.tool` tools (`{TOOLS_PREFIX}_team_usage`/`_bucket_usage`/`_test_usage`) with `action`/`args`/`ctx` + `match action: case "read"` + `tool_span`. Read-only — only `read` action. Each description states 90-day max lookback + default=today.
- [ ] T015 [US1] (AC: FR-009) Wire `usage_manager.register(mcp, token)` into `src/server.py` `register_tools` (additive; existing registrations untouched).

## Phase 4: User Story 2 — Clear errors (Priority: P2)

**Goal**: invalid requests and upstream failures surface clear messages; count 0 is a valid success.

### Tests for User Story 2

- [ ] T016 [P] [US2] (AC: FR-008, SC-003) Add `test_usage_api_error_surfaces_message` in `tests/test_usage_manager.py`: mock `api_request` to raise / return an error (401/403/404/500); assert the tool returns a `BaseResult` with a clear `error` via `http_error_message`, never a fabricated/zero count.
- [ ] T017 [P] [US2] (AC: FR-008, SC-003) Add `test_usage_no_data_returns_zero` in `tests/test_usage_manager.py`: mock `api_request` to return `requests_count=0` (no data in window); assert the tool returns `requests_count == 0` (a legitimate success, not an error).

### Implementation for User Story 2

- [ ] T018 [US2] (AC: FR-008) In `src/tools/usage_manager.py`, ensure each tool's `except` path returns `BaseResult(error=http_error_message(e))` (and `UNEXPECTED_ERROR_MESSAGE` for non-HTTP), records the span error, and never fabricates a count. The no-data `requests_count: 0` from api is surfaced as-is.

## Phase 5: User Story 3 — Existing tools unaffected (Priority: P2)

**Goal**: existing MCP tools and the read-only safety model are unchanged.

- [ ] T019 [US3] (AC: FR-002) Add `test_usage_tools_are_read_only` in `tests/test_usage_manager.py`: assert the three usage tools expose only the `read` action (no create/update/delete/start) and perform no mutation.
- [ ] T020 [US3] (AC: FR-010, SC-004) Regression quality-gate: run the full `pytest` suite + `make lint`; confirm existing managers/models/formatters/registrations are unchanged. Verified by `N/A — full test suite (pytest)`.

## Phase 6: Polish & Cross-Cutting

- [ ] T021 (AC: FR-005) Confirm each usage tool's description text makes the 90-day maximum lookback explicit (older data unavailable) and notes default window = today. Serves: FR-005.
- [ ] T022 (AC: SC-004) Run `make format` then `make lint` and `make test`; confirm line length 108, complexity ≤ 10, and the full suite is green.

## Dependencies & completion order

1. Phase 1 (baseline) then Phase 2 (contract + pattern lock + endpoint constants) first.
2. US1 tests written first (red), then US1 implementation (models → formatters → manager → registration) makes them green.
3. US2 tests then US2 implementation.
4. US3 depends on US1 implementation existing.
5. Polish last.

## Parallel execution examples

- The US1 test tasks marked `[P]` are independent test functions in the same file; can be authored together.
- The US2 error-path test tasks marked `[P]` are independent.
- US1 implementation is ordered: models, then formatters, then manager, then registration.

## Implementation strategy

MVP = User Story 1: three usage tools returning correct counts with the right shape and auth. User Story 2 (error clarity) and User Story 3 (regression safety) harden it. The feature is one new manager/model/formatter trio plus three endpoint constants and one registration line.
