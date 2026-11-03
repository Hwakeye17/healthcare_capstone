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
  outputs.
- Every specialist handoff and final response is validated against its
  Pydantic contract. Invalid JSON or invalid fields are rejected.
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

The RAG and CrewAI workflow are implemented and covered by tests. Remaining
assignment work includes session-based memory, input guardrails, cache and
runtime budget controls, FastAPI/WebSocket deployment and privacy-safe
structured logging, the 15-query four-dimension evaluation, the AutoGen review
stage, governance controls and their required demonstrations. Track these
against the acceptance criteria in the handoff; do not mark a feature complete
until its behavior is demonstrated and tested.
