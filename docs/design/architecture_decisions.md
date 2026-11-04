# Architecture Decision Records — Practo Support Agent

## 1. Purpose

This document records the engineering decisions made while building the Practo Domain Support Agent capstone. It explains the reasoning behind the selected approaches, alternatives considered, known trade-offs, and recorded verification evidence.

The project is an educational prototype for administrative healthcare support. It is not intended to diagnose conditions, recommend treatments, or replace healthcare professionals.

## 2. Decision Status Convention

All architecture decisions in this document are **Implemented and Verified** across the unit, integration, and acceptance test suites (`404 passed, 31 subtests passed`), offline demonstrations, and evaluation reports.

## 3. Decision: Use Synthetic Appointment Records

**Status:** Implemented and verified

### Context

The appointment lookup capability requires structured records containing appointment identifiers, categories, statuses, consultation fees, creation age, and follow-up indicators. Using real patient records would introduce unnecessary privacy risks into an educational project.

### Decision

Generate a reproducible synthetic dataset using Python. The generator produces 240 records using seed `42` and validates the required schema and distribution constraints.

### Alternatives considered

- Using real patient or appointment records.
- Creating records manually.
- Generating records programmatically with a fixed random seed.

### Rationale

Programmatic generation makes the dataset reproducible, easy to validate, and suitable for automated tests. Synthetic records avoid introducing real patient information into the repository.

### Trade-offs

Synthetic data does not represent the full complexity or distribution of real healthcare operations. Passing tests on this dataset does not establish readiness for use with real appointments.

### Evidence

The dataset tests check the required fields, unique record identifiers, the 240-record size, 48 records in every category and status, integer creation-age values between 0 and 30, reproducibility, and a 20% follow-up proportion.

## 4. Decision: Use a Project-Authored Local Knowledge Base

**Status:** Implemented and verified

### Context

The support agent needs a controlled information source for administrative questions about bookings, cancellations, fees, insurance claims, prescription refills, laboratory turnaround, telemedicine, emergencies, privacy, follow-up discounts, second opinions, and home visits.

### Decision

Create 12 Markdown documents specifically for this project and use them as the local knowledge base.

### Alternatives considered

- Retrieving information from arbitrary websites at query time.
- Using a large, uncontrolled collection of external documents.
- Using a small, project-authored collection with explicit topic coverage.

### Rationale

A project-authored knowledge base gives control over the information available to the retrieval system and makes it straightforward to trace generated answers to their sources. It also supports repeatable offline testing.

### Trade-offs

These documents describe sample policies for the capstone. They must not be represented as verified official Practo policies. The knowledge base is limited in scope, and its coverage is evaluated against the labeled query sets.

### Evidence

The knowledge-base validator (`scripts/validate_knowledge_base.py`) checks the required document set and minimum sentence counts (2–5 sentences per document). Unit tests verify document presence and validation behavior.

## 5. Decision: Implement Two Explicit Chunking Strategies

**Status:** Implemented; comparative evaluation completed on 25 labeled queries

### Context

Longer documents need to be divided into smaller pieces before they can be embedded and retrieved. Chunk boundaries can affect whether a retrieved passage contains enough information to answer a question.

### Decision

Implement two strategies:

1. Fixed-size chunking with overlap (`400` characters, `80`-character overlap).
2. Sentence-based chunking with sentence overlap (up to `3` sentences per chunk, `1`-sentence overlap).

### Alternatives considered

- Fixed-size chunking only.
- Sentence-based chunking only.
- Introducing a separate semantic chunking framework.

### Rationale

Implementing both required strategies allows comparing them under the same retrieval queries. A small custom Python implementation makes the boundaries, overlap, and metadata behavior explicit without adding extra dependencies.

### Trade-offs

Fixed-size chunks can split a sentence or concept across boundaries. Sentence-based chunks preserve sentence boundaries but can vary in character length. Each required knowledge-base document contains 2–5 sentences, as specified by the assignment.

### Verification evidence

Both strategies were run against the same 25 labeled queries (`scripts/evaluate_retrieval.py`). Retrieved documents, document-level precision and recall, per-query calculations, and aggregate results are recorded in `evaluation/results/retrieval_results.json` and `evaluation/results/retrieval_comparison.md`.

## 6. Decision: Use Sentence Transformers for Local Embeddings

**Status:** Implemented; real retrieval evaluated on the labeled query set

### Context

The retrieval system needs vector representations of documents and user queries. The capstone must support local execution without requiring a paid embedding API for every request.

### Decision

