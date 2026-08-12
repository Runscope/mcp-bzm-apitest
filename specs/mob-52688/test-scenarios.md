# Test Scenarios: MOB-52688 — mcp-bzm-apim

**Branch**: `ai-mob-52688` | **Generated**: 2026-08-11 | **Total tests**: 8 collected pytest items (6 test functions, 1 parametrized x2) — 5 happy/positive-guard, 3 negative/assumption-challenge

| S# | Type        | Covers          | Test name                                          | Status |
|----|-------------|-----------------|-----------------------------------------------------|--------|
| S1 | happy       | T002            | test_mcp_version_is_1x                              | RED ✓  |
| S2 | negative    | T002            | test_version_predicate_rejects_2x[2.0.0-2]          | GREEN (guard-logic proof) |
| S2 | negative    | T002            | test_version_predicate_rejects_2x[2.1.3-2]          | GREEN (guard-logic proof) |
| S3 | happy       | T003            | test_fastmcp_import_surface                         | RED ✓  |
| S4 | negative    | T003            | test_icon_symbol_not_imported                       | GREEN (constraint currently honored) |
| S5 | contract    | T004            | test_mcp_dependency_has_upper_bound_below_2          | RED ✓  |
| S6 | contract    | T006            | test_lockfile_requires_dist_has_upper_bound          | RED ✓  |
| S7 | edge        | T007            | test_no_production_behavior_change                  | GREEN (scope currently clean; stays-green regression guard) |

## Notes

- **Negative-path coverage**: 3/8 collected items = 37.5% (>= 30% quota).
- **AC-coverage map**:
  - US1 AC1 (fresh install resolves 1.x), FR-001/FR-002, SC-001 → S1, S5
  - US1 AC2 (import surface intact), FR-003, SC-002 → S3
  - US1 AC3 (Docker/PyInstaller build succeeds) → not unit-testable; covered at CI build-job / T005 level per spec.md's own acknowledgment (existing `tests/conftest.py` + `tests/test_integration.py` top-level imports already act as an import smoke test at collection time — see "Collection-time regression" note below).
  - US2 AC1 (guard passes on 1.x) → S1, S3 (both pass once T004 lands and env is reinstalled)
  - US2 AC2 (guard fails on 2.x) → S1, S3 (both currently RED — proves the guard catches the reported regression today) + S2 (predicate-only assumption-challenge, no live 2.x install)
  - FR-004/SC-005 (no production behavior change) → S7
  - FR-006 (lockfile consistency) → S6
  - Negative Constraint (no `Icon` import) → S4
- **AC-coverage gaps**: none. Every FR/SC in spec.md's Requirement Traceability Matrix, and every design-contract.json traceability row (AC-1..AC-4), maps to at least one scenario above or to an explicitly-documented non-unit-testable AC (US1 AC3, build-level).
- **Planner hard-gate scenarios**:
  - Runtime lifecycle: N/A (brownfield-context.md § Runtime Data Availability — no runtime data read/written).
  - Static contract: S5, S6 (pyproject.toml + uv.lock dependency-specifier checks — both read checked-in files only, no live install/network resolution).
  - Mock-reality: S1 and S3 import the REAL installed `mcp` package; no test in this file mocks `mcp` or `mcp.server.fastmcp`. Verified: no `unittest.mock.patch` targets any `mcp*` import in `tests/test_mcp_dependency_pin.py`.
  - Forbidden identifiers: none (spec.md § Field Semantics — zero forbidden identifiers declared).
  - Assumption-challenge: S2 (simulated 2.x version string against the same major-version predicate S1 uses) and S1/S3 themselves (both currently red against the REAL installed 2.0.0, proving the guard would have caught the reported regression without any live 2.x install).
- **Deliberate style exceptions**: none. Tests follow repo convention (pytest, `unittest.mock` available but deliberately unused for the mcp import per Mock-Reality rule, module-level docstrings, `Covers T###` scenario markers).

## Collection-time regression note (important for the implementer)

