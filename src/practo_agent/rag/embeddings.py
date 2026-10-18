
"""Local embedding model interface for the Practo RAG pipeline."""

import os
from typing import Protocol


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingModel(Protocol):
    """Interface expected by the vector-store component."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class SentenceTransformerEmbeddings:
    """Generate embeddings using a locally available Sentence Transformer."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        *,
        local_files_only: bool = True,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install dependencies from requirements.txt."
            ) from exc

        self.model_name = model_name

        try:
            self._model = SentenceTransformer(
                model_name,
                local_files_only=local_files_only,
            )
        except Exception as exc:
            mode_message = (
                "The model must already be cached locally because "
                "local_files_only=True."
                if local_files_only
                else "Check that the model is available and can be loaded."
            )
            raise RuntimeError(
                f"Could not load embedding model {model_name!r}. "
                f"{mode_message}"
            ) from exc

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding input documents cannot be empty.")

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Embedding query cannot be empty.")

        vector = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector.tolist()


class DeterministicTestEmbeddings:
    """Small deterministic embeddings for offline tests only.

    These vectors are not semantic embeddings and must not be used to
    evaluate real retrieval quality.
    """

    def __init__(self, dimensions: int = 32) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero.")
        self.dimensions = dimensions

    def _embed(self, text: str) -> list[float]:
        # Stable character-based features: no model files or network.
        vector = [0.0] * self.dimensions
        normalized = text.casefold()

        for index, character in enumerate(normalized):
            slot = (ord(character) + index) % self.dimensions
            vector[slot] += 1.0

        norm = sum(value * value for value in vector) ** 0.5
        if norm:
            vector = [value / norm for value in vector]

        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any(not text.strip() for text in texts):
            raise ValueError("Embedding input documents cannot be empty.")
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Embedding query cannot be empty.")
        return self._embed(text)


def create_embedding_model(
    *,
    mock_mode: bool | None = None,
    model_name: str = DEFAULT_MODEL_NAME,
) -> EmbeddingModel:
    """Create embeddings based on the explicit mock-mode setting."""

    if mock_mode is None:
        mock_mode = os.getenv("MOCK_LLM", "").strip().lower() == "true"

    if mock_mode:
        return DeterministicTestEmbeddings()

    return SentenceTransformerEmbeddings(
        model_name=model_name,
        local_files_only=True,
    )
