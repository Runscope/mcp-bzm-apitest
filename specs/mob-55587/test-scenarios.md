# Test Scenarios: MOB-55587 — extend blazemeter_apitest_steps

> Planner-seeded scenario set. task-test-author owns the final red tests; this file
> establishes the AC-coverage map and the test names referenced in spec.md's
> Requirement Traceability Matrix. All tests mock `src.tools.step_manager.api_request`;
> none call live/dev/stage/prod endpoints.

**Total: 13**
**Negative: 38%** (5 of 13 are negative-path scenarios)

| S# | Test name | Type | AC | Description |
|----|-----------|------|----|-------------|
| S1 | test_add_inbound_step | happy-path | AC-1 | POST body is `{step_type:"inbound", token, isDynamicUrl}`; returned step has `step_type == "inbound"`. |
| S2 | test_add_condition_step | happy-path | AC-1 | POST body uses `step_type:"condition"` (not `"conditional"`) + `condition_type:"start"`; no explicit end block sent; mocked response returns start+end (auto-end). |
| S3 | test_add_conditional_loop_step | happy-path | AC-1 | POST body uses `step_type:"conditional-loop"` + `condition_type:"start"`; no explicit end block. |
| S4 | test_add_subtest_step | happy-path | AC-1 | POST body carries required subtest fields; builder does not pre-validate `test_uuid` (lazy). |
| S5 | test_teststep_model_roundtrip_inbound_subtest | happy-path | AC-1 | inbound (`token`,`isDynamicUrl`) and subtest (`trigger_token`,`environment_id`,`use_parent_environment`,`params`) survive `format_steps` without dropping fields. |
| S6 | test_add_inbound_step_missing_field | negative | AC-1 | Inbound add with a missing required field surfaces a categorized API error (negative). |
| S7 | test_add_condition_step_invalid_comparison | negative | AC-1 | Condition add with an invalid `comparison` surfaces a categorized parser 400 (negative, lazy validation). |
| S8 | test_update_step | happy-path | AC-2 | read → merge `updates` → `PUT /steps/{step_id}` with the full step dict; returns updated step. |
| S9 | test_update_step_unknown_id | negative | AC-2 | `update_step` on an unknown `step_id` yields a `BaseResult(error=...)` not-found (negative). |
| S10 | test_reorder_steps | happy-path | AC-3 | flat-id `template_order` PUT to `/steps`; reordered list returned. |
| S11 | test_reorder_steps_missing_id | negative | AC-3 | reorder with a non-list / missing-id input yields an error (negative). |
| S12 | test_steps_dispatch_new_actions | happy-path | FR-008 | each of the 6 new `action` values routes to its builder with unpacked args. |
| S13 | test_new_actions_error_handling | negative | FR-010 | an `httpx.HTTPStatusError` in a new action surfaces as a categorized `http_error_message` (no raw status/trace/token) (negative). |

## AC coverage map

| AC | Scenarios |
|----|-----------|
| AC-1 add new step types | S1, S2, S3, S4, S5, S6, S7 |
| AC-2 modify existing step | S8, S9 |
| AC-3 change step order | S10, S11 |
| FR-008 registration | S12 |
| FR-010 error handling | S13 |

## Assumption-challenge coverage

- A-AUTO-END → S2 (condition POST returns start+end).
- Wire-format (condition not conditional) → S2.
- A-SUBTEST-LAZY (no test_uuid pre-check) → S4.
- A-LOOP-REORDER (flat-id reorder works; nesting not exercised) → S10, S11.
