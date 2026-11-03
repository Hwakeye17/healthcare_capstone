# Privacy-Safe Request Observability

The application writes one JSON Lines completion record per HTTP request and
per WebSocket message. Workflow-routing and tool-completion events are
additional records correlated with that request where applicable.

## Log destination and format

The default destination is `logs/practo_agent.jsonl`. Set `PRACTO_LOG_PATH` to
choose another file. Each line is a separate JSON object containing an
ISO-8601 UTC timestamp, event type, trace ID when in a request, and only the
allowlisted fields for that event.

The API returns the HTTP request trace identifier in the `X-Trace-ID`
response header. WebSocket message traces are available in the JSONL records.
Every record from a request, including workflow and tool events, uses the
same trace ID.

Example request completion event:

```json
{
  "timestamp": "2026-11-04T00:00:00+00:00",
  "event": "request_completed",
  "trace_id": "generated-request-id",
  "transport": "http",
  "operation": "query",
  "outcome": "answered",
  "duration_ms": 42.5,
  "status_code": 200
}
```

Workflow events record only whether retrieval, appointment lookup, or
clarification was selected. Tool events record the fixed tool name and its
status. The logger validates event names and values and rejects fields outside
the allowlist.

## Privacy boundary

Do not add request or response text, contact numbers, appointment identifiers,
session identifiers, authorization headers, secrets, or exception messages
to these events. The log schema intentionally does not permit arbitrary
string fields. A request completion records the outcome and duration, while
tool and routing events provide limited operational detail without retaining
patient-supplied content.

Generated logs are local runtime data and are excluded from version control.
Restrict access to the log directory and apply suitable retention and
deletion policies for the deployment environment.

## Validation

Run the API demonstration:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_api.py
```

It exercises a real offline appointment lookup and contextual WebSocket
follow-up, then checks that completion records have trace IDs, tool events
exist, and the log contains neither the user queries nor appointment data.
The demonstration writes `evaluation/results/api_demo.jsonl` alongside its
summary report.