`tests/conftest.py:6` does `from mcp.server.fastmcp import Context` at module scope. Under the CURRENT unbounded pin, a fresh install resolves `mcp` to 2.0.0, and `conftest.py` itself fails to import — this breaks pytest COLLECTION for the entire `tests/` directory (not just the new guard tests), with a `ModuleNotFoundError`, not a per-test assertion failure. This was independently verified: removing the new test file entirely still reproduces the identical `ImportError while loading conftest` under the broken environment.

Red-verification for this stage therefore ran the new test file with `pytest tests/test_mcp_dependency_pin.py --noconftest` to bypass the poisoned fixture module and get real per-test assertion-failure signatures (S1, S3, S5, S6 all fail by `AssertionError`/`pytest.fail`, not by import/collection error). Once T004 (pyproject.toml cap) lands and the environment is reinstalled from the fixed spec, `conftest.py` will import successfully again and the normal `pytest tests/` invocation (with conftest, no `--noconftest` flag) is expected to collect and pass all 8 items plus the full pre-existing suite.

**Existing-suite baseline**: the full pre-existing suite (excluding the new file) is equally uncollectable under the current broken environment — confirmed via `pytest tests/ --ignore=tests/test_mcp_dependency_pin.py`, which fails identically at the `conftest.py` import. This is a pre-existing baseline failure caused directly by the reported bug, not something introduced by the new tests. Per the test-author's existing-suite integrity rule, this is recorded as neutral (`pre_existing_failures: whole-suite, baseline-broken, unchanged by new-test addition`) rather than "test-author broke the suite."

A live sanity check (throwaway venv, `mcp[cli]>=1.19.0,<2`, not committed to this repo) confirmed the fix design resolves to mcp 1.29.0 and both `FastMCP`/`Context` import successfully once the cap is applied — the tests are expected to flip green post-fix, not merely red forever.

## Scope-guard note (T007)

`design-contract.json`'s traceability row for AC-4 (FR-004/SC-005) names `test_no_production_behavior_change` explicitly (task T007) — this test is authored as S7. Its diff-scope allowlist includes `pyproject.toml`, `uv.lock`, `tests/`, `specs/`, and `CLAUDE.md`: the branch (commit a3c5945) already legitimately carries `specs/mob-52688/*` and `CLAUDE.md` changes from the planner stage (spec-kit artifacts), which are documentation, not production behavior. Restricting the allowlist to only `pyproject.toml`/`tests/` (excluding `specs/`/`CLAUDE.md`) would make S7 fail today for the wrong reason (spec-kit docs, not implementation scope creep) — the red-verification rubric's correct-signature requirement rejects that. S7 is a stays-green regression guard: it PASSES today (scope is currently clean) and must keep passing after T004/T006 land; if the implementer's fix touches any `src/`, `main.py`, `Dockerfile`, or `build.py` path, S7 will start failing and flag the scope violation.

## Test Name Registry

Implemented in `tests/test_mcp_dependency_pin.py`:

| Test function | Scenario | Covers |
|----------------|----------|--------|
| `TestMcpVersionCap.test_mcp_version_is_1x` | S1 | T002, FR-001, FR-002, SC-001 |
| `TestMcpVersionCap.test_version_predicate_rejects_2x` (parametrized x2) | S2 | T002, FR-001, FR-002 |
| `TestFastmcpImportSurface.test_fastmcp_import_surface` | S3 | T003, FR-003, FR-005, SC-002 |
| `TestFastmcpImportSurface.test_icon_symbol_not_imported` | S4 | T003, Negative Constraint |
| `TestPyprojectPinIsCapped.test_mcp_dependency_has_upper_bound_below_2` | S5 | T004, FR-001, FR-002, SC-001 |
| `TestNoProductionBehaviorChange.test_no_production_behavior_change` | S7 | T007, FR-004, SC-005 |
| `TestLockfileSpecifierHasUpperBound.test_lockfile_requires_dist_has_upper_bound` | S6 | T006, FR-006 |
