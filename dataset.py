
"""Generate and validate a deterministic synthetic appointment dataset.

This dataset is for the Practo Domain Support Agent capstone only.
It does not represent real Practo appointments or consultation prices.
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "record_id",
    "category",
    "status",
    "consultation_fee_inr",
    "days_since_created",
    "follow_up_required",
}

CATEGORIES = [
    "General Medicine",
    "Cardiology",
    "Dermatology",
    "Pediatrics",
    "Orthopedics",
]

STATUSES = [
    "Scheduled",
    "Completed",
    "Cancelled",
    "No-Show",
    "Rescheduled",
]

# Synthetic sample values for testing only; these are not actual Practo fees.
SYNTHETIC_FEES_INR = {
    "General Medicine": 500,
    "Cardiology": 1000,
    "Dermatology": 700,
    "Pediatrics": 600,
    "Orthopedics": 800,
}

MIN_RECORDS = 40
DEFAULT_RECORDS = 50
DEFAULT_SEED = 42

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "generated" / "appointments.json"


def generate_appointments(
    count: int = DEFAULT_RECORDS,
    seed: int = DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Generate reproducible synthetic appointments."""

    if count < MIN_RECORDS:
        raise ValueError(
            f"At least {MIN_RECORDS} appointment records are required; "
            f"received {count}."
        )

    rng = random.Random(seed)

    # Cycle through every category and status so all required values appear.
    categories = [
        CATEGORIES[index % len(CATEGORIES)]
        for index in range(count)
    ]
    statuses = [
        STATUSES[index % len(STATUSES)]
        for index in range(count)
    ]

    # Shuffle with the local seeded RNG for reproducible variation.
    rng.shuffle(categories)
    rng.shuffle(statuses)

    # Keep the follow-up proportion inside the required 10%-30% range.
    follow_up_count = round(count * 0.20)
    follow_up_flags = (
        [True] * follow_up_count
        + [False] * (count - follow_up_count)
    )
    rng.shuffle(follow_up_flags)

    appointments = []

    for index in range(count):
        category = categories[index]

        appointment = {
            "record_id": f"APT-{index + 1:04d}",
            "category": category,
            "status": statuses[index],
            "consultation_fee_inr": SYNTHETIC_FEES_INR[category],
            "days_since_created": rng.randint(0, 30),
            "follow_up_required": follow_up_flags[index],
        }

        appointments.append(appointment)

    validate_appointments(appointments)
    return appointments


def validate_appointments(
    appointments: list[dict[str, Any]],
) -> None:
    """Raise ValueError if the dataset violates a required constraint."""

    if len(appointments) < MIN_RECORDS:
        raise ValueError(
            f"Dataset must contain at least {MIN_RECORDS} records; "
            f"found {len(appointments)}."
        )

    record_ids = []

    for index, appointment in enumerate(appointments):
        label = f"Record at index {index}"

        if not isinstance(appointment, dict):
            raise ValueError(f"{label} must be a dictionary.")

        actual_fields = set(appointment.keys())
        if actual_fields != REQUIRED_FIELDS:
            missing = REQUIRED_FIELDS - actual_fields
            extra = actual_fields - REQUIRED_FIELDS
            raise ValueError(
                f"{label} has incorrect fields. "
                f"Missing: {sorted(missing)}; extra: {sorted(extra)}."
            )

        record_id = appointment["record_id"]
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"{label} has an invalid record_id.")
        record_ids.append(record_id)

        category = appointment["category"]
        if category not in CATEGORIES:
            raise ValueError(
                f"{label} has an unsupported category: {category!r}."
            )

        status = appointment["status"]
        if status not in STATUSES:
            raise ValueError(
                f"{label} has an unsupported status: {status!r}."
            )

        fee = appointment["consultation_fee_inr"]
        if type(fee) is not int or fee <= 0:
            raise ValueError(
                f"{label} must have a positive integer consultation fee."
            )

        days = appointment["days_since_created"]
        if type(days) is not int or not 0 <= days <= 30:
            raise ValueError(
                f"{label} must have integer days_since_created "
                "between 0 and 30."
            )

        follow_up = appointment["follow_up_required"]
        if type(follow_up) is not bool:
            raise ValueError(
                f"{label} must have a boolean follow_up_required value."
            )

    if len(record_ids) != len(set(record_ids)):
        raise ValueError("Every record_id must be unique.")

    category_counts = Counter(
        appointment["category"] for appointment in appointments
    )
    for category in CATEGORIES:
        if category_counts[category] < 3:
            raise ValueError(
                f"Category {category!r} must appear at least 3 times."
            )

    status_counts = Counter(
        appointment["status"] for appointment in appointments
    )
    for status in STATUSES:
        if status_counts[status] < 1:
            raise ValueError(
                f"Status {status!r} must appear at least once."
            )

    follow_up_count = sum(
        appointment["follow_up_required"]
        for appointment in appointments
    )
    follow_up_ratio = follow_up_count / len(appointments)

    if not 0.10 <= follow_up_ratio <= 0.30:
        raise ValueError(
            "The proportion of follow-up-required records must be "
            f"between 10% and 30%; found {follow_up_ratio:.1%}."
        )


def save_appointments(
    appointments: list[dict[str, Any]],
    output_path: Path = DEFAULT_OUTPUT,
) -> None:
    """Validate and save appointments as a JSON array."""

    validate_appointments(appointments)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(
            appointments,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")


def print_summary(appointments: list[dict[str, Any]]) -> None:
    """Print a human-readable dataset validation summary."""

    category_counts = Counter(
        appointment["category"] for appointment in appointments
    )
    status_counts = Counter(
        appointment["status"] for appointment in appointments
    )
    follow_up_count = sum(
        appointment["follow_up_required"]
        for appointment in appointments
    )

    print("\nDataset validation: PASSED")
    print(f"Total records: {len(appointments)}")

    print("\nCategory counts:")
    for category in CATEGORIES:
        print(f"  {category}: {category_counts[category]}")

    print("\nStatus counts:")
    for status in STATUSES:
        print(f"  {status}: {status_counts[status]}")

    print(
        "\nFollow-up required: "
        f"{follow_up_count}/{len(appointments)} "
        f"({follow_up_count / len(appointments):.1%})"
    )

    days = [
        appointment["days_since_created"]
        for appointment in appointments
    ]
    print(f"Days since created: minimum={min(days)}, maximum={max(days)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic Practo appointment dataset."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_RECORDS,
        help=f"Number of records (minimum {MIN_RECORDS}; default {DEFAULT_RECORDS}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed for reproducibility (default {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path.",
    )

    args = parser.parse_args()

    appointments = generate_appointments(
        count=args.count,
        seed=args.seed,
    )
    save_appointments(appointments, args.output)

    print_summary(appointments)
    print(f"\nSaved dataset to: {args.output.resolve()}")


if __name__ == "__main__":
    main()
