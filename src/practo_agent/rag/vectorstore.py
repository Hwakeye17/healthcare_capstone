
"""Persistent ChromaDB collections for the two required RAG strategies."""

from pathlib import Path
import re

import chromadb

from src.practo_agent.rag.chunkers import TextChunk
from src.practo_agent.rag.embeddings import EmbeddingModel


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_DIR = PROJECT_ROOT / "data" / "vectorstores"

COLLECTION_NAMES = {
    "fixed_size": "practo_fixed_size",
    "sentence": "practo_sentence",
}


def _sanitize_metadata(chunk: TextChunk) -> dict:
    return {
        "source_id": chunk.source_id,
        "source_path": chunk.source_path,
        "title": chunk.title,
        "topic": chunk.topic,
        "strategy": chunk.strategy,
        "chunk_index": chunk.chunk_index,
        "start_char": chunk.start_char,
        "end_char": chunk.end_char,
    }


def _validate_strategy(strategy: str) -> str:
    if strategy not in COLLECTION_NAMES:
        raise ValueError(
            f"Unsupported strategy {strategy!r}. "
            f"Expected one of: {sorted(COLLECTION_NAMES)}."
        )
    return COLLECTION_NAMES[strategy]


class ChromaVectorStore:
    """Store and retrieve chunks from a strategy-specific collection."""

    
    def __init__(
        self,
        strategy: str,
        embeddings: EmbeddingModel,
        persist_directory: Path = DEFAULT_DB_DIR,
        *,
        client=None,
    ) -> None:
        collection_name = _validate_strategy(strategy)

        self.embeddings = embeddings
        self.strategy = strategy

        # Inject an in-memory client during tests. Normal application
        # usage continues to use a persistent on-disk ChromaDB client.
        if client is not None:
            self._client = client
        else:
            persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(persist_directory.resolve())
            )

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Clear this strategy's collection before a fresh ingestion."""

        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[TextChunk]) -> None:
        """Insert chunks with explicit embeddings and source metadata."""

        if not chunks:
            raise ValueError("Cannot add an empty chunk list.")

        if any(chunk.strategy != self.strategy for chunk in chunks):
            raise ValueError(
                f"All chunks must use strategy {self.strategy!r}."
            )

        ids = [chunk.chunk_id for chunk in chunks]
        if len(ids) != len(set(ids)):
            raise ValueError("Chunk IDs must be unique within a batch.")

        texts = [chunk.text for chunk in chunks]
        vectors = self.embeddings.embed_documents(texts)

        self._collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=vectors,
            metadatas=[_sanitize_metadata(chunk) for chunk in chunks],
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Return the nearest chunks with metadata and distance."""

        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if self.count == 0:
            return []

        vector = self.embeddings.embed_query(query)
        results = self._collection.query(
            query_embeddings=[vector],
            n_results=min(top_k, self.count),
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        ids = results["ids"][0]

        return [
            {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": metadata,
                "distance": distance,
            }
            for chunk_id, text, metadata, distance in zip(
                ids, documents, metadatas, distances
            )
        ]
