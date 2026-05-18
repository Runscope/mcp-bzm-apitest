# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BlazeMeter API Test MCP Server — bridges AI tools (Claude, VS Code, Cursor) to the BlazeMeter/Runscope API Testing platform via the Model Context Protocol. Exposes teams, buckets, tests, steps, schedules, results, and environments as MCP tools.

## Commands

```bash
# Install (with test deps)
make install                # or: pip install -e ".[test]"

# Run tests
make test                   # Full suite with coverage
make test-fast              # Stop on first failure (-x)
make test-unit              # Unit tests only (excludes @pytest.mark.integration)
make test-integration       # Integration tests only
pytest tests/test_api_client.py::TestApiClient::test_api_request_success -v  # Single test

# Lint & format
make lint                   # flake8 + black --check + isort --check-only
make format                 # black + isort (auto-fix)

# Build standalone binary (requires build deps — not needed for Docker)
pip install -e ".[build]"   # install PyInstaller (build-only dependency)
python build.py             # PyInstaller → dist/mcp-bzm-apitest-{os}-{arch}

# Build Docker image (uses Python runtime, no binary needed)
docker build -t mcp-bzm-apitest .
```

## Architecture

**Entry point:** `main.py` — CLI that starts a FastMCP server on stdio (`--mcp` flag) or shows setup instructions (no args).

**Core flow:**
```
main.py → FastMCP server → server.py:register_tools() → 8 Tool Managers
```

**Key layers (`src/`):**

| Layer | Purpose |
|-------|---------|
| `tools/` | MCP tool managers — one per domain (team, bucket, test, step, schedule, result, environment, version). Each has a class with action methods + a `register()` function that decorates handlers with `@mcp.tool()`. |
| `models/` | Pydantic models. `BaseResult` is the universal tool response (result, total, has_more, error, info, warning, hint). Domain models extend it. |
| `formatters/` | Transform raw API JSON responses into Pydantic models. Passed as optional callbacks to `api_request()`. |
| `common/api_client.py` | Single async `api_request()` function — handles auth (Bearer token), error codes (401/403), and optional response formatting. |
| `common/errors.py` | Shared error helpers — `http_error_message()` converts HTTP errors into categorized LLM-friendly messages (auth/not-found/rate-limit/server-error), and `UNEXPECTED_ERROR_MESSAGE` for non-HTTP errors. Used by all tool managers. |
| `config/` | `token.py` (token validation + file loading with LRU cache), `defaults.py` (API endpoints/base URL), `version.py` (version extraction from pyproject.toml). |

**Domain hierarchy enforced by tool instructions:** Teams → Buckets → Tests → (Schedules / Steps / Results / Environments)

**Token resolution order:** `BZM_API_TEST_TOKEN` env var → `BZM_API_TEST_TOKEN_FILE` path → local `bzm_api_test_token.env` file.

## Code Style

- **Line length:** 108 characters (black, flake8, isort all aligned)
- **Imports:** isort with black-compatible profile
- **Max complexity:** 10 (flake8)
- **Async:** pytest-asyncio in `auto` mode — test functions are automatically treated as async
- **CI matrix:** Python 3.11, 3.12 on Ubuntu
- **Known issue:** `black` 24.x+ fails on Python 3.12.5. Run lint with `--target-version py311` or use Python 3.12.4 / 3.12.6+. The `make lint` and `make format` targets pass `--target-version py311` explicitly to work around this.

## Testing Conventions

- Tests in `tests/` mirror source structure (`test_<module>.py`)
- Fixtures in `tests/conftest.py` — mock token, context, sample API responses
- Mocking with `unittest.mock` (Mock, AsyncMock) — API calls are mocked, not live
- Markers: `@pytest.mark.integration`, `@pytest.mark.unit`, `@pytest.mark.slow`
- Coverage targets `src/` only
