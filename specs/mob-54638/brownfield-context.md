# Brownfield Context: mcp-bzm-apim — MOB-54638

## Overall Finding

**brownfield** — The repository is an existing MCP server for BlazeMeter API Testing. This ticket extends the read-only `environment_manager.py` tool with CREATE and MODIFY (PATCH/PUT) operations for both shared (bucket-level) and local (test-level) environments. The codebase already has working reference implementations in `test_manager.py` (CREATE via POST), `bucket_manager.py` (CREATE via POST), `schedule_manager.py` (CREATE via POST with Pydantic validation model), and `step_manager.py` (complex PATCH/PUT patterns for modifying nested structures). 

**Critical Blocker:** The Runscope Environments API contract for PATCH vs PUT coverage of `remote_agents` field is **UNVERIFIED from source**. The codebase currently only implements GET endpoints for environments (see TEST_ENVIRONMENT_ENDPOINT at `/buckets/{}/tests/{}/environments`). Whether PATCH is supported by the Runscope API and covers the `remote_agents` field (needed for the Deloitte agent-swap use case) cannot be proven from this MCP server's codebase alone — it would require live API testing or upstream Runscope API documentation.

---

## Semantic Disambiguation

| Ticket Identifier | Codebase Symbol | Codebase Meaning | Decision | Evidence |
|-------------------|-----------------|------------------|----------|----------|
| `environment_manager.py` | `src/tools/environment_manager.py` | Existing tool manager for test-level (local) environments; currently read-only with `list()` and `read()` methods | USE — extend with `create()`, `modify()` | environment_manager.py:1-104 (25-104 show only read/list actions in the class) |
| `test-level environment` (local env) | `TEST_ENVIRONMENT_ENDPOINT = "/buckets/{}/tests/{}/environments"` at defaults.py:15; `Environment` model at models/environment.py:14-95 | Environments scoped to a specific test within a bucket. Model has `test_id` field. All current MCP environment operations are at test level only. | USE for local environments | environment_manager.py:35, 44; models/environment.py:18 (`test_id` field) |
| `bucket-level environment` (shared env) | **NOT YET FOUND IN CODEBASE** — No endpoint defined; ticket AC requires "List shared (bucket-level) environments for a bucket" | Ticket mentions shared environments should be bucket-scoped, but no endpoint or code pattern exists yet. Will require new endpoint constant and manager methods. | NEW — requires new endpoint and API methods | Ticket AC explicitly lists "List shared (bucket-level) environments for a bucket" as a requirement; codebase currently has no evidence of bucket-level env endpoints or model variants |
| `create_environment` / `modify_environment` | **NOT YET FOUND** — Only `read()` and `list()` exist | Ticket AC requires both create and modify (PATCH preferred) actions; not yet implemented in environment_manager | NEW — methods to be added to EnvironmentManager class | environment_manager.py:31-46 shows only read/list; no create/modify methods |
| `PATCH` HTTP method | Used in step_manager.py for PUT (not PATCH) at line 208-244; no PATCH calls in the codebase | MCP server currently uses only GET and POST. Mutating operations in step_manager use PUT. Ticket prefers PATCH for environments per MOB-37659 contract (unverified if that fix is in place). | AMBIGUOUS — PATCH vs PUT for environments is open technical question; need contract verification | step_manager.py:206-262 shows PUT patterns; no PATCH found in codebase; defaults.py has no PATCH_* methods defined in api_client.py |
| `remote_agents` field | `models/environment.py:54-56` — defined as `list[Dict[str, str]]` in Environment model, marked optional (default=None) | The Environment model already carries remote_agents in the data structure. Ticket AC requires: "Agent-swap path works end to end via the MCP tool (Deloitte use case: bulk-swap private agent across 631 per-test local environments)". PATCH must be able to modify this field. | AMBIGUOUS — confirmed in model; unclear if Runscope API PATCH endpoint covers it (see Dependency Contract Facts below) | models/environment.py:54-56 defines field; no existing write/PATCH operations on environments to verify coverage |
| `initial_variables` | `models/environment.py:25-27` — optional dict of environment variables for a test | Environment creation will likely require this field; common pattern in other create actions | USE — likely required parameter for create actions | models/environment.py:25-27; schedule_manager.py shows similar pattern with Pydantic models for create payloads |
| `proxy_settings` / `proxy` | **NOT FOUND** in models/environment.py or anywhere in the codebase | Ticket mentions proxy field in context of PATCH/PUT concern, but not defined in Environment model | BLOCKED — need clarification on whether proxy is a separate field or nested under remote_agents; may require model extension | Ticket text references "proxy_settings" in MOB-49921 concern but models/environment.py has no such field; grep found zero matches |
| Authorization / RBAC gating | `team.ai_consent` field at models/team.py:40; MCP server instruction mentions "ai_consent for a particular team"; no explicit RBAC checks in tool managers | The instruction states: "all further operations can be done if the 'ai_consent' for a particular team is true/given otherwise return an error message". Existing tools do NOT enforce ai_consent checks (inspection shows no validation in bucket_manager, test_manager, etc.). Ticket requires: "Create/modify tools respect existing PAT auth, RBAC, and AI-consent gating". | DO NOT USE (resolved) — ai_consent is enforced server-side by the `api` service for the bzm-apitest-mcp user-agent (api/CLAUDE.md Request Lifecycle); the MCP tool INHERITS it and MUST NOT add a redundant MCP-layer check. | models/team.py:40; MCP server instructions; no enforcement found in any tool manager (searched environment_manager, bucket_manager, test_manager for ai_consent checks — none found) |
| `environment_id` / `uuid` | `models/environment.py:17` — alias `"id"` on `environment_id` field | Primary key for environments; used in read/single operations | USE — standard pattern; confirmed working in read() method | environment_manager.py:35, 85; models/environment.py:17 (alias="id") |
| `bucket_key` | `src/config/defaults.py:9` and across all bucket operations as the bucket identifier | Bucket identifier used to construct endpoint URLs; scoped by team | USE — standard pattern | environment_manager.py:35, 40-41, 44-45 (all read/list operations use bucket_key); bucket_manager.py:33 |
| `test_id` | Parameter in all existing environment operations; passed to TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id) | Test identifier scoped within a bucket; used for test-level (local) environment operations | USE for test-level environments | environment_manager.py:31-46 (all methods take test_id) |

---

## Code Search Coverage

| Search Target | Patterns Used | Files Matched | Files Read | Omitted Matches / Reason |
|---------------|----------------|---------------|-----------|---------------------------|
| Environment manager create/modify methods | `grep -rn "async def create\|async def modify\|async def patch\|async def put" src/tools/environment_manager.py` | 0 matches | N/A — file read fully at lines 1-104 | No create/modify methods exist yet; only read (line 31) and list (line 40) |
| CREATE pattern in tools | `grep -rn "async def create" src/tools/*.py` | Found in: test_manager.py:40, bucket_manager.py:37, schedule_manager.py:41, step_manager.py has add_* methods | All read | Reference implementations: test_manager creates via POST JSON body (40-52); bucket_manager creates via POST params (37-41); schedule_manager creates via POST JSON with Pydantic model (41-54) |
| PATCH/PUT pattern in tools | `grep -rn "\"PUT\"\|\"PATCH\"" src/tools/*.py` | Found only in step_manager.py:206, 208, 241, 259 — all PUT, no PATCH | step_manager.py fully read (1-614) | PUT pattern: read current state, merge changes, PUT full object (read-modify-write); no PATCH examples in codebase |
| Environment endpoints | `grep -rn "TEST_ENVIRONMENT_ENDPOINT\|ENVIRONMENT.*ENDPOINT\|/environments" src/config/defaults.py` | `TEST_ENVIRONMENT_ENDPOINT` at line 15 only | defaults.py fully read (1-16) | Only test-level endpoint defined; no bucket-level endpoint defined (would be `/buckets/{}/environments` for shared environments) |
| Bucket-level operations | `grep -rn "BUCKETS_ENDPOINT.*environments\|buckets.*environments" src/ --include="*.py"` | 0 matches | N/A | Confirms no bucket-level environment endpoint in current code |
| remote_agents references | `grep -rn "remote_agent" src/ --include="*.py"` | 1 match: models/environment.py:54-56 definition only | models/environment.py fully read (1-96) | Field is defined but never read/written/modified by any MCP tool; no usage in environment_manager |
| MOB-49921 or MOB-37659 references | `grep -rn "MOB-49921\|MOB-37659" src/ --include="*.py"` | 0 matches | N/A | No evidence of MOB-49921 (list-of-dicts wipe bug) or MOB-37659 (PATCH endpoint) in the codebase; must come from external ticket history |
| ai_consent enforcement | `grep -rn "ai_consent" src/tools/*.py` | 0 matches in any tool manager | All tool managers checked (bucket_manager, test_manager, schedule_manager, step_manager, environment_manager, team_manager, result_manager, version_manager) | Team model has ai_consent; MCP instructions reference it; but no tool validates it before operations |
| Pydantic validation models | `grep -rn "class Create" src/models/*.py` | Found: `CreateSchedule` in schedule.py:10-28 | schedule.py fully read (1-49) | Pattern: CreateSchedule (request model) and Schedule (response model); includes field_validator for interval enum |
| Formatter functions | `grep -rn "def format_" src/formatters/*.py` | environment.py:6, bucket.py, test.py, step.py, schedule.py, team.py, result.py | All formatters read; environment.py fully read (1-11) | Formatters transform API JSON to Pydantic models; environment formatter at lines 6-10 shows standard pattern |

