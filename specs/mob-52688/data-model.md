# Phase 1 Data Model: MOB-52688

This feature introduces no new persisted entities, database tables, or Pydantic response models. It is a dependency-version-pin fix.

## Entities

None. No data is created, read, updated, or deleted at runtime by this change.

## Configuration artifacts (not runtime data)

| Artifact | File | Field | Change |
|----------|------|-------|--------|
| mcp dependency specifier | pyproject.toml:20 | `dependencies[]` entry `mcp[cli]` | add `,<2` upper bound |
| resolved lockfile (optional) | uv.lock:192-195 | `mcp` package `version` | must remain a 1.x resolution |

## Import surface (contract, not data)

| Symbol | Module | Type | Consumers |
|--------|--------|------|-----------|
| `FastMCP` | `mcp.server.fastmcp` | class | main.py:8, tests/test_integration.py:6 |
| `Context` | `mcp.server.fastmcp` | type | 8 tool managers, tests/conftest.py:6, tests/test_integration.py:75,98 |

These must remain importable after the pin change.
