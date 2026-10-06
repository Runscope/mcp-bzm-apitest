# Test Scenarios: Usage-retrieval MCP tools (consumer) — MOB-53921

> Planner-seeded scenario skeleton. The task-test-author stage expands each row into a failing test in `tests/test_usage_manager.py` (mock `api_request` via `AsyncMock`; no live calls). Scenario names match the traceability matrices in spec.md and plan.md.

| Scenario (test name) | Type | Given | When | Then | Covers (AC/FR/SC) | Task |
|---|---|---|---|---|---|---|
| `test_team_usage_returns_api_count` | unit (mock api_request) | `api_request` mocked to return `requests_count=42` for a team | team usage tool invoked with `team_uuid` | tool output `requests_count == 42`; echoed `team_uuid` matches | FR-001, FR-003, SC-001 | T005 |
| `test_bucket_usage_returns_api_count` | unit | `api_request` mocked for a bucket | bucket usage tool invoked with `bucket_key` | tool output `requests_count` equals the mocked value; echoed `bucket_key` matches | FR-001, FR-003, SC-001 | T006 |
| `test_test_usage_returns_api_count` | unit | `api_request` mocked for a test | test usage tool invoked with `bucket_key` + `test_uuid` | tool output `requests_count` equals the mocked value; echoed `test_uuid` matches | FR-001, FR-003, SC-001 | T007 |
| `test_usage_response_shape` | unit | mocked api response | any usage tool invoked | result carries exactly `requests_count`/`from_date`/`to_date` + identifier; no fabricated fields; no `tests_count`/`result.requests` conflation | FR-007, SC-002 | T008 |
| `test_usage_faithful_passthrough` | unit (falsification) | `api_request` mocked to return `requests_count=7` | usage tool invoked | tool reports exactly 7 (no placeholder/non-empty-only assertion); a different mock value yields exactly that value; no re-aggregation/fabrication | FR-003, SC-001 | T009 |
| `test_usage_default_window_today` | unit | no date params, then `from`/`to` | usage tool invoked | with no params the tool forces no date params (api defaults to today); with `from`/`to` they are passed through to `api_request` | FR-004 | T010 |
| `test_usage_passes_token_no_new_auth` | unit | a `BzmApimToken` | usage tool invoked | the token is passed to `api_request`; the tool adds no auth header/logic | FR-006 | T011 |
| `test_usage_api_error_surfaces_message` | unit (negative) | `api_request` raises / returns 401/403/404/500 | usage tool invoked | `BaseResult.error` via `http_error_message`; never a fabricated/zero count | FR-008, SC-003 | T016 |
| `test_usage_no_data_returns_zero` | unit | `api_request` mocked to return `requests_count=0` | usage tool invoked | tool returns `requests_count == 0` (legitimate success, not an error) | FR-008, SC-003 | T017 |
| `test_usage_tools_are_read_only` | unit | the three usage tools | inspect exposed actions | only `read` exposed (no create/update/delete/start); no mutation | FR-002 | T019 |

## Quality-gate scenario (no unit test owns this)

| Scenario | Type | Verification | Covers |
|---|---|---|---|
| Existing MCP tools unchanged | regression | N/A — full test suite (pytest) + `make lint` pass with no change to existing managers/models/formatters | FR-010, SC-004 |

## Mock-reality rule

Mock `api_request` only — never call live api/stage/dev/prod. Do NOT mock away the api→formatter mapping being proven: `test_usage_faithful_passthrough` must assert the exact `requests_count` from the mocked payload (not merely that it is non-empty), and a non-matching mock must not fabricate a value.
