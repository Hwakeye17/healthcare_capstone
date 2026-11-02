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

## 11. Decision: Use a Consistent Python Import Convention with the `src` Layout

**Status:** Implemented

### Context

The project follows a `src`-based Python package structure:

```text
healthcare_capstone/
├── src/
│   └── practo_agent/
│       ├── __init__.py
│       ├── rag/
│       └── evaluation/
├── scripts/
└── tests/
```

During ingestion-script execution, an import error occurred because an internal module attempted to import another module using `src.practo_agent` as the package root.

The error was:

`ModuleNotFoundError: No module named 'src'`

### Decision

Use `practo_agent` as the Python package import root.

Internal imports must follow this convention:

```python
from practo_agent.rag.chunkers import fixed_size_chunk
from practo_agent.rag.document_loader import load_knowledge_base
```

Avoid imports such as:

```python
from src.practo_agent.rag.chunkers import fixed_size_chunk
```

### Rationale

The `src` directory is the package-discovery location, not part of the actual Python package name.

Adding `src` to Python's module search path allows Python to locate the `practo_agent` package directly.

This convention provides consistent imports across application modules, scripts, and tests.

### Script Execution

Scripts executed directly from the project root must ensure that the `src` directory is available on Python's module search path.

The current ingestion script explicitly adds the project's `src` directory to `sys.path`.

For unit-test execution, the development environment currently uses:

```powershell
$env:PYTHONPATH = "src"
```

This setting applies to the current PowerShell session.

### Alternatives Considered

**1. Import through `src.practo_agent`**

Rejected because `src` is not intended to be a Python package root in this project structure.

**2. Move the application package outside `src`**

Rejected because it would unnecessarily change the established project structure.

**3. Configure the package for editable installation**

Recognized as a more reusable long-term development setup. This can be introduced later through project packaging configuration if needed.

### Trade-offs

The current approach requires the Python path to be configured when running tests or scripts in certain execution contexts.

A future editable installation could make this configuration more consistent across development environments.

### Evidence

The import issue was corrected by changing the internal import from `src.practo_agent` to `practo_agent`.

The ingestion script subsequently loaded the Sentence Transformers model and successfully populated both ChromaDB collections.

The full unit-test suite was rerun after the correction, with all 54 tests passing.

## 12. Decision: Centralize RAG Retrieval Configuration

**Status:** Implemented

### Context

The retrieval pipeline previously used default values directly in its functions. For example, the retrieval function used a default top-k value of 3, while the vector-store implementation independently validated the same parameter.

As the project grows, retrieval settings need to be managed consistently and explicitly.

### Decision

Introduce a centralized, immutable `RetrievalConfig` dataclass in `src/practo_agent/config/retrieval.py`.

The default configuration uses:

- Retrieval strategy: `sentence`
- ChromaDB collection: `practo_sentence`
- Top-k: `3`
- Similarity metric: `cosine`

The collection name is derived from the existing `COLLECTION_NAMES` mapping rather than duplicated.

The configuration validates the selected strategy, positive integer top-k value, and supported similarity metric.

The retrieval wrapper uses this configuration by default and verifies that the supplied vector store matches the configured strategy.

An explicit top-k override remains available for backward compatibility and controlled experiments.

### Alternatives Considered

- Keeping retrieval settings as function-level defaults.
- Defining configuration as module-level constants.
- Using environment variables for every retrieval parameter.
- Introducing a centralized immutable configuration object.

### Rationale

A dataclass provides a typed, explicit, and testable configuration contract. Immutability prevents accidental changes during execution.

The selected sentence-based strategy follows the comparative retrieval experiment completed during Day 2.

### Trade-offs

- The configuration currently supports only cosine distance because that is the metric used by the existing ChromaDB collections.
- The default top-k value remains 3 based on the previous evaluation setup; it has not been independently optimized.
- Explicit per-call top-k overrides remain possible, so callers must use them deliberately.
- The configuration selects a strategy but does not determine whether retrieved evidence is relevant enough to answer a query.

### Evidence

Unit tests validate default values, collection selection, custom top-k values, invalid configurations, and immutability.

Retriever tests verify that configured values are passed to the vector store and mismatched strategies are rejected.

The abstention threshold is intentionally deferred to a separate calibration experiment using in-scope and out-of-scope queries.

## 13. Decision: Use an Empirically Calibrated RAG Abstention Threshold

**Status:** Initial threshold selected; further validation required.

### Context

The retrieval pipeline needs a mechanism to determine whether retrieved
knowledge-base evidence is sufficiently similar to a user query to attempt
an answer.

The system uses cosine distance, where a lower distance indicates greater
embedding similarity.

