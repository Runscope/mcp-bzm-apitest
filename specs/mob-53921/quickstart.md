# Quickstart: Usage-retrieval MCP tools (consumer) — MOB-53921

## What this adds
Three new read-only MCP tools on the API Monitoring (Runscope) MCP server:

- `blazemeter_apitest_team_usage` — team request count over a window
- `blazemeter_apitest_bucket_usage` — bucket request count over a window
- `blazemeter_apitest_test_usage` — test request count over a window

Each wraps an api public usage endpoint. Default window = today when no date params; 90-day maximum lookback.

## Example (once implemented)

Agent prompt: "How many requests did my test <test_uuid> in bucket <bucket_key> make in the last week?"

The agent invokes `blazemeter_apitest_test_usage` with `action="read"`, `args={bucket_key, test_uuid, from, to}`. The tool calls `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` and returns:

```json
{"result": {"test_uuid": "<uuid>", "requests_count": 42, "from_date": "2026-09-29", "to_date": "2026-10-06"},
 "error": null}
```

## Local dev & tests

```bash
make install            # pip install -e ".[test]"
make test-unit          # unit tests (mock api_request; no live calls)
make lint               # flake8 + black --check + isort --check-only
pytest tests/test_usage_manager.py -v
```

## Key implementation anchors
- `src/config/defaults.py` — add `TEAM_USAGE_ENDPOINT` / `BUCKET_USAGE_ENDPOINT` / `TEST_USAGE_ENDPOINT`.
- `src/models/usage.py` — `TeamUsage` / `BucketUsage` / `TestUsage` (mirror `src/models/result.py`).
- `src/formatters/usage.py` — `format_team_usage` / `format_bucket_usage` / `format_test_usage` (mirror `format_results`).
- `src/tools/usage_manager.py` — `UsageManager` + `register(mcp, token)` with three `@mcp.tool` tools calling `api_request`.
- `src/server.py` — wire `usage_manager.register(mcp, token)` into `register_tools`.
- `requests_count` = api `data.requests_count` (faithful pass-through); errors via `http_error_message`.

## Out of scope
- api public usage endpoints (separate producer repo in this shard).
- scorekeeper; 90-day retention (ops); companion doc update; any UI change.
