# Test Scenarios: Usage-retrieval MCP tools (consumer) — MOB-53921

**Branch**: `ai-mob-53921` | **Generated**: 2026-10-06 | **Total tests**: 13 (4 happy / 4 negative / 3 edge / 2 contract)

All tests are authored in `tests/test_usage_manager.py` (a new file). They mock `api_request`
(never calling live api/stage/dev/prod), mirroring the `TestResultManager`/`TestTeamManager`
patterns in this test suite. `src.tools.usage_manager.UsageManager` does not exist yet, so the
module-level import is wrapped in try/except and every test's first statement asserts it is
not `None` — every test currently fails by `AssertionError` (not by collection/import error).

| S# | Type | Covers | Test name | Status |
|----|------|--------|-----------|--------|
| S1 | happy | T005 (FR-001, FR-003, SC-001) | `test_team_usage_returns_api_count` | RED |
| S2 | happy | T006 (FR-001, FR-003, SC-001) | `test_bucket_usage_returns_api_count` | RED |
| S3 | happy | T007 (FR-001, FR-003, SC-001) | `test_test_usage_returns_api_count` | RED |
| S4 | contract | T008 (FR-007, SC-002) | `test_usage_response_shape` | RED |
| S5 | negative (falsification) | T009 (FR-003, SC-001) | `test_usage_faithful_passthrough` | RED |
| S6a | edge | T010 (FR-004) | `test_usage_default_window_today` | RED |
| S6b | edge | T010 (FR-004) | `test_usage_default_window_custom_from_to` | RED |
| S7 | happy | T011 (FR-006) | `test_usage_passes_token_no_new_auth` | RED |
| S8 | negative | T016 (FR-008, SC-003) | `test_usage_api_error_surfaces_message` | RED |
| S9 | edge | T017 (FR-008, SC-003) | `test_usage_no_data_returns_zero` | RED |
| S10 | negative | T019 (FR-002) | `test_usage_tools_are_read_only` | RED |
| S11a | contract (static contract hard-gate) | T004 | `test_usage_endpoint_constants_match_static_api_contract` | RED |
| S11b | negative (boundary compatibility) | T007 | `test_usage_test_tool_maps_response_to_requested_test_only` | RED |

## Quality-gate scenario (no unit test owns this)

| Scenario | Type | Verification | Covers |
|---|---|---|---|
| Existing MCP tools unchanged | regression | N/A — full test suite (pytest) + `make lint` pass with no change to existing managers/models/formatters | FR-010, SC-004 |

## Notes

- Negative-path coverage: 4/13 = 30.8%
- Adverse-path coverage (negative + edge): 7/13 = 53.8%
- AC-coverage gaps: none — every spec.md acceptance criterion maps to >=1 scenario above (see AC map below)
- Planner hard-gate scenarios: S11a (static contract — endpoint constants verified against checked-in api Dependency Contract Facts, no live call); S5 (field/metric provenance falsification — forces a fixed/cached-value implementation to fail); S11b (boundary compatibility — the producer-shaped api envelope is mapped through the real formatter to the requested resource identifier, not a different one)

## AC-coverage map (spec.md Acceptance Scenarios / FRs)

| AC / FR | Scenario(s) |
|---|---|
| Three read-only usage tools wired to api (FR-001, FR-003, FR-009) | S1, S2, S3 |
| Read-only, no mutation (FR-002) | S10 |
| Date params + default=today + 90-day max (FR-004, FR-005) | S6a, S6b |
| PAT auth / no new auth path (FR-006) | S7 |
| Output formatting/model (FR-007, SC-002) | S4 |
| Clear errors; count 0 valid (FR-008, SC-003) | S8, S9 |
| requests_count faithful pass-through (FR-003, SC-001) | S5, S11b |
| Existing tools unchanged (FR-010, SC-004) | quality-gate (full suite + make lint), not a unit test |
| Static api contract (brownfield Dependency Contract Facts) | S11a |

## Mock-reality rule

Mock `api_request` only — never call live api/stage/dev/prod. `test_usage_faithful_passthrough`
(S5) must assert the exact `requests_count` from the mocked payload (not merely that it is
non-empty), and a second differently-valued mock must produce that different exact value — the
tool must not re-aggregate, cache, or fabricate. `test_usage_endpoint_constants_match_static_api_contract`
(S11a) asserts the exact endpoint path constants against the checked-in Dependency Contract Facts;
no live api call is made anywhere in this file.
