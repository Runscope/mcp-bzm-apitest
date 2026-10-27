# Phase 0 Research: MOB-55587

All unknowns were resolved confidence-first from source code (the ticket's R&D note directs reading the public API code). No unresolved clarification markers remained in the spec.

## Decision: radar input wire key for the conditional-if step is `"condition"` (not `"conditional"`)
- **Rationale**: `tea-service/parsers/radar.py` dispatches on `step_type == "condition"` for the if-branch (`radar.py:693`); the flatten logic also keys on `"condition"` (`radar.py:647-656`). The internal stored template type becomes `"conditional"`, but the **input** wire key must be `"condition"`.
- **Alternatives considered**: sending `"conditional"` as the input `step_type` — rejected; the parser would not recognize it and would 400.

## Decision: conditional/loop end block is auto-created by the parser
- **Rationale**: the parser appends `{step_type: "condition"/"conditional-loop", condition_type: "end"}` after the start + nested steps (`radar.py:656, 666`). The tool sends only the start (with optional `steps`).
- **Alternatives considered**: the tool emitting an explicit end step — rejected; would double the end marker.

## Decision: per-step-type builder methods (not a generic passthrough)
- **Rationale**: mirrors the existing `add_request_step`/`add_pause_step` builders in `src/tools/step_manager.py`; gives the LLM typed, self-documenting actions.
- **Alternatives considered**: a single generic `add_step` raw-dict action — rejected (loses per-type affordance).

## Decision: modify = per-step `PUT /steps/{step_id}` with the full step dict
- **Rationale**: `api/resources/tests.py` `TestStepInstance.put` and the existing `_put_step` helper already do this; `update_step` reads, merges, and PUTs.
- **Alternatives considered**: full test-steps PUT replace — rejected (race window + latency).

## Decision: reorder = `PUT /steps` with a `template_order` list
- **Rationale**: `api/resources/tests.py` `TestStepList.put` accepts an ordered list of `{id}` (nested `{id, steps:[...]}` only for conditional starts); 100-step cap; 400 on missing ids.
- **Known limitation (A-LOOP-REORDER)**: reorder end-pairing matches only internal `step_type == "conditional"`, so conditional-loop child nesting under a reorder entry is unsupported; flat-id reorder of all step types works. Documented, not fixed (API-side behavior).

## Decision: lazy validation for subtest `test_uuid`
- **Rationale**: matches the existing `add_request_step` precedent (no URL pre-validation); server errors surface unchanged.

## Decision: extend `TestStep` with inbound + subtest fields
- **Rationale**: `src/models/step.py` lacks `token`/`isDynamicUrl` (inbound) and `trigger_token`/`environment_id`/`use_parent_environment`/`params` (subtest). Pydantic drops unknown keys by default, so these response fields would be silently dropped. Extend the model with `Optional` fields (default `None`) to preserve request/pause compatibility.

## Decision: pause duration is seconds, validated 1–180 (pre-existing, confirms no unit bug for new work)
- **Rationale**: `_parse_pause_template` validates `1 <= duration <= 180`. Pause is already supported; no new work needed here.
