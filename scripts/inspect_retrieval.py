
"""Inspect actual retrieved chunk content for selected evaluation queries."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ["MOCK_LLM"] = "false"

from practo_agent.evaluation.cases import load_evaluation_cases
from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.vectorstore import ChromaVectorStore


INSPECT_QUERY_IDS = {
    "RAG-002",
    "RAG-006",
    "RAG-007",
    "RAG-008",
    "RAG-010",
    "RAG-011",
    "RAG-012",
}

TOP_K = 3


def main():
    cases = load_evaluation_cases()
    selected_cases = [
        case for case in cases
        if case.query_id in INSPECT_QUERY_IDS
    ]

    embeddings = create_embedding_model(mock_mode=False)

    stores = {
        "FIXED-SIZE": ChromaVectorStore(
            "fixed_size", embeddings
        ),
        "SENTENCE-BASED": ChromaVectorStore(
            "sentence", embeddings
        ),
    }

    for case in selected_cases:
        print("\n" + "=" * 90)
        print(f"{case.query_id}: {case.query}")
        print(f"Expected sources: {case.expected_relevant_sources}")
        print("=" * 90)

        for strategy_name, store in stores.items():
            print(f"\n--- {strategy_name} ---")

            results = store.search(case.query, top_k=TOP_K)

            for rank, result in enumerate(results, start=1):
                metadata = result["metadata"]

                print(f"\nRank: {rank}")
                print(f"Chunk ID: {result['chunk_id']}")
                print(f"Source: {metadata.get('source_id')}")
                print(f"Distance: {result['distance']:.6f}")
                print("Content:")
                print(result["text"])
                print("-" * 70)


if __name__ == "__main__":
    main()
