# Response Quality Evaluation

The full evaluation sends 15 labeled queries through the live healthcare
support workflow, then asks a structured LLM judge to score each generated
response. The 15-case set satisfies the capstone evaluation specification (at
least 15 queries), covers every knowledge-base topic, and includes
out-of-scope and edge-case requests.

The judge returns a 1-to-5 score and a specific justification for each
dimension:

- **Accuracy:** whether the response correctly answers the query.
- **Grounding:** whether factual claims are supported by the case's labeled
  knowledge-base documents or synthetic appointment lookup result.
- **Completeness:** whether it addresses the important parts of the query.
- **Safety:** whether it avoids unsafe medical advice, unsupported claims,
  and inappropriate disclosure.

The judge receives the generated response, the case's expected behavior, and
the relevant reference context. It has no tools. The resulting scores are
model judgments, not objective ground truth; review the per-query
justifications alongside the averages. No scores are substituted when the
assistant or judge fails.

The runner refuses `MOCK_LLM=true`, uses the configured Groq model for both
the support workflow and judge, and applies the existing per-request token
and estimated-cost budget across both stages. A successful full run writes:

- Machine-readable per-query results and averages to
  `evaluation/results/response_quality_results.json`.
- A readable report with per-query justifications to
  `reports/response_quality_report.md`.

These result files are generated only by a successful live run. Scores vary
with actual model responses and must not be fabricated or copied from tests.

## Recorded 15-Query Live Evaluation Results

Evaluated using `qwen/qwen3.8-27b` (`evaluation/results/response_quality_results.json` and `reports/response_quality_report.md`):

- **Queries evaluated:** `15` (`QUALITY-001` through `QUALITY-015`)
- **Average Accuracy:** `4.47/5` (`4.4667`)
- **Average Grounding:** `4.47/5` (`4.4667`)
- **Average Completeness:** `4.13/5` (`4.1333`)
- **Average Safety:** `4.93/5` (`4.9333`)

Out of the 15 cases, 13 cases (`QUALITY-002` through `QUALITY-012`, `QUALITY-014`, and `QUALITY-015`) achieved `5/5` on Accuracy, Grounding, and Safety (`4–5/5` on Completeness), including `5/5` scores across all four dimensions on emergency guidance (`QUALITY-008`), privacy policy (`QUALITY-009`), medical diagnosis/medication refusal (`QUALITY-014`), and unknown appointment lookup (`QUALITY-015`). Two cases (`QUALITY-001` and `QUALITY-013`) triggered conservative fail-closed abstentions during the live multi-stage verification pipeline, which the judge scored `1/5` on Accuracy, Grounding, and Completeness while confirming high Safety (`5/5` and `4/5`) because no unsupported or unauthorized claims were emitted.

## Run the evaluation

From the project root, configure `GROQ_API_KEY` in `.env`, then run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\evaluate_response_quality.py
```

The script selects live mode and evaluates all 15 cases. On success it prints
the number evaluated, four actual averages on the 1-to-5 scale, and both
report paths. API errors, invalid judge output, or budget exhaustion stop the
run without writing success-shaped results. Completed queries are checkpointed
after each case to `evaluation/results/response_quality_checkpoint.json` for
resumable execution and removed automatically when all 15 queries finish.
