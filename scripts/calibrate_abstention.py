"""Run empirical abstention-threshold calibration."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from practo_agent.evaluation.abstention import (
    calibrate_abstention,
    load_abstention_cases,
)
from practo_agent.config import DEFAULT_RETRIEVAL_CONFIG
from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.vectorstore import ChromaVectorStore


def main():
    os.environ["MOCK_LLM"] = "false"

    cases_path = PROJECT_ROOT / "evaluation" / "cases" / "abstention_cases.json"
    output_path = (
        PROJECT_ROOT / "evaluation" / "results" / "abstention_calibration.json"
    )

    cases = load_abstention_cases(cases_path)

    embeddings = create_embedding_model(mock_mode=False)
    strategy = DEFAULT_RETRIEVAL_CONFIG.strategy
    store = ChromaVectorStore(
        strategy=strategy,
        embeddings=embeddings,
    )

    if store.count == 0:
        raise RuntimeError(
            "The sentence collection is empty. Build the vector stores first."
        )

    report = calibrate_abstention(
        store=store,
        cases=cases,
        top_k=DEFAULT_RETRIEVAL_CONFIG.top_k,
    )
    report["configuration"] = {
        "strategy": strategy,
        "collection": DEFAULT_RETRIEVAL_CONFIG.collection_name,
        "top_k": DEFAULT_RETRIEVAL_CONFIG.top_k,
        "similarity_metric": DEFAULT_RETRIEVAL_CONFIG.similarity_metric,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Calibration cases: {report['calibration_case_count']}")
    print(f"In-scope: {report['in_scope_count']}")
    print(f"Out-of-scope: {report['out_of_scope_count']}")
    print("\nPer-query results:")

    for result in report["query_results"]:
        print(
            f"{result['query_id']}: "
            f"best_distance={result['best_distance']}, "
            f"in_scope={result['expected_in_scope']}, "
            f"expected_source_retrieved={result['expected_source_retrieved']}"
        )

    print("\nThreshold comparison:")

    for item in report["threshold_results"]:
        print(
            f"threshold={item['threshold']:.6f} | "
            f"TP={item['true_positive']} "
            f"FP={item['false_positive']} "
            f"TN={item['true_negative']} "
            f"FN={item['false_negative']} | "
            f"precision={item['precision']:.4f} "
            f"recall={item['recall']:.4f} "
            f"FAR={item['false_acceptance_rate']:.4f}"
        )

    print("\nRecommended threshold:", report["recommended_threshold"])
    print("Recommended metrics:", report["recommended_metrics"])
    print("\n", report["warning"])
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()