---

## Negative Constraints

- The codebase currently provides NO bucket-level (shared) environment endpoints. These do not exist in `defaults.py` and must be created.
- The codebase currently provides NO modify/patch/put actions for environments. Only read and list.
- No enforcement of `ai_consent` gating exists in any tool manager (despite MCP instructions mentioning it). This may need to be added.
- `proxy` or `proxy_settings` field does NOT exist in the `Environment` model. Ticket mentions it; unclear if it's required or an artifact of MOB-49921 discussion.

---

## Binding Decisions

```yaml
approved_identifiers:
- name: EnvironmentManager class
  reason: Existing tool manager pattern proven in bucket_manager, test_manager, schedule_manager, step_manager. Will be extended with create() and modify() methods following same structure.
  source: 'environment_manager.py:25-46; analogous: bucket_manager.py:25-44, test_manager.py:25-81, schedule_manager.py:26-62, step_manager.py:78-329'
- name: TEST_ENVIRONMENT_ENDPOINT constant
  reason: Existing endpoint for test-level (local) environments. Will be reused for local env create/modify/read/list.
  source: defaults.py:15; used in environment_manager.py:35, 40, 44
- name: CREATE pattern via POST + Pydantic model
  reason: Proven pattern in schedule_manager (CreateSchedule model at schedule.py:10-28; create method at schedule_manager.py:41-54). Will be replicated for environments.
  source: schedule_manager.py:41-54 (create method using CreateSchedule model); schedule.py:10-28 (Pydantic CreateSchedule model with validators)
- name: format_environments formatter function
  reason: Existing formatter converts API response JSON to Environment Pydantic models. Will be used for all create/modify/read responses.
  source: formatters/environment.py:6-10; uses Environment model at models/environment.py:14-95
- name: Environment Pydantic model
  reason: Existing model with all fields for environment operations including remote_agents, initial_variables, headers, etc. Will be extended if needed for new fields (e.g., proxy).
  source: models/environment.py:14-95 (includes remote_agents at line 54-56, initial_variables at line 25-27)
- name: api_request() function for HTTP calls
  reason: Single API client per constitution principle II. All HTTP (GET/POST/PUT/PATCH) MUST go through api_request(). Already tested with GET/POST/PUT in codebase.
  source: src/common/api_client.py:23-71 (method parameter accepts any HTTP verb); used by all tool managers
- name: Error handling via http_error_message() and UNEXPECTED_ERROR_MESSAGE
  reason: Constitution principle IV requires LLM-friendly error messages. All new create/modify tools must use these functions (already done in schedule_manager, step_manager patterns).
  source: src/common/errors.py:4-34; used in environment_manager.py:99, 101-102; bucket_manager.py:92-93, etc.
- name: MCP tool registration pattern with @mcp.tool decorator and action routing via match statement
  reason: Standard pattern across all tool managers. New create/modify actions will add cases to the match statement in the register() function.
  source: 'environment_manager.py:49-104 (register function and action routing via match); analogous: bucket_manager.py:47-98, test_manager.py:84-169, schedule_manager.py:65-145'
- name: telemetry span instrumentation (tool_span, check_result_error, record_span_error)
  reason: Constitution principle and observability requirement. All new actions must be wrapped in tool_span context manager and error handling.
  source: environment_manager.py:78, 82-87, 89-91, 94-103; imported from src/common/telemetry
- name: modify_environment via PATCH (partial merge, remote_agents preserved)
  reason: 'RESOLVED from api source: EnvironmentInstance.patch overlays only payload fields onto the full existing env, preserving remote_agents (agent-swap safe, no MOB-49921 wipe). PATCH is primary verb for modify; PUT retained only as defensive fallback.'
  source: api/api/resources/tests.py:1068-1126; api/api/routes.py:142-144
- name: Shared (bucket-level) env endpoint /buckets/{key}/environments
  reason: 'RESOLVED: SharedEnvironmentList GET/POST exists; single/modify via EnvironmentInstance on bucket-level and test-level routes. Both scopes in scope.'
  source: api/api/resources/tests.py:717-749; api/api/routes.py:140-144
- name: Inherit server-side ai_consent + PAT + RBAC gating (no new MCP-layer check)
  reason: 'RESOLVED: api service validates ai_consent_enabled for bzm-apitest-mcp user-agent plus PAT auth and RBAC permissions; MCP tool inherits. Auditability via existing telemetry spans.'
  source: api/CLAUDE.md:Request Lifecycle; api/api/resources/tests.py:718,753,1009,1065
- name: Surface API-enforced env limits (100 shared / 100 test) via http_error_message
  reason: 'RESOLVED: SHARED_ENVIRONMENT_LIMIT=100 and TEST_ENVIRONMENT_LIMIT=100; api returns HTTP 400 with clear message on overflow. MCP tool surfaces it; does not hardcode caps.'
  source: api/api/config.py:112-113; api/api/resources/tests.py:737,772
forbidden_identifiers:
- name: patch_environment method name
  reason: 'Ambiguity: PATCH vs PUT not yet verified with Runscope API contract. Do NOT create a patch_environment() method until contract verification is complete (see Blocker below). Use generic modify_environment() instead, which can handle both PATCH and PUT internally based on runtime detection.'
  impact: If PATCH is unavailable, a patch_environment() method will be broken; better to have one modify_environment() that tries PATCH first, falls back to PUT if needed (or uses PUT+read-merge strategy like step_manager uses).
- name: ai_consent enforcement in tool managers before contract clarification
  reason: 'MCP instructions reference ai_consent gating, but no tool manager currently enforces it. Ticket AC requires ''respect existing PAT auth, RBAC, and AI-consent gating''. This is ambiguous: does it mean inherit from team context (parent read), or implement new enforcement? Do NOT add ai_consent checks to environment create/modify until this is clarified with product/design.'
  impact: If enforcement is required but not implemented, test/prod may reject operations. If not required (only inherit from team context), unnecessary checks will slow down operations.
ambiguous_identifiers: []
```

---

## Runtime Data Availability Proof

All inputs are supplied by the MCP caller; the `api` service validates ids and performs the
read-and-merge for PATCH server-side. No runtime data is deleted/expired between read and write within
a single MCP action. Every row is available at read time (yes).

| Runtime Data | Written | Updated | Deleted/Expired | Planned Read | Available at Read Time? | Evidence | Safer Alternative if Unavailable |
|--------------|---------|---------|-----------------|--------------|-------------------------|----------|----------------------------------|
| bucket_key (tool arg) | caller | caller | never | every action | yes | caller-provided; invalid ids rejected by api with 404 (api/api/resources/tests.py:1016) | let the API reject invalid ids |
| test_id (tool arg) | caller | caller | never | test-level actions | yes | caller-provided; validated by api (tests.py:1022) | let the API reject |
| environment_id (tool arg) | caller | caller | never | read/modify | yes | caller-provided; api aborts 404 if not found (tests.py:1071-1072) | let the API reject |
| existing environment state (for modify) | api/identity | api on PATCH/PUT | never within one action | server-side during PATCH | yes | api PATCH fetches the full current env and merges server-side (tests.py:1085-1089); the MCP tool does not read-merge | none needed — server handles the merge |
| remote_agents (agent-swap) | api | api on modify | never | server-side merge during PATCH | yes | preserved by api PATCH unless explicitly supplied (tests.py:1085-1089); send only remote_agents to change it | none needed |

