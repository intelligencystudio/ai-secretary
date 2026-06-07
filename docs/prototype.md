# Codex Context Intake Endpoint

Small dependency-free API for receiving project context from an external employer agent. It is designed to be easy to expose through ngrok and friendly to A2A-style discovery.

This workspace contains two small agents:

- `server.py`: employee-side context intake agent.
- `hr_agent.py`: HR-side project context provider that connects to employee agents and sends them context.

## What It Provides

- `GET /healthz` health check.
- `GET /.well-known/agent-card.json` current A2A-style Agent Card.
- `GET /.well-known/agent.json` legacy Agent Card alias for older clients.
- `POST /contexts` REST context intake.
- `GET /contexts` list stored context summaries.
- `GET /contexts/{id}` fetch one stored context bundle.
- `POST /a2a` JSON-RPC endpoint supporting:
  - `context.ingest`
  - `context.list`
  - `context.get`
  - `message/send`
  - `tasks/send`

Stored context is written to `work/context_store.json`.

## Run Locally

```sh
scripts/run_local.sh
```

Open:

```text
http://127.0.0.1:8787/
```

## Optional Auth

Set a token before exposing the endpoint publicly:

```sh
export CONTEXT_API_TOKEN="replace-with-a-long-random-token"
scripts/run_local.sh
```

Then callers must send either:

```text
Authorization: Bearer replace-with-a-long-random-token
```

or:

```text
X-API-Key: replace-with-a-long-random-token
```

## Publish With ngrok

In terminal 1:

```sh
export CONTEXT_API_TOKEN="replace-with-a-long-random-token"
scripts/run_local.sh
```

In terminal 2:

```sh
scripts/run_ngrok.sh
```

Give the other agent the ngrok URL and these endpoints:

```text
https://YOUR-NGROK-DOMAIN/.well-known/agent-card.json
https://YOUR-NGROK-DOMAIN/a2a
https://YOUR-NGROK-DOMAIN/contexts
```

If you set `PUBLIC_BASE_URL`, the Agent Card will advertise that public URL explicitly:

```sh
export PUBLIC_BASE_URL="https://YOUR-NGROK-DOMAIN"
```

## Test Payloads

REST context intake:

```sh
curl -sS http://127.0.0.1:8787/contexts \
  -H 'Content-Type: application/json' \
  --data @examples/context.json
```

A2A-style JSON-RPC:

```sh
curl -sS http://127.0.0.1:8787/a2a \
  -H 'Content-Type: application/json' \
  --data @examples/a2a-context.json
```

With auth enabled, add:

```sh
-H 'Authorization: Bearer replace-with-a-long-random-token'
```

## HR Agent

Run the HR-side project context provider:

```sh
scripts/run_hr.sh
```

Open:

```text
http://127.0.0.1:8788/
```

Optional auth:

```sh
export HR_API_TOKEN="replace-with-a-long-random-token"
scripts/run_hr.sh
```

The HR agent provides:

- `GET /.well-known/agent-card.json` HR Agent Card.
- `POST /projects` create or update project context.
- `GET /projects` list projects.
- `POST /employees` register an employee agent endpoint.
- `GET /employees` list employees, with stored tokens masked.
- `POST /dispatch` send one project context to one employee agent.
- `POST /a2a` JSON-RPC endpoint supporting:
  - `hr.project.upsert`
  - `hr.employee.upsert`
  - `hr.context.dispatch`
  - `hr.context.forEmployee`

Local smoke test with the employee agent on `8787` and HR agent on `8788`:

```sh
curl -sS http://127.0.0.1:8788/projects \
  -H 'Content-Type: application/json' \
  --data @examples/hr-project.json
```

```sh
curl -sS http://127.0.0.1:8788/employees \
  -H 'Content-Type: application/json' \
  --data @examples/hr-employee-local.json
```

```sh
curl -sS http://127.0.0.1:8788/dispatch \
  -H 'Content-Type: application/json' \
  --data @examples/hr-dispatch-local.json
```

For a real contact, replace `agentBaseUrl` in `examples/hr-employee-local.json` with that person's AI secretary URL. If their intake endpoint requires auth, include `"token": "contact-endpoint-token"` in the contact registration payload.

## Notes

The endpoint is A2A-friendly rather than a full production A2A implementation. It publishes an Agent Card at the current `/.well-known/agent-card.json` path and also serves the older `/.well-known/agent.json` path for compatibility. The Agent Card declares a JSON-RPC interface in `supportedInterfaces`, and `/a2a` accepts JSON-RPC calls and stores their payloads as context bundles.
