# HTTP and WebSocket API

The API exposes the existing Practo conversation workflow; it does not
reimplement routing, guardrails, memory, caching, response validation, or
runtime budgets.

## Run locally

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:MOCK_LLM = 'true'
python -m uvicorn practo_agent.api.app:app --host 127.0.0.1 --port 8000
```

The default mock mode uses the local workflow without a Groq API key. The
interactive OpenAPI page is at `http://127.0.0.1:8000/docs`.

## HTTP endpoints

### `GET /health`

Returns `{"status": "ok"}` while the API process is serving requests.

### `POST /query`

Request:

```json
{
  "query": "What is the status of APT-0001?",
  "session_id": "demo-session"
}
```

The response is the validated `AgentResponse` structure, including status,
answer, reason when abstaining, and validated source or appointment
references. Reusing the same session ID preserves history and applies the
existing session-aware response cache. The query must be non-empty and at
most 100,000 characters; the session ID must be non-empty and at most 128
characters. Unknown fields and invalid payloads receive FastAPI's structured
HTTP 422 validation response.

Example:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/query `
  -ContentType 'application/json' `
  -Body '{"query":"What is the status of APT-0001?","session_id":"demo-session"}'
```

## WebSocket conversations

Connect to `/ws/{session_id}`. Send one JSON object per turn:

```json
{"query": "What is the status of APT-0001?"}
```

Each successful request receives the same structured `AgentResponse` JSON
shape as the HTTP endpoint. Consecutive turns on the connection share the
path's session history. The same session ID can be reused by HTTP and
WebSocket requests to the same API process. Invalid messages receive a
structured error object and do not enter conversation history; the
connection remains available for another turn. An invalid session ID receives
an error followed by WebSocket close code 1008. A client disconnect is handled
as a normal end of the conversation.

## Session and deployment boundaries

The API uses one `ConversationMemory` manager per application process.
Histories and cached responses are in memory and disappear when the process
stops. Multiple server workers do not share session state. The API has no
authentication or authorization layer; do not expose it to untrusted
networks or use it for real patient data.

Synchronous workflow execution is dispatched to Starlette's worker thread
pool for both HTTP and WebSocket handling, avoiding blocking the event loop
during retrieval and Crew execution.

HTTP responses include an `X-Trace-ID` header. WebSocket request trace IDs
are recorded in the JSON Lines logs. See
[`observability.md`](observability.md) for the event schema and privacy
boundary.

## Offline demonstration

Run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_api.py
```

The demonstration sends the first appointment question over HTTP and a
context-dependent follow-up over WebSocket using the same session. It asserts
both responses are answered, the follow-up retains the appointment reference,
four history messages are stored, and the WebSocket closes cleanly. The
privacy-safe report is written to `evaluation/results/api_demo.json`.
