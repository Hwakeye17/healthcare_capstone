# Conversation Memory

## Design

`ConversationMemory` in `src/practo_agent/memory/conversation.py` wraps the validated
CrewAI workflow with LangChain `RunnableWithMessageHistory` and
`InMemoryChatMessageHistory`. Callers provide a non-empty `session_id` for
each turn:

```python
from practo_agent.memory import ConversationMemory

conversations = ConversationMemory()
response = conversations.run_turn(
    "What is the status of APT-0001?",
    session_id="conversation-123",
)
```

Reuse the same manager instance for turns in the same process. Different
session IDs receive independent histories. Histories are in memory only and
are lost when the process exits.

The installed LangChain version emits a `LangChainDeprecationWarning` because
`RunnableWithMessageHistory` is deprecated in favor of LangGraph persistence.
The capstone requirement explicitly calls for the LangChain class; it remains
functional here, so the warning is expected and is not suppressed.

Prior user and assistant messages are supplied to the Crew as untrusted
context; they do not replace the current user request or the knowledge base
and appointment tools as sources of truth. Current input guardrails still run
before routing or agent execution. Prompt-injection attempts are rejected
without being added to history.

Contact numbers are masked before the user input enters history. Assistant
answers are likewise masked before storage. This memory feature does not
provide durable storage, cross-process synchronization, or general-purpose
PII detection.

The manager also uses the in-process `ResponseCache`. Cache keys include the
normalized query, session ID, and prior conversation context. An immediately
repeated equivalent turn can reuse an answered response while still appending
the new user/assistant exchange to history. A changed context or a different
session cannot reuse that entry. Abstentions are not cached.

## Demonstration

Run the end-to-end offline demonstration from the repository root:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python .\scripts\demo_conversation_memory.py
```

The first transcript demonstrates a two-turn follow-up using the appointment
ID from the earlier turn:
`evaluation/results/conversation_memory_demo.json`.

The separate fresh-session transcript demonstrates that the same follow-up
question does not inherit the previous session's appointment:
`evaluation/results/conversation_memory_fresh_session.json`.
