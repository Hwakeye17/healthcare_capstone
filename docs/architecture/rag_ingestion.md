# RAG Ingestion Pipeline — Design and Decisions

## 1. Purpose

This document describes how the Practo Support Agent converts its project-authored knowledge-base documents into searchable vector representations.

The ingestion pipeline prepares two independent vector collections corresponding to the two chunking strategies being evaluated:

- Fixed-size chunking.
- Sentence-based chunking.

The objective is to ensure both collections use the same source documents, embedding model, embedding configuration, and storage system so their retrieval performance can be compared fairly.

## 2. Ingestion Pipeline

The ingestion process consists of the following stages:

1. Load the knowledge-base documents.
2. Divide documents into chunks using the selected strategy.
3. Generate embeddings for each chunk.
4. Store chunk text, embeddings, and metadata in ChromaDB.
5. Verify the resulting collection.

The pipeline is executed independently for each chunking strategy.

## 3. Decision: Reuse the Same Embedding Model

**Status:** Implemented and used to build both persistent collections.

### Decision

Use `sentence-transformers/all-MiniLM-L6-v2` for both collections.

### Rationale

Using the same model prevents embedding-model differences from influencing the comparison between chunking strategies.

### Important distinction: Document and query embeddings

Document embeddings represent the knowledge-base chunks stored in the vector database.

Query embeddings represent user questions during retrieval.

Both must be generated using the same embedding model and compatible preprocessing and vector dimensions.

Using different embedding models for documents and queries would make their vector representations incompatible or semantically inconsistent.

## 4. Decision: Generate Embeddings During Ingestion

### Decision

Generate document embeddings when building the vector collections, rather than generating them every time a user asks a question.

### Rationale

Document content changes much less frequently than user queries. Precomputing document embeddings avoids repeating the same computation for every request.

At query time, only the user query needs to be embedded before searching the stored vectors.

### Trade-off

When the knowledge base, chunking configuration, or embedding model changes, the affected collection must be rebuilt.

## 5. Decision: Maintain Independent Collections

### Decision

Use two persistent ChromaDB collections:

- `practo_fixed_size`
- `practo_sentence`

### Rationale

Separate collections prevent chunks from different strategies from being mixed. Each experiment can be rebuilt, inspected, and evaluated independently.

### Trade-off

The two collections require separate ingestion operations and storage. This duplication is intentional because the project needs a controlled comparison.

## 6. Decision: Reuse One Embedding Model Instance During Ingestion

### Decision

Create one Sentence Transformers embedding model instance and reuse it while populating both collections.

### Rationale

Loading a model can consume substantial memory and time. Reusing one instance avoids unnecessary model initialization and ensures both collections use the same in-memory model configuration.

### Trade-off

The ingestion process retains the model in memory while both collections are built.

## 7. Decision: Use Persistent Local Storage

### Decision

Use ChromaDB persistent storage for the actual experiment.

### Rationale

Persistent storage allows collections to survive application restarts. The retrieval evaluation can run repeatedly without rebuilding all document embeddings every time.

### Distinction from unit tests

Unit tests use an in-memory ChromaDB client to provide isolation and avoid filesystem locking issues.

The actual ingestion experiment uses persistent storage because its results must be reusable.

## 8. Decision: Rebuild Collections Explicitly

### Decision

The ingestion operation resets and recreates the target collection before inserting its chunks.

### Rationale

This avoids accidental duplication when the ingestion script is run repeatedly and ensures that the stored collection corresponds to the current source documents and chunking configuration.

### Trade-off

Rebuilding requires regenerating the embeddings. It is appropriate for this small capstone knowledge base but would need a more sophisticated incremental-update strategy for a large production knowledge base.

## 9. Decision: Keep Test Embeddings Separate from Real Embeddings

### Decision

Use Sentence Transformers for actual ingestion and deterministic embeddings only for isolated software tests.

### Rationale

Deterministic test embeddings make unit tests repeatable but do not represent semantic similarity.

The actual retrieval experiment must use real semantic embeddings.

### Safety check

The ingestion script must not silently fall back to deterministic embeddings if the real model is unavailable. It should fail clearly instead.

## 10. Verification Requirements

After ingestion, verify:

- Both collections exist.
- Both collections contain chunks.
- The fixed-size collection contains only fixed-size chunks.
- The sentence-based collection contains only sentence-based chunks.
- Chunk metadata includes source identifiers and chunk strategy.
- The number of stored records matches the number of generated chunks.
- Both collections were built using the same embedding model.

Successful ingestion confirms that the vector database has been populated. It does not establish retrieval accuracy.

## 11. Rebuild Conditions

Rebuild the affected collection when any of the following changes:

- Knowledge-base document contents.
- Chunking algorithm.
- Chunk size or overlap.
- Sentence grouping or overlap.
- Embedding model.
- Embedding preprocessing or normalization.

Record the configuration used for each evaluation experiment.

## 12. Limitations

The current pipeline performs full collection rebuilds rather than incremental updates.

The knowledge base is small and project-authored. The pipeline is designed for reproducible experimentation and is not intended to claim production-scale ingestion performance.

## 13. Future Work

The retrieval evaluation will compare both collections using the same labeled query set and top-k configuration.

Results will be recorded separately, including retrieved source identifiers, distances, precision, recall, and per-query observations.

## 14. Initial Ingestion Results

**Status:** Successfully executed using the real Sentence Transformers model.

### Model

`sentence-transformers/all-MiniLM-L6-v2`

The model weights loaded successfully during ingestion.

### Collection Results

| Collection | Strategy | Stored chunks |
|---|---|---:|
| practo_fixed_size | Fixed-size with overlap | 33 |
| practo_sentence | Sentence-based with overlap | 24 |

### Observations

Both collections were created successfully in the configured persistent ChromaDB directory.

The difference in chunk counts reflects the different boundary and grouping behavior of the two chunking strategies.

The higher chunk count for sentence-based chunking does not establish better retrieval quality.

### Limitations

These results establish successful ingestion and storage only. They do not establish semantic retrieval accuracy, precision, recall, or superiority of either chunking strategy.

Those properties will be evaluated separately using the labeled retrieval evaluation dataset.