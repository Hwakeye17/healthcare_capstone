# Retrieval Strategy Comparison Report

## 1. Objective

The objective of this experiment is to compare fixed-size-with-overlap chunking and sentence-based chunking for the Practo support agent's retrieval pipeline.

Both strategies use the same knowledge base, embedding model, similarity metric, evaluation queries, and retrieval configuration. This ensures that the chunking strategy is the primary independent variable.

The evaluation measures document-level precision and recall and includes inspection of retrieved content to verify whether additional retrieved documents are genuinely useful.

## 2. Experimental Configuration

| Parameter | Configuration |
|---|---|
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Vector database | ChromaDB |
| Similarity metric | Cosine distance |
| Retrieval top-k | 3 |
| Evaluation queries | 12 |
| Knowledge base documents | 12 |
| Fixed-size chunk size | 400 characters |
| Fixed-size overlap | 80 characters |
| Sentence chunk size | 3 sentences |
| Sentence overlap | 1 sentence |
| Fixed-size collection | practo_fixed_size |
| Sentence-based collection | practo_sentence |
| Fixed-size chunks generated | 34 |
| Sentence-based chunks generated | 36 |

Both collections were populated using the same embedding model. The evaluation script reused the existing collections without rebuilding them.

Lower cosine distance indicates greater similarity. However, cosine distance is not a calibrated probability or confidence score.

## 3. Evaluation Methodology

Each evaluation case contains a query and its expected relevant source document.

The evaluation operates at the document level rather than the individual chunk level.

Retrieved chunks are deduplicated using their source document IDs before calculating the metrics. Therefore, multiple chunks retrieved from the same document count as one retrieved document.

For each query:

- True Positive (TP): Number of retrieved documents that are expected relevant sources.
- False Positive (FP): Number of retrieved documents that are not expected relevant sources.
- False Negative (FN): Number of expected relevant documents that were not retrieved.

The metrics are calculated as follows:

**Precision**

Precision = TP / (TP + FP)

**Recall**

Recall = TP / (TP + FN)

When no documents are retrieved, precision is undefined and is represented as null rather than zero.

Macro precision and macro recall are calculated by taking the arithmetic mean of the corresponding per-query metrics.

The same 12 queries and expected-source labels are used for both strategies.

## 4. Per-Query Results

### 4.1 Fixed-Size Chunking

| Query ID | Expected source retrieved | Unique retrieved documents | TP | FP | FN | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|---:|
| RAG-001 | Yes | 3 | 1 | 2 | 0 | 0.3333 | 1.0000 |
| RAG-002 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-003 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-004 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-005 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-006 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-007 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-008 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-009 | Yes | 3 | 1 | 2 | 0 | 0.3333 | 1.0000 |
| RAG-010 | Yes | 3 | 1 | 2 | 0 | 0.3333 | 1.0000 |
| RAG-011 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-012 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |

**Macro precision calculation:**

(0.3333 + 0.5000 + 0.5000 + 0.5000 + 0.5000 + 1.0000 + 0.5000 + 1.0000 + 0.3333 + 0.3333 + 1.0000 + 1.0000) / 12

Macro precision = **0.6250**

**Macro recall calculation:**

(1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1) / 12

Macro recall = **1.0000**

### 4.2 Sentence-Based Chunking

| Query ID | Expected source retrieved | Unique retrieved documents | TP | FP | FN | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|---:|
| RAG-001 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-002 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-003 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-004 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-005 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-006 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-007 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-008 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |
| RAG-009 | Yes | 3 | 1 | 2 | 0 | 0.3333 | 1.0000 |
| RAG-010 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-011 | Yes | 2 | 1 | 1 | 0 | 0.5000 | 1.0000 |
| RAG-012 | Yes | 1 | 1 | 0 | 0 | 1.0000 | 1.0000 |

**Macro precision calculation:**

(0.5000 + 0.5000 + 0.5000 + 0.5000 + 0.5000 + 1.0000 + 1.0000 + 1.0000 + 0.3333 + 0.5000 + 0.5000 + 1.0000) / 12

Macro precision = **0.6528**

**Macro recall calculation:**

(1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1) / 12

Macro recall = **1.0000**

## 5. Aggregate Comparison

| Metric | Fixed-size | Sentence-based |
|---|---:|---:|
| Evaluation queries | 12 | 12 |
| Expected sources retrieved | 12/12 | 12/12 |
| Macro precision | 0.6250 | 0.6528 |
| Macro recall | 1.0000 | 1.0000 |
| Total chunks generated | 34 | 36 |

Sentence-based chunking improves macro precision by:

