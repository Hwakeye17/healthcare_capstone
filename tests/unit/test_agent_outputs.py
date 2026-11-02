
"""Tests for structured CrewAI agent output contracts."""

import pytest
from pydantic import ValidationError

from practo_agent.schemas import (
    AgentResponse,
    AppointmentDetails,
    AppointmentReference,
    EvidenceAssessment,
    LookupAgentOutput,
    LookupAgentStatus,
    ResponseStatus,
    RetrievedEvidence,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
    SourceReference,
)


@pytest.fixture
def accepted_assessment():
    evidence = RetrievedEvidence(
        chunk_id="fee_structure::sentence::0001",
        text="The consultation fee is INR 500.",
        source_id="fee_structure",
        title="Fee Structure",
        distance=0.20,
    )

    return EvidenceAssessment(
        accepted=True,
        best_distance=0.20,
        threshold=0.331998,
        evidence=[evidence],
        reason="Relevant evidence found.",
    )


@pytest.fixture
def rejected_assessment():
    return EvidenceAssessment(
        accepted=False,
        best_distance=None,
        threshold=0.331998,
        evidence=[],
        reason="No usable evidence was retrieved.",
    )


@pytest.fixture
def appointment():
    return AppointmentDetails(
        record_id="APT-0001",
        status="Cancelled",
        consultation_fee_inr=500,
        escalation_score=0.0667,
    )


# -------------------------------------------------------------------
# AppointmentDetails
# -------------------------------------------------------------------

def test_appointment_details_accepts_valid_data(appointment):
    assert appointment.record_id == "APT-0001"
    assert appointment.consultation_fee_inr == 500
    assert appointment.escalation_score == 0.0667


@pytest.mark.parametrize(
    "overrides",
    [
        {"record_id": ""},
        {"status": ""},
        {"consultation_fee_inr": -1},
        {"escalation_score": -0.1},
        {"escalation_score": 1.1},
        {"unexpected": "value"},
    ],
)
def test_appointment_details_rejects_invalid_data(overrides):
    data = {
        "record_id": "APT-0001",
        "status": "Cancelled",
        "consultation_fee_inr": 500,
        "escalation_score": 0.5,
    }
    data.update(overrides)

    with pytest.raises(ValidationError):
        AppointmentDetails(**data)


# -------------------------------------------------------------------
# RetrievalAgentOutput
# -------------------------------------------------------------------

def test_retrieval_output_accepts_success(accepted_assessment):
    output = RetrievalAgentOutput(
        used=True,
        status=RetrievalAgentStatus.SUCCESS,
        assessment=accepted_assessment,
    )

    assert output.status == RetrievalAgentStatus.SUCCESS
    assert output.assessment.accepted is True


def test_retrieval_output_accepts_not_needed():
    output = RetrievalAgentOutput(
        used=False,
        status=RetrievalAgentStatus.NOT_NEEDED,
    )

    assert output.used is False
    assert output.assessment is None


def test_retrieval_output_accepts_no_evidence(rejected_assessment):
    output = RetrievalAgentOutput(
        used=True,
        status=RetrievalAgentStatus.NO_EVIDENCE,
        assessment=rejected_assessment,
        reason="The knowledge base did not contain sufficient evidence.",
    )

    assert output.status == RetrievalAgentStatus.NO_EVIDENCE


def test_retrieval_output_accepts_error():
    output = RetrievalAgentOutput(
        used=True,
        status=RetrievalAgentStatus.ERROR,
        reason="Vector store unavailable.",
    )

    assert output.status == RetrievalAgentStatus.ERROR


def test_retrieval_success_requires_assessment():
    with pytest.raises(ValidationError):
        RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.SUCCESS,
        )


def test_retrieval_success_requires_accepted_assessment(rejected_assessment):
    with pytest.raises(ValidationError):
        RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.SUCCESS,
            assessment=rejected_assessment,
        )


def test_retrieval_not_needed_rejects_used_true():
    with pytest.raises(ValidationError):
        RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.NOT_NEEDED,
        )


def test_retrieval_no_evidence_requires_reason(rejected_assessment):
    with pytest.raises(ValidationError):
        RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.NO_EVIDENCE,
            assessment=rejected_assessment,
        )


def test_retrieval_error_requires_reason():
    with pytest.raises(ValidationError):
        RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.ERROR,
        )


# -------------------------------------------------------------------
# LookupAgentOutput
# -------------------------------------------------------------------

def test_lookup_output_accepts_success(appointment):
    output = LookupAgentOutput(
        used=True,
        status=LookupAgentStatus.SUCCESS,
        record_id="APT-0001",
        appointment=appointment,
    )

    assert output.appointment.status == "Cancelled"


