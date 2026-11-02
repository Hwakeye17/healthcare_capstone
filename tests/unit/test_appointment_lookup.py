
"""Unit tests for the appointment lookup tool."""

import json

import pytest

from practo_agent.tools import appointment_lookup


@pytest.fixture
def sample_appointments():
    """Provide sample appointment records for testing."""

    return [
        {
            "record_id": "APT-0001",
            "category": "General Medicine",
            "status": "Scheduled",
            "consultation_fee_inr": 500,
            "days_since_created": 15,
            "follow_up_required": True,
        },
        {
            "record_id": "APT-0002",
            "category": "Cardiology",
            "status": "Completed",
            "consultation_fee_inr": 1000,
            "days_since_created": 30,
            "follow_up_required": False,
        },
    ]


@pytest.fixture
def temporary_dataset(tmp_path, monkeypatch, sample_appointments):
    """Create a temporary appointment dataset."""

    dataset_path = tmp_path / "appointments.json"

    dataset_path.write_text(
        json.dumps(sample_appointments),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        appointment_lookup,
        "DEFAULT_DATASET_PATH",
        dataset_path,
    )

    return dataset_path


def test_lookup_existing_appointment(temporary_dataset):
    result = appointment_lookup.check_appointment_status("APT-0001")

    assert result == {
        "found": True,
        "record_id": "APT-0001",
        "status": "Scheduled",
        "consultation_fee_inr": 500,
        "escalation_score": 0.8,
    }


def test_lookup_unknown_appointment(temporary_dataset):
    result = appointment_lookup.check_appointment_status("APT-9999")

    assert result == {
        "found": False,
        "record_id": "APT-9999",
        "error": "Appointment record not found.",
    }


def test_lookup_normalizes_lowercase_record_id(temporary_dataset):
    result = appointment_lookup.check_appointment_status("apt-0001")

    assert result["found"] is True
    assert result["record_id"] == "APT-0001"


@pytest.mark.parametrize(
    "record_id",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_lookup_rejects_invalid_record_id(record_id):
    with pytest.raises(ValueError, match="record_id"):
        appointment_lookup.check_appointment_status(record_id)


def test_escalation_score_with_follow_up_required():
    score = appointment_lookup.calculate_escalation_score(
        follow_up_required=True,
        days_since_created=15,
    )

    assert score == 0.8


def test_escalation_score_without_follow_up():
    score = appointment_lookup.calculate_escalation_score(
        follow_up_required=False,
        days_since_created=30,
    )

    assert score == 0.4


def test_escalation_score_minimum_boundary():
    score = appointment_lookup.calculate_escalation_score(
        follow_up_required=False,
        days_since_created=0,
    )

    assert score == 0.0


def test_escalation_score_maximum_boundary():
    score = appointment_lookup.calculate_escalation_score(
        follow_up_required=True,
        days_since_created=30,
    )

    assert score == 1.0


def test_escalation_score_rejects_non_boolean_follow_up():
    with pytest.raises(ValueError, match="boolean"):
        appointment_lookup.calculate_escalation_score(
            follow_up_required=1,
            days_since_created=10,
        )


@pytest.mark.parametrize(
    "days",
    [
        -1,
        31,
        10.5,
        True,
    ],
)
def test_escalation_score_rejects_invalid_days(days):
    with pytest.raises(ValueError):
        appointment_lookup.calculate_escalation_score(
            follow_up_required=True,
            days_since_created=days,
        )


def test_lookup_missing_dataset_raises_error(tmp_path, monkeypatch):
    missing_path = tmp_path / "missing.json"

    monkeypatch.setattr(
        appointment_lookup,
        "DEFAULT_DATASET_PATH",
        missing_path,
    )

    with pytest.raises(FileNotFoundError, match="Appointment dataset"):
        appointment_lookup.check_appointment_status("APT-0001")


def test_lookup_rejects_invalid_dataset_structure(tmp_path, monkeypatch):
    dataset_path = tmp_path / "appointments.json"
    dataset_path.write_text(
        json.dumps({"record_id": "APT-0001"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        appointment_lookup,
        "DEFAULT_DATASET_PATH",
        dataset_path,
    )

    with pytest.raises(ValueError, match="JSON array"):
        appointment_lookup.check_appointment_status("APT-0001")
