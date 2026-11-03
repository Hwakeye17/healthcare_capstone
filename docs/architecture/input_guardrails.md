# Input Guardrails

## Contact-number masking

The assignment explicitly requires an input-side guardrail for its fixed-format
contact-number field. The OCR text does not define the exact digit pattern.
Following the project context and the lecture summary's ten-digit phone-regex
example, this implementation treats an Indian mobile number as ten digits
beginning with 6–9. It also recognizes an optional `+91` or `0` prefix and
optional spaces or hyphens between digits.

The request workflow replaces each match with
`[REDACTED_CONTACT_NUMBER]` before deterministic routing, Crew construction,
or LLM execution. The same sanitized query is supplied to the offline mock
LLM, whose tool-selection behavior otherwise retains its own query value.

For example:

```text
Input:  Please call +91-98765-43210 about my appointment.
Masked: Please call [REDACTED_CONTACT_NUMBER] about my appointment.
```

The assignment explicitly identifies patient names, diagnosis/condition, and
insurance IDs as free text without a universal matching format and excludes
them from this fixed-format masking requirement. Addresses are likewise not
reliably identifiable by this pattern and are not masked. This component is
not general-purpose PII detection; use fabricated examples only, as required
by the assignment. Any future request logging must receive the sanitized
query rather than the original input.

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
necessary. Ordinary appointment and policy questions should continue through
the normal workflow.

Run the offline rejection demonstration from the repository root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_prompt_injection.py
```

The demo exercises `run_practo_query` with a deliberate override attempt and
fails if routing or Crew construction is reached. Its safe transcript,
`evaluation/results/prompt_injection_demo.json`, omits the attack text while
recording the detected category and rejection result.

## Remaining guardrail work

The separate output-side groundedness validator exists for the standalone RAG
flow, but integrating it into the CrewAI response lifecycle remains
outstanding.
