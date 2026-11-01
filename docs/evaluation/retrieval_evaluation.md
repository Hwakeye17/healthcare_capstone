# Retrieval Evaluation — Methodology and Design Decisions

## 1. Purpose

This document defines the experimental methodology for evaluating the retrieval component of the Practo Domain Support Agent.

The primary objective is to compare two document chunking strategies:

1. Fixed-size chunking with overlap.
2. Sentence-based chunking with overlap.

Both strategies will be evaluated using the same project-authored knowledge base, embedding model, evaluation queries, relevance labels, similarity metric, and retrieval configuration.

The experiment will determine which strategy retrieves relevant source documents more effectively for administrative healthcare questions.

This is a retrieval-quality experiment. It does not establish the correctness, safety, or clinical suitability of generated answers.

---

## 2. Experimental Design

### 2.1 Independent Variable

The independent variable is the chunking strategy.

| Strategy | Description |
|---|---|
| Fixed-size | Divides document text into chunks with a configured character limit and character overlap. |
| Sentence-based | Groups a configured number of sentences and overlaps adjacent chunks by a configured number of sentences. |

### 2.2 Controlled Variables

The following must remain identical between experiments:

- Original knowledge-base documents.
- Document contents and source identifiers.
- Embedding model and model configuration.
- Evaluation queries.
- Expected relevant source labels.
- Similarity metric.
- Number of retrieved results (top-k).
- Relevance-assessment methodology.
- Evaluation calculations.

### 2.3 Why Only Chunking Should Change

If the embedding model, query set, or retrieval configuration also changes, it becomes difficult to attribute a difference in retrieval performance to chunking.

Keeping all other variables constant makes the comparison more controlled.

### 2.4 Experimental Configurations

Initial configurations:

| Parameter | Fixed-size | Sentence-based |
|---|---:|---:|
| Chunk size | 400 characters | 3 sentences |
| Overlap | 80 characters | 1 sentence |
| Embedding model | all-MiniLM-L6-v2 | all-MiniLM-L6-v2 |
| Similarity metric | Cosine distance | Cosine distance |
| Initial top-k | 3 | 3 |

These are the current implementation defaults, not experimentally proven optimal settings.

If the configuration is changed, the final report must record the actual settings used.

---

## 3. Decision: Compare Two Chunking Strategies

**Status:** Implemented; comparative effectiveness pending evaluation.

### Context

Chunk boundaries influence the amount of context available to the retrieval system. A poorly selected boundary may separate related information or introduce unnecessary text.

### Decision

Evaluate fixed-size-with-overlap and sentence-based-with-overlap chunking.

### Why Fixed-Size Chunking?

Fixed-size chunking divides text according to a predictable character limit.

Advantages:

- Predictable chunk sizes.
- Straightforward implementation.
- Easy to configure.
- Overlap can preserve text near chunk boundaries.

Limitations:

- Can split sentences.
- Can separate a heading from its explanation.
- Can divide a concept between adjacent chunks.
- Character length does not necessarily represent semantic completeness.

### Why Sentence-Based Chunking?

Sentence-based chunking uses sentence boundaries to construct chunks.

Advantages:

- Preserves complete sentences.
- Makes individual chunks easier to interpret.
- Avoids arbitrary sentence splitting caused by character limits.
- Sentence overlap can preserve some context between chunks.

Limitations:

- Chunk sizes can vary significantly.
- A long sentence may produce a large chunk.
- A fixed number of sentences does not guarantee a fixed token count.
- Related information can still be separated across chunks.

### Why Not Introduce Semantic Chunking?

Semantic chunking would introduce another strategy and potentially additional complexity.

The current project requires a comparison of the two implemented strategies. Adding a third strategy would increase the evaluation scope without being necessary for that requirement.

### Final Decision

Keep the experiment limited to the two required strategies. Use measured results to determine whether either strategy is preferable.

Do not assume sentence-based chunking is better simply because it preserves sentence boundaries.

---

## 4. Decision: Use Document-Level Relevance Rather Than Chunk-Level Relevance

**Status:** Selected for the evaluation methodology.

### Context

A single source document may generate multiple chunks. A query may retrieve several chunks from the same document.

Counting every retrieved chunk as a separate relevant result can inflate performance measurements.

### Decision

Measure relevance at the source-document level.

Each chunk contains source metadata identifying the document from which it originated.

For evaluation:

