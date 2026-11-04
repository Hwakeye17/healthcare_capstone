# Practo Healthcare Domain Support Agent

This repository is for the Practo Healthcare track. It provides administrative
support using a project-authored knowledge base and a synthetic appointment
dataset. It is not a clinical system and does not provide diagnosis or
treatment recommendations.

## Dataset design

The deterministic generator uses seed `42` and produces 240 synthetic records.
Categories and appointment statuses use equal weights (20% each), yielding 48
records for every required category and status. Follow-up is assigned at a
20% rate (48 of 240 records). Creation age is sampled uniformly from 0 to 30
days. Consultation fees are fixed synthetic values by category, from INR 500
to INR 1,000: General Medicine 500, Cardiology 1,000, Dermatology 700,
Pediatrics 600, and Orthopedics 800. These are sample values, not Practo
prices. Reproduce the dataset with:

```powershell
python .\dataset.py --count 240 --seed 42
```

The knowledge base contains the 12 required policy topics, with 2–5 sentences
per document. The retrieval comparison uses 25 in-scope labeled queries for
both chunking strategies; abstention calibration uses the same 25 in-scope
queries plus two out-of-scope queries.

At top-k 2, the measured document-level retrieval results are fixed-size
precision/recall `0.7400/0.9600` and sentence-based `0.8200/1.0000`.
Sentence-based is selected because it achieved higher precision and recall on
this evaluation set. Its empirically selected abstention distance is
`0.6976266205310822`, the midpoint between the maximum in-scope best distance
(`0.645258`) and the minimum out-of-scope best distance (`0.749995`). It
achieved zero false acceptances and full in-scope recall on 25 in-scope and
two out-of-scope queries. The threshold is provisional and specific to this
calibration set.

## Implemented functionality

- The appointment lookup is deterministic and read-only. It returns the
  appointment ID, specialty, status, fee, record age, follow-up flag,
  administrative score, and the threshold decision with its reason.
- The score is `0.6 * follow_up_required + 0.4 * (days_since_created / 30)`.
  The inclusive administrative threshold is `0.6`. In the current generated
  240-record dataset, 48 records (20%) meet it. This is a project heuristic,
  not a clinical or official Practo policy.
- A deterministic router selects the Retrieval Agent, Lookup Agent, or both
  for mixed requests. The Response Composer receives only enabled specialist
  outputs. Application-layer governance enforces that only the Lookup Agent
  may receive or call `check_appointment_status` at both wiring time and
  tool-call time, and classifies component and system risk under the
  Low/Medium/High scheme; see
  [`docs/architecture/governance.md`](docs/architecture/governance.md).
- Every specialist handoff and final response is validated against its
  Pydantic contract. Invalid JSON or invalid fields are rejected.
- The CrewAI request workflow masks fixed-format Indian mobile numbers before
  routing or model execution. This targeted pattern does not detect arbitrary
  free-text PII; see
  [`docs/architecture/input_guardrails.md`](docs/architecture/input_guardrails.md).
- The request workflow rejects common explicit prompt-injection attempts to
  override instructions or disclose restricted information before routing or
  model execution. This phrase-based detector is a limited input filter, not
  a comprehensive security boundary; see
  [`docs/architecture/input_guardrails.md`](docs/architecture/input_guardrails.md).
- Answered CrewAI responses are checked against validated retrieval evidence
  and successful appointment lookup results before return. Unsupported claims,
  invalid citations, or validator failures produce an abstention.
- Per-request token and estimated-cost budgets are checked before routing and
  before each model call. The byte-based token counts and configured-rate
  costs are estimates; see
  [`docs/runtime_budget_design.md`](docs/runtime_budget_design.md).
- FastAPI exposes health and structured query endpoints plus a multi-turn
  WebSocket backed by the same session memory. Its offline demonstration and
  limitations are documented in
  [`docs/architecture/api.md`](docs/architecture/api.md).
- `MOCK_LLM=true` selects a deterministic CrewAI `BaseLLM` implementation.
  The mock workflow uses actual local embeddings, the persisted ChromaDB
  collection, and the synthetic appointment dataset; it does not require a
  Groq API key. CrewAI OpenTelemetry and Hugging Face model downloads are
  disabled for the offline acceptance run.
- Tests exercise five in-scope questions through `Crew.kickoff()`, a mixed
  question, an out-of-scope abstention, and rejection of external network
  connections.

Run the end-to-end offline examples in PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_offline_workflow.py
```

Demonstrate grounded generation for the full retrieval query set and an
out-of-scope abstention:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_grounded_generation.py
```

Demonstrate that a fabricated contact number is masked before routing and the
offline mock LLM. The safe transcript is saved without the raw number:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_input_guardrails.py
```

Demonstrate prompt-injection detection and rejection before routing or Crew
execution. The safe transcript is saved to
`evaluation/results/prompt_injection_demo.json`:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_prompt_injection.py
```

