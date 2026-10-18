# Architecture Decision Records — Practo Support Agent

## 1. Purpose

This document records the important engineering decisions made while building the Practo Domain Support Agent capstone. It explains the reasoning behind the selected approaches, alternatives considered, known trade-offs, and evidence still required.

The project is an educational prototype for administrative healthcare support. It is not intended to diagnose conditions, recommend treatments, or replace healthcare professionals.

## 2. Decision Status Convention

- **Implemented:** The decision is reflected in the current code.
- **Pending evaluation:** The implementation exists, but its effectiveness has not yet been established through experiments.
- **Planned:** The decision concerns a future component that has not yet been implemented.

## 3. Decision: Use Synthetic Appointment Records

**Status:** Implemented

### Context

The appointment lookup capability requires structured records containing appointment identifiers, categories, statuses, consultation fees, creation age, and follow-up indicators. Using real patient records would introduce unnecessary privacy risks into an educational project.

### Decision

Generate a reproducible synthetic dataset using Python. The current generator produces 50 records and validates the required schema and distribution constraints.

### Alternatives considered

- Using real patient or appointment records.
- Creating records manually.
- Generating records programmatically with a fixed random seed.

### Rationale

Programmatic generation makes the dataset reproducible, easy to validate, and suitable for automated tests. Synthetic records avoid the need to introduce real patient information into the repository.

### Trade-offs

Synthetic data does not represent the full complexity or distribution of real healthcare operations. Passing tests on this dataset does not establish readiness for use with real appointments.

### Evidence

The dataset tests check the required fields, unique record identifiers, category and status coverage, integer creation-age values between 0 and 30, reproducibility, and a follow-up proportion between 10% and 30%.

## 4. Decision: Use a Project-Authored Local Knowledge Base

**Status:** Implemented

### Context

The support agent needs a controlled information source for administrative questions about bookings, cancellations, fees, insurance claims, prescription refills, laboratory turnaround, telemedicine, emergencies, privacy, follow-up discounts, second opinions, and home visits.

### Decision

Create 12 Markdown documents specifically for this project and use them as the local knowledge base.

### Alternatives considered

- Retrieving information from arbitrary websites at query time.
- Using a large, uncontrolled collection of external documents.
- Using a small, project-authored collection with explicit topic coverage.

### Rationale

A project-authored knowledge base gives us control over the information available to the retrieval system and makes it easier to trace generated answers to their sources. It also supports repeatable offline testing.

### Trade-offs

These documents describe sample policies for the capstone. They must not be represented as verified official Practo policies. The knowledge base is limited in scope, and its coverage must be evaluated against the required questions.

### Evidence

The knowledge-base validator checks the required document set and minimum sentence counts. Unit tests check document presence and validation behavior.

## 5. Decision: Implement Two Explicit Chunking Strategies

**Status:** Implemented; comparative effectiveness pending evaluation

### Context

Longer documents need to be divided into smaller pieces before they can be embedded and retrieved. Chunk boundaries can affect whether a retrieved passage contains enough information to answer a question.

### Decision

Implement two strategies:

1. Fixed-size chunking with overlap.
2. Sentence-based chunking with sentence overlap.

The current fixed-size defaults are 400 characters with an overlap of 80 characters. The current sentence-based defaults group up to three sentences with an overlap of one sentence.

### Alternatives considered

- Fixed-size chunking only.
- Sentence-based chunking only.
- Introducing a separate semantic chunking system.

### Rationale

Implementing both required strategies allows us to compare them under the same retrieval queries. A small custom Python implementation also makes the boundaries, overlap, and behavior explicit without adding another dependency solely for chunking.

### Trade-offs

Fixed-size chunks can split a sentence or concept across boundaries. Sentence-based chunks preserve sentence boundaries but can vary in character length and may separate information that belongs together. The current sentence splitter is a lightweight implementation, not a complete natural-language sentence parser.

### Evidence still required

Run both strategies against the same evaluation queries. Record retrieved documents, document-level precision and recall, per-query calculations, and aggregate results before recommending one strategy.

## 6. Decision: Use Sentence Transformers for Local Embeddings

**Status:** Implemented; real retrieval quality pending evaluation

### Context

The retrieval system needs vector representations of documents and user queries. The capstone should support local execution without requiring a paid embedding API for every request.

### Decision

Use the Sentence Transformers model `sentence-transformers/all-MiniLM-L6-v2`, configured for local model loading, to produce document and query embeddings.

### Alternatives considered

- Calling a hosted embedding API.
- Using deterministic test-only vectors.
- Loading a locally available Sentence Transformers model.

### Rationale