Selecting an arbitrary threshold could cause two types of errors:

- False acceptance: answering an unsupported or out-of-scope query.
- False rejection: abstaining when the knowledge base contains relevant
  information.

### Decision

Use an empirically calibrated cosine-distance threshold of **0.331998**
with the existing sentence-based retrieval configuration.

A query is accepted for answer generation when its best retrieved cosine
distance is less than or equal to this threshold.

The threshold was selected using a safety-first rule:

1. Require zero false acceptances on the calibration dataset.
2. Maximize recall over in-scope queries.
3. Resolve ties by selecting the lower threshold.

The threshold is configurable and must not be treated as a universal
similarity boundary.

### Alternatives Considered

- Selecting an arbitrary threshold based on intuition.
- Always answering using the top retrieved chunks.
- Always abstaining when retrieval confidence is uncertain.
- Evaluating candidate thresholds against labeled in-scope and
  out-of-scope queries.

### Rationale

The initial calibration experiment evaluated five queries: three in-scope
administrative questions and two out-of-scope questions.

At a threshold of 0.331998, all three in-scope queries were accepted and
both out-of-scope queries were rejected.

This produced:

- True positives: 3
- False positives: 0
- True negatives: 2
- False negatives: 0
- Precision: 1.0000
- Recall: 1.0000
- False acceptance rate: 0.0000

Increasing the threshold to 0.761802 caused the medical diagnosis query
to be accepted, demonstrating the risk of using a more permissive threshold.

The selected threshold therefore provides the best observed result under
the defined selection rule.

### Trade-offs and Limitations

- The calibration dataset contains only five queries and is not
  statistically representative.
- Only two out-of-scope examples were evaluated.
- Cosine distance measures semantic similarity rather than factual support.
- A query may retrieve a semantically similar passage that does not
  contain sufficient information to answer it.
- The threshold depends on the current embedding model, knowledge base,
  chunking strategy, and retrieval configuration.

The threshold must be validated against a larger and more diverse query
dataset before making stronger reliability claims.

### Evidence

The calibration implementation is located in
`src/practo_agent/evaluation/abstention.py`.

Calibration cases are maintained in
`evaluation/cases/abstention_cases.json`.

The experiment is executed using
`scripts/calibrate_abstention.py`, with its detailed output saved to
`evaluation/results/abstention_calibration.json`.

The experiment produced zero false acceptances and zero false rejections
across the five initial calibration queries.

Unit tests validate calibration-case loading, retrieval-distance
collection, threshold evaluation, invalid inputs, and threshold selection.

## 14. Decision: Use Pydantic for Structured Agent Responses

**Status:** Implemented

### Context

The support agent needs a consistent response format across its retrieval,
generation, and agent orchestration components.

Unstructured text responses make it difficult to distinguish successful
answers from abstentions and to verify supporting knowledge-base sources.

### Decision

Use Pydantic models to define a structured response contract.

The initial contract includes:

- `GroundedResponse`: the overall response.
- `ResponseStatus`: answered or abstained.
- `SourceReference`: the knowledge-base source supporting an answer.

Answered responses must include supporting sources. Abstained responses
must provide an explanation and must not claim supporting sources.

Unexpected fields are rejected to keep the response contract explicit.

### Alternatives Considered

- Returning unstructured strings.
- Returning manually constructed dictionaries.
- Using Pydantic models for validated response contracts.

### Rationale

Pydantic provides runtime validation and a reusable typed contract.
Keeping the schema independent of the agent framework allows it to be
reused by CrewAI, API endpoints, and other application components.

### Trade-offs

The response schema enforces structural consistency but cannot independently
prove that an answer is factually supported by its cited sources.

Groundedness validation must be implemented separately.

### Evidence

Unit tests validate successful responses, abstentions, source requirements,
invalid combinations, and unexpected fields.

## 15. Decision: Separate Retrieval Evidence Validation from Generation

**Status:** Implemented

### Context

The retrieval pipeline needs to determine whether retrieved knowledge-base
content is sufficiently similar to a query before allowing answer generation.

The abstention threshold was empirically calibrated in a separate evaluation
experiment. Runtime evidence validation must apply that threshold without
depending on evaluation labels or calibration datasets.


## Decision 16: Separate Grounded Answer Generation

**Status:** Implemented

### Context

The RAG pipeline needs to convert retrieved and validated knowledge-base evidence into structured administrative support responses. Retrieval, evidence validation, and answer generation should remain separate responsibilities.

### Decision

Implement a provider-independent answer generation interface with two implementations:

1. **ChatGroq:** Uses LangChain's ChatGroq integration for real LLM-based answer generation.
2. **Mock Answer Generator:** Provides deterministic responses for offline testing without requiring API keys or network access.

The generator accepts a user query and an `EvidenceAssessment`. It generates an answer only when the evidence assessment is accepted. Source references are constructed programmatically from retrieved evidence rather than generated by the LLM.

### Alternatives Considered

- Directly integrating an LLM into the retrieval implementation.
- Using only a hosted LLM provider.
- Using only deterministic mock responses.

### Rationale

Separating retrieval from generation improves modularity and makes it possible to change the LLM provider without modifying the retrieval pipeline.

The mock implementation supports repeatable offline testing and ensures that acceptance tests can run without external API dependencies.

### Trade-offs

- A provider-independent interface introduces an additional abstraction.
- Hosted LLM generation requires API credentials and network access.
- Validating a response using the Pydantic schema does not guarantee factual correctness or complete grounding.
- Additional groundedness validation and evaluation are required to identify unsupported generated statements.

### Evidence

- Six generator unit tests passed.
- The complete test suite passed with 126 tests.
- Mock generator selection was verified with `MOCK_LLM=true`.
- Source references are constructed from retrieved evidence.


### Decision

Introduce a deterministic evidence-validation component in
`src/practo_agent/rag/evidence.py`.

The component:

- Retrieves chunks using the centralized retrieval configuration.
- Evaluates the minimum cosine distance against the configured abstention
  threshold.
- Preserves retrieved text and source metadata.
- Rejects empty or unusable retrieval results.
- Returns a structured Pydantic evidence assessment.

The initial threshold is maintained in
`src/practo_agent/config/grounding.py`.

Evidence validation and response generation remain separate responsibilities.

### Alternatives Considered

- Allowing the LLM to decide whether retrieved evidence is sufficient.
- Combining retrieval, evidence validation, and generation into one function.
- Using a deterministic evidence-validation component before generation.

### Rationale

A deterministic threshold check makes the initial answer-versus-abstain
decision reproducible and testable.

Separating validation from generation prevents the LLM from overriding the
retrieval acceptance decision.

### Trade-offs and Limitations

Cosine distance measures embedding similarity, not factual support.
Passing the threshold does not guarantee that retrieved content answers
the complete question.

A separate groundedness check is still required after generation.

The threshold is provisional because it was calibrated using only five
queries.

### Evidence

Unit tests cover accepted evidence, rejected evidence, empty retrieval,
threshold boundaries, retrieval configuration, and invalid source metadata.

## 17. Decision: Validate Generated Claims Against Retrieved Evidence

**Status:** Implemented

### Context

Retrieving relevant documents does not guarantee that every claim in a generated answer is supported by the retrieved evidence. A generated answer may contain unsupported information even when retrieval itself is successful.

### Decision

Introduce a separate groundedness-validation stage after answer generation.

The validator evaluates individual claims against the retrieved evidence. The system returns the generated answer only when all assessed claims are supported. Unsupported claims, validation errors, or invalid assessment results cause the system to return a deterministic abstention response.

Two implementations are provided:

1. A deterministic mock validator based on exact normalized sentence matching.
2. A Groq-based LLM validator using structured claim-level assessments.

### Alternatives Considered

- Trusting the answer generator without additional validation.
- Checking only whether relevant documents were retrieved.
- Using exact text matching as the only validation mechanism.
- Using an LLM-based verifier for all execution modes.

### Rationale

Retrieval relevance and factual support are different concerns. A separate validation stage provides an additional check before generated content is returned.

The mock implementation supports deterministic offline testing, while the Groq implementation supports semantic claim assessment.

### Trade-offs

Exact sentence matching is deterministic but cannot recognize semantic paraphrases. The LLM-based validator can assess semantic support but may produce incorrect judgments.

Groundedness validation adds processing overhead and does not guarantee factual correctness. The system therefore fails closed when validation cannot be completed.

### Evidence

- Seven groundedness schema tests.
- Eight groundedness validator tests.
- Six generated-response validation tests.
- Complete project test suite: 147 passed.


## 18. Decision: Implement a Deterministic Appointment Lookup Tool

**Status:** Implemented

### Context

The Practo Support Agent needs to handle appointment-related queries using structured appointment records.

Appointment information should be retrieved deterministically rather than generated or inferred by an LLM. The tool must support appointment status lookup and provide an administrative prioritization signal based on the record's follow-up requirement and age.

The project uses a synthetic dataset containing 50 appointment records.

### Decision

Implement a read-only Python function:

`check_appointment_status(record_id: str) -> dict`

