# Response Quality Evaluation

The full evaluation sends 15 labeled queries through the live healthcare
support workflow, then asks a structured LLM judge to score each generated
response. The 15-case set is required by `docs/Healthcare.txt` (at least 15),
covers every current knowledge-base topic, and includes out-of-scope and
edge-case requests.

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
After completing all project milestones, run and review all 15 cases and
generate the full result files.

## Run the evaluation

From the project root, configure `GROQ_API_KEY` in `.env`, then run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\evaluate_response_quality.py
```

The script selects live mode and evaluates all 15 cases. On success it prints
the number evaluated, four actual averages on the 1-to-5 scale, and both
report paths. API errors, invalid judge output, or budget exhaustion stop the
run without writing success-shaped results.
