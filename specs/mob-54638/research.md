# Phase 0 Research: Environment Management MCP Tools (MOB-54638)

All unknowns were resolved from the `api` service source (read-only; no live calls) and the existing
`mcp-bzm-apim` codebase. Full evidence is in `brownfield-context.md` (binding). Summary:

## Decision 1 — Modify verb: PATCH partial-merge

- **Decision**: Implement `modify_environment` using HTTP PATCH on `.../environments/{env_id}`.
- **Rationale**: `api/api/resources/tests.py:1068-1126` (`EnvironmentInstance.patch`) fetches the
  full existing environment and overlays ONLY the request-body fields, so `remote_agents` and all
  other unspecified fields are preserved. This is exactly what the Deloitte agent-swap path needs and
  avoids the MOB-49921 wipe.
- **Alternatives considered**: PUT wholesale replace + client-side read-merge-write
  (`EnvironmentInstance.put`, tests.py:1012) — REJECTED: unnecessary (server PATCH already merges)
  and reintroduces wipe risk if a field is omitted.

## Decision 2 — Create: POST + typed request model

- **Decision**: Add a typed request model and POST it, mirroring `schedule_manager.create`.
- **Rationale**: `schedule_manager.py:41-54` is the proven create pattern in this codebase
  (`model_dump(by_alias=True, exclude_none=True)` → `api_request(..., "POST", ..., json=body)`).
  Consistency with existing managers.
- **Alternatives considered**: inline dict payload (bucket_manager style) — acceptable but weaker
  validation; typed model preferred per constitution V and FR-013.

## Decision 3 — Shared (bucket-level) endpoint

- **Decision**: Add `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT = "/buckets/{}/environments"` to
  `src/config/defaults.py`; use it for shared list/read/create; reuse `TEST_ENVIRONMENT_ENDPOINT`
  for local.
- **Rationale**: `SharedEnvironmentList` (api tests.py:717, routes.py:140) exposes GET/POST at
  `/buckets/{key}/environments`; single resource via `EnvironmentInstance` (routes.py:142-144).
- **Alternatives considered**: none — endpoint confirmed in source.

## Decision 4 — Tool surface: extend the single `environments` tool

- **Decision**: Add new actions to the existing `environments` `@mcp.tool` via the `match action`
  router, routing shared vs local by the presence of `test_id` (or an explicit `scope` arg).
- **Rationale**: Every manager in this repo is one tool with action routing (constitution I).
- **Alternatives considered**: a separate write-only tool — REJECTED (breaks convention).

## Decision 5 — Auth / consent / limits

- **Decision**: Inherit server-side PAT + RBAC + ai_consent; surface the API's 400 limit message via
  `http_error_message()`; do NOT hardcode caps or add an MCP-layer consent check.
- **Rationale**: `api/CLAUDE.md` Request Lifecycle enforces `ai_consent_enabled` for the
  `bzm-apitest-mcp` user-agent; caps `SHARED_ENVIRONMENT_LIMIT=100`/`TEST_ENVIRONMENT_LIMIT=100`
  (api/api/config.py:112-113) are enforced and messaged by the API.
- **Alternatives considered**: MCP-layer consent check / hardcoded caps — REJECTED (redundant;
  drift risk).

## No remaining open clarifications

All four ticket open points (PATCH coverage, bucket-level endpoint, ai_consent scope, caps) are
resolved and confirmed with the assignee via Slack (thread 1791444463.389279).
