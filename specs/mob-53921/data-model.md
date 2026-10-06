# Phase 1 Data Model: Usage-retrieval MCP tools (consumer) — MOB-53921

No persistent storage. The entities are the transient MCP tool response models and the api dependency contract.

## Response models (src/models/usage.py — extend BaseResult domain models)

### TeamUsage / BucketUsage / TestUsage

| Field | Type | Source | Notes |
|---|---|---|---|
| identifier (`team_uuid` / `bucket_key` / `test_uuid`) | string | tool arg, echoed from api `data.<id>` | which resource the count belongs to |
| `requests_count` | int | api `data.requests_count` | faithful pass-through; 0 is a legitimate value |
| `from_date` | string `YYYY-MM-DD` | api `data.from_date` | window start |
| `to_date` | string `YYYY-MM-DD` | api `data.to_date` | window end |

Each tool returns a `BaseResult` (per Constitution Principle V) whose `result` is the formatted usage model; `error` is populated via `http_error_message` on failure.

## Tool inputs (args)

| Tool | Required args | Optional args |
|---|---|---|
| team usage | `team_uuid` | `from`, `to`, `days`, `date` |
| bucket usage | `bucket_key` | `from`, `to`, `days`, `date` |
| test usage | `bucket_key`, `test_uuid` | `from`, `to`, `days`, `date` |

No date params → api defaults to today; 90-day maximum lookback (api enforces).

## Dependency contract (api — consumed, not owned)

- **Endpoints**: `GET /team/<team_uuid>/requests`, `GET /buckets/<bucket_key>/requests`, `GET /buckets/<bucket_key>/tests/<test_uuid>/requests`
- **Response**: `{data: {<identifier>, requests_count: int, from_date, to_date}, meta: {status}, error}` via `@api_marshal`
- **Date params**: optional `from`/`to`/`days`/`date`; no params → today; 90-day max
- **Auth**: PAT via `BzmApimToken`; api enforces RBAC + AI-consent; no new auth path
- **Binding mapping**: tool `requests_count` = api `data.requests_count` (direct; no re-aggregation)

## State transitions

None — each tool is stateless and read-only.
