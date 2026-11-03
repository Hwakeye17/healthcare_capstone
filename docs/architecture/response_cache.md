# Response Cache

## Design

`ResponseCache` in `src/practo_agent/cache/response.py` stores answered
`AgentResponse` objects in process memory. It does not persist responses
across restarts.

The cache normalizes queries using Unicode NFKC normalization, case-folding,
and whitespace collapsing. It creates a deterministic SHA-256 key from the
normalized query, relevant context, and optional scope. `ConversationMemory`
passes the session ID as scope and the prior history as context, preventing
cross-session and context-mismatched reuse.

Only `ANSWERED` responses are cached. Abstentions and computation errors are
not cached. Cache statistics report hits, misses, computation invocations,
and entry count. Concurrent misses may compute a key more than once; the
cache does not serialize potentially slow workflow calls.

## Demonstration

Run the end-to-end offline demonstration from the repository root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_response_cache.py
```

The script runs the real offline workflow for a synthetic appointment query,
then verifies:

- The normalized equivalent query is a cache hit and does not invoke the
  workflow again.
- The same query with different prior context is a cache miss.
- The same query with a different session scope is a cache miss.

The safe transcript is saved to
`evaluation/results/response_cache_demo.json`.
