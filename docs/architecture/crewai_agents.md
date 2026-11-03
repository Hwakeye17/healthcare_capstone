
# CrewAI Agent Architecture

## 1. Purpose

The CrewAI layer coordinates Practo's administrative support workflow using three specialist agents. Each agent has a distinct responsibility, explicit tool permissions, and a structured Pydantic output contract.

The system is limited to administrative support. It must not provide medical diagnosis, treatment recommendations, or clinical decisions.

## 2. Agent Responsibilities

| Agent | Responsibility | Assigned tools | Output schema |
|---|---|---|---|
| Retrieval Agent | Retrieve and assess relevant administrative knowledge-base evidence | `search_practo_knowledge_base` | `RetrievalAgentOutput` |
| Lookup Agent | Retrieve appointment details using an appointment record ID | `check_appointment_status` | `LookupAgentOutput` |
| Response Composer | Combine specialist outputs into a structured response | None | `AgentResponse` |

### Retrieval Agent

- Uses the existing sentence-based ChromaDB collection.
- Uses the configured retrieval and evidence-assessment pipeline.
- Can report successful retrieval, insufficient evidence, an error, or that retrieval is not required.
- Cannot access appointment lookup functionality.

### Lookup Agent

- Uses the deterministic appointment lookup tool.
- Requires an appointment record ID.
- Preserves the returned appointment details.
- Can report a successful lookup, a missing record, an error, or that lookup is not required.
- Cannot access the knowledge-base search tool.

### Response Composer

- Receives the outputs of both specialist tasks.
- Has no tools.
- Combines only information supported by the specialist outputs.
- Returns an `AgentResponse`.
- Must abstain when the available information cannot support a reliable administrative response.

## 3. Structured Output Contracts

All three agents use Pydantic output contracts.

- `RetrievalAgentOutput`: records whether retrieval was required and whether acceptable evidence was obtained.
- `LookupAgentOutput`: records whether appointment lookup was required and whether the record was found.
- `AgentResponse`: represents the final answer or an explicit abstention, with appropriate source or appointment references.

The schemas validate status-dependent fields and prevent inconsistent combinations of results.

## 4. Tool Permissions

Tool permissions are enforced through the Python agent definitions, not solely through natural-language instructions.

| Agent | Knowledge-base tool | Appointment lookup tool |
|---|---:|---:|
| Retrieval Agent | Allowed | Not allowed |
| Lookup Agent | Not allowed | Allowed |
| Response Composer | Not allowed | Not allowed |

All agents have `allow_delegation=False`.

This follows the principle of least privilege: an agent receives only the capabilities required for its assigned responsibility.

## 5. Task Dependencies and Execution

The CrewAI workflow uses a sequential process. The application entry point
`run_practo_query` masks fixed-format contact numbers and rejects recognized
prompt-injection or restricted-information requests before deterministic
routing and crew construction:

1. Contact numbers are redacted from the query before it is provided to any
   CrewAI LLM, including the offline mock.
2. Recognized prompt-injection attempts are rejected before routing, Crew
   construction, or LLM execution.
3. Policy questions use the Retrieval Agent.
4. Requests containing one appointment record ID use the Lookup Agent.
5. Mixed policy and record questions use both specialists.

Before returning an answered result, the workflow validates citations against
the successful specialist outputs and checks every answer claim against the
retrieved knowledge-base evidence and/or validated appointment lookup fields.
Unsupported claims and validation errors produce a fail-closed abstention.
5. The Response Composer receives outputs only from enabled specialist tasks.

Questions outside the supported scope are sent through calibrated retrieval so
the evidence layer can abstain. A request containing multiple record IDs is
rejected for clarification rather than guessed.

The Response Composer receives the outputs of the enabled specialist tasks as
context.

## 6. Workflow Design

The routing layer separates query classification from CrewAI task execution.
`run_practo_query` creates only the specialist tasks required for a query and
always includes the Response Composer. Disabled tasks are omitted from the
composer's context rather than represented as completed tasks.

This design keeps routing deterministic, limits each specialist to its
assigned tools, and validates specialist handoffs and final responses with
Pydantic contracts. Offline and live modes use the same task definitions,
tool permissions, and output contracts; only the configured LLM differs.
Offline execution uses local retrieval and appointment lookup without API
credentials or external network access.

## 7. Memory Configuration

CrewAI memory is disabled (`memory=False`).

The application can use `ConversationMemory`, which wraps the validated
request workflow with LangChain `RunnableWithMessageHistory` and
`InMemoryChatMessageHistory`. Each `ConversationMemory` instance owns
in-process histories keyed by caller-supplied session IDs. Prior turns are
passed to the agents as explicitly untrusted context; current input guardrails
still run before routing or agent execution.

Contact numbers are masked before the user turn is stored, and the assistant
answer is masked before being added to history. Prompt-injection attempts are
rejected without being added to history. Histories are not persisted across
process restarts; API integrations should retain and reuse one manager
instance for the lifetime of the application process.

`ConversationMemory` also uses the context-aware `ResponseCache`. Cache keys
include the session ID, prior conversation context, and normalized current
query. An immediately repeated equivalent turn can reuse an answered result
without skipping the corresponding history update.

This avoids introducing an additional uncontrolled memory mechanism.

## 8. LLM and Testing Strategy

CrewAI agents receive an LLM through dependency injection.

Unit tests use a test-only implementation of CrewAI's `BaseLLM`. The test implementation raises an error if an LLM call is attempted.

This allows tests to verify agent construction, permissions, task contracts, dependencies, and crew configuration without making external model requests.

`MOCK_LLM=true` selects the project's deterministic `BaseLLM` implementation
without requiring an API key. It uses CrewAI's ReAct action format and selects
the permitted tool by its declared argument schema. The generated assistant
action—not the ReAct system template—is used to read the subsequent tool
observation. OpenTelemetry is disabled for this offline execution path.

Live Groq calls use CrewAI's ReAct tool parser rather than provider-native
function calling. The Groq LLM adapter disables native function calling so
CrewAI can parse the model's ReAct action against the tools assigned to each
agent. The default model is `qwen/qwen3.8-27b`; `GROQ_MODEL` can override it.
The final task outputs are validated against their Pydantic contracts.

The RAG tool uses the locally available real Sentence Transformers embedding model to query the persisted ChromaDB collection. Deterministic test embeddings are not used to establish semantic retrieval quality.

## 9. Validation

The implementation is covered by unit and integration tests for:

- Pydantic output contracts.
- Agent construction and tool permissions.
- Delegation restrictions.
- Task-to-agent assignment.
- Structured output schema assignment.
- Task context dependencies.
- Sequential process configuration.
- Crew agent and task ordering.
- Disabled Crew memory.
- No unexpected LLM invocation during construction.
- Deterministic routing, tool invocation, and Pydantic output validation.
- In-scope end-to-end examples through CrewAI `kickoff()`.
- Mixed-query routing and out-of-scope abstention.
- No attempted external network connection in the offline workflow.

The deterministic integration workflow verifies real local embeddings,
persisted ChromaDB retrieval, and the synthetic appointment dataset. This
establishes the tested tool trajectory and structured response behavior; it
does not establish general semantic answer quality.

## 10. Limitations

- Agent instructions do not constitute a security boundary by themselves; application-level permissions and validation remain necessary.
- Sequential execution runs only the specialist tasks selected by the deterministic router.
- The final response still depends on the quality of specialist outputs.
- Structured output validation does not independently establish factual correctness.
- The deterministic mock adapter is for reproducible acceptance runs; semantic response quality still requires separate evaluation.
