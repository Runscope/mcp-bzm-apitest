# Quickstart: MOB-55587 implementation

## Where the work goes
- `src/tools/step_manager.py` — add 6 async builder methods + 6 `case` branches in `register()` + 6 tool-description entries.
- `src/models/step.py` — extend `TestStep` with `token`, `is_dynamic_url` (alias `isDynamicUrl`), `trigger_token`, `environment_id`, `use_parent_environment`, `params` (all `Optional`, default `None`).
- `tests/test_step_manager.py` + `tests/conftest.py` — failing tests first (constitution III), then make them pass.

## Pattern to copy
`add_pause_step` / `add_request_step`: build a flat body dict with a literal `step_type`, then `return await api_request(self.token, "POST"/"PUT", endpoint, result_formatter=format_steps, json=body)`. Modify uses `_put_step`; reorder uses `PUT` on the list endpoint.

## Must-not
- Do NOT send `"conditional"` as the if-step wire key — use `"condition"`.
- Do NOT send an explicit conditional/loop `end` block — the parser adds it.
- Do NOT pre-validate subtest `test_uuid`.
- Do NOT add a second HTTP call site — everything goes through `api_request()`.

## Verify
```bash
make test        # full suite with coverage — must pass, no regression to request/pause
make lint        # flake8 + black --check + isort (py311 target)
```

## Test checklist
- `test_add_inbound_step` — asserts POST body `{step_type:"inbound", token, isDynamicUrl}`.
- `test_add_condition_step` — asserts body uses `step_type:"condition"` + `condition_type:"start"`, no end block; mocked response returns start+end.
- `test_add_conditional_loop_step` — asserts `step_type:"conditional-loop"`.
- `test_add_subtest_step` — asserts required subtest fields; no `test_uuid` pre-check.
- `test_update_step` — read→merge→PUT /steps/{id}; unknown id → error.
- `test_reorder_steps` — PUT list; missing-id → error path.
- `test_teststep_model_roundtrip_inbound_subtest` — inbound/subtest response fields survive `format_steps`.
- `test_steps_dispatch_new_actions` — each new action routes to its builder.
```
