# Runtime Token and Cost Budget: Design Rationale

## Purpose and scope

The runtime budget requires the Practo workflow to estimate LLM usage, enforce
a per-request token/cost limit, stop before an over-budget model call, and
demonstrate rejection of an oversized request. This note records the
implementation decisions and their trade-offs so the choices are reviewable
and adjustable; it is not a record of private internal reasoning.

The implementation lives in `src/practo_agent/config/runtime_budget.py`.
`run_practo_query` creates one budget for the request and shares it with the
CrewAI LLM and, in live mode, the separate groundedness-verifier LLM.

## Design decisions

### Check the request before routing, then enforce at every model-call boundary

The initial check includes the sanitized user query and formatted conversation
history. It runs before query routing, Crew construction, and model creation.
This rejects a clearly oversized request without paying for agent setup or
calling a model.

A query-only check is not sufficient for the whole workflow: agent prompts,
retrieved evidence, tool results, and the groundedness prompt can add
substantial input after routing. Therefore each actual model-call wrapper
reserves estimated prompt tokens and the configured maximum completion before
dispatch. The same request budget covers CrewAI calls and live groundedness
validation, so one component cannot silently start a separate allowance.

### Estimate instead of claiming exact token counts

The project has multiple prompt formats and model clients, while CrewAI's
completion call returns generated content rather than a uniform provider
usage record suitable for this shared guard. A tokenizer-independent
estimate keeps preflight enforcement available offline and across both model
call paths.

The estimator rounds UTF-8 byte length up at approximately three bytes per
token. It is intentionally simple and deterministic, but it is not the
configured model's tokenizer and is not guaranteed to overestimate every
input. Reported token and cost values must therefore be treated as estimates,
not provider usage or billing.

### Reserve the configured output maximum before dispatch

Actual output length is unknown before a call. Reserving the configured
completion maximum per call prevents starting a call whose possible output
would exceed the remaining allowance. This is conservative: a short response
still consumes the full reservation in the estimate. The live CrewAI and
groundedness model clients receive the same maximum completion setting used
by the reservation.

### Use request-scoped state and fail closed

One `RuntimeBudget` instance accumulates estimated input, reserved output,
call count, estimated cost, and rejection state for a request. The workflow
returns an abstention when a preflight check or model-call reservation fails.
It does not retry the denied call or silently create a fresh budget.

Injected LLM implementations must expose `set_runtime_budget`; otherwise the
workflow raises a `TypeError` rather than proceeding without enforcement.

## Default limits and why they are starting values

| Setting | Default | Rationale |
|---|---:|---|
| `MAX_REQUEST_INPUT_TOKENS` | 8,192 | Bounds the user query plus conversation history before routing. This is a guardrail, not a target prompt size. |
| `MAX_TOTAL_ESTIMATED_TOKENS` | 32,768 | Covers cumulative prompt estimates and output reservations across the multi-agent workflow. The first 16,384-token setting rejected a normal offline integration scenario at an estimated 18,021 tokens, so the default was raised to 32,768 and the existing integration scenario was rerun successfully. |
| `MAX_COMPLETION_TOKENS_PER_CALL` | 1,024 | Limits each individual completion and makes its worst-case output reserve predictable across calls. |
| `MAX_ESTIMATED_COST_USD` | 0.05 | Provides an explicit per-request stop condition when configured input/output rates are applied. Treat as a project default to tune, not as a guarantee of actual charges. |
| `INPUT_COST_PER_MILLION_TOKENS_USD` | 0.80 | Configurable input-rate assumption for the configured Groq model. |
| `OUTPUT_COST_PER_MILLION_TOKENS_USD` | 4.00 | Configurable output-rate assumption for the configured Groq model. |

These are initial configurable caps, not empirically optimized production
limits. Verify the provider's current model and pricing before using live
traffic or changing the configured model. Price tiers, cached-token rates,
tool/provider charges, tokenizer behavior, and provider-side accounting may
differ from this simple estimate.

## Cost calculation

The estimate is:

```text
(estimated_input_tokens * input_USD_per_million
 + reserved_output_tokens * output_USD_per_million) / 1,000,000
```

The configured cost limit is checked before each model dispatch using the
projected cumulative totals. Both token and cost caps must permit the next
call. Cost reporting uses the same estimate; it is not an invoice amount.

## Validation and expected behavior

The offline demo in `scripts/demo_runtime_budget.py` uses a deliberately
oversized request and asserts all of the following:

- The response is abstained.
- The estimated request input exceeds the configured 8,192-token limit.
- Rejection occurs before routing/model execution.
- The mock LLM call count remains zero.

The checked-in transcript is
`evaluation/results/runtime_budget_demo.json`. During validation, the demo
estimated 10,000 tokens for the 30,000-character input and recorded zero LLM
calls, matching the expected result. The full unit and integration test run
passed with 327 tests and 31 subtests.

Run the check from PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests\unit tests\integration -q
python scripts\demo_runtime_budget.py
```

## Limitations and follow-up

- The byte-based heuristic can undercount some text and overcount other text;
  it does not parse provider-specific message/tool serialization exactly.
- Full per-call output reservations can reject a request earlier than actual
  usage would require.
- Estimates do not replace provider usage metadata. If reliable usage
  metadata is later exposed consistently for both model paths, it can be
  recorded alongside estimates and used to assess calibration.
- Revisit caps and rates when the model, provider, prompt structure, or
  workflow changes. Keep the offline oversized-request test as a regression
  check for rejection-before-call behavior.