1. Retrieve the top-k chunks.
2. Extract their source document identifiers.
3. Remove duplicate source identifiers.
4. Compare the unique retrieved source identifiers against the expected relevant sources.

### Example

Retrieved chunks:

```text
appointment_booking::0000
appointment_booking::0001
fee_structure::0000
```

Unique retrieved documents:

```text
appointment_booking
fee_structure
```

The appointment booking document counts once, not twice.

### Why Not Use Chunk-Level Precision and Recall?

Chunk-level relevance would require reliable labels identifying every relevant chunk for every query.

It would also make the comparison more sensitive to chunk counts and boundaries. A strategy generating more chunks could have a different numerical behavior even when both strategies retrieve the same useful source documents.

Document-level relevance provides a common comparison unit across both chunking strategies.

### Limitation

Document-level evaluation does not determine whether the retrieved chunk contains all the exact information needed to answer a question. It measures source-document retrieval, not answer completeness.

---

## 5. Decision: Use Manually Defined Expected Relevant Sources

**Status:** Selected for the evaluation methodology.

### Context

Precision and recall require a reference set of relevant documents.

The retrieval system cannot be allowed to determine its own expected answers, because doing so would make the evaluation circular.

### Decision

Create a labeled evaluation dataset before examining retrieval results.

Each query must contain:

- A unique query identifier.
- The natural-language query.
- Expected relevant source document identifiers.

The labels must be established by inspecting the actual knowledge-base content.

### Why Not Use Retrieval Results as Ground Truth?

The purpose of the experiment is to determine whether retrieval finds relevant documents. Using the retrieved documents to define relevance would invalidate the comparison.

### Labeling Rules

- A document should be labeled relevant only if its content genuinely supports answering the query.
- Multiple documents may be relevant to one query.
- A document should not be labeled relevant solely because its filename or topic appears similar to the query.
- Expected relevant source identifiers must match the document loader's source identifiers.
- The same labels must be used for both experiments.

### Limitation

Manual relevance labels can contain judgment errors. If a query is ambiguous or the knowledge base does not contain enough evidence, the expected-source labels must be reviewed before the experiment.

---

## 6. Decision: Use the Same Evaluation Queries for Both Strategies

**Status:** Selected for the experiment.

### Context

Different queries may vary significantly in difficulty. One strategy should not receive easier questions than the other.

### Decision

Run the exact same labeled queries against both collections.

### Why?

Using different query sets would introduce query difficulty as another variable.

Identical queries make the comparison fairer and allow per-query differences to be examined.

### Evaluation Coverage

The initial retrieval comparison must contain at least five in-scope queries.

The query set should cover different knowledge-base topics rather than repeatedly testing the same document.

The broader evaluation will later include all required knowledge-base topics and out-of-scope queries.

---

## 7. Decision: Use Real Sentence Transformers Embeddings for Retrieval Evaluation

**Status:** Implemented in the embedding interface; actual retrieval experiment pending.

### Context

The vector store needs document and query vectors that represent semantic similarity.

### Decision

Use `sentence-transformers/all-MiniLM-L6-v2` for the actual retrieval experiment.

### Why This Model?

- It supports local embedding generation.
- It avoids a paid embedding API for normal local inference.
- It is suitable for a lightweight educational prototype.
- It provides a consistent embedding model for both chunking experiments.

### Why Not Use Deterministic Test Embeddings?

The deterministic implementation exists to test software behavior without downloading a model or making network requests.

It does not provide genuine semantic representations of text.

Using it for retrieval-quality evaluation would produce results that do not represent the intended semantic retrieval system.

### Final Distinction

| Embedding implementation | Intended purpose |
|---|---|
| Sentence Transformers | Actual semantic retrieval and evaluation |
| Deterministic test embeddings | Unit testing, repeatability, and storage mechanics |

A passing unit test using deterministic embeddings must never be reported as evidence of semantic retrieval quality.

### Model Availability

The Sentence Transformers model must be available locally before offline execution can be expected.

Initial model acquisition may require a download. Once cached, the project should use local-only loading where configured.

---

## 8. Decision: Use Separate ChromaDB Collections

**Status:** Implemented.

### Decision

Store the two experiments independently:

- `practo_fixed_size`
- `practo_sentence`

### Why Separate Collections?

Separate collections prevent chunks produced by different strategies from being mixed.

They also make it easier to:

- Rebuild one experiment independently.
- Inspect stored metadata.
- Run identical queries against each strategy.
- Compare results without accidentally retrieving chunks from the other strategy.

