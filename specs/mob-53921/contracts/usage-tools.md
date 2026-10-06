# MCP Tool Contract: Usage-retrieval tools (MOB-53921)

Three new read-only MCP tools under `TOOLS_PREFIX` `blazemeter_apitest`. Each returns a `BaseResult` whose `result` carries the usage model. All HTTP goes through `api_request`; all errors through `http_error_message`.

## `blazemeter_apitest_team_usage`
- **Action:** `read`
- **Args:** `team_uuid` (required); `from`/`to`/`days`/`date` (optional)
- **Calls:** `GET /team/<team_uuid>/requests` (api, exists)
- **Returns:** `BaseResult(result=TeamUsage(team_uuid, requests_count, from_date, to_date))`
- **Description note:** read-only; 90-day maximum lookback (older data unavailable); default window = today when no date params given.

## `blazemeter_apitest_bucket_usage`
- **Action:** `read`
- **Args:** `bucket_key` (required); `from`/`to`/`days`/`date` (optional)
- **Calls:** `GET /buckets/<bucket_key>/requests` (api, exists)
- **Returns:** `BaseResult(result=BucketUsage(bucket_key, requests_count, from_date, to_date))`

## `blazemeter_apitest_test_usage`
- **Action:** `read`
- **Args:** `bucket_key` (required), `test_uuid` (required); `from`/`to`/`days`/`date` (optional)
- **Calls:** `GET /buckets/<bucket_key>/tests/<test_uuid>/requests` (api, NEW in this shard)
- **Returns:** `BaseResult(result=TestUsage(test_uuid, requests_count, from_date, to_date))`

## Error contract (all three)
- 401/403 → `BaseResult.error` (auth/permission) via `http_error_message`
- 404 → `BaseResult.error` (not found)
- 5xx / unreachable → `BaseResult.error` (server error); never a fabricated or zero count
- success with `requests_count: 0` → legitimate `0` (no data in window)
- unknown action → `BaseResult.error = "Unknown action: <action>"`

## Invariants
- Read-only — no mutating action exposed.
- `requests_count` = api `data.requests_count` (faithful pass-through; no re-aggregation).
- No new auth path; `BzmApimToken` passed to `api_request`; api enforces RBAC + AI-consent.
- scorekeeper's internal list-typed `test_id` is NOT exposed to the tool user.
