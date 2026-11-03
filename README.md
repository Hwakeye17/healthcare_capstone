# Practo Healthcare Domain Support Agent

This repository is for the Practo Healthcare track. It provides administrative
support using a project-authored knowledge base and a synthetic appointment
dataset. It is not a clinical system and does not provide diagnosis or
treatment recommendations.

## Implemented functionality

- The appointment lookup is deterministic and read-only. It returns the
  appointment ID, specialty, status, fee, record age, follow-up flag,
  administrative score, and the threshold decision with its reason.
- The score is `0.6 * follow_up_required + 0.4 * (days_since_created / 30)`.
  The inclusive administrative threshold is `0.6`. In the current generated
  50-record dataset, 10 records (20%) meet it. This is a project heuristic,
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

The repository is not yet complete against every PDF acceptance criterion.
The appointment dataset currently contains 50 records while the brief requires
240, and the retrieval evaluation set contains 12 queries while the brief
requires 25 for its comparison. These requirements remain open and are not
masked by changing test expectations.
