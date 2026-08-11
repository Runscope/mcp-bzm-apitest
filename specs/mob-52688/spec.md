# Feature Specification: Fix Runscope MCP New-Install Failure (Unbounded mcp SDK Pin)

**Feature Branch**: `ai-mob-52688`
**Created**: 2026-08-11
**Status**: Draft
**Jira**: MOB-52688 — https://perforce.atlassian.net/browse/MOB-52688
**Issue type**: Bug (dependency-version-pin regression)
**Input**: User description: "Fix Runscope MCP new-install failure caused by unbounded mcp SDK dependency pin (MOB-52688)"

## Background / Overview

The Runscope MCP server (`mcp-bzm-apitest`, repo `mcp-bzm-apim`) declares its dependency on the Python MCP SDK as `mcp[cli]>=1.19.0` with no upper bound. When the MCP SDK published version 2.0, any fresh install (via the Perforce Agentic Gateway / PAG, `pip install`, `uv sync` without an existing lockfile, Docker build, or PyInstaller build) resolves `mcp` to 2.0.x. The 2.0 release moved/removed the `mcp.server.fastmcp` module, so the server's imports fail immediately at startup:

```
from mcp.server.fastmcp import FastMCP, Icon
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

The current committed `uv.lock` still resolves to `mcp 1.19.0`, so existing checkouts that respect the lockfile keep working — but fresh installs from `pyproject.toml` do not, which is exactly what PAG performs. The fix caps the dependency to the mcp 1.x line so new installs cannot pull 2.0, while preserving the existing `mcp.server.fastmcp` import surface unchanged.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New install of the Runscope MCP server succeeds (Priority: P1)

A PAG user (or any operator using pip/uv/Docker) installs the Runscope MCP server for the first time on a clean machine with no pre-existing lockfile. The install resolves dependencies from `pyproject.toml` and the server starts successfully.

**Why this priority**: This is the exact reported failure. Without it, every new install of the server is broken, blocking the PAG integration entirely. It is the whole point of the ticket.

**Independent Test**: On a clean environment, install the package from `pyproject.toml` only (no committed lockfile), then start the server (or import the entry module). The install resolves `mcp` to a 1.x version and the `mcp.server.fastmcp` import succeeds.

**Acceptance Scenarios**:

1. **Given** a clean environment with no mcp installed and no lockfile, **When** the package dependencies are resolved from `pyproject.toml`, **Then** the resolved `mcp` version is `>=1.19.0` and `<2.0.0` (a 1.x version), never 2.x.
2. **Given** the resolved 1.x mcp is installed, **When** the server entry module and all tool managers are imported, **Then** `from mcp.server.fastmcp import FastMCP, Context` succeeds with no `ModuleNotFoundError`.
3. **Given** the fixed dependency spec, **When** a fresh Docker image is built, **Then** the build completes and the container's Python environment imports `mcp.server.fastmcp` without error.

---

### User Story 2 - Regression guard prevents silent reintroduction (Priority: P2)

A developer (or CI) needs an automated signal that the version cap is present and effective, so that a future change removing the cap — or a future mcp release that breaks the import surface — is caught before release rather than by a customer's failed install.

**Why this priority**: The bug was silent to existing checkouts (the lockfile masked it). A guard test converts "silent on new install" into "loud in CI," preventing recurrence. It is not the fix itself, so it is P2.

**Independent Test**: Run the test suite in an environment where mcp is installed. The guard test asserts the installed mcp major version is 1 and that `mcp.server.fastmcp` symbols import; if mcp 2.x were installed, the test fails.

**Acceptance Scenarios**:

1. **Given** the installed mcp is a 1.x version, **When** the guard test runs, **Then** it passes.
2. **Given** a hypothetical mcp 2.x install, **When** the guard test runs, **Then** it fails with a clear message indicating the mcp version cap was violated / the import surface is unavailable.

---

### Edge Cases

- **A future mcp 1.x minor release (e.g. 1.20) removes `mcp.server.fastmcp`**: The `<2` cap does not protect against this. It is out of scope for this fix; the guard test's import assertion would still fail loudly in CI, and a new ticket would address it. Documented as an assumption.
- **A pre-release specifier (e.g. `2.0.0rc1`)**: The `<2` cap excludes 2.0 pre-releases under standard PEP 440 resolution when pre-releases are not explicitly requested. No pre-release syntax is used in the current pin.
- **An operator installs with the committed `uv.lock`**: Already resolves to 1.19.0 and is unaffected; the fix only changes fresh-resolution behavior from `pyproject.toml`.
- **`Icon` symbol from the ticket traceback**: The traceback names `Icon`, but this repo never imports `Icon`. Do not add an `Icon` import; only `FastMCP` and `Context` are used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `mcp[cli]` dependency in `pyproject.toml` MUST carry an upper bound that excludes mcp 2.0.0 and later (i.e., resolution is constrained to the mcp 1.x line: `>=1.19.0,<2`).
- **FR-002**: A fresh dependency resolution from `pyproject.toml` (no pre-existing lockfile) MUST select an mcp version in the `[1.19.0, 2.0.0)` range and MUST NOT select any 2.x version.
- **FR-003**: After the pin change, all existing imports of `FastMCP` and `Context` from `mcp.server.fastmcp` (entry module, all tool managers, and test suite) MUST continue to import successfully. No import site may be migrated to an mcp 2.0 path as part of this fix.
- **FR-004**: The fix MUST NOT alter any runtime logic, tool handler behavior, API-client behavior, configuration, or public interface of the server. The only production change is the dependency specifier.
- **FR-005**: An automated regression guard test MUST exist that fails when the installed mcp major version is not 1, or when the `mcp.server.fastmcp` import surface (`FastMCP`, `Context`) cannot be imported.
- **FR-006**: The committed `uv.lock`, if regenerated as part of this change, MUST remain consistent with the new constraint (resolving to a 1.x mcp); if not regenerated, it MUST remain valid under the new constraint.

### Key Entities *(include if feature involves data)*

- **Dependency specifier (`mcp[cli]`)**: The version-constraint string in `pyproject.toml` that governs which mcp version a fresh install resolves. The single lever for this fix.
- **Import surface (`mcp.server.fastmcp`)**: The module exposing `FastMCP` (server class) and `Context` (tool-handler type). Consumed by the entry module and all 8 tool managers; must remain importable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of fresh installs from `pyproject.toml` on a clean environment resolve mcp to a 1.x version (0% resolve to 2.x).
- **SC-002**: 100% of the existing `mcp.server.fastmcp` import sites import successfully after the change (no `ModuleNotFoundError`).
- **SC-003**: The full existing test suite plus the new guard test pass on both supported Python versions (3.11 and 3.12) in CI.
- **SC-004**: A fresh Docker build and a fresh PyInstaller build both complete and produce a runnable artifact whose Python environment imports `mcp.server.fastmcp` without error.
- **SC-005**: Zero production code behavior changes — the diff to non-dependency, non-test source files is empty.

## Assumptions

- The mcp 2.0 release moved/removed the `mcp.server.fastmcp` module (proven by the ticket's own traceback: `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` on a new install that pulled 2.0). This fix relies on that being the breaking change.
- mcp 1.19.0 (and later 1.x releases up to but excluding 2.0) continue to export `mcp.server.fastmcp.FastMCP` and `mcp.server.fastmcp.Context` as used today (validated by the existing test suite importing them; the current `uv.lock` resolves to 1.19.0).
- The upper-bound form `<2` (equivalent to `<2.0.0` under PEP 440) is the correct, minimal cap. Exact-pinning (`==1.19.0`) is rejected because it would block safe 1.x security/patch upgrades.
- No sibling repo pattern is available locally to mirror (perfecto-mcp / blazemeter-sv MCP are not checked out under `$RUNSCOPE_HOME`); the cap form follows the PEP 440 major-version-cap convention.
- Migrating the codebase to mcp 2.0 import paths is explicitly out of scope for this bug fix and is deferred to separate feature work.

## Field Semantics (BINDING)

> Source: brownfield semantic disambiguation (brownfield-context.md § Semantic Disambiguation).
> These decisions are NON-NEGOTIABLE. Every downstream artifact — plan.md, tasks.md, tests, and the implementation — must honor them.

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|-------------------|-----------------|------------------|----------|----------|
| `mcp.server.fastmcp` import path | `from mcp.server.fastmcp import FastMCP, Context` | Runtime import module for the FastMCP server class and Context type hint; core to the entire MCP architecture | USE | main.py:8; src/tools/*.py; tests/conftest.py:6; tests/test_integration.py:6,75,98 |
| `mcp[cli]>=1.19.0` dependency pin | pyproject.toml:20 | Unbounded upper-limit pin; resolves to mcp 2.0 on new installs, breaking the import above | USE (needs upper bound `<2`) | pyproject.toml:20 |
| `Icon` (from ticket traceback) | (not imported in this repo) | Named in the traceback example but never used by this project | N/A — do not add | grep found only FastMCP and Context imports |

### Approved Identifiers (USE these for this ticket)

- `mcp.server.fastmcp import path` — correct runtime import used across main.py and all 8 tool managers; must keep working after the pin change.
- `mcp[cli] pin specification` — currently unbounded `>=1.19.0`; must be upper-bounded (`<2`) to prevent mcp 2.0 resolution.

### Forbidden Identifiers (DO NOT USE — belong to a different feature)

none

### Negative Constraints

- Do NOT migrate any import to an mcp 2.0 module path as part of this fix. The `mcp.server.fastmcp` import surface must remain exactly as-is.
- Do NOT add an `Icon` import; it is named in the ticket traceback but is not used by this repo.

## Current Implementation

> Source: brownfield codebase research (brownfield-context.md)

### What exists today

| What | File | Change |
|------|------|--------|
| mcp version pin | pyproject.toml:20 | Change `"mcp[cli]>=1.19.0"` to `"mcp[cli]>=1.19.0,<2"` |

### Key files

- pyproject.toml (line 20 — the unbounded pin)
- uv.lock (line ~193 — currently resolves mcp to 1.19.0)
- main.py:8 — `from mcp.server.fastmcp import FastMCP`
- src/tools/*.py — 8 tool managers importing `Context` from `mcp.server.fastmcp`
- tests/conftest.py:6, tests/test_integration.py:6,75,98 — existing top-level imports of the real module
- .github/workflows/test.yml — CI on Python 3.11 & 3.12 (runs pytest = import smoke test)
- Dockerfile, build.py — distribution channels that install from the pin

### Code search coverage

| Search Target | Patterns Used | Files Matched | Files Read | Omitted Matches / Reason |
|---------------|----------------|---------------|-----------|---------------------------|
| `mcp` package imports | `grep -rn "from mcp\|import mcp" --include="*.py"` | 13 import statements in 8 files | main.py, src/tools/*.py (7), tests/conftest.py, tests/test_integration.py | none; only FastMCP + Context imported |
| `mcp.server.fastmcp` path | `grep -rn "mcp.server.fastmcp"` | 13 exact matches | all read | none omitted |
| pyproject pin | direct read | 1 | pyproject.toml | mcp is the only dep referencing the SDK |

## Runtime Data Availability (BINDING)

> Source: brownfield-context.md § Runtime Data Availability Proof.

| Runtime Data | Written | Updated | Deleted/Expired | Planned Read | Available at Read Time? | Evidence | Safer Alternative if Unavailable |
|--------------|---------|---------|-----------------|--------------|------------------------|----------|----------------------------------|
| none | n/a | n/a | n/a | n/a | n/a | Dependency-pin fix; no runtime data sources are read or written. The mcp import is resolved at package-install time, not at runtime. | N/A |

## Cross-Repo Capability Analysis (BINDING)

> Source: brownfield-context.md § Cross-Repo Capability Analysis.

| Candidate Service/API | Capability | Evidence | Decision | Rationale |
|----------------------|-----------|----------|----------|-----------|
| none | N/A | Only mcp-bzm-apim depends on mcp under `$RUNSCOPE_HOME`; no sibling MCP repos checked out (search commands recorded in brownfield-context.md) | NOT APPLICABLE | No cross-service capability is consumed by this fix |

## Design Alternatives Considered (BINDING)

> Source: brownfield-context.md § Design Alternatives Considered.

| Option | What changes | Pros | Cons/Risks | Evidence | Decision |
|--------|--------------|------|-----------|----------|----------|
| A: upper-bound cap `>=1.19.0,<2` | one-line pin change | minimal, standard PEP 440, allows safe 1.x upgrades | assumes no 1.x minor breaks fastmcp | pyproject.toml:20; ticket traceback | SELECTED |
| B: exact-pin `==1.19.0` | pin to a single version | maximally stable | blocks security/patch upgrades within 1.x | PEP 440 / packaging best practice | REJECTED |
| C: migrate to mcp 2.0 import paths | rewrite 13 import sites | future-proof | large surface, out of scope for a bug fix | ticket labeled bug_fix | REJECTED |

## Test Validity Strategy (BINDING)

> Source: brownfield-context.md § Test Validity Strategy.

- **Required test shape**: a version-constraint guard test asserting the installed mcp major version is `1`, plus an explicit import smoke test that imports `FastMCP` and `Context` from `mcp.server.fastmcp`.
- **Mock reality rule**: DO NOT mock the mcp import — importing the real installed package is the whole point of the guard. Mocking `mcp.server.fastmcp` would hide the bug.
- **Assumption-challenge case**: a test that fails if the installed mcp is 2.x (i.e., would have caught the reported regression).
- **Evidence**: tests/conftest.py:6, tests/test_integration.py:6,75,98 (existing top-level imports of the real module — these already act as an import smoke test at collection time).

## Requirement Traceability Matrix

| AC / Requirement | Spec FR/SC | Plan section | Tasks | Tests | Impl files |
|------------------|-----------|--------------|-------|-------|-----------|
| Fresh install resolves mcp 1.x (US1 AC1) | FR-001, FR-002, SC-001 | plan.md §Approach, §Pin change | T001, T004 | test_mcp_version_is_1x | pyproject.toml |
| Import surface keeps working (US1 AC2) | FR-003, SC-002 | plan.md §Import surface | T003, T004 | test_fastmcp_import_surface + existing suite | pyproject.toml (no code change) |
| Docker/PyInstaller build succeeds (US1 AC3) | FR-002, SC-004 | plan.md §Distribution | T005 | CI build job | Dockerfile, build.py (unchanged) |
| Regression guard exists (US2 AC1/AC2) | FR-005, SC-003 | plan.md §Regression guard | T002, T003 | test_mcp_version_is_1x, test_fastmcp_import_surface | tests/test_mcp_dependency_pin.py |
| No production behavior change (US1) | FR-004, SC-005 | plan.md §Scope guard | T006 | full existing suite | (diff empty outside pin + tests) |

## In Scope

- Add an upper-bound version constraint to the `mcp[cli]` dependency in `pyproject.toml` (line 20) so new installs stay on the mcp 1.x line.
- Add a regression guard test (`tests/test_mcp_dependency_pin.py`) asserting the installed mcp major version is 1 and that the `mcp.server.fastmcp` import surface is intact.

## Out of Scope

- Migrating the codebase to mcp 2.0 import paths / API (deferred to separate feature work).
- Fixing sibling repos (perfecto-mcp, blazemeter-sv MCP) — separate repositories, not in this shard.
- Any change to runtime logic, tool handlers, API-client behavior, or configuration.

## Non-Goals

- This fix does NOT add support for mcp 2.0; it deliberately caps below 2.0 to preserve the existing import surface.
- This fix does NOT regenerate or reshape any Pydantic response model or MCP tool.

## Field/Metric Provenance

Not applicable. This fix derives no output field or metric from any downstream service/API response — it is a dependency-version-pin change with no runtime data flow. See `brownfield-context.md` § Field/Metric Provenance Matrix (`none`).
