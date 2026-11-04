# System Architecture — Practo Support Agent

## 1. Overview

The Practo Domain Support Agent is an educational prototype intended to answer administrative healthcare questions using a controlled knowledge base and retrieve appointment information from a synthetic dataset.

The project is being built incrementally. The current implementation includes
the retrieval foundation and deterministic agent workflow. Additional
components remain planned work.

The system must not diagnose medical conditions or recommend treatments. Emergency-related questions must follow the project's emergency guidance rather than treating the agent as a substitute for emergency services.

## 2. Current Architecture

```text
User Query
    |
    v
Deterministic Router
    |
    +--------------------------+
    |                          |
    v                          v
Retrieval Agent            Lookup Agent
    |                          |
    v                          v
Sentence-based RAG          Appointment Dataset
ChromaDB Collection          Deterministic Lookup
    |                          |
    +------------+-------------+
                 |
                 v
        Response Composer
                 |
                 v
     Pydantic-validated response

Knowledge-base ingestion and retrieval foundation:
Project-authored Markdown -> Document Loader -> Chunking Strategies
    -> Sentence Transformers Embeddings -> ChromaDB Collections
       (practo_fixed_size and practo_sentence)
    -> Similarity Search -> Evaluation
```

The two collections support a controlled comparison of the chunking strategies. They are separate experiments, not two sources that should be mixed indiscriminately.

## 3. Component Responsibilities

### 3.1 Knowledge Base

**Location:** `data/knowledge_base/`

Contains 12 project-authored Markdown documents covering the required administrative topics. The documents use sample policies written for this capstone and are not verified statements of official Practo policy.

### 3.2 Document Loader

**Location:** `src/practo_agent/rag/document_loader.py`

Loads Markdown documents in deterministic order and associates each document with metadata such as source identifier, title, topic, and relative source path.

This metadata supports source tracing during retrieval and evaluation.

### 3.3 Chunking

**Location:** `src/practo_agent/rag/chunkers.py`

Provides two strategies:

- Fixed-size chunks with configurable character overlap.
- Sentence-based chunks with configurable sentence grouping and overlap.

Each chunk retains its source metadata and a chunk identifier. Fixed-size chunks record character offsets. Sentence-based chunks record sentence-index boundaries; those indices should not be interpreted as character offsets.

### 3.4 Embeddings

**Location:** `src/practo_agent/rag/embeddings.py`

Defines the embedding interface and provides:

- A Sentence Transformers implementation for local semantic embeddings.
- A deterministic test implementation for repeatable unit tests.

The deterministic implementation is intended for software testing only. It must not be used as evidence that semantic retrieval is effective.

### 3.5 Vector Store

**Location:** `src/practo_agent/rag/vectorstore.py`

Wraps ChromaDB operations, including collection selection, reset, chunk insertion, metadata storage, and similarity search.

The default collection names are `practo_fixed_size` and `practo_sentence`. The store supports client injection so tests can use an in-memory ChromaDB client.

### 3.6 Retrieval Pipeline

**Location:** `src/practo_agent/rag/retriever.py`

Connects document loading, chunk generation, vector-store construction, and retrieval into reusable functions. It provides a common ingestion path for both chunking strategies.

### 3.7 CrewAI Workflow

**Locations:** `src/practo_agent/agents/`, `src/practo_agent/tools/`,
`src/practo_agent/schemas/`

`run_practo_query` routes each query deterministically and creates a
sequential CrewAI workflow containing only the required specialist tasks.
The Retrieval Agent and Lookup Agent have separate tool permissions
enforced at both wiring time and tool-invocation time (see
[`docs/architecture/governance.md`](governance.md)). The Response Composer
has no tools and combines only validated specialist outputs. The final
`AgentResponse` is validated with Pydantic.

With `MOCK_LLM=true`, the workflow uses a deterministic local CrewAI `BaseLLM`
adapter. This acceptance path does not require a Groq API key, disables
OpenTelemetry, and uses the locally available embedding model and persisted
ChromaDB collection for real retrieval.

## 4. Data Flow

### Knowledge Retrieval

