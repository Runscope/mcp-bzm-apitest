# Phase 1 Data Model: Environment Management MCP Tools (MOB-54638)

## Entity: Environment (existing — reused)

Defined at `src/models/environment.py:14-95`. Response model, parsed by `format_environments`. Key
fields relevant to this feature:

| Field | Type | Role in this feature |
|-------|------|----------------------|
| `environment_id` (alias `id`) | str | Returned on read/create/modify; input to read/modify |
| `test_id` | str | Distinguishes local (present) vs shared (absent) scope |
| `name` | str | Required on create; modifiable |
| `initial_variables` | Dict[str, str] | Set on create; modifiable |
| `regions` | list[str] | Set on create; modifiable |
| `remote_agents` | list[Dict[str, str]] | **Agent-swap target**; preserved on partial modify unless supplied |
| (notification/SSL/cookie/script fields) | various | Optional; pass-through |

No change to the `Environment` response model is expected.

## Entity: CreateEnvironment / ModifyEnvironment (new — request models)

A typed request model (or a pair) for validating create/modify input before the API call
(constitution V, FR-013). Mirrors `CreateSchedule` (`src/models/schedule.py:10-28`).

**CreateEnvironment** (writable fields; alias-mapped; `exclude_none` on dump):

| Field | Type | Required? | Notes |
|-------|------|-----------|-------|
| `name` | str | yes | Environment name |
| `initial_variables` | Optional[Dict[str, str]] | no | Env variables |
| `regions` | Optional[list[str]] | no | Execution regions |
| `remote_agents` | Optional[list[Dict[str, str]]] | no | Private/public agents |
| (other common optional toggles) | Optional | no | preserve_cookies, verify_ssl, etc. as needed |

**ModifyEnvironment** — the same writable fields, ALL optional, so a PATCH body carries only the
fields the caller wants to change (partial update). Serialized with `by_alias=True, exclude_none=True`
so unspecified fields are omitted from the PATCH body and thus preserved server-side.

Validation rules:
- `name` required and non-empty for create.
- At least one field present for modify (empty modify → return current env unchanged, no API write).
- Field aliases match the API's wire names (consistent with the existing `Environment` aliases).

## Scope routing

| Scope | Determined by | Endpoint template |
|-------|---------------|-------------------|
| local (test-level) | `test_id` present | `TEST_ENVIRONMENT_ENDPOINT` = `/buckets/{}/tests/{}/environments` |
| shared (bucket-level) | `test_id` absent | `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT` = `/buckets/{}/environments` (new constant) |
| single (read/modify) | `environment_id` + scope | `.../environments/{environment_id}` |

## State transitions

Environments have no lifecycle state machine. Operations: create → read/modify (repeatable). No
delete (out of scope, FR-012).
