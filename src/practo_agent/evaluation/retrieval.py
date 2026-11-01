
"""Document-level retrieval evaluation for the Practo RAG system."""

from typing import Any, Protocol, Sequence

from practo_agent.evaluation.cases import EvaluationCase


class SearchableVectorStore(Protocol):
    """Minimum interface required by the evaluation engine."""

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        ...


def evaluate_query(
    case: EvaluationCase,
    retrieved_chunks: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate document-level metrics for one evaluation query."""

    expected_sources = set(case.expected_relevant_sources)

    retrieved_source_ids = []
    retrieved_chunk_details = []

    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {})
        source_id = metadata.get("source_id")

        if not source_id:
            raise ValueError(
                f"Retrieved chunk {chunk.get('chunk_id')} "
                "does not contain a source_id."
            )

        retrieved_source_ids.append(source_id)

        retrieved_chunk_details.append({
            "chunk_id": chunk.get("chunk_id"),
            "source_id": source_id,
            "distance": chunk.get("distance"),
        })

    # Preserve retrieval order while removing duplicate source documents.
    unique_retrieved_sources = list(dict.fromkeys(retrieved_source_ids))
    retrieved_source_set = set(unique_retrieved_sources)

    relevant_retrieved = expected_sources & retrieved_source_set
    false_positives = retrieved_source_set - expected_sources
    false_negatives = expected_sources - retrieved_source_set

    true_positive_count = len(relevant_retrieved)
    false_positive_count = len(false_positives)
    false_negative_count = len(false_negatives)

    precision_denominator = (
        true_positive_count + false_positive_count
    )
    recall_denominator = (
        true_positive_count + false_negative_count
    )

    # None represents an undefined metric, not a score of zero.
    precision = (
        true_positive_count / precision_denominator
        if precision_denominator > 0
        else None
    )

    recall = (
        true_positive_count / recall_denominator
        if recall_denominator > 0
        else None
    )

    return {
        "query_id": case.query_id,
        "query": case.query,
        "expected_relevant_sources": sorted(expected_sources),
        "retrieved_source_ids": unique_retrieved_sources,
        "retrieved_chunks": retrieved_chunk_details,
        "true_positives": sorted(relevant_retrieved),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "tp_count": true_positive_count,
        "fp_count": false_positive_count,
        "fn_count": false_negative_count,
        "precision": precision,
        "recall": recall,
    }


def _macro_average(
    results: Sequence[dict[str, Any]],
    metric_name: str,
) -> float | None:
    """Calculate a macro average, excluding undefined values."""

    values = [
        result[metric_name]
        for result in results
        if result[metric_name] is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)


def evaluate_strategy(
    cases: Sequence[EvaluationCase],
    store: SearchableVectorStore,
    strategy: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """Evaluate one vector-store strategy against all labeled cases."""

    if not cases:
        raise ValueError("At least one evaluation case is required.")

    if not strategy.strip():
        raise ValueError("Strategy name cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    query_results = []

    for case in cases:
        retrieved_chunks = store.search(
            case.query,
            top_k=top_k,
        )

        query_results.append(
            evaluate_query(case, retrieved_chunks)
        )

    return {
        "strategy": strategy,
        "top_k": top_k,
        "query_count": len(query_results),
        "macro_precision": _macro_average(
            query_results,
            "precision",
        ),
        "macro_recall": _macro_average(
            query_results,
            "recall",
        ),
        "queries": query_results,
    }


def compare_strategies(
    cases: Sequence[EvaluationCase],
    fixed_store: SearchableVectorStore,
    sentence_store: SearchableVectorStore,
    top_k: int = 3,
) -> dict[str, Any]:
    """Evaluate both chunking strategies using identical cases."""

    fixed_results = evaluate_strategy(
        cases=cases,
        store=fixed_store,
        strategy="fixed_size",
        top_k=top_k,
    )

    sentence_results = evaluate_strategy(
        cases=cases,
        store=sentence_store,
        strategy="sentence",
        top_k=top_k,
    )

    return {
        "top_k": top_k,
        "query_count": len(cases),
        "strategies": {
            "fixed_size": fixed_results,
            "sentence": sentence_results,
        },
    }
