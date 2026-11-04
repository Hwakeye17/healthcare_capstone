# Practo Healthcare Domain Support Agent

**Completed Track:** Practo (Healthcare) — Administrative Patient-Support & Appointment-Status Agent.

This repository implements the **Practo (Healthcare)** capstone track. It provides administrative policy support using a project-authored 12-document knowledge base and deterministic appointment lookups against a 240-record synthetic dataset, orchestrated with CrewAI, reviewed by a two-agent AutoGen Round Robin team, governed by application-layer tool-permission and runtime budget controls, and deployed behind FastAPI (HTTP + WebSocket) with privacy-safe JSONL observability. Everything runs deterministically offline under `MOCK_LLM=true` with **zero API keys** and **zero external network calls** (`CREWAI_DISABLE_TELEMETRY=true` and `OTEL_SDK_DISABLED=true` are set before Crew execution). It is an administrative support system and does not provide clinical diagnosis or treatment recommendations.

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
  Groq API key. `CREWAI_DISABLE_TELEMETRY=true`, `OTEL_SDK_DISABLED=true`,
  `HF_HUB_OFFLINE=1`, and `TRANSFORMERS_OFFLINE=1` are set so CrewAI
  telemetry and Hugging Face hub calls are disabled for zero-network offline
  execution.
- A root entry point (`main.py`) exposes both the FastAPI application
  (`main:app` and `create_app`) and a keyless offline CLI check (`python main.py`).
- End-to-end integration tests (`tests/integration/test_end_to_end_system.py`)
  and the 20-scenario acceptance suite (`scripts/run_acceptance_suite.py` and
  `tests/acceptance/test_acceptance_suite.py`) verify all 15 subsystems
  working together offline with zero external network connections.

Run the keyless root entry point in PowerShell:

```powershell
python .\main.py
```

Run the 20-scenario offline acceptance suite and generate
`evaluation/results/acceptance_results.json`,
`evaluation/traces/acceptance_traces.jsonl`, and
`reports/acceptance_report.md`:

```powershell
python .\scripts\run_acceptance_suite.py
```

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

Run the local HTTP and WebSocket API in offline mock mode (via `main:app` or `practo_agent.api.app:app`):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:MOCK_LLM = 'true'
$env:CREWAI_DISABLE_TELEMETRY = 'true'
$env:OTEL_SDK_DISABLED = 'true'
python -m uvicorn main:app --host 127.0.0.1 --port 8000
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

This evaluates the required 15 queries (`QUALITY-001` through `QUALITY-015`)
with a structured LLM judge (`qwen/qwen3.8-27b`) and writes per-query scores,
justifications, aggregate averages, and a readable report to
`evaluation/results/response_quality_results.json` and
`reports/response_quality_report.md`. In the recorded 15-query live run, the
aggregate averages on the 1-to-5 scale are: **Accuracy `4.47/5` (`4.4667`)**,
**Grounding `4.47/5` (`4.4667`)**, **Completeness `4.13/5` (`4.1333`)**, and
**Safety `4.93/5` (`4.9333`)**. See
[`docs/architecture/response_quality_evaluation.md`](docs/architecture/response_quality_evaluation.md)
for the scoring dimensions, per-query analysis, and output files.

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

## Assignment verification summary

All 15 subsystems—knowledge-base retrieval, deterministic appointment lookup,
sequential CrewAI specialists, Pydantic output contracts, input/output
guardrails (contact-number PII masking, phrase-based prompt-injection
rejection, and output groundedness validation), LangChain session memory,
context-aware response caching, runtime token/cost budgets, FastAPI
HTTP/WebSocket endpoints, two-agent AutoGen Round Robin review,
application-layer tool-permission governance and risk classification,
privacy-safe JSONL observability, zero-tolerance safety evaluation (`7/7`
passed), the 15-query live LLM-as-a-judge response-quality evaluation
(`evaluation/results/response_quality_results.json` and
`reports/response_quality_report.md`), and the 20-scenario offline acceptance
suite (`20/20` passed)—are integrated, tested (`404 passed, 31 subtests
passed`), and demonstrated.
