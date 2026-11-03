
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
from practo_agent.config import DEFAULT_RETRIEVAL_CONFIG
from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.vectorstore import ChromaVectorStore


RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "retrieval_results.json"
REPORT_PATH = RESULTS_DIR / "retrieval_comparison.md"

TOP_K = DEFAULT_RETRIEVAL_CONFIG.top_k
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def format_metric(value):
    """Format a metric while preserving undefined values."""
    return f"{value:.4f}" if value is not None else "N/A"


def _per_query_calculation(result, metric):
    """Render the arithmetic behind one per-query metric."""
    true_positives = result["tp_count"]

    if metric == "precision":
        denominator = true_positives + result["fp_count"]
    else:
        denominator = true_positives + result["fn_count"]

    value = result[metric]
    if value is None:
        return "undefined (no retrieved documents)"

    return f"{true_positives}/{denominator} = {value:.4f}"


def write_markdown_report(results):
    """Write the assignment's per-query arithmetic and comparison report."""
    strategies = results["strategies"]
    selected_strategy = max(
        strategies,
        key=lambda strategy: (
            strategies[strategy]["macro_recall"],
            strategies[strategy]["macro_precision"],
        ),
    )

    lines = [
        "# Retrieval Strategy Comparison Report",
        "",
        "Both chunking strategies were evaluated against the same "
        f"{results['query_count']} in-scope queries, using document-level "
        "relevance labels and deduplicated source documents.",
        "",
        f"- Embedding model: {results['configuration']['embedding_model']}",
        f"- Similarity metric: {results['configuration']['similarity_metric']}",
        f"- Top-k: {results['top_k']}",
        "",
    ]

    for strategy, label in (
        ("fixed_size", "Fixed-size-with-overlap"),
        ("sentence", "Sentence-based"),
    ):
        strategy_results = strategies[strategy]
        lines.extend([
            f"## {label}",
            "",
            "| Query | Expected source(s) | Retrieved source(s) | TP | FP | FN | Precision arithmetic | Recall arithmetic |",
            "|---|---|---|---:|---:|---:|---|---|",
        ])

        for result in strategy_results["queries"]:
            expected = ", ".join(result["expected_relevant_sources"])
            retrieved = ", ".join(result["retrieved_source_ids"]) or "None"
            lines.append(
                f"| {result['query_id']} | {expected} | {retrieved} | "
                f"{result['tp_count']} | {result['fp_count']} | "
                f"{result['fn_count']} | "
                f"{_per_query_calculation(result, 'precision')} | "
                f"{_per_query_calculation(result, 'recall')} |"
            )

        lines.extend([
            "",
            f"Macro precision: **{strategy_results['macro_precision']:.4f}** "
            f"(mean over {strategy_results['query_count']} queries).",
            f"Macro recall: **{strategy_results['macro_recall']:.4f}** "
            f"(mean over {strategy_results['query_count']} queries).",
            "",
        ])

    fixed = strategies["fixed_size"]
    sentence = strategies["sentence"]
    selected = strategies[selected_strategy]
    difference = (
        sentence["macro_precision"] - fixed["macro_precision"]
    )
    lines.extend([
        "## Recommendation",
        "",
        (
            f"Select **{selected_strategy.replace('_', ' ')}** chunking: "
            f"recall is prioritized to reduce missed policy sources; it has "
            f"macro recall {selected['macro_recall']:.4f} and macro precision "
            f"{selected['macro_precision']:.4f}. "
            f"The sentence-based minus fixed-size precision difference is "
            f"{difference:+.4f}; this recommendation is limited to this "
            f"{results['query_count']}-query labeled evaluation."
        ),
        "",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


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

    write_markdown_report(results)

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
    print("Readable report saved to:")
    print(REPORT_PATH)

    return results


if __name__ == "__main__":
    run_evaluation()
