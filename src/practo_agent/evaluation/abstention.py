"""Empirical calibration of the RAG abstention threshold."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class SearchableVectorStore(Protocol):
    """Minimal interface required by the calibration evaluator."""

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        ...


def load_abstention_cases(path: str | Path) -> list[dict]:
    """Load and validate labeled abstention calibration cases."""

    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Abstention cases must be a non-empty JSON list.")

    required_fields = {
        "query_id",
        "query",
        "expected_in_scope",
        "expected_source_ids",
    }

    seen_ids = set()

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case at index {index} must be an object.")

        missing = required_fields - case.keys()
        if missing:
            raise ValueError(
                f"Case at index {index} is missing fields: {sorted(missing)}"
            )

        query_id = case["query_id"]
        query = case["query"]
        expected_in_scope = case["expected_in_scope"]
        expected_sources = case["expected_source_ids"]

        if not isinstance(query_id, str) or not query_id.strip():
            raise ValueError(f"Case at index {index} has an invalid query_id.")

        if query_id in seen_ids:
            raise ValueError(f"Duplicate query_id: {query_id}")

        seen_ids.add(query_id)

        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Case {query_id} has an empty query.")

        if not isinstance(expected_in_scope, bool):
            raise ValueError(
                f"Case {query_id}: expected_in_scope must be a boolean."
            )

        if not isinstance(expected_sources, list):
            raise ValueError(
                f"Case {query_id}: expected_source_ids must be a list."
            )

        if expected_in_scope and not expected_sources:
            raise ValueError(
                f"Case {query_id}: in-scope cases need expected source IDs."
            )

        if not expected_in_scope and expected_sources:
            raise ValueError(
                f"Case {query_id}: out-of-scope cases must have no expected sources."
            )

    in_scope_count = sum(case["expected_in_scope"] for case in cases)
    out_of_scope_count = len(cases) - in_scope_count

    if in_scope_count == 0 or out_of_scope_count == 0:
        raise ValueError(
            "Calibration requires both in-scope and out-of-scope cases."
        )

    return cases


def collect_calibration_results(
    store: SearchableVectorStore,
    cases: list[dict],
    top_k: int = 3,
) -> list[dict]:
    """Retrieve evidence and record the best cosine distance per query."""

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    results = []

    for case in cases:
        retrieved = store.search(case["query"], top_k=top_k)

        distances = []
        source_ids = []

        for chunk in retrieved:
            distance = chunk.get("distance")
            source_id = chunk.get("metadata", {}).get("source_id")

            if distance is not None:
                distances.append(float(distance))

            if source_id is not None and source_id not in source_ids:
                source_ids.append(source_id)

        best_distance = min(distances) if distances else None

        expected_sources = set(case["expected_source_ids"])
        retrieved_sources = set(source_ids)

        results.append({
            "query_id": case["query_id"],
            "query": case["query"],
            "expected_in_scope": case["expected_in_scope"],
            "expected_source_ids": sorted(expected_sources),
            "retrieved_source_ids": source_ids,
            "best_distance": best_distance,
            "has_retrieval": best_distance is not None,
            "expected_source_retrieved": bool(
                expected_sources & retrieved_sources
            ),
        })

    return results


def _calculate_metrics(
    results: list[dict],
    threshold: float,
) -> dict:
    """Calculate classification metrics for one distance threshold."""

    true_positive = 0
    false_positive = 0
    true_negative = 0
    false_negative = 0

    for result in results:
        expected = result["expected_in_scope"]
        distance = result["best_distance"]

        predicted = (
            distance is not None
            and distance <= threshold
        )

        if expected and predicted:
            true_positive += 1
        elif not expected and predicted:
            false_positive += 1
        elif not expected and not predicted:
            true_negative += 1
        else:
            false_negative += 1

    accepted = true_positive + false_positive

    precision = (
        true_positive / accepted
        if accepted else 0.0
    )

    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative else 0.0
    )

    false_acceptance_rate = (
        false_positive / (false_positive + true_negative)
        if false_positive + true_negative else 0.0
    )

    return {
        "threshold": threshold,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "false_acceptance_rate": round(false_acceptance_rate, 4),
    }


def evaluate_thresholds(results: list[dict]) -> dict:
    """Evaluate candidate thresholds and select a conservative recommendation."""

    if not results:
        raise ValueError("At least one calibration result is required.")

    observed_distances = sorted({
        result["best_distance"]
        for result in results
        if result["best_distance"] is not None
    })

    if not observed_distances:
        raise ValueError("No valid retrieval distances were recorded.")

    # Include observed boundaries and gap midpoints so the selected threshold
    # can sit between the nearest in-scope and out-of-scope clusters.
    candidate_thresholds = {0.0, *observed_distances}
    candidate_thresholds.update(
        (left + right) / 2
        for left, right in zip(observed_distances, observed_distances[1:])
    )

    threshold_results = [
        _calculate_metrics(results, threshold)
        for threshold in sorted(candidate_thresholds)
    ]

    # Safety-first policy:
    # 1. Require zero false acceptances.
    # 2. Among those thresholds, maximize in-scope recall.
    # 3. If tied, choose the lower (more conservative) threshold.
    safe_candidates = [
        item for item in threshold_results
        if item["false_positive"] == 0
    ]

    recommended = None
    separating_midpoint = None
    in_scope_distances = [
        result["best_distance"]
        for result in results
        if result["expected_in_scope"]
        and result["best_distance"] is not None
    ]
    out_of_scope_distances = [
        result["best_distance"]
        for result in results
        if not result["expected_in_scope"]
        and result["best_distance"] is not None
    ]

    if safe_candidates:
        best_recall = max(item["recall"] for item in safe_candidates)
        best_candidates = [
            item for item in safe_candidates
            if item["recall"] == best_recall
        ]

        if (
            in_scope_distances
            and out_of_scope_distances
            and max(in_scope_distances) < min(out_of_scope_distances)
            and best_recall == 1.0
        ):
            separating_midpoint = (
                max(in_scope_distances) + min(out_of_scope_distances)
            ) / 2
            recommended = min(
                best_candidates,
                key=lambda item: abs(
                    item["threshold"] - separating_midpoint
                ),
            )
        else:
            recommended = min(
                best_candidates,
                key=lambda item: item["threshold"],
            )

    return {
        "threshold_results": threshold_results,
        "recommended_threshold": (
            recommended["threshold"] if recommended else None
        ),
        "recommended_metrics": recommended,
        "selection_rule": (
            "Zero false acceptances, then maximum in-scope recall; "
            "when the observed classes are fully separable, select the "
            "midpoint between their nearest boundaries; otherwise select "
            "the lower threshold among tied candidates."
        ),
        "separating_midpoint": separating_midpoint,
        "calibration_case_count": len(results),
        "in_scope_count": sum(
            result["expected_in_scope"] for result in results
        ),
        "out_of_scope_count": sum(
            not result["expected_in_scope"] for result in results
        ),
        "warning": (
            "A threshold selected from a small calibration set is provisional. "
            "It must be validated against a larger, representative query set."
        ),
    }


def calibrate_abstention(
    store: SearchableVectorStore,
    cases: list[dict],
    top_k: int = 3,
) -> dict:
    """Run retrieval, collect distances, and evaluate thresholds."""

    results = collect_calibration_results(
        store=store,
        cases=cases,
        top_k=top_k,
    )

    evaluation = evaluate_thresholds(results)

    return {
        "top_k": top_k,
        "query_results": results,
        **evaluation,
    }