### Why Not Use One Collection?

A shared collection would require additional filtering and stricter metadata handling to ensure that each experiment only retrieves its own chunks.

Separate collections provide a clearer experimental boundary.

### Trade-off

Both collections require independent ingestion and storage. Changes to source documents, chunking parameters, or the embedding model require rebuilding the affected collection.

---

## 9. Decision: Use Cosine Distance

**Status:** Implemented.

### Context

The vector store needs a similarity metric to rank candidate chunks.

### Decision

Configure ChromaDB to use cosine distance.

### Why?

Cosine distance compares the direction of embedding vectors and is a common choice for semantic embedding retrieval.

It is appropriate for the normalized embeddings produced by the selected implementation.

### Important Distinction

Cosine similarity and cosine distance are not interchangeable numerical values.

For normalized vectors:

Cosine distance = 1 - Cosine similarity

Therefore:

- Lower cosine distance means greater similarity.
- Higher cosine distance means lower similarity.

The retrieval implementation returns distances, not relevance probabilities.

### Why Not Treat Distance as Confidence?

A distance score does not directly indicate the probability that a document is relevant.

It must not be described as a confidence percentage without separate calibration and validation.

---

## 10. Decision: Start with top-k = 3

**Status:** Initial experimental setting.

### Context

The retrieval system needs to return a limited number of chunks for each query.

### Decision

Start with three retrieved chunks per query.

### Why?

A small, fixed top-k makes initial comparisons easier to inspect and keeps the retrieval context manageable.

It also allows us to compare both strategies using the same retrieval budget.

### Why Not Retrieve Every Chunk?

Retrieving all chunks would defeat the purpose of nearest-neighbor retrieval and would make precision less meaningful.

It would also introduce unnecessary context into later response generation.

### Trade-off

A small top-k can miss relevant documents ranked below the cutoff.

A larger top-k may improve recall but introduce irrelevant documents and reduce precision.

### Final Decision

Use top-k = 3 for the initial controlled comparison. Do not claim it is optimal. If later experiments change top-k, document that as a separate experiment.

---

## 11. Evaluation Metrics

### 11.1 True Positive

A true positive is a unique retrieved document that appears in the expected relevant source list.

### 11.2 False Positive

A false positive is a unique retrieved document that does not appear in the expected relevant source list.

### 11.3 False Negative

A false negative is an expected relevant document that was not retrieved.

### 11.4 Precision

Precision measures the proportion of retrieved unique documents that are relevant.

Precision = TP / (TP + FP)

A high precision means the retrieved results contain relatively few irrelevant documents.

### 11.5 Recall

Recall measures the proportion of expected relevant documents that were retrieved.

Recall = TP / (TP + FN)

A high recall means the retrieval system finds a greater proportion of the expected relevant sources.

### 11.6 Example

Expected relevant sources:

```text
appointment_booking
fee_structure
```

Retrieved unique sources:

```text
appointment_booking
cancellation_rescheduling
fee_structure
```

Therefore:

- TP = 2
- FP = 1
- FN = 0

Precision = 2 / 3 = 0.667

Recall = 2 / 2 = 1.000

### 11.7 Why Both Metrics Are Necessary

Precision and recall measure different properties.

A system can retrieve only one highly relevant document and achieve high precision while missing other relevant documents.

Another system can retrieve nearly every relevant document but also return many irrelevant documents, producing high recall but low precision.

Neither metric alone provides a complete picture.

---

## 12. Decision: Use Macro-Averaged Metrics

**Status:** Selected for reporting.

### Context

Queries may have different numbers of expected relevant documents.

A single aggregate calculation over all retrieved documents can give greater influence to queries with more relevant sources or more retrieved documents.

### Decision

Calculate precision and recall for each query independently, then calculate the arithmetic mean across queries.

Macro Precision = Sum of per-query precision / Number of queries

Macro Recall = Sum of per-query recall / Number of queries

### Why Macro Averaging?

Each query receives equal weight in the final average.

This is useful for evaluating the average query experience rather than allowing a small number of document-rich queries to dominate the result.

### Why Not Only Micro Averaging?

Micro averaging combines all true positives, false positives, and false negatives before calculating the metrics.

It is useful for understanding overall retrieval counts, but it can hide poor performance on individual queries.

### Reporting Decision

Report:

- Per-query precision.
- Per-query recall.
- Macro-average precision.
- Macro-average recall.
- Optional micro-average metrics if useful.

