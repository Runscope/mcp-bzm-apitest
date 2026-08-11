# Test Scenarios: MOB-52688 — Fix Unbounded mcp SDK Pin

Scenarios the test-author stage will implement as failing tests, then the implementer turns green. All tests import the REAL installed mcp package — no mocking of `mcp.server.fastmcp` (Mock-Reality rule).

## AC coverage map

| Scenario | Covers (AC / FR / SC) | Tasks | Category |
|----------|-----------------------|-------|----------|
| test_mcp_version_is_1x | US1 AC1, FR-001, FR-002, SC-001 | T002, T004 | version-cap guard (positive + assumption-challenge) |
| test_fastmcp_import_surface | US1 AC2, US2 AC1/AC2, FR-003, FR-005, SC-002 | T003 | import-surface guard (assumption-challenge) |
| fresh-resolution check (manual/CI) | US1 AC1, FR-002, SC-001, SC-004 | T005 | resolution proof |
| full existing suite unchanged | FR-004, SC-005 | T007 | scope-guard / non-regression |

## Scenarios

### S1 — mcp installed version is on the 1.x line (positive + negative)

- **Given** the package is installed from the fixed `pyproject.toml`, **when** `mcp.__version__` is read, **then** the major component equals `1`.
- **Assumption-challenge (negative)**: parametrize/simulate an mcp version string of `2.0.0` and assert the guard's version check would FAIL (proves the guard would have caught the reported regression). This is done by testing the version-parsing predicate against a `"2.0.0"` string, NOT by installing mcp 2.0.
- Maps to: T002, FR-001, FR-002, SC-001.

### S2 — `mcp.server.fastmcp` import surface is intact

- **Given** a 1.x mcp is installed, **when** `from mcp.server.fastmcp import FastMCP, Context` executes, **then** it succeeds, `FastMCP` is a class, and `Context` is a usable type.
- **Assumption-challenge**: this is the exact regression — under mcp 2.x the import raises `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. The test's real (unmocked) import is the falsification: it fails under 2.x.
- Maps to: T003, FR-003, FR-005, SC-002.

### S3 — Fresh resolution excludes 2.x (resolution proof)

- **Given** a clean environment with no lockfile, **when** deps are resolved from the fixed `pyproject.toml`, **then** the resolved mcp version satisfies `>=1.19.0,<2.0.0`.
- Maps to: T005, FR-002, SC-001, SC-004. Verified in CI install step + local quickstart.

### S4 — No production behavior change (non-regression)

- **Given** the fix, **when** the full existing pytest suite runs on Python 3.11 and 3.12, **then** all pre-existing tests pass unchanged and the diff to non-dependency, non-test source files is empty.
- Maps to: T007, FR-004, SC-005.

## Planner-hard-gate categories

| Category | Applies? | Handling |
|----------|----------|----------|
| Runtime lifecycle | No | No runtime data is read/written by this change (brownfield-context.md § Runtime Data Availability). No lifecycle test required. |
| Static contract | No | No cross-service/API capability is consumed (brownfield-context.md § Cross-Repo Capability Analysis). No contract-verification test required. |
| Forbidden identifier | No | Zero forbidden identifiers (brownfield-context.md § Binding Decisions). No negative/contrast test required. |
| Mock-reality | Yes | S1/S2 import the real mcp package; mocking the import is explicitly forbidden and would hide the bug. |
| Performance (N×M) | No | No external calls, no nested loops, no aggregation. PERF-001..008 are N/A (plan.md § Performance Strategy). |

## Negative-quota note

Of the guarding scenarios, S1's assumption-challenge (simulated 2.x fails the predicate) and S2's real-import falsification (fails under 2.x) are the negative/challenge cases proving the guard would catch the regression, satisfying the negative-test expectation for this fix's small surface.

## Test Name Registry

The scenarios above are implemented as these pytest functions in `tests/test_mcp_dependency_pin.py` (and the non-regression check):

| Test function | Scenario | Covers |
|---------------|----------|--------|
| test_mcp_version_is_1x | S1 | AC-1, FR-001, FR-002, SC-001 |
| test_fastmcp_import_surface | S2 | AC-2, AC-3, FR-003, FR-005, SC-002 |
| test_no_production_behavior_change | S4 | AC-4, FR-004, SC-005 (asserts the production diff outside the pin and the new test file is empty; realized via the T007 scope-guard check plus the full existing suite passing unchanged) |