0.6528 - 0.6250 = **0.0278**

This corresponds to approximately **2.78 percentage points**.

Both strategies achieve identical macro recall.

## 6. Retrieved Content Inspection

All 12 queries were inspected for both strategies. The inspection included retrieved source IDs, chunk content, and cosine distances.

The expected source document was retrieved for every query by both strategies.

### 6.1 Repeated Retrieval of second_opinions

The `second_opinions` document appeared in the results for several unrelated queries.

The retrieved content included references to:

- Appointment requirements and availability.
- Consultation fees.
- Previous prescriptions and medical records.
- Booking processes.

These references create semantic overlap with queries about appointment booking, fees, insurance claims, prescription refills, and privacy.

However, topical overlap does not necessarily mean that a document directly answers a query.

The document was therefore not counted as relevant for those unrelated queries.

### 6.2 Other Additional Retrieved Documents

Several other additional documents were retrieved:

- `appointment_booking` appeared for RAG-002 because it discusses appointment references and alternative slots.
- `fee_structure` appeared for RAG-010 under sentence-based chunking, but it does not explain follow-up discount eligibility.
- `insurance_claims` appeared for RAG-009, but claim-document retention does not answer the broader question about patient information protection.
- `prescription_refills` appeared for RAG-011 under sentence-based chunking, but the retrieved content does not explain how to arrange a second opinion.

These results demonstrate that semantic similarity alone is insufficient to establish document relevance.

### 6.3 Chunk Coherence

The fixed-size chunk retrieved for RAG-001 begins in the middle of a sentence. This illustrates how fixed-size chunk boundaries can split contextual information.

Sentence-based chunking preserves sentence boundaries and generally provides more coherent context in the inspected examples.

However, sentence-based chunking can still retrieve semantically related but irrelevant documents.

### 6.4 Evaluation Label Decision

The expected-source labels were reviewed against the retrieved content and retained.

A document is considered relevant when it directly provides information useful for answering the evaluation query. Merely sharing terminology or discussing a related topic is insufficient.

The evaluation therefore retains its original direct-answer relevance definition rather than changing labels to improve retrieval scores.

## 7. Interpretation

Both strategies successfully retrieved the expected source document for all 12 queries.

Sentence-based chunking achieved slightly higher macro precision while maintaining identical recall.

The difference is modest, but the retrieved-content inspection provides additional qualitative support for sentence-based chunking:

- It maintains sentence boundaries.
- It provides more coherent retrieved context in the inspected examples.
- It produces fewer irrelevant document-level results for some queries.
- It achieves the same expected-source retrieval coverage as fixed-size chunking.

The results also reveal that both strategies can retrieve semantically related but irrelevant documents. This issue cannot be resolved solely by changing chunk boundaries.

## 8. Final Recommendation

**Recommended strategy: Sentence-based chunking**

Sentence-based chunking is selected as the preferred retrieval strategy for the current Practo support agent implementation.

The recommendation is based on:

1. Higher macro precision: 0.6528 compared with 0.6250.
2. Identical macro recall: 1.0000 for both strategies.
3. More coherent sentence-level context in the inspected results.
4. Slightly fewer irrelevant document-level retrievals in this experiment.

The recommendation is specific to the current knowledge base, embedding model, chunking configuration, and evaluation queries.

It should not be interpreted as proof that sentence-based chunking is universally superior.

## 9. Limitations and Future Improvements

The experiment has the following limitations:

- Only 12 evaluation queries were used.
- Each query currently has one expected relevant source document.
- The evaluation covers a small, project-authored synthetic knowledge base.
- Results depend on the selected embedding model and chunking parameters.
- Top-k was fixed at 3 and was not independently optimized.
- Document-level precision and recall do not measure the quality or completeness of generated answers.
- The experiment does not evaluate abstention behavior or out-of-scope queries.
- The results do not establish production-level retrieval reliability.

Future improvements could include:

1. Adding queries with multiple expected relevant documents.
2. Expanding the evaluation query set.
3. Evaluating additional top-k values.
4. Calibrating an abstention threshold using in-scope and out-of-scope queries.
5. Evaluating generated answers separately for accuracy, grounding, completeness, and safety.

## 10. Conclusion

The retrieval experiment demonstrates that both chunking strategies can retrieve the expected source documents for all 12 evaluation queries.

Sentence-based chunking achieves a modest improvement in macro precision and provides more coherent sentence-level context in the inspected examples.

Therefore, sentence-based chunking is selected for the next stage of the Practo support agent implementation.

The retrieval evaluation is a project-level experiment and does not establish clinical or production-grade reliability.