# Input Guardrails

## Contact-number masking

The assignment specification requires an input-side guardrail for its
fixed-format contact-number field. Following the ten-digit phone-regex pattern
from the course specification, this implementation treats an Indian mobile
number as ten digits beginning with 6–9. It also recognizes an optional `+91`
or `0` prefix and optional spaces or hyphens between digits.

The request workflow replaces each match with
`[REDACTED_CONTACT_NUMBER]` before deterministic routing, Crew construction,
or LLM execution. The same sanitized query is supplied to the offline mock
LLM, whose tool-selection behavior otherwise retains its own query value.

For example:

```text
Input:  Please call +91-98765-43210 about my appointment.
Masked: Please call [REDACTED_CONTACT_NUMBER] about my appointment.
```

The capstone specification identifies patient names, diagnosis/condition, and
insurance IDs as free text without a universal matching format and excludes
them from this fixed-format masking requirement. Addresses are likewise not
reliably identifiable by this pattern and are not masked. This component is
not general-purpose PII detection; use fabricated examples only, as required
by the assignment. Request logging uses an allowlisted JSONL event schema that
excludes raw user queries and contact numbers.

Run the end-to-end offline demonstration from the repository root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_input_guardrails.py
```

The script runs the real offline Crew workflow, observes the sanitized value
at the routing boundary and mock LLM, verifies the expected retrieval tool
executes, and saves a safe transcript to
`evaluation/results/input_guardrail_demo.json`. The transcript marks the
fabricated number without persisting its digits.

## Prompt-injection detection

The request workflow checks the contact-number-masked query for clear,
common attempts to override system/developer/safety instructions, adopt an
unrestricted role, or obtain hidden instructions, credentials, or other
patients' records. A detected request is rejected with a fixed abstention
response before deterministic routing, Crew construction, or LLM execution.

This is a deterministic phrase-based input filter, not a semantic classifier
or a complete security boundary. It can miss novel or obfuscated attacks and
may flag wording that resembles a known pattern. Agent prompts, least-
privilege tool assignments, output validation, and other controls remain
necessary. Ordinary appointment and policy questions continue through the
normal workflow.

Run the offline rejection demonstration from the repository root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_prompt_injection.py
```

The demo exercises `run_practo_query` with a deliberate override attempt and
fails if routing or Crew construction is reached. Its safe transcript,
`evaluation/results/prompt_injection_demo.json`, omits the attack text while
recording the detected category and rejection result.

## CrewAI output groundedness

Before returning an `ANSWERED` CrewAI result, the workflow gathers evidence
from the validated Retrieval Agent output and successful appointment lookup
output. Knowledge-base citations and appointment references must correspond
to those specialist results. The groundedness validator checks each answer
claim against that evidence. Existing specialist abstentions pass through
without validation; missing evidence, unsupported claims, invalid references,
or validator errors fail closed as an abstention without retaining citations.

The offline validator uses conservative normalized exact-text matching; it
does not establish semantic entailment and does not accept arbitrary
paraphrases. Live mode uses the configured Groq groundedness validator. Neither
validator replaces source permissions, structured-output checks, or human
review.

Demonstrate rejection of a deliberately unsupported answer through the
application workflow:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_groundedness_guardrail.py
```

The script uses a controlled Crew result to exercise the real workflow gate
and saves `evaluation/results/groundedness_guardrail_demo.json`. Supported
offline Crew scenarios are also exercised by
`scripts/demo_grounded_generation.py` and the integration tests.

The input and output checks run as part of the shared CrewAI request
lifecycle alongside session-based memory (`src/practo_agent/memory/`),
context-aware response caching (`src/practo_agent/cache/`), runtime token/cost
budgets (`src/practo_agent/config/runtime_budget.py`), FastAPI HTTP/WebSocket
transports (`src/practo_agent/api/`), and privacy-safe JSONL logging
(`src/practo_agent/observability/`).