## Cross-Repo Capability Analysis

| Candidate Service/API | Capability | Evidence | Decision | Rationale |
|----------------------|-----------|----------|----------|-----------|
| Runscope/BlazeMeter Environments REST API (external, upstream of MCP) | GET /buckets/{}/tests/{}/environments (list test-level envs); GET /buckets/{}/tests/{}/environments/{id} (read single); UNKNOWN: POST /buckets/{}/tests/{}/environments (create); UNKNOWN: PATCH/PUT (modify) | Only GET endpoints are evident from MCP code (environment_manager.py:31-46 use GET only). POST, PATCH, PUT are inferred from ticket AC but not provable from MCP source code. | PARTIAL — GET operations proven; CREATE/MODIFY operations are inferred from ticket AC but not yet implemented in MCP code | MCP server is a client to Runscope API; Runscope API must support POST/PATCH/PUT for environments, but this is not confirmed in the MCP source code (only mentioned in ticket description) |
| Runscope/BlazeMeter Environments API — bucket-level endpoint | UNKNOWN: GET /buckets/{}/environments (list shared envs); GET /buckets/{}/environments/{id} (read single); UNKNOWN: POST/PATCH/PUT (create/modify) | Zero evidence in MCP codebase. Ticket AC explicitly requires "List shared (bucket-level) environments for a bucket", but this endpoint is not defined in defaults.py or used anywhere | NOT YET DEFINED — must be added | Assume bucket-level endpoint exists (likely /buckets/{}/environments by REST convention), but must be verified with Runscope API docs (external source) |
| Runscope/BlazeMeter API — PATCH support for environments | Unknown: Does PATCH verb work on /buckets/{}/tests/{}/environments/{id}? Does it cover remote_agents field? | Zero evidence of PATCH in MCP codebase. Ticket mentions MOB-37659 (where PATCH was supposedly added), but no PATCH calls are in current code. | UNVERIFIED — Blocker | Critical decision point: If PATCH not supported, spec must define PUT+read-merge-fallback (step_manager pattern). If PATCH supported but doesn't cover remote_agents, spec must handle that limitation. |
| Runscope/BlazeMeter API — PUT behavior for list-of-dicts fields | Unknown: Does PUT preserve remote_agents list, or wipe it (MOB-49921 concern)? | Ticket mentions MOB-49921 as a risk ("wipe bug"), suggesting PUT may destroy list-of-dicts fields. No evidence in MCP code of how this was handled for other resources (step_manager uses PUT but for different data structure). | UNVERIFIED — Blocker | If PUT wipes remote_agents, then PATCH is mandatory for agent-swap use case. If PATCH not available, spec must use read-merge-write pattern (confirmed safe by step_manager precedent). |

---

## Cross-Service Contract Verification

Required because the Cross-Repo Capability Analysis selects the Runscope environment API (served by
the `api` service). Verification is static/source-only — no live/dev/stage/prod endpoint was called.

| API/Capability | Route/Method/Path Evidence | Schema/Serializer/Response Evidence | Query/Filter/Ownership Evidence | Client/Auth/Fallback Evidence | Existing Tests/Fixtures | Decision |
|----------------|----------------------------|-------------------------------------|---------------------------------|-------------------------------|-------------------------|----------|
| List/create shared envs | `GET/POST /buckets/<bucket_key>/environments` (api/api/routes.py:140; SharedEnvironmentList api/api/resources/tests.py:717-749) | env JSON marshalled via `fetch_environment_json`/`fetch_environments_json` (tests.py:745, 740); MCP side `Environment` model models/environment.py:14-95 | bucket-scoped; `bucket:shared_environment:modify` / `bucket:tests:view` permissions (tests.py:718, 742) | PAT via `api_request()` (constitution II); MCP tool uses existing error ladder; api aborts 400 on limit (tests.py:737) | mcp: tests/test_environment_manager.py (to extend); api: its own resource tests | USE |
| List/create local envs | `GET/POST /buckets/<bucket_key>/tests/<test_id>/environments` (TestEnvironmentList tests.py:752-783; routes.py:138-139) | same env marshalling; MCP `format_environments` formatters/environment.py:6 | test-scoped; `bucket:tests:modify`/`view` (tests.py:753, 776) | PAT via `api_request()`; 400 on limit (tests.py:772) | tests/test_environment_manager.py (existing list/read; extend for create) | USE |
| Read/modify single env | `GET/PATCH/PUT .../environments/<environment_id>` (EnvironmentInstance tests.py:1008-1137; routes.py:142-144) | PATCH partial-merge: fetch full env + overlay payload fields (tests.py:1085-1089); marshalled response | `bucket:tests:modify` for write, `view` for read (tests.py:1009, 1065, 1128); bucket/test ownership checks (tests.py:1019-1023, 1075-1079) | PAT via `api_request()`; PATCH primary, PUT available but not used | mcp: extend test_environment_manager.py with modify tests | USE (PATCH) |

Evidence is static source only. No live/env probe was performed. `ai_consent_enabled` gating for the
`bzm-apitest-mcp` user-agent is enforced in the api `@validate_authentication` decorator
(api/CLAUDE.md Request Lifecycle), so the MCP tool inherits it.

## Reference Implementation Trace

### Behavioral Portrait

The ticket requires extending the read-only `environment_manager.py` tool with two new capabilities: CREATE and MODIFY (via PATCH partial-merge, resolved). The existing code structure follows a consistent tool-manager pattern:

1. **Manager class** (e.g., `EnvironmentManager`) with action methods (e.g., `read()`, `list()`)
2. **API calls** via centralized `api_request()` function in `common/api_client.py`
3. **Pydantic models** for request validation (e.g., `CreateSchedule` in schedule_manager) and response formatting via formatters (e.g., `format_environments()`)
4. **MCP registration** via `register()` function with `@mcp.tool()` decorator and action routing via `match` statement
5. **Error handling** via `http_error_message()` and structured `BaseResult` responses
6. **Telemetry** via `tool_span`, `check_result_error`, and `record_span_error` instrumentation

The ticket also has a unique challenge: **Runscope API contract ambiguity** — whether PATCH is supported and covers `remote_agents` field for the Deloitte agent-swap use case (bulk modify of 631+ local environments). This determines whether to implement PATCH-only, PUT-only, or PUT+read-merge-fallback.

### Candidate Analogs

**Best Matches (use as reference):**

1. **`schedule_manager.py:41-54` (CREATE pattern)**
   - Uses Pydantic model `CreateSchedule` for request validation (schedule.py:10-28)
   - Calls `api_request()` with POST method and JSON body
   - Formatter `format_schedules()` transforms response
   - Includes optional fields (note) and required fields (interval, environment_id)
   - Has field validators (interval enum)

2. **`bucket_manager.py:37-41` (CREATE via POST with params)**
   - Simpler POST variant: inline params dict instead of Pydantic model
   - Shows flexibility in how POST payloads can be constructed

3. **`test_manager.py:40-52` (CREATE via POST with inline JSON)**
   - Creates test with inline dict payload
   - Sets description automatically ("Test {name} created via MCP tool")

4. **`step_manager.py:197-212, 238-244, 255-262, 273-277` (MODIFY pattern — read-merge-write via PUT)**
   - Does NOT use PATCH; uses PUT (line 208, 241, 259)
   - Pattern: `read()` step, merge/modify locally, `PUT()` full object back
   - Shows how to handle complex nested structures safely
   - Relevant for agent-swap use case if PATCH not available

### Per-Layer Trace

**Layer 1: Manager Class Methods**

| Analog | File | Line | Method Signature | Pattern |
|--------|------|------|------------------|---------|
| Create (schedule) | schedule_manager.py | 41 | `async def create(self, bucket_key: str, test_id: str, environment_id: str, interval: str) -> BaseResult` | Takes scalar parameters, validates via Pydantic model, calls api_request with POST |
| Create (bucket) | bucket_manager.py | 37 | `async def create(self, bucket_name: str, team_id: int) -> BaseResult` | Similar; uses params dict for POST |
| Modify (step) | step_manager.py | 206-212 | `async def add_body_to_step(...)` → calls `_put_step()` at line 255-262 | Reads current state, modifies locally, PUT's back (no PATCH) |