Use the Sentence Transformers model `sentence-transformers/all-MiniLM-L6-v2`, configured for local model loading, to produce normalized document and query embeddings.

### Alternatives considered

- Calling a hosted embedding API.
- Using deterministic test-only vectors for all runs.
- Loading a locally available Sentence Transformers model.

### Rationale

A local embedding model supports repeatable retrieval experiments and avoids per-request embedding charges to a hosted provider. It also fits the project's local-first design.

### Trade-offs

The model must be available in the local model cache. Local execution consumes memory and CPU time. Model selection alone does not prove that retrieval quality is adequate.

### Verification evidence

Real retrieval was evaluated against the project's 25-query labeled set and 27-query abstention calibration set. The reported results are specific to that set and do not establish held-out generalization.

## 7. Decision: Use ChromaDB with Separate Collections

**Status:** Implemented; retrieval evaluated on 25 labeled queries

### Context

The two chunking strategies need to be evaluated independently. Their stored chunks and search results must not be mixed.

### Decision

Use ChromaDB with cosine-distance configuration and separate collections:

- `practo_fixed_size` (`33` chunks)
- `practo_sentence` (`24` chunks)

The vector-store implementation supports persistent storage, while tests inject an in-memory client.

### Alternatives considered

- Storing vectors manually in application code.
- Using one collection for both strategies.
- Using separate collections in a local vector database.

### Rationale

Separate collections provide a clear boundary between the two experiments. ChromaDB handles vector storage and nearest-neighbor retrieval, allowing the project code to focus on ingestion, metadata, search, and evaluation. Injectable clients allow tests to avoid persistent database files.

### Trade-offs

Separate collections require independent ingestion and evaluation. Persisted collections must be rebuilt when their source documents, chunking settings, or embedding model change. Lower cosine distance indicates greater similarity.

### Verification evidence

Both collections are verified by `scripts/build_vectorstores.py` and `scripts/evaluate_retrieval.py`, with per-query results recorded in `evaluation/results/retrieval_comparison.md`.

## 8. Decision: Use Deterministic Test Embeddings for Unit Tests

**Status:** Implemented and verified

### Context

Unit tests should be fast, repeatable, and independent of model downloads or external network calls.

### Decision

Provide a deterministic test embedding implementation for isolated unit tests. Use it to test vector-store mechanics and validation behavior, while preserving `SentenceTransformerEmbeddings` for all persistent ChromaDB collection queries (including `MOCK_LLM=true` acceptance runs).

### Alternatives considered

- Loading the full embedding model in every isolated unit test.
- Using deterministic vectors for isolated unit tests and real embeddings for persistent collection queries.

### Rationale

Deterministic embeddings reduce unit-test startup overhead and make isolated unit tests fast and repeatable, while real local embeddings ensure full vector compatibility with `practo_sentence` and `practo_fixed_size`.

### Trade-offs

Deterministic test embeddings are not a substitute for a semantic embedding model and are never used to query the persisted ChromaDB collections.

### Evidence

Unit tests cover embedding input validation and deterministic construction, while integration and acceptance tests verify `SentenceTransformerEmbeddings` against the persisted ChromaDB collections.

## 9. Decision: Test Components Independently and End-to-End

**Status:** Implemented across all foundation, agent, guardrail, API, governance, and evaluation modules

### Context

The system contains 15 integrated subsystems: data generation, document loading, chunking, embeddings, vector storage, retrieval, lookup, CrewAI specialists, Pydantic schemas, guardrails, memory, caching, runtime budgets, FastAPI HTTP/WebSocket endpoints, AutoGen review, governance, observability, and evaluation.

### Decision

Maintain focused unit tests for every component alongside end-to-end integration tests (`tests/integration/test_end_to_end_system.py`) and the 20-scenario acceptance suite (`tests/acceptance/test_acceptance_suite.py`).

### Rationale

Focused unit tests identify defects close to their source, while integration and acceptance tests verify that all components work together through the shared request lifecycle.

### Evidence

The complete test suite passes **404 tests and 31 subtests** under `MOCK_LLM=true` with zero external network calls.

## 10. Decision: Keep Reference Course Materials Out of the Public Repository

**Status:** Implemented through repository ignore rules

### Context

Course reference documents and local environment credentials are local materials rather than project deliverables.

### Decision

Exclude `.env`, local ChromaDB binaries (`/data/vectorstores/`), and private reference files from version control via `.gitignore`.

### Evidence

Verified via `.gitignore` and `git status`.

## 11. Decision: Use a Consistent Python Import Convention with the `src` Layout

**Status:** Implemented and verified

### Context

