---
description: "Task list for MOB-52688 — fix unbounded mcp SDK dependency pin"
---

# Tasks: Fix Runscope MCP New-Install Failure (Unbounded mcp SDK Pin)

**Input**: Design documents from `specs/mob-52688/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md (all present)
**Jira**: MOB-52688 (Bug)

**Tests**: REQUIRED — the spec's Test Validity Strategy and Constitution Principle III (Test-First, NON-NEGOTIABLE) mandate a regression guard test written before the fix is accepted.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: parallelizable (different file, no incomplete dependency)
- **[Story]**: US1 (fresh install succeeds) / US2 (regression guard)

## Path Conventions

Single-project layout: `pyproject.toml`, `tests/` at repository root.

---

## Phase 1: Setup

- [ ] T001 Verify the clean-environment reproduction: in a fresh venv, resolve deps from `pyproject.toml` only (no lockfile) and confirm the CURRENT unbounded pin `mcp[cli]>=1.19.0` (pyproject.toml:20) is present. Record the currently-resolvable mcp version. This establishes the baseline before the fix. (No code change in this task.)

---

## Phase 2: Foundational

_No blocking foundational work. The fix is a single dependency-spec change plus a guard test; there is no shared infrastructure to build first._

---

## Phase 3: User Story 2 — Regression guard (Priority: P2, authored FIRST per Test-First)

**Story goal**: An automated guard fails if mcp 2.x is ever installed or if the `mcp.server.fastmcp` import surface breaks (FR-005, SC-003).

**Independent test**: Run the guard test file — both tests pass on a 1.x mcp; the version test would fail on a 2.x mcp.

> Constitution III (Test-First, NON-NEGOTIABLE): these guard tests are written and must be red-verified by the test-author stage BEFORE the pin fix in Phase 4 is applied. Because the current `uv.lock` resolves to 1.19.0, the version guard is GREEN today; its value is catching a future removal of the cap. The assumption-challenge case (mcp 2.x -> fail) is documented in the test and verified by the test-author via a simulated/parametrized 2.x version string, not by installing mcp 2.0.

- [ ] T002 [P] [US2] Add regression guard test `tests/test_mcp_dependency_pin.py::test_mcp_version_is_1x` — import the REAL `mcp` package (no mock) and assert `int(mcp.__version__.split(".")[0]) == 1`, with a clear failure message naming the version cap. Honors the Mock-Reality rule (do NOT mock the mcp import). (FR-005, SC-001, SC-003; spec.md § Test Validity Strategy)
- [ ] T003 [P] [US2] Add import-surface guard test `tests/test_mcp_dependency_pin.py::test_fastmcp_import_surface` — execute `from mcp.server.fastmcp import FastMCP, Context` (no mock) and assert `FastMCP` is a class and `Context` is usable as a type. This is the assumption-challenge test: it fails with `ModuleNotFoundError` under mcp 2.x (the exact reported regression). (FR-003, FR-005, SC-002; spec.md § Test Validity Strategy)

---

## Phase 4: User Story 1 — Fresh install succeeds (Priority: P1)

**Story goal**: A fresh install from `pyproject.toml` resolves mcp to 1.x, so `mcp.server.fastmcp` imports succeed and the server starts (FR-001, FR-002, FR-003, SC-001, SC-002, SC-004).

**Independent test**: In a clean venv, `pip install -e ".[test]"`, then `python -c "import mcp; assert mcp.__version__.startswith('1.')"` and `python -c "from mcp.server.fastmcp import FastMCP, Context"` both succeed.

- [ ] T004 [US1] Apply the pin cap in `pyproject.toml` line 20: change `"mcp[cli]>=1.19.0"` to `"mcp[cli]>=1.19.0,<2"`. This is the SELECTED design (Option A). Do NOT change any other dependency line and do NOT touch any import site (Negative Constraint). (FR-001, FR-002, SC-001)
- [ ] T005 [US1] Validate resolution + import surface after the cap: in a clean venv install from the edited `pyproject.toml` (no pre-existing lockfile), confirm the resolved mcp is on the 1.x line (at least 1.19.0 and below 2.0.0), then run the guard tests and the full existing suite (`make test`) on Python 3.11 and 3.12. Confirm the reported traceback no longer occurs. (FR-002, FR-003, SC-002, SC-003, SC-004)
- [ ] T006 [US1] uv.lock consistency: confirm the committed `uv.lock` (currently resolves mcp 1.19.0, uv.lock:193) is still valid under the new cap. Regeneration is OPTIONAL; if `uv lock` is run, verify the diff shows a 1.x mcp and NO unrelated dependency churn. (FR-006)

---

## Phase 5: Polish & Cross-Cutting

- [ ] T007 [US1] Scope-guard verification via `test_no_production_behavior_change`: confirm `git diff` against the base shows changes ONLY in `pyproject.toml` (line 20), the new `tests/test_mcp_dependency_pin.py`, and (optionally) `uv.lock`. Assert the diff to all other production source files is empty. (FR-004, SC-005)
- [ ] T008 [P] Lint the new test file with `make lint` (108-char line length, isort, black `--target-version py311`) so CI style checks pass. (Constitution § Code Quality)

---

## Dependencies

- Baseline setup (Phase 1) precedes the guard tests (Phase 3), which are authored first per Test-First.
- The pin fix (Phase 4) must NOT be applied until the guard tests exist and are red-verified by the test-author stage.
- Validation, then lockfile consistency, then the scope guard, then lint follow in order within and after Phase 4.

## Parallel Execution Examples

- The two guard tests in Phase 3 are marked `[P]` — they live in the same new file as independent functions and are implemented together.
- The lint pass in Phase 5 can run in parallel with the lockfile-consistency and scope-guard checks (independent).

## Implementation Strategy

MVP = User Story 1 (Phase 4): the pin cap is the fix that unblocks new installs. User Story 2 (Phase 3 guard tests) is authored first to satisfy Test-First and to lock in the fix against regression. Deliver both together in one PR — the change is a single-line production edit plus one test file.

## Assumption-Challenge / Validation Coverage

- **A2 (mcp 2.0 moved fastmcp)** — proven by the ticket traceback; challenged by the import-surface guard (Phase 3) which fails under 2.x.
- **A4 (the cap resolves correctly)** — validated by the fresh-resolution check (Phase 4) and the version-major guard (Phase 3).
- **No runtime-data / no cross-service tasks** — none required: the change reads no runtime data and consumes no external API (brownfield-context.md §§ Runtime Data Availability, Cross-Repo Capability Analysis). No live/dev/stage/prod endpoint is called by any task.
