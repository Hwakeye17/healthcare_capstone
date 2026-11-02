import pytest
from pydantic import ValidationError

from practo_agent.schemas import (
    GroundedResponse,
    ResponseStatus,
    SourceReference,
)


def test_valid_answered_response():
    response = GroundedResponse(
        status=ResponseStatus.ANSWERED,
        answer="You can reschedule your appointment through the booking section.",
        sources=[
            SourceReference(
                source_id="cancellation_rescheduling",
                title="Cancellation and Rescheduling",
            )
        ],
    )

    assert response.status == ResponseStatus.ANSWERED
    assert len(response.sources) == 1
    assert response.reason is None


def test_valid_abstained_response():
    response = GroundedResponse(
        status=ResponseStatus.ABSTAINED,
        answer="I cannot provide a diagnosis or recommend medication.",
        reason="Medical diagnosis and treatment are outside the agent's scope.",
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert response.sources == []
    assert response.reason is not None


def test_answered_response_requires_sources():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ANSWERED,
            answer="Your appointment can be rescheduled.",
        )


def test_answered_response_rejects_empty_answer():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ANSWERED,
            answer="   ",
            sources=[
                SourceReference(
                    source_id="appointment_booking",
                    title="Appointment Booking",
                )
            ],
        )


def test_abstained_response_requires_reason():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ABSTAINED,
            answer="I cannot answer that question.",
        )


def test_abstained_response_rejects_sources():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ABSTAINED,
            answer="I cannot answer that question.",
            reason="The question is outside the supported scope.",
            sources=[
                SourceReference(
                    source_id="appointment_booking",
                    title="Appointment Booking",
                )
            ],
        )


def test_answered_response_rejects_abstention_reason():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ANSWERED,
            answer="You can book an appointment online.",
            reason="Insufficient evidence.",
            sources=[
                SourceReference(
                    source_id="appointment_booking",
                    title="Appointment Booking",
                )
            ],
        )


def test_source_reference_rejects_empty_source_id():
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="",
            title="Appointment Booking",
        )


def test_response_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        GroundedResponse(
            status=ResponseStatus.ABSTAINED,
            answer="I cannot answer that.",
            reason="Outside supported scope.",
            unexpected_field="not allowed",
        )