The project follows a `src`-based Python package structure (`src/practo_agent/`).

### Decision

Use `practo_agent` as the Python package import root (e.g., `from practo_agent.rag.chunkers import fixed_size_chunk`) with `PYTHONPATH=src` (and automatic `sys.path` bootstrapping in `main.py` and `scripts/`).

### Rationale

The `src` directory is the package-discovery root, not part of the package name. This convention provides consistent imports across application modules, scripts, and tests.

### Evidence

All 16 scripts in `scripts/`, `main.py`, and all 404 pytest tests execute cleanly using `practo_agent` imports.

## 12. Decision: Centralize RAG Retrieval Configuration

**Status:** Implemented and verified

### Decision

Introduce a centralized, immutable `RetrievalConfig` dataclass in `src/practo_agent/config/retrieval.py` defaulting to `sentence` strategy (`practo_sentence`), `top_k=2`, and `cosine` similarity.

### Rationale

At top-k 2 across the 25-query benchmark, sentence-based chunking achieved `0.8200` macro precision and `1.0000` macro recall compared with `0.7400` and `0.9600` for fixed-size chunking.

### Evidence

Unit tests validate default values, collection selection, custom top-k overrides, strategy-mismatch rejection, and immutability.

## 13. Decision: Use an Empirically Calibrated RAG Abstention Threshold

**Status:** Implemented and calibrated on the 27-query dataset

### Decision

Use an empirically calibrated cosine-distance threshold of **`0.6976266205310822`** (`src/practo_agent/config/grounding.py`) selected via a safety-first rule: require zero false acceptances, maximize in-scope recall, and select the midpoint between the maximum observed in-scope distance (`0.6452579498`) and minimum observed out-of-scope distance (`0.7499952912`).

### Trade-offs and Limitations

The 27-query calibration dataset (25 in-scope, 2 out-of-scope) is small and specific to the project knowledge base; therefore, retrieval distance filtering is paired with post-generation groundedness validation.

### Evidence

Reproducible via `scripts/calibrate_abstention.py` with machine-readable output in `evaluation/results/abstention_calibration.json` (`TP=25, FP=0, TN=2, FN=0`).

## 14. Decision: Use Pydantic for Structured Agent Responses

**Status:** Implemented and verified

### Decision

Use strict Pydantic models (`GroundedResponse`, `RetrievalAgentOutput`, `LookupAgentOutput`, `AgentResponse`, `ReviewFeedback`, `ResponseQualityScores`) across all RAG, CrewAI, AutoGen, API, and evaluation boundaries, rejecting unexpected fields (`extra="forbid"`) and invalid status/field combinations.

### Evidence

Covered by `tests/unit/test_response_schema.py`, `tests/unit/test_agent_outputs.py`, and end-to-end workflow tests.

## 15. Decision: Separate Retrieval Evidence Validation from Generation

**Status:** Implemented and verified

### Decision

Introduce a deterministic evidence-validation component in `src/practo_agent/rag/evidence.py` that retrieves chunks using `DEFAULT_RETRIEVAL_CONFIG`, checks best cosine distance against `DEFAULT_ABSTENTION_THRESHOLD`, and returns a validated `EvidenceAssessment` before any LLM generation occurs.

### Evidence

Unit tests cover accepted evidence, rejected evidence, empty retrieval, threshold boundaries, and invalid source metadata.

## 16. Decision: Separate Grounded Answer Generation

**Status:** Implemented and verified

### Decision

Implement a provider-independent `AnswerGenerator` protocol (`src/practo_agent/rag/generator.py`) with `GroqAnswerGenerator` (`ChatGroq`) for live execution and `MockAnswerGenerator` for deterministic offline execution under `MOCK_LLM=true`. Source references are constructed programmatically in Python from validated evidence rather than trusted to the LLM.

### Evidence

Covered by `tests/unit/test_rag_generator.py` and `scripts/demo_grounded_generation.py`.

## 17. Decision: Validate Generated Claims Against Retrieved Evidence

**Status:** Implemented in both standalone RAG generation and the shared CrewAI workflow (`run_practo_query`)

### Decision

Enforce a fail-closed groundedness-validation stage (`src/practo_agent/rag/groundedness.py` and `src/practo_agent/agents/workflow.py`) after answer generation and after AutoGen response revision. Unsupported claims, invalid source/appointment references, or validator errors convert the response into a safe abstention with empty references.

### Evidence

Covered by `tests/unit/test_groundedness.py`, `scripts/demo_groundedness_guardrail.py`, and Scenario `SAF-03` in `scripts/evaluate_safety.py`.