The per-query results must remain visible.

### Zero-Denominator Cases

If a query produces no retrieved documents, precision is undefined. If a query has no expected relevant documents, recall is undefined.

These cases must be reported explicitly and must not silently be converted into perfect scores.

---

## 13. Decision: Separate Retrieval Evaluation from Answer Evaluation

**Status:** Selected.

### Context

Retrieving the correct source document does not guarantee that the language model will generate a correct answer.

Similarly, a generated answer can appear plausible even when the retrieval system failed to find supporting evidence.

### Decision

Evaluate retrieval and generation as separate stages.

### Retrieval Evaluation

Measures:

- Relevant source retrieval.
- Precision.
- Recall.
- Retrieval ranking and distance observations.

### Response Evaluation

Will separately measure:

- Accuracy.
- Grounding.
- Completeness.
- Safety.

### Why Separate Them?

Separating the stages helps identify the actual cause of failures.

For example:

- Correct document not retrieved: retrieval failure.
- Correct document retrieved but incorrect answer generated: generation failure.
- Unsupported answer despite missing evidence: grounding or safety failure.

The final evaluation will assess the complete workflow as well.

---

## 14. Decision: Keep Retrieval Evaluation Separate from Abstention Calibration

**Status:** Planned next-stage experiment.

### Context

The agent must avoid answering questions when the available knowledge base does not provide sufficient support.

### Decision

First compare the retrieval strategies. Then calibrate the abstention threshold using a separate labeled query set containing in-scope and out-of-scope questions.

### Why Not Choose the Threshold During Chunking Comparison?

Chunking comparison asks which strategy retrieves relevant sources more effectively.

Abstention calibration asks when the system should decline to answer.

These are related but distinct objectives.

### Planned Calibration Evidence

The calibration experiment must include at least:

- Three in-scope queries.
- Two out-of-scope queries.

It must also demonstrate at least five in-scope queries receiving answers and at least one out-of-scope query receiving the required fallback.

The selected threshold must be justified using observed retrieval behavior, including false acceptance and false rejection cases.

A cosine distance must not be treated as a calibrated probability.

---

## 15. Experiment Execution Procedure

1. Validate the evaluation cases and expected source identifiers.
2. Load the same knowledge-base documents.
3. Build the fixed-size collection using real Sentence Transformers embeddings.
4. Build the sentence-based collection using the same embedding model.
5. Verify that each collection contains the intended chunks.
6. Execute every evaluation query against both collections.
7. Retrieve the same top-k number of chunks.
8. Extract and deduplicate source document identifiers.
9. Calculate TP, FP, FN, precision, and recall per query.
10. Calculate macro-average precision and recall.
11. Inspect individual failures and compare retrieved content.
12. Record the results and limitations.
13. Recommend a strategy only when supported by the evidence.

---

## 16. Result Interpretation and Limitations

The comparison should not automatically declare a winner.

Possible outcomes include:

- Fixed-size chunking provides better precision.
- Sentence-based chunking provides better recall.
- One strategy performs better across both metrics.
- The strategies perform similarly.
- Different strategies perform better for different query types.

If the results are close, report that they are inconclusive.

The evaluation dataset is project-authored and relatively small. The findings apply to this knowledge base and query set; they do not establish general retrieval superiority across all domains.

Document-level metrics also do not measure the completeness of information inside a retrieved chunk.

---

## 17. Result Storage

Evaluation cases:

`evaluation/cases/retrieval_cases.json`

Raw retrieval results:

`evaluation/results/retrieval_results.json`

Human-readable comparison:

`evaluation/results/retrieval_comparison.md`

The results should record the model identifier, chunking parameters, top-k, similarity metric, query identifier, retrieved chunks, source identifiers, distances, and calculated metrics.

Do not overwrite earlier experiment results when changing configurations. Preserve the configuration associated with each result.

---

## 18. Maintenance

Update this document whenever:

- An evaluation parameter changes.
- A new retrieval strategy is introduced.
- A new relevance-labeling rule is adopted.
- An experiment produces evidence that changes an earlier decision.
- A limitation or failure mode is discovered.

Record the actual experiment configuration and observed results separately from design expectations.

All recommendations must be traceable to documented evidence.

---

## 19. Evaluation Case Validation

The retrieval evaluation cases are stored in `evaluation/cases/retrieval_cases.json`.

A dedicated Python loader validates the evaluation dataset before any retrieval experiment is executed.

