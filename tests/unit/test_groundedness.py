
import pytest

from practo_agent.rag.groundedness import (
    GroundednessValidationError,
    MockGroundednessValidator,
    create_groundedness_validator,
)
from practo_agent.schemas import RetrievedEvidence


@pytest.fixture
def evidence():
    return [
        RetrievedEvidence(
            chunk_id="booking::sentence::0001",
            text=(
                "Appointment requests remain pending until the clinic "
                "or booking system confirms the slot. Patients should "
                "retain their appointment reference."
            ),
            source_id="appointment_booking",
            title="Appointment Booking",
            distance=0.25,
        )
    ]


def test_factory_returns_mock_validator(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")

    validator = create_groundedness_validator()

    assert isinstance(validator, MockGroundednessValidator)


def test_accepts_exactly_supported_answer(evidence):
    validator = MockGroundednessValidator()

    result = validator.validate(
        "Appointment requests remain pending until the clinic "
        "or booking system confirms the slot.",
        evidence,
    )

    assert result.grounded is True
    assert len(result.claim_assessments) == 1
    assert result.claim_assessments[0].supported is True


def test_rejects_unsupported_claim(evidence):
    validator = MockGroundednessValidator()

    result = validator.validate(
        "Every appointment is automatically confirmed.",
        evidence,
    )

    assert result.grounded is False
    assert result.claim_assessments[0].supported is False


def test_rejects_answer_with_supported_and_unsupported_claims(evidence):
    validator = MockGroundednessValidator()

    result = validator.validate(
        "Patients should retain their appointment reference. "
        "Every appointment is automatically confirmed.",
        evidence,
    )

    assert result.grounded is False
    assert len(result.claim_assessments) == 2
    assert result.claim_assessments[0].supported is True
    assert result.claim_assessments[1].supported is False


def test_exact_matching_ignores_case_and_whitespace(evidence):
    validator = MockGroundednessValidator()

    result = validator.validate(
        "APPOINTMENT REQUESTS REMAIN PENDING UNTIL THE CLINIC "
        "OR BOOKING SYSTEM CONFIRMS THE SLOT.",
        evidence,
    )

    assert result.grounded is True


def test_rejects_empty_answer(evidence):
    validator = MockGroundednessValidator()

    with pytest.raises(ValueError, match="non-empty"):
        validator.validate("", evidence)


def test_rejects_empty_evidence():
    validator = MockGroundednessValidator()

    with pytest.raises(ValueError, match="evidence"):
        validator.validate("Some answer.", [])


def test_factory_does_not_require_groq_key(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    validator = create_groundedness_validator()

    assert isinstance(validator, MockGroundednessValidator)
