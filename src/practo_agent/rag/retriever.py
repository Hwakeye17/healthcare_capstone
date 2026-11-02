
"""Build and query separate ChromaDB collections for RAG strategies."""

from pathlib import Path

from practo_agent.rag.chunkers import (
    fixed_size_chunk,
    sentence_based_chunk,
)
from practo_agent.rag.document_loader import (
    load_knowledge_documents,
)
from practo_agent.rag.embeddings import EmbeddingModel
from practo_agent.rag.vectorstore import ChromaVectorStore


def chunk_documents(strategy: str, documents) -> list:
    """Chunk documents using one of the required strategies."""

    chunks = []

    for document in documents:
        if strategy == "fixed_size":
            chunks.extend(
                fixed_size_chunk(
                    document,
                    chunk_size=400,
                    overlap=80,
                )
            )
        elif strategy == "sentence":
            chunks.extend(
                sentence_based_chunk(
                    document,
                    sentences_per_chunk=3,
                    overlap_sentences=1,
                )
            )
        else:
            raise ValueError(
                "strategy must be 'fixed_size' or 'sentence'."
            )

    return chunks


def build_vector_store(
    strategy: str,
    embeddings: EmbeddingModel,
    *,
    kb_dir: Path | None = None,
    persist_directory: Path | None = None,
) -> ChromaVectorStore:
    """Build a fresh collection for the selected strategy."""

    documents = (
        load_knowledge_documents(kb_dir)
        if kb_dir is not None
        else load_knowledge_documents()
    )

    chunks = chunk_documents(strategy, documents)

    store = (
        ChromaVectorStore(strategy, embeddings, persist_directory)
        if persist_directory is not None
        else ChromaVectorStore(strategy, embeddings)
    )

    store.reset()
    store.add_chunks(chunks)

    return store

def retrieve(
    store: ChromaVectorStore,
    query: str,
    top_k: int | None = None,
    *,
    config=None,
) -> list[dict]:
    """Return ranked chunks using validated retrieval configuration."""

    from practo_agent.config import DEFAULT_RETRIEVAL_CONFIG

    selected_config = config or DEFAULT_RETRIEVAL_CONFIG

    if store.strategy != selected_config.strategy:
        raise ValueError(
            f"Retrieval configuration uses strategy "
            f"{selected_config.strategy!r}, but the supplied store uses "
            f"{store.strategy!r}."
        )

    selected_top_k = (
        selected_config.top_k if top_k is None else top_k
    )

    return store.search(query, top_k=selected_top_k)