Validation includes:

- Minimum evaluation case count.
- Unique query identifiers.
- Non-empty query text.
- At least one expected relevant source per query.
- No duplicate expected source identifiers.
- Verification that every expected source corresponds to an existing Markdown knowledge-base document.
- Strict validation of the JSON field structure.

The loader converts validated records into immutable `EvaluationCase` dataclass instances.

The validator confirms structural correctness and source existence. It does not independently establish semantic relevance. Expected source labels remain subject to content review.

Unit tests cover valid loading and invalid evaluation cases.

---

## 20. Decision: Evaluate Existing Persistent Collections Without Rebuilding Them

**Status:** Planned for implementation.

### Context

The two ChromaDB collections have already been populated using real Sentence Transformers embeddings.

The evaluation engine must search these collections without changing their contents.

### Decision

Create a separate evaluation runner that opens the existing persistent collections and passes them to the common comparison engine.

### Rationale

Ingestion and evaluation serve different purposes:

- Ingestion creates and stores document embeddings.
- Evaluation queries the stored embeddings and measures retrieval quality.

Combining these operations would unnecessarily regenerate embeddings every time an experiment is executed.

### Important distinction: Rebuilding versus reopening

The ingestion function resets and rebuilds a collection. The evaluation runner must not call that function.

Instead, it should initialize ChromaDB against the existing persistence directory and retrieve the already-created collections.

### Decision: Fail on Missing or Empty Collections

The evaluation runner must verify that both collections exist and contain records before executing queries.

It must not silently create empty collections and report misleading retrieval results.

### Decision: Preserve Experiment Evidence

Save the complete query-level results, including:

- Evaluation query identifier.
- Query text.
- Expected relevant source identifiers.
- Retrieved unique source identifiers.
- Retrieved chunk identifiers.
- Retrieval distances.
- True positives, false positives, and false negatives.
- Per-query precision and recall.
- Aggregate macro precision and recall.

### Rationale

Preserving raw retrieval evidence allows individual failures to be inspected and metrics to be recalculated without repeating model inference.

### Decision: Keep Experiment Configuration with Results

Record the embedding model, collection names, similarity metric, and top-k setting alongside the results.

This makes the experiment reproducible and helps identify when results from different configurations are being compared incorrectly.

### Limitation

A successful evaluation run demonstrates retrieval behavior on the current knowledge base and labeled query set only. It does not establish general retrieval superiority or answer-generation correctness.

---

## 21. Initial Retrieval Experiment Results

**Status:** Experiment executed successfully; interpretation remains preliminary.

### Experimental Configuration

| Parameter | Value |
|---|---|
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Similarity metric | Cosine distance |
| Top-k | 3 |
| Evaluation queries | 12 |
| Fixed-size collection | practo_fixed_size |
| Sentence-based collection | practo_sentence |
| Fixed-size chunks | 34 |
| Sentence-based chunks | 36 |

### Aggregate Results

| Metric | Fixed-size | Sentence-based |
|---|---:|---:|
| Macro precision | 0.6250 | 0.6528 |
| Macro recall | 1.0000 | 1.0000 |

### Observations

Both strategies retrieved the expected relevant source document for all 12 queries.

Sentence-based chunking achieved a macro precision of 0.6528, compared with 0.6250 for fixed-size chunking.

The precision difference is 0.0278, equivalent to approximately 2.78 percentage points.

Both strategies achieved identical macro recall.

### Retrieved Chunk Inspection

**Inspection scope:** Five queries with repeated retrieval of `second_opinions` or low precision were inspected for both chunking strategies. The inspection included retrieved source IDs, chunk content, and cosine distances.

**Findings:**

| Query ID | Expected source | Additional retrieved source | Relevance assessment |
|---|---|---|---|
| RAG-001 | appointment_booking | second_opinions | Not directly relevant. Mentions appointment requirements but does not explain new appointment booking. |
| RAG-003 | fee_structure | second_opinions | Partially relevant. Mentions that consultation fees depend on the selected clinician and clinic, but does not provide the fee structure. |
| RAG-004 | insurance_claims | second_opinions | Not relevant to the insurance claim submission process. |
| RAG-005 | prescription_refills | second_opinions | Not directly relevant. Mentions bringing prescriptions to a consultation but does not explain the refill process. |
| RAG-009 | privacy_policy | insurance_claims, second_opinions | Neither additional source directly answers the question about collecting, storing, and protecting patient information. |

