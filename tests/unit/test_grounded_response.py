
import pytest

from practo_agent.rag.groundedness import (
    generate_validated_response,
)
from practo_agent.schemas import (
    ClaimAssessment,
    EvidenceAssessment,
    GroundedResponse,
    GroundednessAssessment,
    ResponseStatus,
    RetrievedEvidence,
    SourceReference,
)


@pytest.fixture
def accepted_evidence():
    item = RetrievedEvidence(
        chunk_id="booking::sentence::0001",
        text="Patients should retain their appointment reference.",
        source_id="appointment_booking",
        title="Appointment Booking",
        distance=0.25,
    )

    return EvidenceAssessment(
        accepted=True,
        best_distance=0.25,
        threshold=0.331998,
        evidence=[item],
        reason="Evidence passed the configured threshold.",
    )


class FakeGenerator:
    def __init__(self, response):
        self.response = response
        self.called = False

    def generate(self, query, assessment):
        self.called = True
        return self.response


class FakeValidator:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.called = False

    def validate(self, answer, evidence):
        self.called = True

        if self.error:
            raise self.error

        return self.result


def answered_response():
    return GroundedResponse(
        status=ResponseStatus.ANSWERED,
        answer="Patients should retain their appointment reference.",
        sources=[
            SourceReference(
                source_id="appointment_booking",
                title="Appointment Booking",
            )
        ],
    )


def grounded_assessment():
    return GroundednessAssessment(
        grounded=True,
        reason="All claims are supported.",
        claim_assessments=[
            ClaimAssessment(
                claim="Patients should retain their appointment reference.",
                supported=True,
                explanation="The evidence explicitly states this.",
            )
        ],
    )


def unsupported_assessment():
    return GroundednessAssessment(
        grounded=False,
        reason="One claim is unsupported.",
        claim_assessments=[
            ClaimAssessment(
                claim="Every appointment is automatically confirmed.",
                supported=False,
                explanation="The evidence does not support this.",
            )
        ],
    )


def test_returns_answer_when_validation_passes(accepted_evidence):
    generator = FakeGenerator(answered_response())
    validator = FakeValidator(result=grounded_assessment())

    response = generate_validated_response(
        "What should patients retain?",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.status == ResponseStatus.ANSWERED
    assert response.sources
    assert generator.called
    assert validator.called


def test_abstains_when_claim_is_unsupported(accepted_evidence):
    generator = FakeGenerator(answered_response())
    validator = FakeValidator(result=unsupported_assessment())

    response = generate_validated_response(
        "What should patients retain?",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert response.sources == []
    assert response.reason


def test_abstains_when_validator_raises_error(accepted_evidence):
    generator = FakeGenerator(answered_response())
    validator = FakeValidator(error=RuntimeError("Verifier unavailable"))

    response = generate_validated_response(
        "What should patients retain?",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert response.sources == []
    assert response.reason == "Groundedness validation could not be completed."


def test_does_not_validate_generator_abstention(accepted_evidence):
    abstention = GroundedResponse(
        status=ResponseStatus.ABSTAINED,
        answer="I could not find sufficient information.",
        reason="Insufficient evidence.",
        sources=[],
    )

    generator = FakeGenerator(abstention)
    validator = FakeValidator(result=grounded_assessment())

    response = generate_validated_response(
        "An unsupported question",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert generator.called
    assert not validator.called


def test_validation_failure_never_returns_original_answer(accepted_evidence):
    original = answered_response()
    generator = FakeGenerator(original)
    validator = FakeValidator(error=ValueError("Invalid verifier output"))

    response = generate_validated_response(
        "What should patients retain?",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert response.answer != original.answer


def test_sources_are_removed_when_validation_fails(accepted_evidence):
    generator = FakeGenerator(answered_response())
    validator = FakeValidator(result=unsupported_assessment())

    response = generate_validated_response(
        "What should patients retain?",
        accepted_evidence,
        generator,
        validator,
    )

    assert response.sources == []