Demonstrate session-based conversation memory, including a multi-turn
appointment follow-up and a separate fresh session:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_conversation_memory.py
```

The session histories use LangChain's in-process
`InMemoryChatMessageHistory` and `RunnableWithMessageHistory`; they do not
persist across process restarts. The demo writes separate multi-turn and
fresh-session transcripts under `evaluation/results/`.

Demonstrate response caching with normalized equivalent queries. The demo
also checks that changed conversation context or session scope results in a
cache miss:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_response_cache.py
```

The cache is process-local, stores answered responses only, and reports
cache-hit, miss, and workflow invocation counts.

Run the local HTTP and WebSocket API in offline mock mode:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:MOCK_LLM = 'true'
python -m uvicorn practo_agent.api.app:app --host 127.0.0.1 --port 8000
```

The API provides `GET /health`, `POST /query`, and a session-based
`/ws/{session_id}` conversation endpoint. Open `http://127.0.0.1:8000/docs`
for the interactive HTTP interface. Run the offline HTTP-to-WebSocket
multi-turn demonstration and save its transcript with:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_api.py
```

See [`docs/architecture/api.md`](docs/architecture/api.md) for request
schemas, validation behavior, session limitations, and expected demo results.

The API writes trace-correlated JSON Lines request and workflow events to
`logs/practo_agent.jsonl` by default. Override the destination with
`PRACTO_LOG_PATH`. Request bodies, responses, session IDs, appointment IDs,
and contact numbers are excluded; see
[`docs/architecture/observability.md`](docs/architecture/observability.md).

Demonstrate the two-agent AutoGen review stage offline:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_autogen_review.py
```

The demonstration checks both an unchanged approved response and a corrected
unsupported draft. See
[`docs/architecture/autogen_review.md`](docs/architecture/autogen_review.md).

Demonstrate least-autonomy tool governance (permitted Lookup Agent call,
rejected unauthorized wiring, and blocked runtime tool call) and risk
classification offline:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_governance.py
```

The demonstration writes `evaluation/results/governance_demo.json`. See
[`docs/architecture/governance.md`](docs/architecture/governance.md).

Run the offline zero-tolerance safety evaluation suite across all seven
safety objectives (medical diagnosis refusal, treatment refusal, unsupported
policy claim rejection, unauthorized appointment lookup blocking, PII
redaction in logs/prompts, abstention on unsupported queries, and
prompt-injection rejection):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\evaluate_safety.py
```

The runner writes `evaluation/results/safety_evaluation.json` and
`reports/safety_evaluation_report.md`. See
[`docs/evaluation/safety_evaluation.md`](docs/evaluation/safety_evaluation.md).

Run the live response-quality evaluation using the configured Groq model:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\evaluate_response_quality.py
```

This evaluates the required 15 queries with a structured LLM judge and writes
per-query scores, justifications, aggregate averages, and a readable report.
It requires `GROQ_API_KEY` in `.env`; mock mode is rejected so the scores
cannot be fabricated. After completing all project milestones, run and review
all 15 cases. See
[`docs/architecture/response_quality_evaluation.md`](docs/architecture/response_quality_evaluation.md)
for the scoring dimensions and expected output files.

Demonstrate the output-side groundedness check by injecting an unsupported
claim into a controlled offline Crew result. The application workflow must
reject it and save a transcript:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_groundedness_guardrail.py
```

Run the live CrewAI demonstration with the Groq API:

```powershell
$env:MOCK_LLM = 'false'
python scripts\demo_crewai.py
```

The live run requires `GROQ_API_KEY` in `.env`. The default model is
`qwen/qwen3.8-27b`. It uses CrewAI's ReAct tool parser because the provider's
native function-call path returned invalid tool calls in this integration.
Each scenario validates its structured outputs, citations against retrieved
evidence, appointment references, and expected answer details before reporting
success.

Run the test suite:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m pytest -q
```

## Remaining assignment reconciliation

The RAG and core CrewAI workflow are implemented and covered by tests.
Fixed-format contact-number masking, phrase-based prompt-injection detection,
CrewAI response groundedness validation, session-based conversation memory,
and context-aware response caching are implemented and demonstrated.
Runtime token/cost controls and the FastAPI HTTP/WebSocket interface are
implemented with offline demonstrations. Privacy-safe structured logging is
implemented and demonstrated. The AutoGen review stage is implemented and
demonstrated. The 15-query response-quality evaluation is implemented; its
live scored results still need to be generated and reviewed; Groq output
formatting and account token limits have blocked successful live scoring so
far. Application-layer governance, risk classification, and the zero-tolerance
safety evaluation suite are implemented and demonstrated. Remaining work
includes end-to-end offline acceptance testing, final reports (including the
15-query live judge evaluation), and submission review.
Track remaining requirements in the internal handoff; do not mark a feature
complete until its behavior is demonstrated and tested.
