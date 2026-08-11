# Quickstart: MOB-52688 mcp SDK Pin Fix

## What changes

1. `pyproject.toml:20`: `"mcp[cli]>=1.19.0"` → `"mcp[cli]>=1.19.0,<2"`.
2. New test `tests/test_mcp_dependency_pin.py` guarding the version cap and the `mcp.server.fastmcp` import surface.

## Verify locally

```bash
# From the repo root, in a clean venv (no pre-existing lockfile respected):
pip install -e ".[test]"

# Confirm the resolved mcp is 1.x, not 2.x:
python -c "import mcp; print(mcp.__version__)"   # expect 1.x

# Confirm the import surface works:
python -c "from mcp.server.fastmcp import FastMCP, Context; print('ok')"

# Run the guard test + full suite (Python 3.11 and 3.12 in CI):
make test
```

## Expected result

- `mcp.__version__` starts with `1.`
- The `mcp.server.fastmcp` import prints `ok`
- `tests/test_mcp_dependency_pin.py::test_mcp_version_is_1x` and `::test_fastmcp_import_surface` pass
- The full existing suite continues to pass unchanged

## Regression it prevents

A fresh install pulling mcp 2.0 → `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` at server startup (the reported PAG failure). After the cap, fresh installs stay on mcp 1.x and the server starts.
