
"""Run the real retrieval comparison against persistent ChromaDB collections."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# This experiment must use real semantic embeddings.
os.environ["MOCK_LLM"] = "false"

from practo_agent.evaluation.cases import load_evaluation_cases
from practo_agent.evaluation.retrieval import compare_strategies
from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.vectorstore import ChromaVectorStore


RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "retrieval_results.json"

TOP_K = 3
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def format_metric(value):
    """Format a metric while preserving undefined values."""
    return f"{value:.4f}" if value is not None else "N/A"

def run_evaluation():
    """Load existing collections and evaluate both retrieval strategies."""

    print("=" * 65)
    print("PRACTO RAG - REAL RETRIEVAL EVALUATION")
    print("=" * 65)

    print("\nLoading validated evaluation cases...")
    cases = load_evaluation_cases()
    print(f"Evaluation cases loaded: {len(cases)}")

    print("\nLoading real embedding model...")
    embeddings = create_embedding_model(mock_mode=False)

    print("\nOpening existing persistent ChromaDB collections...")

    # Do not call build_vector_store() here.
    # That function resets and rebuilds collections.
    fixed_store = ChromaVectorStore(
        strategy="fixed_size",
        embeddings=embeddings,
    )

    sentence_store = ChromaVectorStore(
        strategy="sentence",
        embeddings=embeddings,
    )

    print(
        f"Fixed-size collection: {fixed_store._collection.name} "
        f"({fixed_store.count} chunks)"
    )
    print(
        f"Sentence collection: {sentence_store._collection.name} "
        f"({sentence_store.count} chunks)"
    )

    if fixed_store.count == 0:
        raise RuntimeError(
            "Fixed-size collection is empty. Run the ingestion script first."
        )

    if sentence_store.count == 0:
        raise RuntimeError(
            "Sentence-based collection is empty. Run the ingestion script first."
        )

    print("\nRunning both retrieval experiments...")
    results = compare_strategies(
        cases=cases,
        fixed_store=fixed_store,
        sentence_store=sentence_store,
        top_k=TOP_K,
    )

    # Attach experiment configuration to the raw results.
    results["configuration"] = {
        "embedding_model": EMBEDDING_MODEL,
        "similarity_metric": "cosine",
        "top_k": TOP_K,
        "collections": {
            "fixed_size": fixed_store._collection.name,
            "sentence": sentence_store._collection.name,
        },
        "evaluation_case_count": len(cases),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with RESULTS_PATH.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 65)

    for strategy, strategy_results in results["strategies"].items():
        print(f"\nStrategy: {strategy}")
        print(f"Queries: {strategy_results['query_count']}")
        print(
            f"Macro precision: "
            f"{format_metric(strategy_results['macro_precision'])}"
        )
        print(
            f"Macro recall: "
            f"{format_metric(strategy_results['macro_recall'])}"
        )

        print("\nPer-query results:")

        for query_result in strategy_results["queries"]:
            print(
                f"  {query_result['query_id']}: "
                f"Precision={format_metric(query_result['precision'])}, "
                f"Recall={format_metric(query_result['recall'])}"
            )

    print("\nFull results saved to:")
    print(RESULTS_PATH)

    return results


if __name__ == "__main__":
    run_evaluation()