A local embedding model supports repeatable retrieval experiments and avoids per-request embedding charges to a hosted provider. It also fits the project's local-first design.

### Trade-offs

The model must be available in the local model cache. Initial model acquisition may require a separate download unless the model is already cached. Local execution still consumes memory and processing time. Model selection alone does not prove that retrieval quality is adequate.

### Evidence still required

Evaluate retrieval against the project's labeled queries. Do not infer semantic quality from successful model loading or unit tests alone.

## 7. Decision: Use ChromaDB with Separate Collections

**Status:** Implemented; retrieval quality pending evaluation

### Context

The two chunking strategies need to be evaluated independently. Their stored chunks and search results must not be mixed.

### Decision

Use ChromaDB with cosine-distance configuration and separate collections:

- `practo_fixed_size`
- `practo_sentence`

The vector-store implementation supports persistent storage, while tests can inject an in-memory client.

### Alternatives considered

- Storing vectors manually in application code.
- Using one collection for both strategies.
- Using separate collections in a local vector database.

### Rationale

Separate collections provide a clear boundary between the two experiments. ChromaDB handles vector storage and nearest-neighbor retrieval, allowing the project code to focus on ingestion, metadata, search, and evaluation.

Injectable clients allow tests to avoid persistent database files and their associated cleanup problems.

### Trade-offs

Separate collections require independent ingestion and evaluation. Persisted collections must be rebuilt when their source documents, chunking settings, or embedding model change. Cosine-distance results must be interpreted correctly; lower distance indicates greater similarity for the configured distance metric.

### Evidence still required

Verify that each collection contains the intended chunks and that searches return the expected source content. Compare both strategies on the same evaluation set.

## 8. Decision: Use Deterministic Test Embeddings for Unit Tests

**Status:** Implemented

### Context

Unit tests should be fast, repeatable, and independent of model downloads or external network calls.

### Decision

Provide a deterministic test embedding implementation for mock mode. Use it to test vector-store mechanics and validation behavior, not semantic relevance.

### Alternatives considered

- Downloading and loading the full embedding model in every unit test.
- Using deterministic vectors for isolated tests and real embeddings for retrieval experiments.

### Rationale

Deterministic embeddings reduce environmental dependencies and make tests repeatable. They allow tests to check storage, metadata, input validation, and retrieval plumbing without relying on external services.

### Trade-offs

Deterministic test embeddings are not a substitute for a semantic embedding model. Passing tests with them does not demonstrate that a natural-language query will retrieve the correct knowledge-base passage.

### Evidence

Unit tests cover embedding input validation and deterministic mock-mode construction. Real retrieval quality remains a separate evaluation task.

## 9. Decision: Test Components Independently Before Integrating Agents

**Status:** Implemented for the current foundation

### Context

The final system contains multiple components, including data generation, document loading, chunking, embedding, vector storage, retrieval, agents, memory, guardrails, and APIs. Debugging all components simultaneously would make failures harder to isolate.

### Decision

Build the foundation incrementally and add unit tests for each implemented component before integrating the full agent workflow.

### Rationale

Focused tests identify defects close to their source. Deterministic tests also make regression checks practical as the codebase grows.

### Trade-offs

Unit tests cannot establish end-to-end correctness. Integration tests, acceptance tests, retrieval evaluation, and safety checks are still required.

### Evidence

The current unit-test suite covers the synthetic dataset, knowledge-base validation, document loading, chunking, embeddings, and ChromaDB vector-store behavior.

## 10. Decision: Keep Reference Course Materials Out of the Public Repository

**Status:** Implemented through repository ignore rules

### Context

The course PDFs and combined lecture summary are local reference materials rather than project deliverables.

### Decision

Keep `docs/combined_summary.md` and `docs/Healthcare.pdf` excluded from version control.

### Rationale

The repository should contain the project's own implementation, documentation, tests, evaluation evidence, and other required deliverables—not copies of the private reference materials.

### Evidence

The repository's `.gitignore` contains exclusions for these reference files.

## 11. Decisions Still to Be Made

The following choices must be informed by implementation and evaluation evidence rather than assumed in advance:

- Which chunking strategy provides better document-level precision and recall.
- Which retrieval-distance threshold provides a suitable balance between answering and abstaining.
- How retrieval results should be passed into grounded response generation.
- How the agent workflow should enforce tool permissions and structured response contracts.
- How the final evaluation will measure accuracy, grounding, completeness, and safety.

These decisions will be documented as the corresponding components are implemented and evaluated.

## 12. Maintenance

Update this document when a material architecture decision is made, when an experiment changes a previous conclusion, or when an important trade-off becomes better understood. Record observed results separately from expectations and assumptions.