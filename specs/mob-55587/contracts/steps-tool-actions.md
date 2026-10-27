# Contract: blazemeter_apitest_steps new actions (MOB-55587)

The tool interface is the MCP `blazemeter_apitest_steps` tool, invoked as `action` + `args`. New actions added by this feature:

## add_inbound_step
- **args**: `bucket_key` (str, req), `test_id` (str, req), `token` (str, req), `isDynamicUrl` (bool, req)
- **effect**: `POST /steps` with `{step_type:"inbound", token, isDynamicUrl}`
- **returns**: `BaseResult` with the updated step list; new step has `step_type == "inbound"`.

## add_condition_step
- **args**: `bucket_key`, `test_id`, `comparison` (str, req), `left_value` (str, req), `right_value` (str, req), `steps` (list, opt)
- **effect**: `POST /steps` with `{step_type:"condition", condition_type:"start", comparison, left_value, right_value, steps?}`. Wire key is `condition` (not `conditional`). No explicit end step.
- **returns**: step list containing the conditional start and the parser-auto-created end.

## add_conditional_loop_step
- **args**: `bucket_key`, `test_id`, `comparison`, `left_value`, `right_value`, `steps` (opt)
- **effect**: `POST /steps` with `{step_type:"conditional-loop", condition_type:"start", comparison, left_value, right_value, steps?}`. No explicit end step.
- **returns**: step list containing the loop start and the auto-created end.

## add_subtest_step
- **args**: `bucket_key`, `test_id`, `test_uuid` (str, req), `trigger_token` (str, req), `environment_uuid` (str, req), `subtest_bucket_key` (str, req), `use_parent_environment` (bool, req), `params` (list, opt)
- **effect**: `POST /steps` with `{step_type:"subtest", test_uuid, trigger_token, environment_uuid, bucket_key:subtest_bucket_key, use_parent_environment, params?}`. Lazy validation — `test_uuid` existence not pre-checked.
- **returns**: step list containing the subtest step.

## update_step
- **args**: `bucket_key`, `test_id`, `step_id` (str, req), `updates` (object, req)
- **effect**: read current step → shallow-merge `updates` → `PUT /steps/{step_id}` with the full step dict.
- **returns**: the updated step. Unknown `step_id` → categorized not-found error.

## reorder_steps
- **args**: `bucket_key`, `test_id`, `step_order` (list of `{id}` or `{id, steps:[...]}`, req)
- **effect**: `PUT /steps` with `step_order` as the `template_order` body.
- **returns**: the reordered step list. Missing ids → API 400 categorized message. Conditional-loop child nesting unsupported (A-LOOP-REORDER).

## Error contract (all actions)
All errors are surfaced via the existing categorized handling (`http_error_message` / `UNEXPECTED_ERROR_MESSAGE`). No raw status codes, stack traces, or token values in responses. Input-shape problems return `BaseResult(error=...)` directly from the builder.