**For environment_manager, adopt pattern:**
- `create_bucket_environment(bucket_key: str, name: str, initial_variables: Optional[Dict]=None, ...) -> BaseResult` for shared envs
- `create_test_environment(bucket_key: str, test_id: str, name: str, initial_variables: Optional[Dict]=None, ...) -> BaseResult` for local envs
- `modify_environment(bucket_key: str, test_id: str, environment_id: str, updates: Dict) -> BaseResult` or separate PATCH/PUT based on contract verification

**Layer 2: Pydantic Models for Request Validation**

| Analog | File | Line | Class | Fields | Validators |
|--------|------|------|-------|--------|-----------|
| CreateSchedule | schedule.py | 10-28 | `CreateSchedule` | note (optional), interval (required), environment_id (required) | `@field_validator("interval")` checks enum (line 23-27) |

**For environment_manager, create:**
- `CreateEnvironment` model with required fields (name, region/regions), optional (initial_variables, preserve_cookies, stop_on_failure, verify_ssl, etc.)
- Consider separate `CreateBucketEnvironment` and `CreateTestEnvironment` if they differ structurally

**Layer 3: API Client Calls**

| Method | Pattern in Code | Example |
|--------|-----------------|---------|
| GET (read single) | `api_request(token, "GET", f"{ENDPOINT}/{id}", result_formatter=format_fn)` | environment_manager.py:32-37 |
| GET (list) | `api_request(token, "GET", f"{ENDPOINT}", result_formatter=format_fn, params={...})` | test_manager.py:54-63 |
| POST (create) | `api_request(token, "POST", f"{ENDPOINT}", result_formatter=format_fn, json=body)` | schedule_manager.py:48-54 |
| POST (params) | `api_request(token, "POST", f"{ENDPOINT}", result_formatter=format_fn, params=params_dict)` | bucket_manager.py:39-41 |
| PUT (modify) | `api_request(token, "PUT", f"{ENDPOINT}/{id}", result_formatter=format_fn, json=full_object)` | step_manager.py:206-212 |
| PATCH (modify) | **NOT FOUND in codebase** — must be added if contract supports it | N/A |

**For environment_manager create/modify:**
```python
# Create (POST)
return await api_request(
    self.token,
    "POST",
    f"{BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)}",  # or TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)
    result_formatter=format_environments,
    json=body  # body = CreateEnvironment model dumped as dict
)

# Modify (PATCH partial-merge — confirmed from api tests.py:1068-1126)
return await api_request(
    self.token,
    "PATCH",  # or "PUT"
    f"{endpoint}/{environment_id}",
    result_formatter=format_environments,
    json=update_body
)
```

**Layer 4: Formatters**

| Formatter | File | Line | Transforms |
|-----------|------|------|-----------|
| format_environments | formatters/environment.py | 6 | List[API JSON] → List[Environment Pydantic models] (via model_dump) |
| format_schedules | formatters/schedule.py | similar | Same pattern for Schedule model |

**For environment_manager, reuse:**
- `format_environments()` already exists and handles both single and list responses

**Layer 5: Tool Registration**

Pattern across all managers:

```python
def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(
        name=f"{TOOLS_PREFIX}_environments",
        description="...",
    )
    async def environments(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        manager = EnvironmentManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_environments", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(span, await manager.read(...))
                    case "list":
                        return check_result_error(span, await manager.list(...))
                    case "create":  # NEW
                        return check_result_error(span, await manager.create(...))
                    case "modify":  # NEW
                        return check_result_error(span, await manager.modify(...))
                    case _:
                        return BaseResult(error=f"Action {action} not found...")
            except httpx.TimeoutException:
                ...
            except httpx.HTTPStatusError as e:
                ...
            except Exception as e:
                ...
```

**Layer 6: Error Handling & Telemetry**

All new methods must:
1. Wrap in `async with tool_span(...)` context (line 78-103 pattern)
2. Call `check_result_error(span, result)` to record errors in telemetry
3. Use `http_error_message(e)` for HTTPStatusError exceptions (not raw stack traces)
4. Record span errors via `record_span_error(span, error_type)`

Existing pattern in environment_manager.py:94-103 already does this for read/list; extend for create/modify.

### Binding Pattern Extractions

**SHAPE 1: API Client Call Signature for CREATE**
```python
# From schedule_manager.py:48-54
return await api_request(
    self.token,                           # BzmApimToken
    "POST",                               # HTTP method
    f"/v1{SCHEDULES_ENDPOINT.format(...)}",  # endpoint URL
    result_formatter=format_schedules,    # Callable to format response
    json=body,                            # Request payload dict
)
```
**For environment create, adapt:**
```python
return await api_request(
    self.token,
    "POST",
    f"{BUCKET_LEVEL_ENVIRONMENT_ENDPOINT.format(bucket_key)}" or
    f"{TEST_ENVIRONMENT_ENDPOINT.format(bucket_key, test_id)}",
    result_formatter=format_environments,
    json=validated_body  # Created from CreateEnvironment model
)
```

**SHAPE 2: Request Payload Structure**
```python
# From schedule_manager.py:43-46
schedule_data = CreateSchedule(
    environment_id=environment_id,
    interval=interval,
    note="Schedule created via MCP tool"
)
body = schedule_data.model_dump(by_alias=True, exclude_none=True)
```
**For environment create, adapt:**
```python
env_data = CreateEnvironment(
    name=name,
    initial_variables=initial_variables,
    preserve_cookies=preserve_cookies,  # optional
    ...
)
body = env_data.model_dump(by_alias=True, exclude_none=True)
```

**SHAPE 3: Pydantic Model with Validators**
```python
# From schedule.py:10-28
class CreateSchedule(BaseModel):
    note: Optional[str] = Field(default=None, ...)
    interval: str = Field(...)
    environment_id: str = Field(...)

    @field_validator("interval")
    def validate_interval(cls, v):
        valid_intervals = ["1m", "5m", "15m", "30m", "1h", "6h", "1d"]
        if v not in valid_intervals:
            raise ValueError(f'Interval must be one of: {", ".join(valid_intervals)}')
        return v
```
**For environment create, will need:**
```python
class CreateEnvironment(BaseModel):
    name: str = Field(..., description="Environment name")
    initial_variables: Optional[Dict[str, str]] = Field(default=None, ...)
    preserve_cookies: bool = Field(default=False, ...)
    verify_ssl: bool = Field(default=True, ...)
    regions: Optional[List[str]] = Field(default=None, ...)
    # Add validators for regions (if enum), or other fields as needed
```

**SHAPE 4: MCP Tool Registration with Action Routing**
```python
# From environment_manager.py:49-104
def register(mcp, token: Optional[BzmApimToken]):
    @mcp.tool(name=f"{TOOLS_PREFIX}_environments", description="...")
    async def environments(action: str, args: Dict[str, Any], ctx: Context) -> BaseResult:
        environment_manager = EnvironmentManager(token, ctx)
        meta = get_meta_from_ctx(ctx)
        parent_context = extract_trace_context(meta)
        async with tool_span(f"{TOOLS_PREFIX}_environments", action, parent_context) as span:
            try:
                match action:
                    case "read":
                        return check_result_error(
                            span,
                            await environment_manager.read(
                                args["bucket_key"], args["test_id"], args["environment_id"]
                            ),
                        )
                    case "list":
                        return check_result_error(
                            span, await environment_manager.list(args["bucket_key"], args["test_id"])
                        )
                    # NEW CASES BELOW:
                    case "create":
                        return check_result_error(
                            span,
                            await environment_manager.create(
                                args["bucket_key"],
                                args.get("test_id"),  # None for bucket-level, set for test-level
                                args["name"],
                                args.get("initial_variables"),
                                ...
                            ),
                        )
                    case "modify":
                        return check_result_error(
                            span,
                            await environment_manager.modify(
                                args["bucket_key"],
                                args["test_id"],
                                args["environment_id"],
                                args["updates"],  # Partial update dict
                            ),
                        )
                    case _:
                        return BaseResult(error=f"Action {action} not found in environments manager tool")
            except httpx.TimeoutException:
                record_span_error(span, "timeout")
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
            except httpx.HTTPStatusError as e:
                record_span_error(span, http_status_to_error_type(e.response.status_code))
                return BaseResult(error=http_error_message(e))
            except Exception as e:
                record_span_error(span, "tool_error")
                logger.exception("Unexpected error in environments tool: %s", e)
                return BaseResult(error=UNEXPECTED_ERROR_MESSAGE)
```