## 18. Decision: Implement a Deterministic Appointment Lookup Tool

**Status:** Implemented and verified

### Decision

Implement `check_appointment_status(record_id: str) -> dict` in `src/practo_agent/tools/appointment_lookup.py` to read `data/generated/appointments.json` deterministically and compute the administrative prioritization score:

\[
E = 0.6F + 0.4\left(\frac{D}{30}\right)
\]

with an inclusive escalation threshold of `0.6`.

### Evidence

Covered by `tests/unit/test_appointment_lookup.py` (18 unit tests) and `docs/architecture/appointment_lookup.md`.

## 19. Decision: Use Three Specialist Agents with Sequential CrewAI Orchestration

**Status:** Implemented and verified in both offline (`MOCK_LLM=true`) and live Groq execution

### Decision

Coordinate three specialist agents (`Retrieval Agent`, `Lookup Agent`, and tool-free `Response Composer`) using CrewAI `Process.sequential`, deterministic query routing (`route_query`), disabled CrewAI memory (`memory=False`), and `allow_delegation=False`.

### Evidence

Verified across `tests/unit/test_crew.py`, `tests/unit/test_specialist_agents.py`, `tests/unit/test_specialist_tasks.py`, `scripts/demo_offline_workflow.py`, and `scripts/demo_crewai.py`.

## 20. Decisions for Security, Infrastructure, Review, Governance, and Evaluation

**Status:** Implemented and verified

1. **Input Guardrails (`src/practo_agent/guardrails/`):** Mask fixed-format Indian mobile numbers (`[REDACTED_CONTACT_NUMBER]`) and reject phrase-based prompt-injection attempts before routing, Crew construction, memory storage, or logging (`scripts/demo_input_guardrails.py`, `scripts/demo_prompt_injection.py`).
2. **Session Memory and Context-Aware Caching (`src/practo_agent/memory/`, `src/practo_agent/cache/`):** Wrap the workflow with LangChain `RunnableWithMessageHistory` and `InMemoryChatMessageHistory` keyed by `session_id`, paired with a SHA-256 `ResponseCache` scoped by session ID, prior conversation context, and NFKC-normalized query (`scripts/demo_conversation_memory.py`, `scripts/demo_response_cache.py`).
3. **Runtime Token and Cost Budget (`src/practo_agent/config/runtime_budget.py`):** Enforce pre-routing request input limits (`8,192` tokens) and per-call cumulative token (`65,536`) and cost (`$0.10`) caps across CrewAI, groundedness validation, AutoGen review, and LLM-as-a-judge evaluation (`scripts/demo_runtime_budget.py`).
4. **FastAPI HTTP/WebSocket Transports and Privacy-Safe Observability (`src/practo_agent/api/`, `src/practo_agent/observability/`):** Expose `GET /health`, `POST /query`, and `/ws/{session_id}` backed by shared `ConversationMemory` and allowlisted JSONL trace logging (`logs/practo_agent.jsonl`) that excludes raw queries, contact numbers, session IDs, and appointment IDs (`scripts/demo_api.py`).
5. **Two-Agent AutoGen Response Review (`src/practo_agent/review/`):** Review answered drafts in a two-turn `RoundRobinGroupChat` (`Reviewer Agent` and `Final Editor Agent`) with post-revision groundedness re-verification (`scripts/demo_autogen_review.py`).
6. **Least-Autonomy Governance and Risk Classification (`src/practo_agent/governance/`):** Enforce default-deny tool permissions (`check_appointment_status` restricted exclusively to `Practo Appointment Lookup Specialist`) at both wiring time (`ToolPermissionError`) and runtime tool-call time (`before_tool_call` hook logging `tool_call_blocked`), and classify component/system risk under the Low/Medium/High scheme (`scripts/demo_governance.py`).
7. **Zero-Tolerance Safety, 15-Query Live LLM-as-a-Judge, and 20-Scenario Offline Acceptance Evaluation (`src/practo_agent/evaluation/`):** Verify all seven zero-tolerance safety objectives (`7/7` passed in `scripts/evaluate_safety.py`), evaluate all 15 live queries across Accuracy (`4.47/5`), Grounding (`4.47/5`), Completeness (`4.13/5`), and Safety (`4.93/5`) (`scripts/evaluate_response_quality.py`), and run the 20-scenario keyless offline acceptance suite (`20/20` passed in `scripts/run_acceptance_suite.py`).

## 21. Maintenance

Update this document when a material architecture decision is made, when an experiment changes a previous conclusion, or when an important trade-off becomes better understood. Record observed results separately from expectations and assumptions.
