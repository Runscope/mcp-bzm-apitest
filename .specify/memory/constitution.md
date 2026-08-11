<!--
SYNC IMPACT REPORT
==================
Version change: (template / unfilled) → 1.0.0
Type of bump: MINOR — initial population of all principle sections and governance from template placeholders.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Domain-Scoped MCP Tools (new, filled)
  - [PRINCIPLE_2_NAME] → II. Single API Client (new, filled)
  - [PRINCIPLE_3_NAME] → III. Test-First (NON-NEGOTIABLE) (new, filled)
  - [PRINCIPLE_4_NAME] → IV. LLM-Friendly Error Handling (new, filled)
  - [PRINCIPLE_5_NAME] → V. Structured Pydantic Responses (new, filled)

Added sections:
  - Code Quality & Style Standards
  - Security & Token Handling
  - Governance

Removed sections: none

Templates reviewed:
  - .specify/templates/plan-template.md       ✅ — Constitution Check gate references this file by design; no structural changes needed
  - .specify/templates/spec-template.md       ✅ — Generic template; no principle-driven mandatory sections missing
  - .specify/templates/tasks-template.md      ✅ — Generic template; task categories align with principles (test tasks, observability tasks)

Follow-up TODOs: none — all placeholders resolved.
-->

# BlazeMeter API Test MCP Server Constitution

## Core Principles

### I. Domain-Scoped MCP Tools

Each feature domain (team, bucket, test, step, schedule, result, environment, version) MUST be
encapsulated in its own dedicated tool manager class under `src/tools/`. A tool manager MUST expose
only actions that belong to its domain. New domains MUST get their own manager; existing managers
MUST NOT absorb unrelated actions.

The domain hierarchy enforced in tool instructions is:
**Teams → Buckets → Tests → (Schedules / Steps / Results / Environments)**

Tool managers MUST register their handlers via a `register()` function decorated with `@mcp.tool()`.
No tool handler logic MUST be placed outside a tool manager class.

**Rationale**: Scoped tool managers keep the MCP surface predictable for AI agents, simplify
discovery, and prevent cross-domain coupling that would make testing and maintenance brittle.

### II. Single API Client

All HTTP communication with the BlazeMeter/Runscope API MUST go through the single async function
`api_request()` in `src/common/api_client.py`. Tool managers and formatters MUST NOT call the API
directly. Authentication (Bearer token), HTTP error detection (401/403 handling), and optional
response formatting MUST be handled exclusively inside `api_request()`.

**Rationale**: A single call site for outbound HTTP guarantees consistent auth, error handling,
and observability. It makes mocking in tests trivial and prevents secret leakage in ad-hoc callers.

### III. Test-First (NON-NEGOTIABLE)

Tests MUST be written before implementation for every new tool action or behaviour change.
Tests MUST fail (red) before implementation begins. The Red-Green-Refactor cycle is strictly
enforced.

- Test files MUST mirror the source structure (`tests/test_<module>.py`).
- API calls MUST be mocked using `unittest.mock.AsyncMock`; no live API calls in the test suite.
- Integration tests MUST be marked `@pytest.mark.integration`.
- Coverage target applies to `src/` only.
- `pytest-asyncio` auto mode is active — all async test functions are treated as async automatically.

**Rationale**: Mocked-first tests let the full suite run offline and in CI without credentials.
Writing tests first surfaces interface design problems before code is written.

### IV. LLM-Friendly Error Handling

Every error surfaced to the calling LLM MUST be a categorized, human-readable message.

- HTTP errors MUST be processed by `http_error_message()` from `src/common/errors.py`, which maps
  status codes to named categories: auth / not-found / rate-limit / server-error.
- Non-HTTP / unexpected errors MUST use the `UNEXPECTED_ERROR_MESSAGE` constant from the same module.
- Raw HTTP status codes, stack traces, and internal field names MUST NOT appear in tool responses.
- Token values MUST NEVER appear in any error message or log line.

**Rationale**: AI agents act on the text of error messages. Vague or technical messages lead to
incorrect retry logic. Consistent categorized messages let agents make deterministic decisions.

### V. Structured Pydantic Responses

Every MCP tool MUST return a `BaseResult` (or a domain-specific subclass) Pydantic model defined
in `src/models/`. The `BaseResult` schema provides the universal response envelope:

| Field | Type | Purpose |
|-------|------|---------|
| `result` | any | Primary payload |
| `total` | int | Total items available (for paginated resources) |
| `has_more` | bool | Pagination continuation flag |
| `error` | str \| None | Error description (populated on failure) |
| `info` | str \| None | Informational note for the agent |
| `warning` | str \| None | Non-fatal warning |
| `hint` | str \| None | Suggested next action |

Formatters in `src/formatters/` MUST transform raw API JSON into Pydantic models before returning
to the tool layer. Tool managers MUST NOT perform raw JSON parsing themselves.

**Rationale**: A uniform envelope makes every tool predictable for the LLM. Structured Pydantic
models provide validation and type safety at the boundary between API responses and MCP output.

## Code Quality & Style Standards

- **Line length**: 108 characters enforced by `black`, `flake8`, and `isort`.
- **Import order**: `isort` with the `black`-compatible profile.
- **Max complexity**: 10 per function (flake8 `max-complexity`).
- **Python version**: 3.11+ required; CI matrix covers 3.11 and 3.12.
- **Lint targets**: `--target-version py311` MUST be passed to `black` to avoid the 24.x+/3.12.5
  incompatibility. Use `make lint` and `make format` — do not invoke `black` directly without this flag.
- **Async**: `pytest-asyncio` in `auto` mode — no `@pytest.mark.asyncio` decorator needed.

## Security & Token Handling

- Token resolution order: `BZM_API_TEST_TOKEN` env var → `BZM_API_TEST_TOKEN_FILE` path →
  local `bzm_api_test_token.env` file. This order MUST NOT be changed.
- Token loading uses LRU cache in `src/config/token.py`; callers MUST use this module, not
  direct `os.environ` reads.
- Bearer auth MUST be applied exclusively in `api_request()`; no other layer MUST add auth headers.
- Token values MUST NOT be logged, printed, or included in any response or error message.
- Dependency sanitisation: `defusedxml` MUST be used for XML parsing; `nh3` for HTML sanitisation.

## Governance

This constitution supersedes all other development practices for this project. When a practice
conflicts with a principle stated here, the constitution wins.

**Amendment procedure**:
1. Propose the change with a rationale explaining which principle is affected and why.
2. Increment `CONSTITUTION_VERSION` following semantic versioning:
   - MAJOR: a principle removed, replaced, or redefined incompatibly.
   - MINOR: a new principle or section added, or materially expanded guidance.
   - PATCH: clarifications, wording improvements, or typo fixes.
3. Update `LAST_AMENDED_DATE` to the amendment date.
4. Run the consistency propagation checklist: review all templates under `.specify/templates/`
   and runtime guidance in `CLAUDE.md` for references that must change.
5. Commit with message: `docs: amend constitution to vX.Y.Z (<brief summary>)`.

**Compliance**:
- All PRs MUST include a Constitution Check confirming no principles are violated.
- Complexity violations MUST be explicitly justified in the plan's Complexity Tracking table.
- For runtime development guidance see `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-08-11 | **Last Amended**: 2026-08-11