**SHAPE 5: Auth/RBAC/AI-Consent Gating Pattern**
```python
# NOT CURRENTLY ENFORCED IN CODEBASE — must clarify if needed
# From MCP server instructions: "all further operations can be done if the 'ai_consent' for a particular team is true/given otherwise return an error message"
# From team_manager.py and models/team.py:40: ai_consent field exists in Team model

# If enforcement is required, pattern could be:
# Option A (read parent team, check ai_consent):
#   team_result = await api_request(...GET .../teams/{team_id}...)
#   if not team_result.result[0].ai_consent:
#       return BaseResult(error="AI consent not enabled for this team")

# Option B (centralized in api_client or server.py): validate before tool execution
# Option C (inherit from caller context): assume caller already validated

# Current codebase suggests Option C (no validation in tools); must be clarified.
```

---

## Dependency Contract Facts: runscope-env-api

Based on source code inspection of mcp-bzm-apim (api_client.py, models, environment.py, environment_manager.py, defaults.py, tests):

### Confirmed Endpoints (GET operations already implemented)

| Endpoint | HTTP Method | Purpose | Evidence in Source | Parameters |
|----------|------------|---------|-------------------|-----------|
| `/buckets/{bucket_key}/tests/{test_id}/environments` | GET | List test-level (local) environments | environment_manager.py:40-46 (list method); defaults.py:15 (TEST_ENVIRONMENT_ENDPOINT) | count, offset (params dict not shown but inferred from test_manager pattern) |
| `/buckets/{bucket_key}/tests/{test_id}/environments/{environment_id}` | GET | Read single test-level environment | environment_manager.py:31-38 (read method); used at line 35 | None |

### Inferred Endpoints (NOT YET IMPLEMENTED, but required by ticket AC)

| Endpoint | HTTP Method | Purpose | Ticket AC Requirement | Evidence/Gap |
|----------|------------|---------|----------------------|-----------------|
| `/buckets/{bucket_key}/environments` | GET | List shared (bucket-level) environments | "List shared (bucket-level) environments for a bucket" | CONFIRMED in api: SharedEnvironmentList GET (tests.py:745); add BUCKET_LEVEL_ENVIRONMENT_ENDPOINT to defaults.py |
| `/buckets/{bucket_key}/environments/{environment_id}` | GET | Read single shared (bucket-level) environment | "Retrieve a single environment by ID (shared or test-level)" | CONFIRMED in api: EnvironmentInstance GET (tests.py:1131); add endpoint constant to defaults.py |
| `/buckets/{bucket_key}/tests/{test_id}/environments` | POST | Create test-level environment | "Create a local (test-level) environment" | CONFIRMED in api: TestEnvironmentList POST (tests.py:756) |
| `/buckets/{bucket_key}/environments` | POST | Create shared (bucket-level) environment | "Create a shared (bucket-level) environment" | CONFIRMED in api: SharedEnvironmentList POST (tests.py:721) |
| `/buckets/{bucket_key}/tests/{test_id}/environments/{environment_id}` | PATCH | Modify test-level environment (preferred) | "Modify an environment via PATCH (partial update), preferred over PUT" | CONFIRMED in api: EnvironmentInstance.patch partial-merge preserves remote_agents (tests.py:1068-1126) |
| `/buckets/{bucket_key}/tests/{test_id}/environments/{environment_id}` | PUT | Modify test-level environment (fallback) | "if not PATCH, then PUT (avoid MOB-49921 remote_agents wipe bug)" | PUT exists (EnvironmentInstance.put, tests.py:1012) but replaces wholesale; NOT needed — PATCH is primary |
| `/buckets/{bucket_key}/environments/{environment_id}` | PATCH or PUT | Modify shared (bucket-level) environment | Implicit from ticket AC | CONFIRMED: same EnvironmentInstance.patch handles bucket-level route (routes.py:143) |

### Response Shape (Fields in Environment Model)

From models/environment.py:14-95 (parsed from API responses):

| Field | Type | Description | Required? | Evidence |
|-------|------|-----------|-----------|----------|
| id (alias environment_id) | str | Unique environment identifier | Yes | line 17 (alias="id") |
| test_id | str | Test ID this env belongs to (test-level only) | Yes | line 18; will be None for bucket-level envs? |
| name | str | Environment name | Yes | line 19 |
| parent_environment_id | str | If inherited from another env | No | line 20-23 |
| initial_variables | Dict[str, str] | Environment variables | No | line 25-27 |
| retry_on_failure | bool | Retry test on failure | Yes | line 28-29 |
| script | str | Pre-execution script | No | line 31-33 |
| webhooks | List | Webhook URLs for notifications | No | line 34-36 |
| integrations | List[Dict] | 3rd party integrations (Slack, Teams) | No | line 38-41 |
| emails | EmailSettings | Email notification settings | No | line 43-44 |
| preserve_cookies | bool | Preserve cookies between steps | Yes | line 46 |
| stop_on_failure | bool | Stop on first failure | Yes | line 47-48 |
| verify_ssl | bool | Verify SSL certificates | Yes | line 50 |
| http_version_support | str | HTTP version (1.1, 2.0, etc.) | Yes | line 51 |
| force_h2c | bool | Force HTTP/2 cleartext | Yes | line 52 |
| regions | List[str] | Cloud regions for execution | Yes | line 53 |
| **remote_agents** | List[Dict[str, str]] | Remote agents configuration | No (default=None) | **line 54-56 — CRITICAL for agent-swap use case** |
| headers | Dict | Headers for all requests | No | line 57-59 |
| pre_request_scripts | List[str] | Pre-request scripts | No | line 60-62 |
| post_response_scripts | List[str] | Post-response scripts | No | line 63-65 |
| is_client_certificate_used | bool | Client cert auth used | No (default=False) | line 66-69 |
| is_auth_enabled | bool | Any auth enabled | No (default=False) | line 70-71 |
| auth_type | str | Auth type (basic, oauth1, oauth2, client_cert) | No | line 73-77 |

### PATCH Endpoint Coverage — RESOLVED (confirmed from api service source)

**Question from Ticket:** "whether the existing PATCH endpoint (added in MOB-37659) covers remote_agents/proxy fields needed for the agent-swap path; if not, the tool must handle PUT + the MOB-49921 list-of-dicts wipe behavior"

**Status:** RESOLVED — PATCH exists and is safe for the agent-swap path.

**Confirmed evidence (read-only source inspection of the `api` service, no live calls):**
- `EnvironmentInstance.patch()` — `api/api/resources/tests.py:1068-1126`, registered at
  `api/api/routes.py:142-144` on BOTH `/buckets/<bucket_key>/environments/<environment_id>` and
  `/buckets/<bucket_key>/tests/<test_id>/environments/<environment_id>`.
- PATCH does a partial merge: fetches the full current env JSON (`fetch_environment_json`,
  tests.py:1085), overlays ONLY the payload fields (tests.py:1088-1089), re-validates via
  tea-service, then PUTs the merged object to identity. => `remote_agents` is PRESERVED unless the
  caller explicitly supplies it. The agent-swap path (set `remote_agents` to the new agent) works
  correctly and does NOT wipe other fields. No MOB-49921 exposure when using PATCH.
- PUT (`EnvironmentInstance.put()`, tests.py:1012-1063) replaces the whole payload — it is the
  unsafe verb for partial updates and is NOT needed for this story.

**DECISION:** modify_environment uses PATCH as the primary verb. PUT is NOT required for
correctness.

## Field/Metric Provenance Matrix

