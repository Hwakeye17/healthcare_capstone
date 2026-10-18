
"""Validate required Practo capstone knowledge-base documents."""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KB_DIR = PROJECT_ROOT / "data" / "knowledge_base"

REQUIRED_DOCUMENTS = {
    "appointment_booking.md",
    "cancellation_rescheduling.md",
    "fee_structure.md",
    "insurance_claims.md",
    "prescription_refills.md",
    "lab_turnaround.md",
    "telemedicine.md",
    "emergency_visits.md",
    "privacy_policy.md",
    "follow_up_discounts.md",
    "second_opinions.md",
    "home_visits.md",
}


def count_sentences(markdown_text: str) -> int:
    """Count sentences after excluding Markdown headings."""

    body_lines = [
        line
        for line in markdown_text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    body = "\n".join(body_lines).strip()

    return len(re.findall(r"[^.!?]+[.!?]+", body))


def validate_knowledge_base(
    kb_dir: Path = DEFAULT_KB_DIR,
) -> dict[str, int]:
    """Validate required files and minimum sentence count.

    Returns a mapping of filename to sentence count.
    Raises ValueError when requirements are not satisfied.
    """

    if not kb_dir.is_dir():
        raise ValueError(f"Knowledge-base directory does not exist: {kb_dir}")

    actual_documents = {
        path.name
        for path in kb_dir.glob("*.md")
        if path.is_file()
    }

    missing = REQUIRED_DOCUMENTS - actual_documents
    if missing:
        raise ValueError(
            "Missing required knowledge-base documents: "
            + ", ".join(sorted(missing))
        )

    sentence_counts = {}
    errors = []

    for filename in sorted(REQUIRED_DOCUMENTS):
        path = kb_dir / filename
        text = path.read_text(encoding="utf-8").strip()

        if not text:
            errors.append(f"{filename}: document is empty.")
            continue

        sentence_count = count_sentences(text)
        sentence_counts[filename] = sentence_count

        if sentence_count < 2:
            errors.append(
                f"{filename}: expected at least 2 sentences, "
                f"found {sentence_count}."
            )

    if errors:
        raise ValueError("\n".join(errors))

    return sentence_counts


def main() -> None:
    sentence_counts = validate_knowledge_base()

    print("Knowledge-base validation: PASSED")
    print(f"Required documents validated: {len(sentence_counts)}")

    for filename, count in sentence_counts.items():
        print(f"  {filename}: {count} sentences")


if __name__ == "__main__":
    main()
