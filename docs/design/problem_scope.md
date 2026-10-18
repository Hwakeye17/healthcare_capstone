
# Practo Domain Support Agent — Design Contract

**Status:** Initial design baseline  
**Project type:** Healthcare administrative support capstone  
**Implementation constraint:** `MOCK_LLM=true` must work without API keys or network access.

## 1. Problem and Scope

### Problem statement

Build an administrative support agent for the Practo domain that answers clinic-policy questions using a project-authored local knowledge base and checks appointment status using a seeded synthetic dataset.

The system must provide grounded, structured responses, recognize unsupported questions, protect personal information, and produce auditable evidence of its behavior.

### In scope

- Answer administrative questions using the project-authored local knowledge base.
- Retrieve relevant passages using two independently evaluated chunking strategies.
- Decline to invent information when evidence is insufficient.
- Look up appointment status and associated administrative fields using a controlled tool.
- Coordinate specialist agents through explicit task contracts.
- Maintain isolated conversational sessions.
- Apply input, output, privacy, budget, and tool-permission guardrails.
- Expose HTTP endpoints and a multi-turn WebSocket interface.
- Evaluate responses, retrieval quality, tool use, safety, and review outcomes.
- Run the required acceptance tests with `MOCK_LLM=true`, without API keys or network access.

### Out of scope

- Diagnosing medical conditions or recommending treatment.
- Replacing a clinician, emergency service, or clinic employee.
- Using real patient records or real appointment systems.
- Booking, cancelling, or rescheduling real appointments.
- Making payments, issuing refunds, or changing appointment records.
- Claiming that synthetic data represents actual Practo operations.
- Automatically taking clinical or other high-impact actions.

## 2. Roles and Non-Goals

### Retrieval Agent

**Responsibility:** Retrieve relevant project-authored knowledge-base passages for an administrative question.

**Allowed capability:** Read-only access through the designated RAG tool.

**Must not:** Invent policy, access appointment records, or answer from unsupported assumptions.

### Lookup Agent

**Responsibility:** Retrieve administrative fields for a supplied synthetic appointment record ID.

**Allowed capability:** Call the explicitly authorized appointment lookup tool.

**Must not:** Modify records, access unrelated data, or infer missing appointment details.

### Response Composer

**Responsibility:** Combine validated evidence and tool results into a clear, structured support response.

**Allowed capability:** Use the outputs handed off by the preceding stages.

**Must not:** Invent facts, bypass guardrails, or turn administrative information into clinical advice.

### Review stage

A separate AutoGen review stage will review the CrewAI draft. It must use the required two-agent Round Robin Group Chat, bounded to two turns, and return structured output.

The reviewer and final editor do not receive additional appointment-system permissions.

## 3. Handoffs and Contracts

Every agent boundary must have an explicit, validated data contract.

### User request

The request contract must identify the user's query and the session identifier where applicable. Input validation and PII masking occur before the request is logged or passed to model-facing components.

### Retrieval result

The retrieval handoff must preserve:
- The retrieved text.
- The source document identifier.
- Chunk or passage metadata sufficient for evaluation.
- Retrieval scores or other available ranking evidence.

The response must not cite or claim support from a source that was not retrieved.

### Appointment lookup result

The lookup tool accepts `record_id: str` and returns the required administrative fields:
- `status`
- `consultation_fee_inr`
- `escalation_score`

The score must be bounded between 0 and 1 and derived from the specified synthetic dataset fields using a documented, deterministic formula.

### Final response

Every CrewAI response must conform to a Pydantic output schema. The response contract must distinguish a grounded answer from an unsupported answer or escalation.

The AutoGen final editor must also return its required Pydantic structured output.

## 4. Tools, Data, Permissions, and Owners

| Resource | Access | Owner / enforcing component |
|---|---|---|
| Project-authored policy documents | Read-only | RAG pipeline |
| Fixed-size chunk collection | Read-only retrieval | RAG retriever |
| Sentence-based chunk collection | Read-only retrieval | RAG retriever |
| Synthetic appointment dataset | Read-only | Dataset loader and lookup tool |
| Appointment lookup tool | Lookup only | Lookup Agent permission boundary |
| Session history | Current session only | Session memory component |
| Response cache | Normalized query lookup | Cache component |
| JSONL request logs | Append-only | Observability component |
| Evaluation outputs and traces | Write during evaluation | Evaluation runner |

Only the Lookup Agent may invoke the appointment lookup tool. This restriction must be enforced by application code, not merely stated in an agent prompt.

The implementation must not depend on live Practo services or external network calls in mock mode.

## 5. Human Gates, SLAs, and Fallbacks

This capstone does not perform real clinical or appointment-changing actions. Therefore, it does not authorize autonomous high-impact decisions.

The system must:
- Admit when retrieved evidence is insufficient.
- Use the calibrated retrieval threshold to determine when to abstain.
- Refuse requests for diagnosis or treatment advice.
- Avoid guessing when an appointment record cannot be found.
- Fail closed when a required tool or validation step fails.
- Return a safe, structured fallback when groundedness checks fail.
- Make escalation or human assistance explicit when the request cannot safely be resolved.

No operational SLA is assumed by this synthetic capstone. Any real deployment would require a named support owner, an approved escalation process, and agreed response-time targets.

## 6. Risks and Success Metrics

### Principal risks

- Unsupported or fabricated policy answers.
- Incorrect appointment status or fee.
- PII leakage through prompts, responses, or logs.
- Prompt injection and attempts to bypass tool permissions.
- Retrieval failure caused by chunk boundaries or poor ranking.
- Session history leaking across independent users.
- Excessive token use, runtime, or repeated model calls.
- Mock mode accidentally making network requests.
- Review or evaluation scores hiding a failed tool-use trajectory.

### Required measurable outcomes

- At least 40 valid synthetic appointment records.
- All required category and status values represented at the specified minimum counts.
- Follow-up-required proportion between 10% and 30%.
- At least 12 original knowledge-base documents covering all required topics.
- Both required chunking strategies evaluated on the same set of at least five queries.
- Retrieval precision and recall calculated at document level, with per-query arithmetic.
- Threshold calibration using at least three in-scope and two out-of-scope queries.
- At least five in-scope demonstrations and one out-of-scope fallback demonstration.
- A lookup tool demonstration and separate demonstrations of the required CrewAI tools.
- Multi-turn memory demonstrated, including isolation of a fresh session.
- Every required input/output guardrail exercised by a deliberate test.
- At least two HTTP endpoints and a multi-turn WebSocket workflow.
- JSONL request logs containing trace IDs and timing without unmasked fixed-format PII.
- At least 15 evaluation queries, covering all required knowledge-base topics and including at least two out-of-scope or edge-case queries.
- Accuracy, Grounding, Completeness, and Safety scores recorded per query and averaged.
- At least two AutoGen review demonstrations: one approval without changes and one revision of an intentionally unsupported draft.
- Risk classification, least-privilege enforcement, runtime budget enforcement, and a demonstrated cache hit.
- Successful acceptance tests under `MOCK_LLM=true` with zero API keys and zero network access.

### Safety metric

**Target: zero successful unauthorized appointment-tool calls and zero unmasked fixed-format PII occurrences in application logs during the acceptance suite.**

### Evaluation principle

Assess both the final answer and the trajectory that produced it. Verify required tool calls, forbidden tool calls, retrieved evidence, fallback behavior, and the final response. Record failures in reproducible traces rather than relying only on whether an answer sounds plausible.
