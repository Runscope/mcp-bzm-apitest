# Phase 1 Data Model: MOB-55587

The tool is a stateless adapter; the only data entities are the request bodies it POSTs/PUTs and the `TestStep` response model it returns.

## Radar-input step bodies (what the tool POSTs to `POST /steps`)

| Step type (`step_type`) | Fields | Required | Notes |
|---|---|---|---|
| `inbound` | `token: str`, `isDynamicUrl: bool` | both | — |
| `condition` (if) | `condition_type: "start"`, `comparison: str`, `left_value: str`, `right_value: str`, `steps: list?` | first four | wire key is `condition`; no explicit end block |
| `conditional-loop` | `condition_type: "start"`, `comparison: str`, `left_value: str`, `right_value: str`, `steps: list?` | first four | no explicit end block |
| `subtest` | `test_uuid: str`, `trigger_token: str`, `environment_uuid: str`, `bucket_key: str`, `use_parent_environment: bool`, `params: list?` | first five | `bucket_key` here = subtest's bucket |

## Update body (what `update_step` PUTs to `/steps/{step_id}`)

The full current step dict (read via `read(..., result_formatter=None)`) with the caller's `updates` shallow-merged in. No schema change; any field the API accepts on the step.

## Reorder body (what `reorder_steps` PUTs to `/steps`)

`template_order`: an ordered JSON list. Each element is `{"id": "<step_id>"}` or, for a conditional start, `{"id": "<step_id>", "steps": [{"id": "..."}, ...]}`. Flat-id reordering of all step types supported; conditional-loop child nesting unsupported (A-LOOP-REORDER).

## `TestStep` response model (extended)

Existing fields (unchanged): `step_id` (alias `id`), `step_type`, `skipped`, `duration`, `note`, `auth`, `body`, `form`, `multipart_form`, `binary_body`, `headers`, `method`, `url`, `assertions`, `variables`, `scripts`, `before_scripts`, `steps`, `comparison`, `left_value`, `right_value`, `test_uuid`, `bucket_key`.

New fields (added by this feature, all `Optional`, default `None`):

| Field | Type | Alias | For |
|---|---|---|---|
| `token` | `Optional[str]` | — | inbound |
| `is_dynamic_url` | `Optional[bool]` | `isDynamicUrl` | inbound |
| `trigger_token` | `Optional[str]` | — | subtest |
| `environment_id` | `Optional[str]` | — | subtest |
| `use_parent_environment` | `Optional[bool]` | — | subtest |
| `params` | `Optional[List[Any]]` | — | subtest |

**Validation rules**: all new fields are optional so request/pause/condition responses that omit them still validate. `format_steps` calls `TestStep(**step).model_dump(by_alias=False)`, so aliased fields round-trip under their python names.

**State transitions**: none (stateless adapter).
