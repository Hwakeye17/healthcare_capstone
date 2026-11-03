
"""Loading and validation of labeled retrieval evaluation cases."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CASES_PATH = (
    PROJECT_ROOT / "evaluation" / "cases" / "retrieval_cases.json"
)

DEFAULT_KB_DIR = PROJECT_ROOT / "data" / "knowledge_base"

MINIMUM_CASE_COUNT = 25

REQUIRED_FIELDS = {
    "query_id",
    "query",
    "expected_relevant_sources",
}


@dataclass(frozen=True)
class EvaluationCase:
    """A labeled query used to evaluate document retrieval."""

    query_id: str
    query: str
    expected_relevant_sources: tuple[str, ...]


def _available_source_ids(kb_dir: Path) -> set[str]:
    """Return source identifiers derived from Markdown filenames."""

    if not kb_dir.exists() or not kb_dir.is_dir():
        raise ValueError(f"Knowledge-base directory does not exist: {kb_dir}")

    return {
        path.stem
        for path in kb_dir.glob("*.md")
        if path.is_file()
    }


def _validate_case(
    raw_case: Any,
    index: int,
    available_sources: set[str],
) -> EvaluationCase:
    """Validate and convert one raw JSON case into a typed case."""

    if not isinstance(raw_case, dict):
        raise ValueError(f"Case at index {index} must be a JSON object.")

    if set(raw_case.keys()) != REQUIRED_FIELDS:
        missing = REQUIRED_FIELDS - set(raw_case.keys())
        extra = set(raw_case.keys()) - REQUIRED_FIELDS

        raise ValueError(
            f"Case at index {index} has invalid fields. "
            f"Missing: {sorted(missing)}; extra: {sorted(extra)}"
        )

    query_id = raw_case["query_id"]
    query = raw_case["query"]
    sources = raw_case["expected_relevant_sources"]

    if not isinstance(query_id, str) or not query_id.strip():
        raise ValueError(
            f"Case at index {index} must have a non-empty query_id."
        )

    if not isinstance(query, str) or not query.strip():
        raise ValueError(
            f"Case {query_id!r} must have non-empty query text."
        )

    if not isinstance(sources, list) or not sources:
        raise ValueError(
            f"Case {query_id!r} must have at least one expected source."
        )

    if any(not isinstance(source, str) or not source.strip()
           for source in sources):
        raise ValueError(
            f"Case {query_id!r} contains an invalid source identifier."
        )

    if len(sources) != len(set(sources)):
        raise ValueError(
            f"Case {query_id!r} contains duplicate source identifiers."
        )

    unknown_sources = set(sources) - available_sources

    if unknown_sources:
        raise ValueError(
            f"Case {query_id!r} references unknown knowledge-base sources: "
            f"{sorted(unknown_sources)}"
        )

    return EvaluationCase(
        query_id=query_id.strip(),
        query=query.strip(),
        expected_relevant_sources=tuple(sources),
    )


def load_evaluation_cases(
    cases_path: Path = DEFAULT_CASES_PATH,
    kb_dir: Path = DEFAULT_KB_DIR,
) -> list[EvaluationCase]:
    """Load and validate all retrieval evaluation cases."""

    cases_path = Path(cases_path)
    kb_dir = Path(kb_dir)

    if not cases_path.exists() or not cases_path.is_file():
        raise ValueError(
            f"Evaluation cases file does not exist: {cases_path}"
        )

    try:
        with cases_path.open("r", encoding="utf-8") as file:
            raw_cases = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in evaluation cases file: {exc}"
        ) from exc

    if not isinstance(raw_cases, list):
        raise ValueError("Evaluation cases file must contain a JSON array.")

    if len(raw_cases) < MINIMUM_CASE_COUNT:
        raise ValueError(
            f"At least {MINIMUM_CASE_COUNT} evaluation cases are required; "
            f"found {len(raw_cases)}."
        )

    available_sources = _available_source_ids(kb_dir)

    cases = [
        _validate_case(raw_case, index, available_sources)
        for index, raw_case in enumerate(raw_cases)
    ]

    query_ids = [case.query_id for case in cases]

    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Evaluation query IDs must be unique.")

    return cases
