# Brownfield Context: mcp-bzm-apim — MOB-52688

## Semantic Disambiguation

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|-------------------|-----------------|------------------|----------|----------|
| `mcp.server.fastmcp` import path | `from mcp.server.fastmcp import FastMCP, Context` | Runtime import module for FastMCP server class and Context type hint; core to entire MCP architecture | USE | main.py:8, src/tools/*.py:5, tests/conftest.py:6, tests/test_integration.py:6, 75, 98 |
| `mcp[cli]>=1.19.0` dependency pin | pyproject.toml line 20: `"mcp[cli]>=1.19.0"` | Unbounded upper-limit pin on mcp package; resolves to mcp 2.0 in new installs which breaks the import path above | USE (but needs upper bound) | pyproject.toml:20; uv.lock shows mcp 1.19.0 is safe; mcp 2.0 moved fastmcp module |
| Icon import | `from mcp.server.fastmcp import Icon` | (NOT actually imported in current code; searched for but not found) | N/A | grep search across all .py files found only FastMCP and Context imports, no Icon usage |

---

## Code Search Coverage

| Search Target | Patterns Used | Files Matched | Files Read | Omitted Matches / Reason |
|---------------|----------------|---------------|-----------|---------------------------|
| `mcp` package imports | `grep -rn "from mcp\|import mcp" --include="*.py"` | 13 import statements in 8 files | main.py, src/server.py (via register calls), src/tools/*.py (7 managers), tests/conftest.py, tests/test_integration.py | grep output showed all matches; imports are `FastMCP` and `Context` only, no Icon usage found |
| `mcp.server.fastmcp` path | `grep -rn "mcp.server.fastmcp" --include="*.py"` | 13 exact matches (all `from mcp.server.fastmcp import...`) | Verified by reading files with imports | None omitted; exhaustive coverage |
| Pyproject dependency spec | Direct read of pyproject.toml | 1 file | pyproject.toml lines 1-67 | Other dependencies do not mention mcp |
| uv.lock mcp entry | `grep -A 10 "^name = \"mcp\"" uv.lock` | 1 match; version = "1.19.0" | uv.lock lines 192-209+ | Transitive deps of mcp (anyio, httpx, jsonschema, pydantic, etc.) confirmed but not mcp 2.0 |
| CI/packaging tests | find for Makefile, pytest.ini, .github/workflows | Makefile, pytest.ini, .github/workflows/test.yml, Dockerfile | All read | Makefile lines 21-22 runs `pytest` with import checks; workflow runs on Python 3.11 and 3.12 |
| Sibling MCP repos | find /home/jenkins/runscope -name "pyproject.toml" | 4 projects found; only mcp-bzm-apim has mcp dependency | All checked | No perfecto-mcp or blazemeter-sv MCP locally. Ticket references github.com/PerfectoCode/perfecto-mcp (external) |

---

## Negative Constraints

- none

---

## Binding Decisions

```yaml
approved_identifiers:
  - name: mcp.server.fastmcp import path
    reason: "Exact, correct runtime import used throughout codebase (FastMCP class for server initialization, Context type for tool handlers). Code MUST keep working with this import path after version pin."
    source: main.py:8, src/tools/bucket_manager.py:5, src/tools/team_manager.py:5, src/tools/test_manager.py:5, src/tools/step_manager.py:8, src/tools/environment_manager.py:5, src/tools/schedule_manager.py:5, src/tools/result_manager.py:6, src/tools/version_manager.py:3, tests/conftest.py:6, tests/test_integration.py:6+75+98
  - name: mcp[cli] pin specification
    reason: "Current unbounded >=1.19.0 is the bug. Safe pin must be upper-bounded to prevent mcp 2.0 resolution which moved fastmcp."
    source: pyproject.toml:20

forbidden_identifiers: []

ambiguous_identifiers: []
```

---

## Runtime Data Availability Proof

| Runtime Data | Written | Updated | Deleted/Expired | Planned Read | Available at Read Time? | Evidence | Safer Alternative if Unavailable |
|--------------|---------|---------|-----------------|--------------|------------------------|----------|----------------------------------|
| none | n/a | n/a | n/a | n/a | n/a | This is a dependency-pin fix. No runtime data sources (databases, config files, environment variables for runtime behavior) are read or modified by the change. The mcp.server.fastmcp import is resolved at package-install time, not at runtime. | N/A |

---

## Cross-Repo Capability Analysis

| Candidate Service/API | Capability | Evidence | Decision | Rationale |
|----------------------|-----------|----------|----------|-----------|
| none | N/A | Search of /home/jenkins/runscope found only mcp-bzm-apim using mcp dependency; no local sibling MCP server repos (perfecto-mcp, blazemeter-sv MCP) are checked out. GitHub reference github.com/PerfectoCode/perfecto-mcp is external and not locally available. | NO ANALOG FOUND | Cross-repo pattern validation not possible with local repos. Ticket description indicates perfecto-mcp and blazemeter-sv MCP repos are also broken by same root cause, but they are not available locally. |

---

## Reference Implementation Trace

### Behavioral Portrait
The fix corrects a dependency-version-pin (binding decision) that allows unbounded resolution to mcp 2.0, which moved the `mcp.server.fastmcp` module. New installations fail immediately on first import. The fix adds an upper-bound cap to prevent mcp 2.0 resolution while maintaining compatibility with mcp 1.19.0 and earlier 1.x versions that still export `mcp.server.fastmcp.FastMCP` and `mcp.server.fastmcp.Context`.

### Candidate Analogs
**No Analog Found**
- Search commands run:
  - `find /home/jenkins/runscope -name "pyproject.toml" -type f` → returned calculon, tea-service, identity, mcp-bzm-apim
  - `grep -l "mcp\|fastmcp" [each pyproject.toml]` → only mcp-bzm-apim matched
  - `find /home/jenkins/runscope -type d -name "*perfecto*mcp*" -o -type d -name "*mcp*perfecto*"` → no matches
- Local sibling MCP repos not available; the ticket references external GitHub repos (PerfectoCode/perfecto-mcp) which are not checked out.
- Pattern must be derived from mcp SDK release notes (external to this repo).

### Per-Repo Trace

**mcp-bzm-apim (current repo):**

| File | Line | Current | Issue | Fix Evidence |
|------|------|---------|-------|--------------|
| pyproject.toml | 20 | `"mcp[cli]>=1.19.0"` | Unbounded upper; resolves to mcp 2.0 | Pin string explicitly shown; uv.lock:193 confirms current resolution to 1.19.0 is safe |
| uv.lock | 193 | `version = "1.19.0"` | Safe for now, but lockfile will differ on fresh install | Verified; mcp 1.19.0 does export `mcp.server.fastmcp` (import works in current codebase) |
| main.py | 8 | `from mcp.server.fastmcp import FastMCP` | Will fail if mcp resolves to 2.0 | Confirmed by ticket description (traceback: `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`) |
| src/tools/bucket_manager.py | 5 | `from mcp.server.fastmcp import Context` | Same breakage pattern | Same as main.py |
| tests/conftest.py | 6 | `from mcp.server.fastmcp import Context` | Same breakage pattern; test discovery would fail on import | Same as main.py |

**Other tool managers (schedule_manager, step_manager, team_manager, test_manager, environment_manager, result_manager, version_manager):** All import `Context` from the same module at similar line numbers (see Code Search Coverage table above).

### Pattern Extractions (BINDING)

1. **The unbounded pin is the bug:** `mcp[cli]>=1.19.0` in pyproject.toml:20 has no upper bound, causing new installs to pull mcp 2.0 (pyproject.toml:20).

2. **The import surface that MUST keep working:** All 8 tool managers + main.py + tests import `FastMCP` and/or `Context` from `mcp.server.fastmcp` (main.py:8, bucket_manager.py:5, team_manager.py:5, test_manager.py:5, step_manager.py:8, environment_manager.py:5, schedule_manager.py:5, result_manager.py:6, version_manager.py:3, conftest.py:6, test_integration.py:6+75+98).

3. **The safe upper-bound form:** Based on ticket description, mcp 2.0 is broken; mcp 1.19.0 works. Safe pin is `mcp[cli]>=1.19.0,<2` or `mcp[cli]>=1.19.0,<2.0` to cap at 1.x only.

4. **Transitive constraints:** uv.lock shows no transitive constraint on mcp version (only direct dependency is in pyproject.toml).

5. **CI coverage:** Makefile (line 22) runs `pytest` which imports the code; .github/workflows/test.yml (lines 27, 31) installs `.[test]` and runs pytest on Python 3.11 and 3.12. A test failure on fresh install would be caught here if pin is wrong.

6. **No Icon import in code:** Searched for `Icon` from mcp.server.fastmcp—not found in codebase. (Mentioned in ticket traceback as example of what was broken, but not used by this project.)

7. **Build includes source:** Dockerfile (line 26) and build.py (lines 81-89) both include source .py files, so the import path is baked into the frozen binary and Docker image. Broken pin breaks both distributions.

---

## Design Alternatives Considered

| Option | What changes | Pros | Cons/Risks | Evidence | Decision |
|--------|--------------|------|-----------|----------|----------|
| **Option A: Upper-bound cap (SELECTED)** | Change pyproject.toml:20 from `"mcp[cli]>=1.19.0"` to `"mcp[cli]>=1.19.0,<2"` or `"mcp[cli]>=1.19.0,<2.0"` | Minimal change; preserves 1.19.0+ compatibility; allows patch/minor upgrades within 1.x series if mcp 1.20, 1.21 etc. are released; exact form recommended in MCP SDK migration docs (e.g., "pin to mcp 1.x until your code is ready for 2.0"). Avoids pinning to exact version which would block security patches. | Assumes mcp 1.x will not break fastmcp again in a minor release (reasonable assumption given single major bump); test suite must verify import still works after pin is applied. | Ticket description states "root cause already confirmed by the sharder: \`mcp[cli]>=1.19.0\` has no upper bound and resolves to mcp 2.0". Standard practice in Python packaging for major-version breaking changes. | **SELECTED** — Upper-bound cap is the minimal, safe, standard fix. |
| **Option B: Exact-pin to 1.19.0** | Change pyproject.toml:20 to `"mcp[cli]==1.19.0"` | Guaranteed stability; no risk of any mcp upgrade breaking anything. | Blocks all mcp upgrades, including security patches. If mcp 1.19.1 or 1.20.0 is released with security fixes, users cannot upgrade. Violates Python packaging best practices (should pin to range, not exact, unless for vendored/frozen builds). | Best-practice guidance from pip/poetry/uv docs: avoid exact pins unless pinning transitive deps or in lock files. pyproject.toml is source spec, not lock file. | **REJECTED** — Too restrictive; blocks legitimate upgrades. |
| **Option C: Migrate code to mcp 2.0 import paths** | Rewrite all 13 import statements to use mcp 2.0 module paths (e.g., `from mcp import FastMCP` or equivalent new form). | Future-proofs code; allows using new mcp 2.0 features if released. | Large surface area (10+ files to edit); requires testing against mcp 2.0 API stability; mcp 2.0 import structure not documented in this repo (external risk). Ticket is labeled "bug fix", not "feature add" or "migration". Blocks immediate fix. | Ticket description does not indicate mcp 2.0 support is planned; the mcp SDK is external (Anthropic's MCP package). | **REJECTED** — Out of scope for a bug fix; deferred to future feature work. |

---

## Assumption Ledger

| ID | Assumption / Claim | Type | Evidence For | Evidence Against / Unknowns | Risk | Validation / Challenge Required | Decision |
|----|--------------------|------|--------------|------------------------------|------|--------------------------------|----------|
| A1 | mcp 1.19.0 exports `mcp.server.fastmcp.FastMCP` and `mcp.server.fastmcp.Context` and they work as used in the code. | CODE PROPERTY | uv.lock:193 pins to mcp 1.19.0; current code runs tests and builds successfully (per ticket, it was working before the new-install issue). Dockerfile and build.py package the code. | We do not have mcp 1.19.0 or 2.0 source code in this repo to inspect the module structure directly. Assuming mcp SDK follows semantic versioning (1.x → 2.x is major bump). | MEDIUM | Run the test suite after applying the pin fix to confirm imports still pass. The CI workflow (test.yml) already does this on every commit. | **VALIDATE** — Run `make test` or `pytest` after pin change; should pass. |
| A2 | mcp 2.0 removed or moved `mcp.server.fastmcp` module, causing `ModuleNotFoundError`. | ROOT CAUSE | Ticket description states: "Python MCP SDK released version 2.0 and all those servers pin that package to '>=1.19.0' style (unbounded upper bound). New installs pull 2.0, and the module names those servers import have changed in 2.0. Traceback: `from mcp.server.fastmcp import FastMCP, Icon` -> `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`". Confirmed by sharder. | We have not tested mcp 2.0 ourselves; relying on ticket description and sharder analysis. | HIGH | Inspect mcp 2.0 release notes or GitHub repo (anthropic-ai/python-sdk / model-context-protocol) to confirm module path changed. Or, test with `pip install mcp==2.0` and try the import. | **VALIDATE** — External dependency behavior; must confirm before finalizing the bound version. If mcp 2.0.x still breaks fastmcp, bound is correct. If a later mcp 1.x (e.g., 1.20) is released and also breaks fastmcp, we may need tighter bound. |
| A3 | Unbounded pin `>=1.19.0` allows pip/uv to resolve to any version >= 1.19.0, including 2.0.0 (when released). | PIP/UV BEHAVIOR | Standard pip/uv/poetry resolution logic: `>=X` means "X or any later version". mcp 2.0 is numerically >= 1.19.0, so it matches the constraint. Confirmed by uv.lock snapshot showing current resolve to 1.19.0, but lockfile is not kept on fresh clone (fresh installs use pyproject.toml only). | If mcp is pinned to a pre-release (e.g., `mcp>=1.19.0rc1`), the behavior could differ. Current pyproject.toml does not use pre-release syntax. | LOW | Standard behavior; no validation needed. |
| A4 | The safe pin form is `mcp[cli]>=1.19.0,<2` (or `<2.0`), capping mcp to 1.x only. | PIN FORM | Python packaging standard: comma-separated version specifiers. `<2` is equivalent to `<2.0.0` in semantic versioning. Prevents mcp 2.0.x from being selected. Example: `Flask>=1.0,<2` is common pattern. | The exact upper bound (1.19.0 vs 1.20 vs 1.21) could differ if later 1.x releases are made. Ticket does not confirm whether mcp 1.20+ will also export fastmcp. | MEDIUM | Assume current 1.x series (up to latest 1.x) will keep fastmcp; apply `<2` bound. If a later 1.x breaks fastmcp, a new bug ticket would be filed. | **ASSUME + VALIDATE** — Use `<2` form; validate by testing import after applying the pin. If future 1.x breaks it, that is a separate bug. |
| A5 | No runtime data reads or writes occur in this change; it is pure packaging/dependency. | FIX SCOPE | Ticket is labeled "dependency-version-pin bug fix". The change modifies only pyproject.toml:20 (one line). No code changes to logic, config, database, API calls, or env-var reads. The import is resolved at install time, not runtime. | We have not run the code with mcp 2.0 to see if runtime behavior differs (but that is out of scope—the code breaks before it runs). | LOW | Review change: only pyproject.toml is modified. No test data, fixtures, or mocked API responses are added. | **VALIDATE** — Confirm only pyproject.toml:20 is changed in the final PR. |
| A6 | The import smoke test (a test that actually imports `mcp.server.fastmcp` symbols) will fail if the pin allows mcp 2.0. | TEST VALIDITY | tests/conftest.py:6 and tests/test_integration.py:6+75+98 import `Context` and `FastMCP` from `mcp.server.fastmcp`. Running `pytest` will execute these imports. If mcp 2.0 is installed, the import fails and the test suite fails to even load. | We have not tested with mcp 2.0; but the import is explicit and top-level, so failure is certain if the module is moved/removed in 2.0. | LOW | Run the CI workflow (test.yml) after applying the pin to confirm tests pass. The workflow runs on both Python 3.11 and 3.12. | **VALIDATE** — CI smoke test is built-in; pytest discovery will fail if import breaks. |

---

## Test Validity Strategy

### Required Test Shape
An **import smoke test** that verifies `mcp.server.fastmcp.FastMCP` and `mcp.server.fastmcp.Context` can be imported and are the correct types. Existing tests in conftest.py (line 6) and test_integration.py (lines 6, 75, 98) already do this at the top level; if these imports fail, pytest cannot even discover or run tests.

**Additionally:** A **version-constraint guard test** that verifies the installed mcp version is 1.x, not 2.0+. Example:
```python
def test_mcp_version_is_1x():
    """Verify mcp is pinned to 1.x to prevent import path breakage."""
    import mcp
    version_tuple = tuple(int(x) for x in mcp.__version__.split('.')[:2])
    assert version_tuple[0] == 1, f"Expected mcp 1.x, got {mcp.__version__}"
```

### Mock Reality Rule
**DO NOT mock the import.** The entire point of this fix is to ensure the real import path still works. Mocking `mcp.server.fastmcp` would hide the bug. Tests must import the real module from the installed mcp package.

Current test structure (conftest.py:6, test_integration.py:6) already does this correctly: it directly imports `Context` from the real mcp package. No mocking is needed.

### Assumption-Challenge Case
A test that would fail if the pin allowed mcp 2.0:
```python
@pytest.mark.asyncio
async def test_fastmcp_import_with_context_parameter():
    """Verify mcp.server.fastmcp.Context is available and used in tool handlers."""
    # This test fails immediately if mcp 2.0 is installed (import fails).
    from mcp.server.fastmcp import FastMCP, Context
    from src.tools.bucket_manager import BucketManager
    
    # Verify Context is a real type hint, not a mock.
    import inspect
    sig = inspect.signature(BucketManager.__init__)
    assert 'ctx' in sig.parameters
    assert sig.parameters['ctx'].annotation == Context
```

This test is a refinement of the existing test_integration.py structure. If mcp 2.0 is installed, the first `import` line fails and pytest reports the error before running any assertion.

### Evidence (Existing Tests)
- `tests/conftest.py:6` — `from mcp.server.fastmcp import Context` (fixture `mock_context` uses it)
- `tests/test_integration.py:6` — `from mcp.server.fastmcp import FastMCP` (test class imports it)
- `tests/test_integration.py:75, 98` — Inline imports inside async test methods
- `tests/test_team_manager.py`, `tests/test_bucket_manager.py`, etc. — All import Context indirectly via conftest fixture

**None of these tests mock the import.** All use the real module. Thus, the import smoke test is **already in place**. If the pin is wrong (allows mcp 2.0), `pytest` will fail immediately on import discovery.

---

## Current State

### Relevant Files

| File | Line Range | Description |
|------|-----------|-------------|
| pyproject.toml | 19–27 | Dependencies section; line 20 has the unbounded mcp pin |
| uv.lock | 192–209+ | Lock file showing current resolve to mcp 1.19.0; confirms 1.19.0 exports the needed modules |
| main.py | 1–14 | Entry point; line 8 imports FastMCP from mcp.server.fastmcp |
| src/server.py | 1–30 | Registers all tool managers; calls their register() functions |
| src/tools/bucket_manager.py | 1–98 | Example manager; line 5 imports Context from mcp.server.fastmcp; register() decorator uses mcp.tool() |
| src/tools/team_manager.py | 1–50+ | Similar pattern; line 5 imports Context |
| src/tools/test_manager.py | 1–50+ | Similar pattern; line 5 imports Context |
| src/tools/step_manager.py | 1–50+ | Similar pattern; line 8 imports Context |
| src/tools/environment_manager.py | 1–50+ | Similar pattern; line 5 imports Context |
| src/tools/schedule_manager.py | 1–50+ | Similar pattern; line 5 imports Context |
| src/tools/result_manager.py | 1–50+ | Similar pattern; line 6 imports Context |
| src/tools/version_manager.py | 1–50+ | Similar pattern; line 3 imports Context |
| tests/conftest.py | 1–50+ | Pytest fixtures; line 6 imports Context from mcp.server.fastmcp |
| tests/test_integration.py | 1–120+ | Integration tests; lines 6, 75, 98 import FastMCP and Context |
| Dockerfile | 15–42 | Docker build; line 30 installs package with dependencies; line 40 runs main.py --mcp |
| build.py | 1–95 | PyInstaller build script; lines 81–89 package main.py and source files |
| .github/workflows/test.yml | 1–79 | CI workflow; line 27 installs `.[test]`; line 31 runs pytest (which imports mcp.server.fastmcp in conftest.py) |
| Makefile | 1–61 | Development targets; line 22 runs pytest; line 45 runs lint |

### Root Cause / Gap
**Unbounded `mcp[cli]>=1.19.0` pin in pyproject.toml:20** allows pip/uv to resolve to any version >= 1.19.0. When mcp 2.0 was released, new installations (fresh `pip install` or `uv sync` with no lockfile) pull mcp 2.0. The mcp 2.0 release moved the `mcp.server.fastmcp` module to a different import path or removed it entirely. When the code tries to execute `from mcp.server.fastmcp import FastMCP` (main.py:8), it fails with:
```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

This breaks:
1. **Direct installation:** `pip install .` or `pip install mcp-bzm-apitest` (from PyPI, if released with unbounded pin)
2. **Docker build:** `docker build -t ...` → installs with unbounded pin → mcp 2.0 → import fails → container build fails
3. **PyInstaller binary build:** `python build.py` → similar breakage
4. **PAG (Perforce Agentic Gateway) new install:** PAG installs mcp-bzm-apitest (and perfecto-mcp) with dependencies from pyproject.toml → unbounded pin → mcp 2.0 → import error

The ticket confirms this: "Runscope MCP new installation via PAG not working. Root cause already confirmed by the sharder: `mcp[cli]>=1.19.0` in pyproject.toml (line 20) has no upper bound and resolves to mcp 2.0, which broke the `mcp.server.fastmcp` import path."

---

## Desired State Delta

| What | File | Change |
|------|------|--------|
| mcp version pin | pyproject.toml | Line 20: Change `"mcp[cli]>=1.19.0"` to `"mcp[cli]>=1.19.0,<2"` (or `<2.0`) |

**Expected outcome:** After change, new installations (fresh `pip install` or `uv sync` with no pre-existing lockfile) will resolve to mcp 1.19.0, 1.19.1, or any later 1.x version (up to but not including 2.0). The `from mcp.server.fastmcp import FastMCP, Context` imports will succeed. The code will run. PAG installations will succeed. Docker builds will succeed. PyInstaller binaries will build and run.

---

## Files the Planner Must Read for spec.md

- pyproject.toml (full file; focus on line 20)
- tests/test_integration.py (to understand import coverage)
- .github/workflows/test.yml (to understand CI smoke test)
- Dockerfile (to understand runtime packaging)
- build.py (to understand frozen build)

---

## Planner Blockers

- **VALIDATE A2 (external):** Confirm mcp 2.0 release notes or source code shows the `mcp.server.fastmcp` module was removed or moved. This is external to the repo (Anthropic's MCP SDK). The ticket description claims this; sharder confirmed it. If this is incorrect, the pin fix may be unnecessary or insufficient. **Resolution:** Check mcp 2.0 release notes at https://github.com/anthropic-ai/python-sdk or https://github.com/modelcontextprotocol/python-sdk (or wherever Anthropic publishes mcp) before finalizing the spec.

- **VALIDATE A4 (upper bound form):** Decide whether `<2` or `<2.0` is the correct syntax (both are equivalent in PEP 440; either is fine). Recommend `<2` for brevity (common in pip specs). Document choice in spec.md.

---

## overall_finding

**brownfield** (dependency-version-pin bug fix; no new identifiers, no new runtime behavior, no new APIs)

### Summary for Planner

**Forbidden identifiers:** 0
**Ambiguous identifiers:** 0
**Recommended pin string:** `mcp[cli]>=1.19.0,<2` (evidence: ticket description, pyproject.toml:20, mcp 2.0 breaking change)
**Key binding decisions:**
  1. Upper-bound cap at mcp 1.x only (do not allow 2.x)
  2. Keep using existing `mcp.server.fastmcp.FastMCP` and `mcp.server.fastmcp.Context` imports (DO NOT migrate to mcp 2.0 paths in this fix)
  3. Verify import smoke test passes after pin change (CI already covers this)

**Planner blockers:**
  1. Confirm mcp 2.0 release notes show fastmcp module was moved/removed (external validation; ticket description provides claim)
  2. Confirm upper-bound form `<2` vs `<2.0` (either works; recommend `<2`)

**Files to read for spec.md:**
  - pyproject.toml (dependency pin location)
  - tests/test_integration.py (import smoke test evidence)
  - .github/workflows/test.yml (CI coverage)
  - Dockerfile, build.py (packaging context)

---



## Cross-Service Contract Verification

Not applicable. No cross-service/API capability is selected or consumed by this change (see § Cross-Repo Capability Analysis — `NOT APPLICABLE`). There is no downstream service route, schema, query, client, or fixture to verify because the fix is a dependency-version-pin change with no runtime service interaction. No live/dev/stage/prod endpoint is called during planning or implementation.

## Field/Metric Provenance Matrix

Not applicable — `none`. This change derives, aggregates, formats, or renders no output field or metric from any downstream service/API response. It edits a single dependency specifier in `pyproject.toml` and adds a regression guard test; there is no data flow and therefore no field to prove provenance for. Evidence: § Runtime Data Availability Proof (`none`) and § Cross-Repo Capability Analysis (`NOT APPLICABLE`) above.


## Boundary Compatibility Analysis

The only boundary this change touches is the import boundary between the mcp SDK (producer) and this server (consumer). The change adds a version cap; it does not reshape any payload.

| Boundary | Producer / Source Shape | Consumer / Helper Expected Shape | Compatibility Proof | Adapter / Mapping | Decision |
|----------|-------------------------|----------------------------------|---------------------|-------------------|----------|
| mcp SDK import surface -> server import sites | mcp 1.x exposes `FastMCP` class and `Context` type at module `mcp.server.fastmcp` (source: FILE:main.py:8) | main.py and 8 tool managers import `FastMCP` / `Context` from `mcp.server.fastmcp` and expect those symbols (consumer input; source: FILE:src/tools/bucket_manager.py:5) | Equivalent and compatible: capping to the 1.x line keeps the producer module path identical to what the consumer imports; mcp 1.19.0 exports these symbols today (source: FILE:uv.lock:193) | No adapter needed — shapes are identical under the cap | USE |

The compatibility is proven (not unknown): the producer and consumer shapes are identical because the cap preserves the mcp 1.x module layout. No incompatible/unknown row exists, so no adapter is required.
