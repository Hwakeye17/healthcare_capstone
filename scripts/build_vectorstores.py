
"""Build both persistent ChromaDB collections using real embeddings."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Do not allow mock embeddings for the actual retrieval experiment.
os.environ["MOCK_LLM"] = "false"

from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.retriever import build_vector_store


def main():
    print("=" * 60)
    print("Practo RAG - Vector Store Ingestion")
    print("=" * 60)

    print("\nLoading real Sentence Transformers embedding model...")

    embeddings = create_embedding_model(mock_mode=False)

    strategies = ("fixed_size", "sentence")
    stores = {}

    for strategy in strategies:
        print(f"\nBuilding {strategy} collection...")

        store = build_vector_store(
            strategy=strategy,
            embeddings=embeddings,
        )

        stores[strategy] = store

        print(f"Collection: {store._collection.name}")
        print(f"Stored chunks: {store.count}")

        if store.count == 0:
            raise RuntimeError(
                f"Collection {strategy} contains no chunks."
            )

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)

    for strategy, store in stores.items():
        print(f"{strategy}: {store.count} chunks")

    print("\nBoth vector collections were built successfully.")


if __name__ == "__main__":
    main()