| Output Field | Source | Type | Derivation | Notes |
|--------------|--------|------|-----------|-------|
| environment_id | API response (id field, aliased) | Direct pass-through | Runscope API → models/environment.py (alias="id") → formatter → MCP response | Primary key; populated by Runscope on creation |
| test_id | API response | Direct pass-through | API response field → model → formatter → MCP | Identifies parent test (test-level envs only) |
| name | API request (create/modify) + API response (read/list) | Direct pass-through / User-provided | User provides on create; API returns on read | Required field |
| initial_variables | API request (create/modify) + API response (read/list) | Direct pass-through / User-provided | User provides on create; API returns on read | Optional; used for environment variable substitution |
| remote_agents | API response (read) + API request (modify) | Direct pass-through / User-provided | API returns on read; user modifies via create/modify actions (Deloitte agent-swap use case) | **CRITICAL**: List of dicts; must be preserved/modified correctly during PATCH/PUT |
| regions | API request (create) + API response | Direct pass-through | User provides list of regions on create; API returns on read | Required list of cloud region codes |
| preserve_cookies, stop_on_failure, verify_ssl, etc. | API request (create/modify) + API response (read/list) | Direct pass-through | User-provided on create; API echoes back on read | Configuration flags; defaulted by API if not specified |
| **all other fields** | API response | Direct pass-through | No derivation; Runscope API computes/stores these | See Environment model at models/environment.py for field descriptions |

---

## Assumption Ledger

| ID | Assumption / Claim | Type | Evidence For | Evidence Against / Unknowns | Risk | Validation / Challenge Required | Decision |
|----|--------------------|------|--------------|-----------------------------|------|---------------------------------|----------|
| A001 | PATCH endpoint exists for environments and is a partial merge (not wholesale replace) | API contract | `api/api/resources/tests.py:1068-1126` (`EnvironmentInstance.patch` overlays only payload fields onto full current env); `api/api/routes.py:142-144` registers PATCH on both scopes | none — read directly from source | high | Contract test asserting PATCH with a single changed field leaves other fields intact | PROVEN |
| A002 | PATCH preserves `remote_agents` unless explicitly provided (agent-swap safe, no MOB-49921 wipe) | API contract | PATCH starts from `fetch_environment_json` full env, overlays only request keys (tests.py:1085-1089); `remote_agents` not in payload => unchanged | none — proven by merge logic | critical | Falsification test: PATCH env with only `remote_agents` changed → assert all other fields (name, initial_variables, regions) unchanged; and PATCH with `name` only → assert `remote_agents` unchanged | PROVEN |
| A003 | Bucket-level (shared) environment endpoints exist at `/buckets/{key}/environments` | API contract | `SharedEnvironmentList` GET/POST `api/api/resources/tests.py:717-749`; `api/api/routes.py:140`; single via `EnvironmentInstance` routes:142-144 | none | high | Contract test for list/create/read on bucket-level route | PROVEN |
| A004 | Create (POST) exists for both shared and test-level environments | API contract | `SharedEnvironmentList.post` tests.py:721; `TestEnvironmentList.post` tests.py:756 | none | high | Contract test: POST returns 201 + created env | PROVEN |
| A005 | Environment caps are 100 shared/bucket and 100 test/test, API-enforced with HTTP 400 | API contract | `SHARED_ENVIRONMENT_LIMIT = 100`, `TEST_ENVIRONMENT_LIMIT = 100` `api/api/config.py:112-113`; 400 abort with message tests.py:737, 772 | ticket's "~10 unconfirmed" superseded | medium | Test that a 400 limit-reached response surfaces via `http_error_message()` unchanged | PROVEN |
| A006 | ai_consent + PAT + RBAC gating is enforced server-side; MCP tool inherits, no new MCP-layer check | API contract | api validates `ai_consent_enabled` for `bzm-apitest-mcp` user-agent + `@validate_authentication(permissions=[...])` (`api/CLAUDE.md` Request Lifecycle; tests.py:718,753,1009,1065) | none | medium | No new check needed; existing api_request PAT path + telemetry spans provide auth + auditability | PROVEN |
| A007 | `Environment` Pydantic model already carries every field needed (incl. `remote_agents`, `initial_variables`, `name`) for create/modify | code shape | `src/models/environment.py:14-95` (remote_agents:54-56, initial_variables:25-27, name:19) | create may need a slimmer request model (only writable fields) | low | Author a Create/Modify request model (alias-mapped, exclude_none) mirroring `CreateSchedule` | PROVEN |
| A008 | The existing `api_request()` generic client supports POST/PATCH with a `json=` body and a result_formatter | code shape | `src/common/api_client.py:23-60` (method param + **kwargs → client.request); `schedule_manager.create` uses POST+json (`schedule_manager.py:41-54`) | first PATCH call in this codebase — none currently use PATCH verb | low | Unit test the new modify path with a mocked PATCH response | PROVEN |


---

## Boundary Compatibility Analysis

### MCP Server ↔ Runscope API (HTTP/REST)

**Boundary Type:** Conformist (MCP server is downstream; Runscope API is upstream authority)

**Context Map:**

```
┌─────────────────────────┐
│   MCP Tool (Client)     │
│   environment_manager   │
│   (calls api_request)   │
└────────────┬────────────┘
             │
       (HTTP GET/POST/PUT/PATCH)
       (Bearer token auth)
       (JSON request/response bodies)
             │
┌────────────▼────────────────────────────┐
│   Runscope API (Server)                 │
│   /buckets/{}/tests/{}/environments     │
│   /buckets/{}/environments (assumed)    │
└─────────────────────────────────────────┘
```

**Shape Compatibility:**

| Aspect | MCP Server | Runscope API | Compatibility | Issue |
|--------|-----------|--------------|---------------|-------|
| Request Format | JSON body via api_request(json=...) | Expects JSON in request body | Compatible | api_client.py:50 uses httpx.request with json= parameter |
| Response Format | JSON response → BaseResult envelope | Returns JSON with "data" and "error" fields | Compatible | api_client.py:52-69 parses response.json() and wraps in BaseResult |
| Authentication | Bearer token in Authorization header | Expects "Authorization: Bearer {token}" | Compatible | api_client.py:42 sets Authorization header |
| Error Codes | 401/403 (auth), 404 (not found), 429 (rate limit), 500+ (server error) | Responds with HTTP status codes | Compatible | errors.py:4-27 maps HTTP status to LLM-friendly messages |
| Pagination | "total", "skip", "limit" in response JSON | Runscope API uses these fields | Compatible | api_client.py:53-67 handles pagination response fields |
| Field Names (remote_agents) | Python dict keys "remote_agents" (snake_case) | API likely returns "remote_agents" (snake_case) per REST convention | Assumed Compatible | Environment model at line 54 uses "remote_agents"; not yet tested with write operations |
| Nested Objects (remote_agents as list-of-dicts) | Python list[Dict[str, str]] | API returns list of objects | Assumed Compatible | step_manager uses PUT with complex nested structures (headers, assertions); works with current api_client |
| PATCH Support | Would require PATCH method string in api_request() call | **UNVERIFIED**: Does Runscope API support PATCH? | **INCOMPATIBILITY RISK** | Blocker: If Runscope API doesn't support PATCH, MCP tool must use PUT+read-merge-write pattern (step_manager precedent) |

**Context Mapping** (how MCP translates LLM intent → Runscope API calls):

| LLM Intent | MCP Tool Action | Runscope API Call | Response Handling |
|-----------|-----------------|------------------|------------------|
| "List environments for bucket ABC123, test T1" | Call `list(bucket_key="ABC123", test_id="T1")` | GET `/buckets/ABC123/tests/T1/environments` | Parse JSON array → Environment models → BaseResult |
| "Create environment named 'prod' in bucket ABC123, test T1" | Call `create(bucket_key="ABC123", test_id="T1", name="prod", ...)` | POST `/buckets/ABC123/tests/T1/environments` with JSON body | Parse response → Environment model → BaseResult |
| "Modify environment E1 in bucket ABC123, test T1 to add agent X" | Call `modify(bucket_key="ABC123", test_id="T1", environment_id="E1", updates={...})` | PATCH or PUT `/buckets/ABC123/tests/T1/environments/E1` with JSON body | Parse response → Environment model → BaseResult |

**Anti-Corruption Layer:** None currently implemented. MCP directly exposes Runscope API fields (remote_agents, regions, headers, etc.) to LLM without translation. This is acceptable for a generic API bridge, but means:
- If Runscope API field names change, MCP tool responses change (coupling)
- If Runscope API adds new optional fields, MCP Environment model must be updated
- No validation of remote_agents format (assumed list[Dict[str, str]] but not validated until PUT)

---

## Design Alternatives Considered

### Alternative 1: PATCH-Only (Preferred)