def test_lookup_output_accepts_not_found():
    output = LookupAgentOutput(
        used=True,
        status=LookupAgentStatus.NOT_FOUND,
        record_id="UNKNOWN-ID",
        reason="Appointment record not found.",
    )

    assert output.appointment is None
    assert output.status == LookupAgentStatus.NOT_FOUND


def test_lookup_output_accepts_not_needed():
    output = LookupAgentOutput(
        used=False,
        status=LookupAgentStatus.NOT_NEEDED,
    )

    assert output.used is False
    assert output.record_id is None


def test_lookup_output_accepts_error():
    output = LookupAgentOutput(
        used=True,
        status=LookupAgentStatus.ERROR,
        record_id="APT-0001",
        reason="Appointment dataset unavailable.",
    )

    assert output.status == LookupAgentStatus.ERROR


def test_lookup_success_requires_appointment():
    with pytest.raises(ValidationError):
        LookupAgentOutput(
            used=True,
            status=LookupAgentStatus.SUCCESS,
            record_id="APT-0001",
        )


def test_lookup_success_requires_matching_record_id(appointment):
    with pytest.raises(ValidationError):
        LookupAgentOutput(
            used=True,
            status=LookupAgentStatus.SUCCESS,
            record_id="APT-0002",
            appointment=appointment,
        )


def test_lookup_not_found_rejects_appointment(appointment):
    with pytest.raises(ValidationError):
        LookupAgentOutput(
            used=True,
            status=LookupAgentStatus.NOT_FOUND,
            record_id="APT-0001",
            appointment=appointment,
            reason="Record not found.",
        )


def test_lookup_not_found_requires_reason():
    with pytest.raises(ValidationError):
        LookupAgentOutput(
            used=True,
            status=LookupAgentStatus.NOT_FOUND,
            record_id="UNKNOWN-ID",
        )


def test_lookup_not_needed_rejects_appointment(appointment):
    with pytest.raises(ValidationError):
        LookupAgentOutput(
            used=False,
            status=LookupAgentStatus.NOT_NEEDED,
            appointment=appointment,
        )


# -------------------------------------------------------------------
# AgentResponse
# -------------------------------------------------------------------

def test_agent_response_accepts_kb_source():
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer="The consultation fee is INR 500.",
        sources=[
            SourceReference(
                source_id="fee_structure",
                title="Fee Structure",
            )
        ],
    )

    assert response.status == ResponseStatus.ANSWERED
    assert len(response.sources) == 1


def test_agent_response_accepts_appointment_reference():
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer="Appointment APT-0001 is cancelled.",
        appointments=[
            AppointmentReference(record_id="APT-0001")
        ],
    )

    assert len(response.appointments) == 1


def test_agent_response_accepts_both_reference_types():
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer="The appointment is cancelled. The applicable fee is INR 500.",
        sources=[
            SourceReference(
                source_id="fee_structure",
                title="Fee Structure",
            )
        ],
        appointments=[
            AppointmentReference(record_id="APT-0001")
        ],
    )

    assert response.sources
    assert response.appointments


def test_agent_response_rejects_answer_without_references():
    with pytest.raises(ValidationError):
        AgentResponse(
            status=ResponseStatus.ANSWERED,
            answer="This answer has no supporting reference.",
        )


def test_agent_response_accepts_abstention():
    response = AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer="I cannot confirm this information.",
        reason="The available information is insufficient.",
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert not response.sources
    assert not response.appointments


def test_agent_response_abstention_requires_reason():
    with pytest.raises(ValidationError):
        AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer="I cannot confirm this information.",
        )


def test_agent_response_abstention_rejects_references():
    with pytest.raises(ValidationError):
        AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer="I cannot confirm this information.",
            reason="Insufficient evidence.",
            appointments=[
                AppointmentReference(record_id="APT-0001")
            ],
        )


def test_agent_response_rejects_empty_answer():
    with pytest.raises(ValidationError):
        AgentResponse(
            status=ResponseStatus.ANSWERED,
            answer="",
            appointments=[
                AppointmentReference(record_id="APT-0001")
            ],
        )


def test_agent_response_rejects_answer_with_abstention_reason():
    with pytest.raises(ValidationError):
        AgentResponse(
            status=ResponseStatus.ANSWERED,
            answer="Appointment APT-0001 is cancelled.",
            reason="No reason should be present for an answered response.",
            appointments=[
                AppointmentReference(record_id="APT-0001")
            ],
        )
