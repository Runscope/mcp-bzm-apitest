# Quickstart: Environment Management MCP Tools (MOB-54638)

## Agent-swap (primary use case)

Swap the private agent on a per-test (local) environment without touching anything else:

```
Tool: blazemeter_apitest_environments
action: "modify"
args: {
  "bucket_key": "abc123def456",
  "test_id": "11112222333344445555666677778888",
  "environment_id": "aaaabbbbccccddddeeeeffff00001111",
  "remote_agents": [{"uuid": "<new-agent-uuid>", "name": "<new-agent-name>"}]
}
```

Result: the environment now uses the new agent; `name`, `initial_variables`, `regions`, and every
other field are unchanged (server-side PATCH partial-merge). Repeat per test to bulk-swap across many
environments.

## Create a local environment

```
action: "create"
args: {
  "bucket_key": "abc123def456",
  "test_id": "11112222333344445555666677778888",
  "name": "Staging",
  "initial_variables": {"BASE_URL": "https://stage.example.com"}
}
```

## Create a shared (bucket-level) environment

```
action: "create"
args: {
  "bucket_key": "abc123def456",
  "name": "Prod Shared"
}
```

## List / read shared environments

```
action: "list"
args: { "bucket_key": "abc123def456" }        # shared scope (no test_id)

action: "read"
args: { "bucket_key": "abc123def456", "environment_id": "<env_id>" }
```

## Error behavior

- Invalid id → clear not-found message.
- Over the 100/100 limit → the API's "Cannot create more than 100 …" message, surfaced as-is.
- No permission/consent → clear auth message.
- No `delete` action exists.
