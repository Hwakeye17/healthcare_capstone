
import pytest

from practo_agent.rag.generator import (
    MockAnswerGenerator,
    create_answer_generator,
)
from practo_agent.schemas import (
    EvidenceAssessment,
    RetrievedEvidence,
    ResponseStatus,
)


@pytest.fixture
def accepted_assessment():
    evidence = [
        RetrievedEvidence(
            chunk_id="booking::sentence::0001",
            text=(
                "Appointment requests remain pending until the clinic "
                "or booking system confirms the slot."
            ),
            source_id="appointment_booking",
            title="Appointment Booking",
            distance=0.25,
        ),
        RetrievedEvidence(
            chunk_id="booking::sentence::0002",
            text=(
                "Patients should retain their appointment reference "
                "and review the confirmed date and time."
            ),
            source_id="appointment_booking",
            title="Appointment Booking",
            distance=0.30,
        ),
    ]

    return EvidenceAssessment(
        accepted=True,
        best_distance=0.25,
        threshold=0.331998,
        evidence=evidence,
        reason="Retrieved evidence passed the configured distance threshold.",
    )


@pytest.fixture
def rejected_assessment():
    return EvidenceAssessment(
        accepted=False,
        best_distance=0.75,
        threshold=0.331998,
        evidence=[
            RetrievedEvidence(
                chunk_id="booking::sentence::0001",
                text="Appointment requests require clinic confirmation.",
                source_id="appointment_booking",
                title="Appointment Booking",
                distance=0.75,
            )
        ],
        reason="Retrieved evidence did not pass the configured distance threshold.",
    )


def test_factory_returns_mock_generator():
    generator = create_answer_generator(mock_mode=True)

    assert isinstance(generator, MockAnswerGenerator)


def test_mock_generator_answers_using_accepted_evidence(
    accepted_assessment,
):
    generator = MockAnswerGenerator()

    response = generator.generate(
        "How are appointments confirmed?",
        accepted_assessment,
    )

    assert response.status == ResponseStatus.ANSWERED
    assert response.answer
    assert "pending" in response.answer.lower()
    assert len(response.sources) == 1
    assert response.sources[0].source_id == "appointment_booking"


def test_mock_generator_abstains_when_evidence_is_rejected(
    rejected_assessment,
):
    generator = MockAnswerGenerator()

    response = generator.generate(
        "What is the appointment process?",
        rejected_assessment,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert response.reason
    assert response.sources == []


def test_mock_generator_deduplicates_source_references(
    accepted_assessment,
):
    generator = MockAnswerGenerator()

    response = generator.generate(
        "How are appointments confirmed?",
        accepted_assessment,
    )

    assert len(response.sources) == 1


def test_mock_generator_rejects_empty_query(accepted_assessment):
    generator = MockAnswerGenerator()

    with pytest.raises(ValueError, match="non-empty"):
        generator.generate("", accepted_assessment)


def test_factory_does_not_require_groq_in_mock_mode(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("MOCK_LLM", "true")

    generator = create_answer_generator()

    assert isinstance(generator, MockAnswerGenerator)
