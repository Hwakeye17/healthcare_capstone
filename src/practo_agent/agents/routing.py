"""Deterministic routing for Practo administrative support queries."""

import re
from dataclasses import dataclass


_RECORD_ID_PATTERN = re.compile(r"\b[A-Z]{3,5}-\d{4}\b", re.IGNORECASE)
_POLICY_TERMS = (
    "book",
    "booking",
    "cancel",
    "cancellation",
    "reschedul",
    "fee",
    "fees",
    "price",
    "cost",
    "insurance",
    "claim",
    "prescription",
    "refill",
    "lab",
    "test result",
    "telemedicine",
    "video consultation",
    "emergency",
    "privacy",
    "data",
    "follow-up",
    "follow up",
    "second opinion",
    "home visit",
    "policy",
)


@dataclass(frozen=True)
class QueryRoute:
    """The specialist tasks selected for one user query."""

    retrieval_enabled: bool
    lookup_enabled: bool
    record_id: str | None = None
    clarification_required: bool = False


def route_query(query: str) -> QueryRoute:
    """Select specialist capabilities without delegating routing to an LLM."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    normalized_query = query.casefold()
    record_ids = [
        match.upper()
        for match in _RECORD_ID_PATTERN.findall(query)
    ]

    if len(record_ids) > 1:
        return QueryRoute(
            retrieval_enabled=False,
            lookup_enabled=False,
            clarification_required=True,
        )

    needs_retrieval = any(
        term in normalized_query
        for term in _POLICY_TERMS
    )

    if record_ids:
        return QueryRoute(
            retrieval_enabled=needs_retrieval,
            lookup_enabled=True,
            record_id=record_ids[0],
        )

    # Route other questions through calibrated retrieval so unsupported
    # requests can receive the evidence-based abstention response.
    return QueryRoute(
        retrieval_enabled=True,
        lookup_enabled=False,
    )