**Approach:** Implement `modify_environment()` using PATCH verb exclusively for partial updates.

**Pros:**
- Efficient: Only sends changed fields, not full environment object
- Safe for remote_agents: PATCH partial updates should preserve unmodified fields
- Aligns with ticket preference ("Modify an environment via PATCH (partial update), preferred over PUT")

**Cons:**
- **BLOCKER**: PATCH support is unverified from source; if not available, tool fails
- Requires verifying MOB-37659 work is deployed to Runscope API
- Higher implementation risk

**Evidence:** No PATCH calls in current codebase; step_manager uses PUT instead.

---

### Alternative 2: PUT-Only (Fallback)

**Approach:** Implement `modify_environment()` using PUT verb with full environment object (read-merge-write pattern from step_manager).

**Pros:**
- Proven pattern: step_manager uses PUT successfully for complex nested objects (lines 206-262)
- Guaranteed to work if PUT is supported (which it is, based on step_manager precedent)
- No dependency on unverified PATCH support

**Cons:**
- Inefficient: Must read full environment, merge changes, PUT everything back (3 API calls for agent-swap use case = 3×631 = 1893 calls vs. 631 PATCH calls)
- Risk of MOB-49921 (list-of-dicts wipe): If Runscope API PUT wipes remote_agents, this approach fails
- Slower for Deloitte's bulk-swap use case (631 environments)

**Safer because:** Read-merge-write ensures we never lose unmodified fields; step_manager precedent proves this works.

---

### Alternative 3: PATCH-with-PUT-Fallback (Recommended)

**Approach:** Implement `modify_environment()` to try PATCH first; if it fails (405 Method Not Allowed), fall back to PUT+read-merge-write.

**Pros:**
- Handles both scenarios: PATCH if available (fast), PUT if not (safe)
- Resilient to unverified API contract
- Performance-optimized: Deloitte's agent-swap gets PATCH efficiency if available
- Provides useful error information (tells user whether API supports PATCH)

**Cons:**
- More complex implementation (two code paths)
- First failure triggers retry (slight latency cost for first PATCH attempt)
- Requires handling both response shapes (PATCH partial vs. PUT full)

**Recommended because:** Balances risk (unverified PATCH) with efficiency (avoids overhead if PATCH works). Aligns with ticket's uncertainty ("if not PATCH, then PUT + MOB-49921 handling").

---

### Alternative 4: Separate Bucket-Level and Test-Level Managers

**Approach:** Create `BucketEnvironmentManager` (for shared envs) and `TestEnvironmentManager` (for local envs) as separate tool managers per constitution principle I.

**Pros:**
- Cleaner separation of concerns per constitution
- Could have different APIs if bucket-level and test-level share different behavior
- Mirrors structure of buckets, tests, schedules (each in separate manager)

**Cons:**
- Duplicates code (both would have create/modify/read/list patterns)
- Violates DRY principle
- Unnecessary complexity if APIs are similar

**Decision:** NOT recommended. Extend single EnvironmentManager with conditional logic (if test_id is None → bucket-level; else → test-level). Keep similar behavior together in one manager.

---

## Test Validity Strategy

### Existing Tests (tests/test_environment_manager.py)

Current tests cover:
- `test_list_environments()` — mocks api_request, verifies list() returns BaseResult with 2 envs
- `test_read_environment()` — mocks api_request, verifies read() returns BaseResult with specific env data

**Pattern:** Tests mock api_request entirely; do NOT make live HTTP calls.

### Tests Needed for New Actions

**Test 1: Create Test-Level Environment**
```python
async def test_create_test_environment(self, mock_token, mock_context):
    manager = EnvironmentManager(mock_token, mock_context)
    with patch("src.tools.environment_manager.api_request") as mock_api:
        mock_api.return_value = BaseResult(
            result=[{
                "id": "new_env_123",
                "name": "Prod",
                "test_id": "test_123",
                "initial_variables": {"API_KEY": "secret"},
                ...
            }],
            total=1
        )
        result = await manager.create(
            bucket_key="bucket_abc",
            test_id="test_123",
            name="Prod",
            initial_variables={"API_KEY": "secret"},
            ...
        )
        assert result.error is None
        assert result.result[0]["id"] == "new_env_123"
        # Verify api_request was called with POST method
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        assert call_args[0][1] == "POST"  # method
        assert "test_123/environments" in call_args[0][2]  # endpoint
```

**Test 2: Create Bucket-Level Environment**
```python
async def test_create_bucket_environment(self, mock_token, mock_context):
    # Similar to above, but:
    # - endpoint should be /buckets/bucket_abc/environments (no test_id)
    # - test_id param should be None or omitted
```

**Test 3: Modify Environment via PATCH**
```python
async def test_modify_environment_patch(self, mock_token, mock_context):
    manager = EnvironmentManager(mock_token, mock_context)
    with patch("src.tools.environment_manager.api_request") as mock_api:
        mock_api.return_value = BaseResult(
            result=[{
                "id": "env_123",
                "name": "Prod",
                "remote_agents": [{"id": "agent_1", "name": "Private Agent X"}],
                ...
            }],
            total=1
        )
        result = await manager.modify(
            bucket_key="bucket_abc",
            test_id="test_123",
            environment_id="env_123",
            updates={"remote_agents": [{"id": "agent_2", "name": "New Agent"}]}
        )
        assert result.error is None
        # Verify PATCH method was used
        call_args = mock_api.call_args
        assert call_args[0][1] == "PATCH"  # method
        assert "env_123" in call_args[0][2]  # endpoint includes env_id
```

**Test 4: Modify Environment via PUT (Fallback)**
```python
async def test_modify_environment_put_fallback(self, mock_token, mock_context):
    # Verify that if PATCH returns 405 Method Not Allowed, tool falls back to PUT
    # (requires implementing PATCH-with-PUT-fallback pattern)
```

**Test 5: Error Handling — Invalid Bucket/Test/Env IDs**
```python
async def test_create_environment_bucket_not_found(self, mock_token, mock_context):
    manager = EnvironmentManager(mock_token, mock_context)
    with patch("src.tools.environment_manager.api_request") as mock_api:
        mock_api.side_effect = httpx.HTTPStatusError(
            message="404",
            request=Mock(),
            response=Mock(status_code=404)
        )
        result = await manager.create(
            bucket_key="invalid_bucket",
            test_id="test_123",
            name="Prod"
        )
        assert result.error is not None
        assert "Not found" in result.error or "404" in result.error
```

**Test 6: MCP Tool Registration — Create Action**
```python
async def test_create_action_via_mcp_tool(self, mock_token, mock_context):
    # Call the environments() MCP tool with action="create"
    # Verify it dispatches to manager.create() and returns properly formatted BaseResult
```

**Test Coverage Target:** All new create/modify methods, error paths (404, 401/403, 429, 500, timeout), and MCP tool registration.

---

## Current State

| Component | Current State | Gap to Ticket AC |
|-----------|---------------|-----------------|
| Environment Manager | Read-only: `list()`, `read()` methods only (lines 31-46) | Missing: `create()` (bucket-level and test-level), `modify()` (PATCH/PUT) |
| Environment Model | Complete: `Environment` Pydantic model with all fields (lines 14-95 in models/environment.py) | May need: `CreateEnvironment` validation model; possible `proxy` field (currently missing) |
| API Endpoints (defaults.py) | Test-level only: `TEST_ENVIRONMENT_ENDPOINT = "/buckets/{}/tests/{}/environments"` (line 15) | Missing: `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT` for shared environments |
| API Client | Supports GET/POST/PUT; flexible to accept any HTTP method string | Supports PATCH implicitly (any method string), but never called; no evidence PATCH is available upstream |
| Formatters | `format_environments()` handles list/single responses (formatters/environment.py:6-10) | No changes needed |
| Tool Registration | Current: 2 actions (read, list) via match statement (lines 49-104) | Add: create, modify action cases |
| Error Handling | Uses http_error_message(), UNEXPECTED_ERROR_MESSAGE, telemetry spans | No changes needed for existing patterns |
| Tests | `test_list_environments()`, `test_read_environment()` only | Add: create (bucket + test level), modify, error scenarios |
| AI-Consent Gating | No enforcement in tool managers; team.ai_consent exists in model | Ambiguous: Clarify if new enforcement needed or inherited from parent context |

---

## Desired State Delta

