# AutoGen Response Review

The CrewAI workflow sends an answered draft and its validated query/evidence
to a separate, tool-free AutoGen review stage. It consists of a Reviewer Agent
and a Final Editor Agent in a `RoundRobinGroupChat` with `max_turns=2`.
Neither agent receives appointment-system tools or permissions.

The reviewer returns structured Pydantic feedback indicating approval or
specific issues. The editor returns a structured Pydantic final response.
When the reviewer approves the draft, the editor must preserve it exactly.
For a revision, the editor may correct or remove identified unsupported
claims, but may not add unsupported facts or change source/appointment
references. Revised answers are checked against the validated evidence again;
an unsupported revision is rejected.

In `MOCK_LLM=true` mode, the application uses AutoGen's replay model client so
the team runs without network access or an API key. Live mode uses the
configured Groq model through its OpenAI-compatible endpoint. Both turns are
reserved against the request's configured token and cost budget.

## Offline demonstration

Run:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python scripts\demo_autogen_review.py
```

The demonstration runs two real AutoGen team sessions using scripted offline
model responses: an approved answer that remains unchanged, and an
intentionally unsupported draft that is corrected. It verifies the final
Pydantic responses, both two-turn limits, and groundedness, then writes
`evaluation/results/autogen_review_demo.json`.
