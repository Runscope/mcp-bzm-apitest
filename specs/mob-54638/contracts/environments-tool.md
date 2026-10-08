# MCP Tool Contract: `blazemeter_apitest_environments`

Single tool, action-routed. Existing actions `list`/`read` retained; `create`/`modify` added; `list`/
`read` extended to the shared (bucket-level) scope. Returns `BaseResult` for every action. No `delete`
action.

## Action: `list`

Lists environments for a scope.

- **args (local)**: `{ "bucket_key": str, "test_id": str }` → GET `/buckets/{key}/tests/{id}/environments`
- **args (shared)**: `{ "bucket_key": str }` (no `test_id`) → GET `/buckets/{key}/environments`
- **returns**: `BaseResult(result=[Environment, …])`

## Action: `read`

Reads a single environment by id.

- **args (local)**: `{ "bucket_key": str, "test_id": str, "environment_id": str }` → GET `/buckets/{key}/tests/{id}/environments/{env_id}`
- **args (shared)**: `{ "bucket_key": str, "environment_id": str }` → GET `/buckets/{key}/environments/{env_id}`
- **returns**: `BaseResult(result=Environment)`
- **errors**: invalid id → not-found message

## Action: `create`

Creates a shared or local environment.

- **args (local)**: `{ "bucket_key": str, "test_id": str, "name": str, "initial_variables"?: dict, "regions"?: list, "remote_agents"?: list, … }` → POST `/buckets/{key}/tests/{id}/environments`
- **args (shared)**: `{ "bucket_key": str, "name": str, "initial_variables"?: dict, … }` (no `test_id`) → POST `/buckets/{key}/environments`
- **body**: `CreateEnvironment` model dumped `by_alias=True, exclude_none=True`
- **returns**: `BaseResult(result=Environment)` (201)
- **errors**: limit reached (API 400) → surfaced via `http_error_message`; invalid bucket/test → not-found; validation → validation message

## Action: `modify`

Partial update (PATCH). Only supplied fields change; all others (incl. `remote_agents`) preserved.

- **args (local)**: `{ "bucket_key": str, "test_id": str, "environment_id": str, <fields to change> }` → PATCH `/buckets/{key}/tests/{id}/environments/{env_id}`
- **args (shared)**: `{ "bucket_key": str, "environment_id": str, <fields to change> }` → PATCH `/buckets/{key}/environments/{env_id}`
- **body**: `ModifyEnvironment` model dumped `by_alias=True, exclude_none=True` (only changed fields)
- **agent-swap**: `{ "remote_agents": [<new agent>] }` → new agent set, everything else preserved
- **empty payload**: returns current environment unchanged (no write)
- **returns**: `BaseResult(result=Environment)`
- **errors**: invalid id → not-found; validation → validation message; auth/consent → auth message

## Auth / consent / limits

- PAT applied in `api_request()`; RBAC + ai_consent enforced server-side by the `api` service for the
  `bzm-apitest-mcp` user-agent. The tool adds no consent check and no bypass.
- Caps (100 shared/bucket, 100 local/test) enforced + messaged by the API; surfaced unchanged.

## No `delete`

A delete action is intentionally absent (FR-012 — destructive ops out of scope).