**Additional observations:**

1. The `second_opinions` document contains generic references to appointments, consultation fees, and prescriptions. These references create semantic overlap with several evaluation queries.
2. RAG-003 demonstrates partial topical relevance because the `second_opinions` document mentions factors affecting consultation fees. However, the dedicated `fee_structure` document provides the information required to answer the query.
3. For RAG-009, the `insurance_claims` document discusses retaining claim-related documents, but this does not establish how patient information is collected, stored, or protected.
4. The fixed-size chunk retrieved for RAG-001 begins in the middle of a sentence. This illustrates how fixed-size chunk boundaries can split contextual information.
5. Sentence-based chunking provides more coherent sentence boundaries in the inspected examples, although it does not eliminate semantically unrelated retrievals.

**Evaluation decision:**

The existing expected-source labels are retained. A retrieved document is considered relevant when its content directly provides information useful for answering the query, rather than merely containing related terminology. Partial topical overlap is recorded as an observation but is not automatically counted as a relevant source.

The retrieved-source inspection supports the preliminary precision results and highlights the importance of evaluating actual retrieved content alongside numerical metrics.

### Remaining Query Inspection

The remaining seven evaluation queries were inspected for both chunking strategies, completing the content-level inspection of all 12 queries.

**Findings:**

| Query ID | Expected source | Additional retrieved source | Relevance assessment |
|---|---|---|---|
| RAG-002 | cancellation_rescheduling | appointment_booking | Partially related. Discusses alternative appointment slots and references but does not explain cancellation or rescheduling procedures. |
| RAG-006 | lab_turnaround | None | All retrieved chunks belong to the expected document. |
| RAG-007 | telemedicine | second_opinions (fixed-size only) | Not directly relevant to attending a telemedicine consultation. |
| RAG-008 | emergency_visits | None | All retrieved chunks belong to the expected document. |
| RAG-010 | follow_up_discounts | second_opinions, telemedicine (fixed-size); fee_structure (sentence-based) | The additional documents do not directly explain follow-up discounts. The fee document provides general fee information but not discount eligibility. |
| RAG-011 | second_opinions | prescription_refills (sentence-based only) | Not directly relevant. Discusses consultation requirements for medication reviews rather than arranging a second opinion. |
| RAG-012 | home_visits | None | All retrieved chunks belong to the expected document. |

**Additional observations:**

1. RAG-006, RAG-008, and RAG-012 retrieve only chunks from their respective expected source documents under both strategies.
2. RAG-002 retrieves `appointment_booking` because both documents discuss appointment references and alternative appointment options. However, the cancellation and rescheduling document remains the direct source for answering the query.
3. RAG-010 demonstrates that a semantically related document is not necessarily sufficient to answer a query. General consultation fee information does not establish follow-up discount eligibility.
4. Sentence-based retrieval returns `prescription_refills` for RAG-011, although the retrieved content does not explain second-opinion arrangements.
5. Multiple retrieved chunks from the same source document are treated as one document during evaluation. This prevents repeated chunks from artificially increasing the number of relevant or irrelevant documents.

**Overall inspection conclusion:**

The expected source document was retrieved for all 12 queries by both strategies. Additional retrieved documents generally contained topical overlap rather than information directly required to answer the query.

The existing expected-source labels are therefore retained under the direct-answer relevance definition. No evaluation labels are changed merely to improve the reported metrics.

### Preliminary Interpretation

Sentence-based chunking demonstrated slightly better document-level precision in this experiment while maintaining the same recall.

However, the difference is relatively small and should not be treated as conclusive evidence of general superiority.

The current evaluation queries each have one expected relevant source document. Consequently, the 100% recall result demonstrates retrieval of that expected source for every query, rather than complete coverage of all potentially relevant documents.

### Limitations

- The evaluation contains only 12 queries.
- Each query currently has one expected relevant source.
- Results are specific to the current knowledge base, embedding model, chunking parameters, and top-k setting.
- Precision and recall are document-level metrics and do not assess answer completeness.
- The experiment does not evaluate abstention or generated-answer quality.

### Next Steps

[x] Inspect retrieved source content for selected low-precision queries.
[x] Investigate repeated retrieval of second_opinions.
[x] Verify the inspected expected-source labels against document content.
[ ] Inspect the remaining evaluation queries.
[ ] Complete the comparison report and select a preferred strategy.

The recommendation remains provisional until the retrieval results and evaluation labels have been inspected.