1. Load the project-authored Markdown documents.
2. Split the documents using the selected chunking strategy.
3. Generate embeddings for the resulting chunks.
4. Store the vectors, chunk text, and source metadata in the corresponding ChromaDB collection.
5. Embed a user query with the same embedding model.
6. Retrieve the nearest matching chunks from the selected collection.
7. Assess retrieved evidence and cite source metadata in the specialist
   output. Retrieval quality evaluation against labeled query expectations
   remains a separate evaluation task.

The local retrieval tool and response workflow are implemented. The current
evaluation set still needs to be reconciled with the brief's required query
count and full comparison criteria.

### Appointment Lookup

The project also contains a synthetic appointment dataset at `data/generated/appointments.json`, generated by `dataset.py`.

The lookup tool retrieves records deterministically by identifier and
returns the specialty, status, consultation fee, record age, follow-up flag,
administrative score, threshold decision, and explanation. The score is
`0.6 * follow_up_required + 0.4 * (days_since_created / 30)` with an inclusive
threshold of `0.6`. These are project heuristics for administrative
prioritization, not clinical or official Practo policy.

Appointment records are structured data and should be accessed through a deterministic lookup tool rather than inferred from the knowledge-base documents.

## 5. Current Data and Metadata Boundaries

The knowledge-base pipeline handles explanatory text and source metadata. The appointment dataset contains structured synthetic records.

These are distinct data paths:

- Knowledge-base documents support grounded answers to administrative policy questions.
- Appointment records support record-specific status and fee lookups.

Retrieval results should retain their source information so answers and evaluation results can be traced to the relevant documents.

## 6. Current Integration

The current implementation includes LangChain session memory, input and
output guardrails, a FastAPI HTTP/WebSocket interface, runtime token/cost
budgets, session-aware response caching, and privacy-safe JSONL request
observability, the two-agent AutoGen response-review stage, enforced
application-layer governance and risk classification, the zero-tolerance
safety evaluation suite, and the LLM-as-a-judge response-quality evaluation. The API details and process-local
session limitations are documented in
[`docs/architecture/api.md`](api.md).

The response-quality case set and evaluator are implemented, but live scoring
has not generated valid scores or a report: Groq returned malformed judge
output, and a later attempt encountered the account's token limit. End-to-end acceptance, final
reports, and submission review remain pending. Do not mark the project ready
for submission until these items are completed and verified.

## 7. Quality and Safety Principles

The implementation should follow these principles:

1. **Grounded responses:** Policy answers should be based on retrieved knowledge-base content.
2. **Explicit abstention:** Insufficient evidence should lead to a safe fallback rather than invented policy.
3. **Deterministic structured lookup:** Appointment facts should come from the synthetic dataset.
4. **Least privilege:** Only the designated lookup agent should receive access to the appointment lookup tool.
5. **Typed contracts:** Structured inter-component outputs should be validated.
6. **Privacy-aware observability:** Request logging must not retain unmasked fixed-format contact numbers.
7. **Testability:** Core behavior should be independently testable without paid APIs or network access in mock mode.
8. **Evidence-based evaluation:** Retrieval and response quality must be measured rather than inferred from successful execution.

## 8. Current Verification Status

The project has unit and integration tests for dataset generation,
knowledge-base validation, retrieval, routing, specialist tools, structured
response validation, runtime budgets, HTTP validation, WebSocket session
context, the offline CrewAI workflow, and the two-agent AutoGen review.

An earlier full test run contained 351 passing tests and 31 passing subtests;
this is historical and has not been rerun after all subsequent changes. The
latest focused regression run passed 56 tests. The AutoGen demonstration
verifies an approved response remains
unchanged and an unsupported draft is corrected in exactly two agent turns.
The API demonstration exercises a real local retrieval/appointment workflow
through HTTP and a context-dependent WebSocket follow-up. The offline CrewAI
integration test rejects external network connections. Dependency deprecation
warnings remain. These results are evidence of tested behavior, not proof of
general semantic retrieval quality.

The remaining assignment work is tracked in
[`docs/handoff_summary.md`](../handoff_summary.md), including
successful live scoring of all required 15 response
queries, end-to-end offline acceptance, final evidence/reports, and submission
cleanup.