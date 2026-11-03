
"""Centralized configuration for the Practo RAG retrieval pipeline."""

from dataclasses import dataclass

from practo_agent.rag.vectorstore import COLLECTION_NAMES


@dataclass(frozen=True)
class RetrievalConfig:
    """Validated settings for selecting and querying a vector collection."""

    strategy: str = "sentence"
    top_k: int = 2
    similarity_metric: str = "cosine"

    def __post_init__(self) -> None:
        if self.strategy not in COLLECTION_NAMES:
            raise ValueError(
                f"Unsupported retrieval strategy {self.strategy!r}. "
                f"Expected one of: {sorted(COLLECTION_NAMES)}."
            )

        if isinstance(self.top_k, bool) or not isinstance(self.top_k, int):
            raise ValueError("top_k must be a positive integer.")

        if self.top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if self.similarity_metric != "cosine":
            raise ValueError(
                "Only the cosine similarity metric is currently supported."
            )

    @property
    def collection_name(self) -> str:
        """Return the ChromaDB collection associated with this strategy."""

        return COLLECTION_NAMES[self.strategy]


DEFAULT_RETRIEVAL_CONFIG = RetrievalConfig()