The function retrieves appointment details from `data/generated/appointments.json` and returns the appointment status, consultation fee, and administrative prioritization score.

The score is calculated using:

\[
E = 0.6F + 0.4\left(\frac{D}{30}\right)
\]

Where:

- `F` is 1 when follow-up is required and 0 otherwise.
- `D` is the number of days since record creation.
- 30 is the maximum record age in the generated dataset.

### Alternatives Considered

- Allowing the LLM to answer appointment queries directly.
- Using only the follow-up flag.
- Using only record age.

### Rationale

A deterministic lookup function provides predictable and testable results for structured appointment queries and avoids relying on LLM-generated appointment details.

The follow-up flag receives 60% weight because it explicitly identifies records requiring follow-up consideration. Record age contributes the remaining 40%.

The dataset contains 10 follow-up records out of 50 (20%). Follow-up flags occur across multiple appointment statuses, so the score must always be interpreted alongside the actual appointment status.

The score is an administrative prioritization heuristic, not a clinically validated urgency or risk measure. The selected weights are design assumptions rather than statistically optimized values.

### Trade-offs

The deterministic implementation provides predictable results but depends on the locally generated dataset.

The current implementation loads the JSON dataset during each lookup. This is acceptable for the small synthetic dataset but may need optimization if the dataset grows.

The prioritization score is specific to the project's synthetic data assumptions and should not be treated as a production clinical metric.

### Evidence

- Implementation: `src/practo_agent/tools/appointment_lookup.py`
- Unit tests: `tests/unit/test_appointment_lookup.py`
- Appointment lookup unit tests: 18 passed.
- Complete project test suite: 165 passed, with 31 subtests passed.


## 19. Decision: Use Three Specialist Agents with Sequential CrewAI Orchestration

**Status:** Implemented; execution behavior pending demonstration and evaluation

### Context

The Practo support system needs to combine knowledge-base retrieval, appointment lookup, and final response composition. Combining all responsibilities into one agent would make tool permissions, responsibility boundaries, and intermediate outputs harder to inspect.

### Decision

Use three specialist agents:

1. Retrieval Agent — administrative knowledge-base retrieval.
2. Lookup Agent — deterministic appointment lookup.
3. Response Composer — final structured response generation.

Coordinate them using CrewAI's `Process.sequential`.

Each agent receives a dedicated Pydantic output contract. The Response Composer receives both specialist task outputs through explicit task context dependencies.

### Alternatives Considered

- A single agent with access to all tools.
- A hierarchical CrewAI process with a manager agent.
- A three-agent sequential workflow with explicit specialist responsibilities.

### Rationale

The sequential workflow provides clear task dependencies and inspectable intermediate results. Separating responsibilities makes tool permissions easier to enforce and test.

A hierarchical process would introduce additional manager behavior that is not currently necessary for this fixed three-stage workflow.

### Tool Permissions and Safety

- Retrieval Agent receives only the RAG search tool.
- Lookup Agent receives only the appointment lookup tool.
- Response Composer receives no tools.
- All agents have `allow_delegation=False`.
- Specialist outputs and final responses use Pydantic schemas.
- The workflow is restricted to administrative support.

### Memory Decision

CrewAI memory is disabled. Session memory will be implemented separately through LangChain so that its behavior, session isolation, and lifecycle can be tested explicitly.

### Testing Evidence

The agent, task, and crew configurations are covered by unit tests. The complete test suite reports 219 passing tests.

A test-only CrewAI `BaseLLM` subclass is used to verify that construction does not invoke an external LLM.

### Trade-offs and Limitations

Sequential execution still runs all three tasks. An irrelevant specialist must return `NOT_NEEDED` rather than invoke its tool.

Pydantic validation checks output structure but does not guarantee semantic correctness. Actual tool selection, intermediate results, and final answer grounding must be verified through execution traces.

### Evidence Still Required

- Demonstrate a knowledge-base query invoking the RAG tool.
- Demonstrate an appointment query invoking the appointment lookup tool.
- Verify that irrelevant tools are not called.
- Inspect all three task outputs and the final structured response.
- Test unsupported and not-found scenarios.

## 20. Decisions Still to Be Made

The following choices must be informed by implementation and evaluation
evidence rather than assumed in advance:

- How retrieval results should be passed into grounded response generation.
- How the agent workflow should enforce tool permissions and structured response contracts.
- How the final evaluation will measure accuracy, grounding, completeness, and safety.

These decisions will be documented as the corresponding components are implemented and evaluated.

## 21. Maintenance

Update this document when a material architecture decision is made, when an experiment changes a previous conclusion, or when an important trade-off becomes better understood. Record observed results separately from expectations and assumptions.