"""Deterministic appointment lookup for the Practo support agent."""

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DATASET_PATH = (
    PROJECT_ROOT / "data" / "generated" / "appointments.json"
)


def _load_appointments() -> list[dict[str, Any]]:
    """Load appointment records from the generated JSON dataset."""

    if not DEFAULT_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Appointment dataset not found: {DEFAULT_DATASET_PATH}"
        )

    with DEFAULT_DATASET_PATH.open("r", encoding="utf-8") as file:
        appointments = json.load(file)

    if not isinstance(appointments, list):
        raise ValueError("Appointment dataset must contain a JSON array.")

    return appointments


def calculate_escalation_score(
    follow_up_required: bool,
    days_since_created: int,
) -> float:
    """Calculate an administrative prioritization score between 0 and 1."""

    if type(follow_up_required) is not bool:
        raise ValueError("follow_up_required must be a boolean.")

    if type(days_since_created) is not int:
        raise ValueError("days_since_created must be an integer.")

    if not 0 <= days_since_created <= 30:
        raise ValueError(
            "days_since_created must be between 0 and 30."
        )

    follow_up_score = 1.0 if follow_up_required else 0.0
    recency_score = days_since_created / 30

    escalation_score = (
        0.6 * follow_up_score
        + 0.4 * recency_score
    )

    return round(escalation_score, 4)


def check_appointment_status(record_id: str) -> dict[str, Any]:
    """Look up an appointment and return its administrative details."""

    if not isinstance(record_id, str) or not record_id.strip():
        raise ValueError("record_id must be a non-empty string.")

    normalized_record_id = record_id.strip().upper()

    appointments = _load_appointments()

    for appointment in appointments:
        if appointment.get("record_id") == normalized_record_id:
            escalation_score = calculate_escalation_score(
                follow_up_required=appointment["follow_up_required"],
                days_since_created=appointment["days_since_created"],
            )

            return {
                "found": True,
                "record_id": appointment["record_id"],
                "status": appointment["status"],
                "consultation_fee_inr": appointment[
                    "consultation_fee_inr"
                ],
                "escalation_score": escalation_score,
            }

    return {
        "found": False,
        "record_id": normalized_record_id,
        "error": "Appointment record not found.",
    }