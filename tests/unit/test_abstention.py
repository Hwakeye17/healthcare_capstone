import json

import pytest

from practo_agent.evaluation.abstention import (
    calibrate_abstention,
    collect_calibration_results,
    evaluate_thresholds,
    load_abstention_cases,
)


class FakeVectorStore:
    def __init__(self, responses):
        self.responses = responses

    def search(self, query, top_k=3):
        return self.responses.get(query, [])[:top_k]


@pytest.fixture
def calibration_cases():
    return [
        {
            "query_id": "ABS-001",
            "query": "Booking question",
            "expected_in_scope": True,
            "expected_source_ids": ["appointment_booking"],
        },
        {
            "query_id": "ABS-002",
            "query": "Insurance question",
            "expected_in_scope": True,
            "expected_source_ids": ["insurance_claims"],
        },
        {
            "query_id": "ABS-003",
            "query": "Lab question",
            "expected_in_scope": True,
            "expected_source_ids": ["lab_turnaround"],
        },
        {
            "query_id": "ABS-004",
            "query": "Diagnosis question",
            "expected_in_scope": False,
            "expected_source_ids": [],
        },
        {
            "query_id": "ABS-005",
            "query": "Cricket question",
            "expected_in_scope": False,
            "expected_source_ids": [],
        },
    ]


def test_load_abstention_cases(tmp_path, calibration_cases):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(calibration_cases), encoding="utf-8")

    cases = load_abstention_cases(path)

    assert len(cases) == 5
    assert sum(case["expected_in_scope"] for case in cases) == 3


def test_load_abstention_cases_rejects_duplicate_ids(
    tmp_path, calibration_cases
):
    calibration_cases[1]["query_id"] = calibration_cases[0]["query_id"]

    path = tmp_path / "cases.json"
    path.write_text(json.dumps(calibration_cases), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate"):
        load_abstention_cases(path)


def test_load_abstention_cases_requires_both_classes(tmp_path):
    cases = [
        {
            "query_id": "ABS-001",
            "query": "Booking question",
            "expected_in_scope": True,
            "expected_source_ids": ["appointment_booking"],
        }
    ]

    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")

    with pytest.raises(ValueError, match="both in-scope"):
        load_abstention_cases(path)


def test_load_abstention_cases_rejects_sources_for_out_of_scope(
    tmp_path, calibration_cases
):
    calibration_cases[3]["expected_source_ids"] = ["privacy_policy"]

    path = tmp_path / "cases.json"
    path.write_text(json.dumps(calibration_cases), encoding="utf-8")

    with pytest.raises(ValueError, match="out-of-scope"):
        load_abstention_cases(path)


def test_collect_calibration_results_records_best_distance(
    calibration_cases,
):
    store = FakeVectorStore({
        "Booking question": [
            {
                "distance": 0.42,
                "metadata": {"source_id": "appointment_booking"},
            },
            {
                "distance": 0.31,
                "metadata": {"source_id": "appointment_booking"},
            },
        ]
    })

    results = collect_calibration_results(
        store,
        calibration_cases[:1],
    )

    assert results[0]["best_distance"] == 0.31
    assert results[0]["expected_source_retrieved"] is True
    assert results[0]["retrieved_source_ids"] == ["appointment_booking"]


def test_collect_calibration_results_handles_no_results(
    calibration_cases,
):
    store = FakeVectorStore({})

    results = collect_calibration_results(
        store,
        calibration_cases[:1],
    )

    assert results[0]["best_distance"] is None
    assert results[0]["has_retrieval"] is False


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_collect_calibration_results_rejects_invalid_top_k(
    calibration_cases, top_k
):
    with pytest.raises(ValueError, match="top_k"):
        collect_calibration_results(
            FakeVectorStore({}),
            calibration_cases[:1],
            top_k=top_k,
        )


def test_evaluate_thresholds_selects_zero_false_acceptance_threshold():
    results = [
        {
            "expected_in_scope": True,
            "best_distance": 0.20,
        },
        {
            "expected_in_scope": True,
            "best_distance": 0.30,
        },
        {
            "expected_in_scope": False,
            "best_distance": 0.70,
        },
        {
            "expected_in_scope": False,
            "best_distance": 0.80,
        },
    ]

    report = evaluate_thresholds(results)

    assert report["recommended_threshold"] == 0.5
    assert report["recommended_metrics"]["false_positive"] == 0
    assert report["recommended_metrics"]["recall"] == 1.0


def test_evaluate_thresholds_preserves_full_observed_distance_precision():
    observed_distance = 0.35277605056762695
    results = [
        {
            "expected_in_scope": True,
            "best_distance": observed_distance,
        },
        {
            "expected_in_scope": False,
            "best_distance": 0.75,
        },
    ]

    report = evaluate_thresholds(results)

    expected_midpoint = (observed_distance + 0.75) / 2
    assert report["recommended_threshold"] == expected_midpoint
    assert report["recommended_metrics"]["recall"] == 1.0


def test_evaluate_thresholds_can_recommend_reject_all():
    results = [
        {
            "expected_in_scope": True,
            "best_distance": 0.60,
        },
        {
            "expected_in_scope": False,
            "best_distance": 0.20,
        },
    ]

    report = evaluate_thresholds(results)

    assert report["recommended_threshold"] == 0.0
    assert report["recommended_metrics"]["false_positive"] == 0
    assert report["recommended_metrics"]["recall"] == 0.0


def test_evaluate_thresholds_returns_no_recommendation_without_distances():
    results = [
        {
            "expected_in_scope": True,
            "best_distance": None,
        },
        {
            "expected_in_scope": False,
            "best_distance": None,
        },
    ]

    with pytest.raises(ValueError, match="No valid retrieval distances"):
        evaluate_thresholds(results)


def test_calibrate_abstention_combines_retrieval_and_evaluation(
    calibration_cases,
):
    store = FakeVectorStore({
        "Booking question": [
            {
                "distance": 0.20,
                "metadata": {"source_id": "appointment_booking"},
            }
        ],
        "Insurance question": [
            {
                "distance": 0.30,
                "metadata": {"source_id": "insurance_claims"},
            }
        ],
        "Lab question": [
            {
                "distance": 0.40,
                "metadata": {"source_id": "lab_turnaround"},
            }
        ],
        "Diagnosis question": [
            {
                "distance": 0.80,
                "metadata": {"source_id": "emergency_visits"},
            }
        ],
        "Cricket question": [
            {
                "distance": 0.90,
                "metadata": {"source_id": "home_visits"},
            }
        ],
    })

    report = calibrate_abstention(store, calibration_cases)

    assert report["calibration_case_count"] == 5
    assert report["in_scope_count"] == 3
    assert report["out_of_scope_count"] == 2
    assert len(report["query_results"]) == 5
    assert report["recommended_threshold"] == pytest.approx(0.6)


def test_evaluate_thresholds_uses_midpoint_between_separated_classes():
    results = [
        {"expected_in_scope": True, "best_distance": 0.1},
        {"expected_in_scope": True, "best_distance": 0.4},
        {"expected_in_scope": False, "best_distance": 0.8},
        {"expected_in_scope": False, "best_distance": 0.9},
    ]

    report = evaluate_thresholds(results)

    assert report["separating_midpoint"] == pytest.approx(0.6)
    assert report["recommended_threshold"] == report["separating_midpoint"]