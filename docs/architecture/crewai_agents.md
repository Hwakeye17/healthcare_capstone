
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

The workflow uses CrewAI's sequential process.

1. The Retrieval Agent evaluates the query and retrieves evidence when relevant.
2. The Lookup Agent evaluates the query and performs appointment lookup when relevant.
3. The Response Composer receives both specialist task outputs through CrewAI task context and produces the final structured response.

The specialist agents can return `NOT_NEEDED` when their respective capabilities are irrelevant. Sequential execution therefore does not imply that both tools must be invoked for every query.

The Response Composer is configured with both specialist tasks as context dependencies.

## 6. Memory Configuration

CrewAI memory is disabled (`memory=False`).

The current workflow uses the outputs of its explicitly defined tasks as the information handoff mechanism. Session-level conversational memory will be implemented separately using LangChain on Day 3.

This avoids introducing an additional uncontrolled memory mechanism.

## 7. LLM and Testing Strategy

CrewAI agents receive an LLM through dependency injection.

Unit tests use a test-only implementation of CrewAI's `BaseLLM`. The test implementation raises an error if an LLM call is attempted.

This allows tests to verify agent construction, permissions, task contracts, dependencies, and crew configuration without making external model requests.

`MOCK_LLM=true` does not automatically replace CrewAI's LLM. The CrewAI test double is explicitly supplied to the agent factory.

The RAG tool uses the locally available real Sentence Transformers embedding model to query the persisted ChromaDB collection. Deterministic test embeddings are not used to establish semantic retrieval quality.

## 8. Validation

The implementation is covered by unit tests for:

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

The complete test suite currently reports 219 passing tests.

These tests establish structural correctness. They do not, by themselves, establish correct LLM tool selection, semantic answer accuracy, or end-to-end workflow reliability. Those behaviors will be evaluated through Task 2.3 and subsequent integration testing.

## 9. Limitations

- Agent instructions do not constitute a security boundary by themselves; application-level permissions and validation remain necessary.
- Sequential execution runs all specialist tasks, even when a specialist ultimately determines that its tool is not required.
- The final response still depends on the quality of specialist outputs.
- Structured output validation does not independently establish factual correctness.
- The current unit tests do not replace real execution traces or end-to-end acceptance tests.