| Component | Desired State | Changes Required |
|-----------|--------------|-----------------|
| Environment Manager | Read/create/modify for both bucket-level and test-level environments | Add: `create_test_environment()`, `create_bucket_environment()`, `modify_environment()` methods; or single `create()` with test_id=None logic |
| Environment Model | Add `CreateEnvironment` validation model | Create src/models/environment.py additions: `CreateEnvironment` Pydantic class with required fields (name, regions), optional (initial_variables, preserve_cookies, verify_ssl, stop_on_failure, etc.), validators |
| API Endpoints (defaults.py) | Add bucket-level endpoint constant | Add: `BUCKET_LEVEL_ENVIRONMENT_ENDPOINT = "/buckets/{}/environments"` |
| MCP Tool Registration | Expand action routing for create/modify | Modify environment_manager.py register() function: add "create_test", "create_bucket", "modify" action cases |
| Tests | Comprehensive coverage of all new actions + error scenarios | Add test_environment_manager.py tests: create_test_environment, create_bucket_environment, modify_environment (PATCH), modify_environment (PUT fallback), error scenarios (404, 401/403, 429, timeout, validation errors) |
| Tool Instructions | Expand description to cover new actions | Update environment_manager.py MCP tool description with examples for create/modify actions |
| Contract Verification (external) | Confirm PATCH endpoint availability and remote_agents field coverage | Verification task: Test against Runscope stage API; confirm PATCH method, field coverage, MOB-49921 behavior |

---

## Files the Planner Must Read for spec.md

1. **src/tools/environment_manager.py** (full) — Current implementation to extend
2. **src/tools/schedule_manager.py** (lines 41-54, 65-145) — Reference for CREATE pattern + Pydantic model
3. **src/tools/step_manager.py** (lines 197-212, 238-262) — Reference for MODIFY (PUT) pattern
4. **src/models/environment.py** (full) — Environment response model; need to create CreateEnvironment model
5. **src/models/schedule.py** (lines 10-28) — Reference for CreateSchedule Pydantic model pattern
6. **src/common/api_client.py** (full) — Understand how api_request() works, HTTP method handling
7. **src/common/errors.py** (full) — Error handling patterns
8. **src/config/defaults.py** (full) — Add BUCKET_LEVEL_ENVIRONMENT_ENDPOINT constant
9. **src/formatters/environment.py** (full) — Formatter already complete; verify reusability
10. **tests/test_schedule_manager.py** (full) — Reference for test patterns
11. **tests/test_step_manager.py** (lines 99-145, 209-250) — Reference for modify/PUT test patterns
12. **tests/test_environment_manager.py** (full) — Extend with new test cases
13. **tests/conftest.py** (full) — Mock fixtures to use/extend

---

## Planner Blockers

All prior blockers are **RESOLVED** from the `api` service source (public Runscope APIs at
`$CODE_ROOT/api`), which the assignee identified as the authoritative contract source for the
MCP tools (SLACK:1791444463.389279:1791446359.673359). Read-only source inspection only — no
live/stage/prod endpoint was called. No remaining blockers; spec may proceed.

### RESOLVED — Blocker 1: PATCH support + remote_agents coverage

- PATCH is implemented: `EnvironmentInstance.patch()` at `api/api/resources/tests.py:1068-1126`,
  registered on both `/buckets/<bucket_key>/environments/<uuid:environment_id>` and
  `/buckets/<bucket_key>/tests/<uuid:test_id>/environments/<uuid:environment_id>`
  (`api/api/routes.py:142-144`).
- PATCH is a true partial merge: it fetches the full current environment
  (`fetch_environment_json(environment_id)`, tests.py:1085), overlays ONLY the fields present in
  the request payload (`for field, value in env_in_payload.items(): formatted_env_json[field] = value`,
  tests.py:1088-1089), then writes the merged object back. Therefore `remote_agents` is PRESERVED
  unless the caller explicitly sets it — the agent-swap path is safe via PATCH and does NOT trigger
  the MOB-49921 list-of-dicts wipe. PUT (tests.py:1012-1063) replaces the payload wholesale and is
  the unsafe path for partial updates.
- DECISION: spec `modify_environment` to use **PATCH** as the primary verb (partial update). No PUT
  fallback is required for correctness; it may be retained only as defensive robustness if PATCH
  returns 405/not-allowed at runtime.

### RESOLVED — Blocker 2: bucket-level (shared) environment endpoint exists

- `SharedEnvironmentList` — `GET /buckets/<bucket_key>/environments` (list) and
  `POST /buckets/<bucket_key>/environments` (create), `api/api/resources/tests.py:717-749`,
  registered at `api/api/routes.py:140`.
- Single/modify for shared envs uses the same `EnvironmentInstance` routes as test-level
  (`api/api/routes.py:142-144`). DECISION: Q2 Option A — spec both scopes:
  shared = `/buckets/{key}/environments`, local = `/buckets/{key}/tests/{id}/environments`,
  single/modify = `/buckets/{key}/environments/{env_id}` or `/buckets/{key}/tests/{id}/environments/{env_id}`.

### RESOLVED — Blocker 3: AI-consent gating is enforced server-side

- The `api` service validates `ai_consent_enabled` for MCP-server requests (identified by the
  `bzm-apitest-mcp` user-agent) in its `@validate_authentication` decorator, alongside PAT auth and
  RBAC permission checks (e.g. `permissions=["bucket:shared_environment:modify"]` at tests.py:718,
  `permissions=["bucket:tests:modify"]` at tests.py:753/1009/1065). Source: `api/CLAUDE.md` Request
  Lifecycle section ("Checks `ai_consent_enabled` flag for MCP server requests").
- DECISION: Q3 Option A — the MCP tool INHERITS existing gating (PAT + server-side RBAC +
  server-side ai_consent). No new ai_consent check is added in the MCP layer. Auditability is
  provided by existing telemetry spans (constitution + telemetry instrumentation already in every
  tool manager).

### RESOLVED — Blocker 4: environment per-bucket / per-test limits

- `SHARED_ENVIRONMENT_LIMIT = 100` and `TEST_ENVIRONMENT_LIMIT = 100` (`api/api/config.py:112-113`).
- The API itself enforces these and returns HTTP 400 with a clear message
  ("Cannot create more than 100 shared environments per bucket.", tests.py:737; and the per-test
  equivalent at tests.py:772) BEFORE creating. DECISION: Q4 Option A — the MCP tool does NOT
  hardcode caps; it surfaces the API's 400 limit message via the existing `http_error_message()`
  LLM-friendly error path. (The ticket's "~10 unconfirmed" shared cap and "max 100 local" are both
  superseded by the confirmed 100/100.)


## Overall Commitment Summary

| Dimension | Finding |
|-----------|---------|
| **Brownfield Type** | brownfield — extending existing read-only tool with create/modify actions |
| **Reference Analog** | schedule_manager.py (CREATE pattern) + step_manager.py (MODIFY/PUT pattern) |
| **Approved Identifiers** | EnvironmentManager class, Environment model, TEST_ENVIRONMENT_ENDPOINT, api_request(), format_environments, tool registration pattern, error handling pattern, telemetry instrumentation |
| **Forbidden Identifiers** | "patch_environment" method (ambiguous until PATCH verified); ai_consent enforcement without clarification |
| **Ambiguous Identifiers** | bucket-level vs test-level distinction, PATCH vs PUT for modify, ai_consent gating scope, per-bucket shared/local env count caps |
| **Critical Blockers** | 1. PATCH endpoint support for remote_agents field (UNVERIFIED), 2. Bucket-level endpoint existence (NOT YET DEFINED), 3. ai_consent gating scope (UNCLEAR) |
| **Dependency Contract** | Runscope Environments API — GET endpoints proven; POST/PATCH/PUT endpoints inferred from ticket AC but not confirmed in code. PATCH support is explicitly unverified (blocker). |
| **Test Strategy** | Mock-only (no live API calls); extend test_environment_manager.py with create/modify scenarios, error paths, MCP tool registration tests |
| **Confidence** | **MEDIUM** — Reference implementations (schedule_manager, step_manager) are clear; existing code patterns are consistent. But critical API contract uncertainties (PATCH, bucket-level endpoint, ai_consent) block full spec authorship until verified. Recommend scheduling Slack/design clarification for blockers before /specify step. |


## overall_finding
brownfield
