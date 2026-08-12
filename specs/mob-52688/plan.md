# Implementation Plan: Fix Runscope MCP New-Install Failure (Unbounded mcp SDK Pin)

**Branch**: `ai-mob-52688` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/mob-52688/spec.md`
**Jira**: MOB-52688 (Bug)

## Summary

New installs of the Runscope MCP server fail because `mcp[cli]>=1.19.0` (pyproject.toml:20) has no upper bound, so a fresh resolve pulls mcp 2.0, which moved the `mcp.server.fastmcp` module and breaks the server's imports. The fix adds an upper-bound cap (`>=1.19.0,<2`) to keep new installs on the mcp 1.x line, plus a regression guard test that fails if mcp 2.x is ever installed or if the `mcp.server.fastmcp` import surface breaks. No production code logic changes.

## Technical Context

**Language/Version**: Python 3.11+ (CI matrix: 3.11, 3.12 — .github/workflows/test.yml)
**Primary Dependencies**: `mcp[cli]` (FastMCP over stdio), httpx, pydantic, defusedxml, nh3, opentelemetry-api (pyproject.toml:19-27)
**Storage**: N/A — stateless MCP server; no database or persistence
**Testing**: pytest + pytest-asyncio (auto mode) + pytest-cov; `make test` runs `pytest -v --cov=src` (Makefile:21-22)
**Target Platform**: Linux/macOS/Windows via pip, uv, Docker image (Dockerfile), and PyInstaller frozen binary (build.py)
**Project Type**: Single-project CLI / MCP stdio server
**Performance Goals**: N/A — this is a packaging/dependency fix; no runtime performance surface is touched
**Constraints**: The `mcp.server.fastmcp` import surface (`FastMCP`, `Context`) MUST remain importable and unchanged; the only production change permitted is the dependency specifier in pyproject.toml
**Scale/Scope**: 1 production line change (pyproject.toml:20) + 1 new test file; 13 existing import sites must remain valid

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0:

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Domain-Scoped MCP Tools | PASS | No tool managers added or changed; no cross-domain coupling introduced |
| II. Single API Client | PASS | No HTTP/API code touched; `api_request()` untouched |
| III. Test-First (NON-NEGOTIABLE) | PASS | The regression guard test (test_mcp_dependency_pin.py) is written first and must fail before the fix is considered verified; TDD honored. Mocking rule respected — no live API calls |
| IV. LLM-Friendly Error Handling | PASS | No error surfaces changed |
| V. Structured Pydantic Responses | PASS | No response models changed |
| Code Quality & Style | PASS | New test respects 108-char line length, isort/black, `--target-version py311` via `make lint` |
| Security & Token Handling | PASS | No token/auth code touched; no new dependency introduced (only a version cap on an existing one) |

**Result**: PASS — no violations. Complexity Tracking table is empty (below).

## Approach

### Pin change

Change the single dependency specifier in `pyproject.toml:20`:

```
- "mcp[cli]>=1.19.0",
+ "mcp[cli]>=1.19.0,<2",
```

This is the SELECTED option (A) from the Design Alternatives (spec.md / brownfield-context.md). `<2` is equivalent to `<2.0.0` under PEP 440 and caps resolution to the mcp 1.x line while still allowing safe patch/minor upgrades (1.19.1, 1.20, …). No transitive constraint on mcp exists (uv.lock:192-195 shows mcp is a direct dependency only), so this direct pin is the only lever.

### Import surface

The `mcp.server.fastmcp` import surface MUST remain unchanged. It is consumed at 13 sites:

- `main.py:8` — `from mcp.server.fastmcp import FastMCP`
- `src/tools/bucket_manager.py:5`, `team_manager.py:5`, `test_manager.py:5`, `environment_manager.py:5`, `schedule_manager.py:5`, `result_manager.py:6`, `step_manager.py:8`, `version_manager.py:3` — `from mcp.server.fastmcp import Context`
- `tests/conftest.py:6` — `from mcp.server.fastmcp import Context`
- `tests/test_integration.py:6` — `from mcp.server.fastmcp import FastMCP`; `:75`, `:98` — `from mcp.server.fastmcp import Context`

No import site is migrated to an mcp 2.0 path (Negative Constraint, spec.md § Field Semantics). mcp 1.19.0 (uv.lock:193) exports these symbols today.

### Regression guard

Add `tests/test_mcp_dependency_pin.py` with two tests:

1. `test_mcp_version_is_1x` — asserts the installed `mcp.__version__` major component is `1`. Fails loudly if a 2.x is ever installed.
2. `test_fastmcp_import_surface` — imports `FastMCP` and `Context` from `mcp.server.fastmcp` and asserts they are usable (class / type object). Fails with `ModuleNotFoundError` if the surface moves (the exact regression the ticket reports).

These are pure import/version assertions against the REAL installed package — no mocking (Test Validity Strategy, spec.md). They run under the existing `pytest` invocation (Makefile:21-22) and CI (.github/workflows/test.yml) on Python 3.11 and 3.12.

### Distribution

The pin flows into every distribution channel with no additional change:

- pip / uv: resolve from pyproject.toml:20
- Docker: `Dockerfile` installs the package with its dependencies
- PyInstaller: `build.py` freezes the installed environment

Because all channels resolve the same specifier, the single pyproject.toml change fixes all of them.

### uv.lock handling

The committed `uv.lock` already resolves mcp to 1.19.0 (uv.lock:193), which satisfies the new `<2` constraint. If the implementer regenerates the lockfile (`uv lock`), it MUST still resolve to a 1.x mcp. Regenerating is optional; the lockfile is already valid under the new constraint. If regenerated, the diff must show no mcp 2.x and no unrelated dependency churn.

### Scope guard

The production diff outside `pyproject.toml:20` (and the new test file) MUST be empty (FR-004, SC-005). No runtime logic, tool handler, formatter, model, config, or error-handling code is edited.

## Performance Strategy

**Not applicable.** This is a packaging/dependency-pin fix. There is no runtime data read, no external API call introduced, and no nested/looped call pattern (no N×M dimension). The change is resolved entirely at package-install time. No latency budget, timeout, cap, concurrency, batch, or degradation contract is required because no runtime execution path is added or modified. (Recorded explicitly to satisfy the performance gate: PERF-001..008 are N/A — there are zero external calls in the change.)

## Aggregation / Multi-level Data Reads

**Not applicable.** No aggregation, multi-level data read, or cross-service join exists in this change. No aggregation pseudocode is required because no data is read, joined, or rendered. (Recorded explicitly for the aggregation-pseudocode gate.)

## Interfaces

| Interface | Producer | Consumer | Shape | Compatibility |
|-----------|----------|----------|-------|---------------|
| `mcp.server.fastmcp` module | mcp SDK (1.x) | this server (13 import sites) | `FastMCP` class, `Context` type | Preserved — cap keeps mcp on 1.x so the module path is stable. Evidence: main.py:8, src/tools/*.py, uv.lock:193 |

## Project Structure

### Documentation (this feature)

```text
specs/mob-52688/
├── spec.md                 # feature spec (written)
├── plan.md                 # this file
├── research.md             # Phase 0 output
├── data-model.md           # Phase 1 output (N/A entities — see file)
├── quickstart.md           # Phase 1 output
├── brownfield-context.md   # brownfield disambiguation (written pre-spec)
├── design-contract.json    # structured design contract (planner)
├── evidence-index.json     # evidence index (planner)
├── checklists/
│   └── requirements.md      # spec quality checklist
└── tasks.md                # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml               # line 20: the dependency pin (THE production change)
uv.lock                      # already resolves mcp 1.19.0; valid under new constraint
main.py                      # main.py:8 import site (unchanged)
src/tools/*.py               # 8 tool managers with Context imports (unchanged)
tests/
├── conftest.py              # conftest.py:6 import site (unchanged)
├── test_integration.py      # existing import smoke coverage (unchanged)
└── test_mcp_dependency_pin.py   # NEW — regression guard (version cap + import surface)
```

**Structure Decision**: Single-project layout, unchanged. The only new file is a test under `tests/`; the only edited production file is `pyproject.toml`.

## Complexity Tracking

> No constitution violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |

## Post-Design Constitution Re-Check

Re-evaluated after Phase 1 design: still PASS on all principles. The design adds only a test file and a version cap; no principle is stressed. No new dependency is introduced (the cap tightens an existing dependency). Test-First is honored by authoring the guard test before the fix is accepted.

## Design

The design is a single upper-bound dependency cap plus a real-import regression guard. See § Approach (Pin change, Import surface, Regression guard) above for the full design; § Interfaces documents the preserved `mcp.server.fastmcp` producer/consumer contract. Selected Option A from the Design Alternatives (spec.md); exact-pin and mcp 2.0 migration rejected.

## Failure Modes

- **Fresh install still pulls mcp 2.x**: mitigated by the `,<2` cap (FR-002); detected by T005's fresh-resolution check and the T002 version guard. Fallback: the guard test fails loudly in CI before release.
- **A future mcp 1.x minor removes `mcp.server.fastmcp`**: not covered by the `<2` cap; the T003 import-surface guard fails loudly, and a new ticket would address it. Documented as an assumption, not silently ignored.
- **Lockfile drift**: if `uv.lock` is regenerated it must still resolve a 1.x mcp (FR-006); T006 verifies no unrelated churn.
- **Scope creep**: any edit outside `pyproject.toml` + the new test file is caught by T007's scope-guard diff assertion (FR-004).

## Non-Goals

- Not migrating to mcp 2.0 import paths (out of scope; deferred).
- Not changing any tool manager, model, formatter, API-client, or config code.
- Not fixing sibling MCP repositories (separate repos, not in this shard).
