"""Validate retrieved knowledge-base evidence before answer generation."""

from typing import Protocol

from practo_agent.config import (
    DEFAULT_GROUNDING_CONFIG,
    DEFAULT_RETRIEVAL_CONFIG,
    GroundingConfig,
    RetrievalConfig,
)
from practo_agent.rag.retriever import retrieve
from practo_agent.schemas import (
    EvidenceAssessment,
    RetrievedEvidence,
)


class EvidenceStore(Protocol):
    """Minimum vector-store interface required by evidence validation."""

    strategy: str

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        ...


def assess_evidence(
    store: EvidenceStore,
    query: str,
    *,
    retrieval_config: RetrievalConfig = DEFAULT_RETRIEVAL_CONFIG,
    grounding_config: GroundingConfig = DEFAULT_GROUNDING_CONFIG,
) -> EvidenceAssessment:
    """Retrieve evidence and decide whether it passes the calibrated threshold."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    chunks = retrieve(
        store,
        query,
        config=retrieval_config,
    )

    evidence = []

    for index, chunk in enumerate(chunks):
        distance = chunk.get("distance")

        if distance is None:
            continue

        metadata = chunk.get("metadata") or {}
        source_id = metadata.get("source_id")
        title = metadata.get("title")

        if not source_id:
            raise ValueError(
                f"Retrieved chunk at index {index} has no source_id metadata."
            )

        if not title:
            raise ValueError(
                f"Retrieved chunk at index {index} has no title metadata."
            )

        evidence.append(
            RetrievedEvidence(
                chunk_id=str(chunk.get("chunk_id") or f"retrieved-{index}"),
                text=chunk.get("text", ""),
                source_id=source_id,
                title=title,
                distance=distance,
            )
        )

    if not evidence:
        return EvidenceAssessment(
            accepted=False,
            best_distance=None,
            threshold=grounding_config.abstention_threshold,
            evidence=[],
            reason="No usable evidence was retrieved from the knowledge base.",
        )

    best_distance = min(item.distance for item in evidence)
    accepted = best_distance <= grounding_config.abstention_threshold

    if accepted:
        reason = "Retrieved evidence passed the configured distance threshold."
    else:
        reason = (
            "Retrieved evidence did not pass the configured distance threshold."
        )

    return EvidenceAssessment(
        accepted=accepted,
        best_distance=best_distance,
        threshold=grounding_config.abstention_threshold,
        evidence=evidence,
        reason=reason,
    )