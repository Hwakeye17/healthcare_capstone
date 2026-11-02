import pytest
from pydantic import ValidationError

from practo_agent.config import GroundingConfig, RetrievalConfig
from practo_agent.rag.evidence import assess_evidence
from practo_agent.schemas import EvidenceAssessment


class FakeVectorStore:
    def __init__(self, responses, strategy="sentence"):
        self.responses = responses
        self.strategy = strategy
        self.last_query = None
        self.last_top_k = None

    def search(self, query, top_k=3):
        self.last_query = query
        self.last_top_k = top_k
        return self.responses.get(query, [])[:top_k]


def make_chunk(
    distance,
    source_id="appointment_booking",
    title="Appointment Booking",
    text="Appointments can be booked through the booking section.",
):
    return {
        "chunk_id": f"chunk-{distance}",
        "text": text,
        "metadata": {
            "source_id": source_id,
            "title": title,
        },
        "distance": distance,
    }


def test_accepts_evidence_below_threshold():
    store = FakeVectorStore({
        "How can I book?": [
            make_chunk(0.25),
            make_chunk(0.31),
        ]
    })

    assessment = assess_evidence(store, "How can I book?")

    assert assessment.accepted is True
    assert assessment.best_distance == 0.25
    assert assessment.threshold == 0.331998348236084
    assert len(assessment.evidence) == 2


def test_accepts_evidence_exactly_at_threshold():
    store = FakeVectorStore({
        "How can I book?": [
            make_chunk(0.331998),
        ]
    })

    assessment = assess_evidence(store, "How can I book?")

    assert assessment.accepted is True


def test_rejects_evidence_above_threshold():
    store = FakeVectorStore({
        "Diagnose my rash": [
            make_chunk(0.761802),
        ]
    })

    assessment = assess_evidence(store, "Diagnose my rash")

    assert assessment.accepted is False
    assert assessment.best_distance == 0.761802
    assert len(assessment.evidence) == 1


def test_rejects_when_no_chunks_are_retrieved():
    store = FakeVectorStore({})

    assessment = assess_evidence(store, "Unknown question")

    assert assessment.accepted is False
    assert assessment.best_distance is None
    assert assessment.evidence == []


def test_rejects_chunks_without_distances():
    store = FakeVectorStore({
        "Question": [
            {
                "chunk_id": "chunk-1",
                "text": "Some text",
                "metadata": {
                    "source_id": "appointment_booking",
                    "title": "Appointment Booking",
                },
                "distance": None,
            }
        ]
    })

    assessment = assess_evidence(store, "Question")

    assert assessment.accepted is False
    assert assessment.best_distance is None


def test_uses_configured_top_k():
    store = FakeVectorStore({
        "Question": [
            make_chunk(0.2),
            make_chunk(0.3),
            make_chunk(0.4),
        ]
    })

    config = RetrievalConfig(strategy="sentence", top_k=2)

    assessment = assess_evidence(
        store,
        "Question",
        retrieval_config=config,
    )

    assert store.last_top_k == 2
    assert len(assessment.evidence) == 2


def test_uses_custom_grounding_threshold():
    store = FakeVectorStore({
        "Question": [make_chunk(0.4)]
    })

    assessment = assess_evidence(
        store,
        "Question",
        grounding_config=GroundingConfig(abstention_threshold=0.5),
    )

    assert assessment.accepted is True
    assert assessment.threshold == 0.5


def test_rejects_mismatched_retrieval_strategy():
    store = FakeVectorStore(
        {"Question": [make_chunk(0.2)]},
        strategy="fixed_size",
    )

    with pytest.raises(ValueError, match="supplied store"):
        assess_evidence(
            store,
            "Question",
            retrieval_config=RetrievalConfig(strategy="sentence"),
        )


def test_rejects_empty_query():
    store = FakeVectorStore({})

    with pytest.raises(ValueError, match="non-empty"):
        assess_evidence(store, "   ")


def test_rejects_chunk_without_source_id():
    store = FakeVectorStore({
        "Question": [
            {
                "chunk_id": "chunk-1",
                "text": "Some text",
                "metadata": {"title": "Appointment Booking"},
                "distance": 0.2,
            }
        ]
    })

    with pytest.raises(ValueError, match="source_id"):
        assess_evidence(store, "Question")


def test_rejects_chunk_without_title():
    store = FakeVectorStore({
        "Question": [
            {
                "chunk_id": "chunk-1",
                "text": "Some text",
                "metadata": {"source_id": "appointment_booking"},
                "distance": 0.2,
            }
        ]
    })

    with pytest.raises(ValueError, match="title"):
        assess_evidence(store, "Question")


def test_evidence_assessment_rejects_inconsistent_decision():
    with pytest.raises(ValidationError):
        EvidenceAssessment(
            accepted=True,
            best_distance=0.8,
            threshold=0.331998,
            evidence=[{
                "chunk_id": "chunk-1",
                "text": "Some text",
                "source_id": "appointment_booking",
                "title": "Appointment Booking",
                "distance": 0.8,
            }],
            reason="Accepted",
        )