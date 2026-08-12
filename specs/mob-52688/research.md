# Phase 0 Research: MOB-52688 mcp SDK Pin Fix

All Technical Context items were resolvable from the repo and brownfield research; no open clarification markers remained. Findings below.

## Decision: Upper-bound cap `mcp[cli]>=1.19.0,<2`

- **Decision**: Change pyproject.toml:20 from `"mcp[cli]>=1.19.0"` to `"mcp[cli]>=1.19.0,<2"`.
- **Rationale**: The unbounded `>=1.19.0` lets a fresh resolve pick mcp 2.0.x, which moved the `mcp.server.fastmcp` module and breaks all 13 import sites (ticket traceback: `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`). The upper bound caps to the 1.x line while allowing safe patch/minor upgrades. Standard major-version-cap convention.
- **Alternatives considered**:
  - Exact-pin `==1.19.0` — REJECTED: blocks 1.x security/patch upgrades.
  - Migrate code to mcp 2.0 import paths — REJECTED: large surface (13 sites), out of scope for a bug fix, deferred to feature work.

## Decision: Preserve the `mcp.server.fastmcp` import surface

- **Decision**: Do not change any import site. `FastMCP` and `Context` continue to be imported from `mcp.server.fastmcp`.
- **Rationale**: mcp 1.19.0 (uv.lock:193) exports these symbols and the code works today under the lockfile. Capping to the 1.x line keeps that surface valid. Migrating imports is explicitly out of scope.
- **Evidence**: main.py:8; src/tools/{bucket,team,test,environment,schedule,result,step,version}_manager.py; tests/conftest.py:6; tests/test_integration.py:6,75,98.

## Decision: Regression guard via a real-import test

- **Decision**: Add `tests/test_mcp_dependency_pin.py` with a version-major assertion and an import-surface assertion, using the real installed mcp (no mocks).
- **Rationale**: The bug was invisible to lockfile-respecting checkouts. A real-import guard converts a silent new-install failure into a loud CI failure. Mocking the import would defeat the purpose (Test Validity Strategy).
- **Alternatives considered**: relying solely on existing tests' collection-time imports — insufficient because they do not assert the mcp *version* cap, only that the current install imports; an explicit version guard catches a future removal of the cap.

## Decision: uv.lock left as-is (optional regenerate)

- **Decision**: Do not require lockfile regeneration; current uv.lock already resolves mcp 1.19.0, valid under the new cap.
- **Rationale**: The reported failure is on fresh installs from pyproject.toml (no lockfile). The committed lockfile is already correct. If regenerated, it must still land on a 1.x mcp with no unrelated churn.

## Runtime data / cross-service

None. Confirmed no runtime data reads and no cross-service capability consumed (brownfield-context.md §§ Runtime Data Availability, Cross-Repo Capability Analysis).
