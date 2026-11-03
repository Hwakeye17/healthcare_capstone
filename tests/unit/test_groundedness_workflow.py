from types import SimpleNamespace

from practo_agent.agents import workflow
from practo_agent.rag.groundedness import MockGroundednessValidator
from practo_agent.schemas import (
    AgentResponse,
    AppointmentDetails,
    AppointmentReference,
    EvidenceAssessment,
    LookupAgentOutput,
    LookupAgentStatus,
    ResponseStatus,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
    RetrievedEvidence,
    SourceReference,
)


_BOOKING_EVIDENCE = RetrievedEvidence(
    chunk_id="appointment_booking::sentence::0001",
    text=(
        "Appointment requests remain pending until the clinic or booking "
        "system confirms the slot."
    ),
    source_id="appointment_booking",
    title="Appointment Booking",
    distance=0.25,
)


def _retrieval_output():
    assessment = EvidenceAssessment(
        accepted=True,
        best_distance=0.25,
        threshold=0.6976266205310822,
        evidence=[_BOOKING_EVIDENCE],
        reason="Evidence passed the configured threshold.",
    )
    return RetrievalAgentOutput(
        used=True,
        status=RetrievalAgentStatus.SUCCESS,
        assessment=assessment,
    )


def _run_with_crew_output(
    monkeypatch,
    *,
    query,
    response,
    specialist_role,
    specialist_output,
    validator=None,
):
    specialist_task = SimpleNamespace(
        agent=SimpleNamespace(role=specialist_role),
    )
    composition_task = SimpleNamespace(
        agent=SimpleNamespace(role="Practo Support Response Composer"),
    )
    tasks = [specialist_task, composition_task]

    class FakeCrew:
        def kickoff(self, inputs):
            return SimpleNamespace(
                tasks_output=[
                    SimpleNamespace(raw=specialist_output.model_dump_json()),
                    SimpleNamespace(raw=response.model_dump_json()),
                ],
                raw=response.model_dump_json(),
            )

    monkeypatch.setattr(
        workflow,
        "create_practo_crew",
        lambda **kwargs: SimpleNamespace(tasks=tasks, kickoff=FakeCrew().kickoff),
    )

    return workflow.run_practo_query(
        query,
        groundedness_validator=(
            validator
            if validator is not None
            else MockGroundednessValidator()
        ),
    )


def test_accepted_retrieval_claim_passes_groundedness_validation(monkeypatch):
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=(
            "According to Appointment Booking: Appointment requests remain "
            "pending until the clinic or booking system confirms the slot."
        ),
        sources=[
            SourceReference(
                source_id="appointment_booking",
                title="Appointment Booking",
            )
        ],
    )

    result = _run_with_crew_output(
        monkeypatch,
        query="When is an appointment confirmed?",
        response=response,
        specialist_role="Practo Knowledge Retrieval Specialist",
        specialist_output=_retrieval_output(),
    )

    assert result.status == ResponseStatus.ANSWERED
    assert result.sources == response.sources


def test_unsupported_claim_is_rejected_and_references_are_removed(monkeypatch):
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer="Every appointment is automatically confirmed.",
        sources=[
            SourceReference(
                source_id="appointment_booking",
                title="Appointment Booking",
            )
        ],
    )

    result = _run_with_crew_output(
        monkeypatch,
        query="When is an appointment confirmed?",
        response=response,
        specialist_role="Practo Knowledge Retrieval Specialist",
        specialist_output=_retrieval_output(),
    )

    assert result.status == ResponseStatus.ABSTAINED
    assert result.sources == []
    assert result.appointments == []
    assert "unsupported claims" in result.reason
    assert result.answer != response.answer


def test_validated_lookup_fields_are_used_as_grounding_evidence(monkeypatch):
    appointment = AppointmentDetails(
        record_id="APT-0001",
        specialty="General Medicine",
        status="confirmed",
        consultation_fee_inr=500,
        days_since_created=24,
        follow_up_required=True,
        escalation_score=0.92,
        escalation_required=True,
        escalation_reason="The record meets the administrative threshold.",
    )
    lookup_output = LookupAgentOutput(
        used=True,
        status=LookupAgentStatus.SUCCESS,
        record_id=appointment.record_id,
        appointment=appointment,
    )
    answer = (
        "Appointment APT-0001 is in specialty General Medicine with status "
        "confirmed. The consultation fee is INR 500. The record is 24 days "
        "old and its follow-up-required flag is True. Its administrative "
        "escalation score is 0.9200; escalation required: True. The record "
        "meets the administrative threshold."
    )
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=answer,
        appointments=[AppointmentReference(record_id="APT-0001")],
    )

    result = _run_with_crew_output(
        monkeypatch,
        query="What is the status of APT-0001?",
        response=response,
        specialist_role="Practo Appointment Lookup Specialist",
        specialist_output=lookup_output,
    )

    assert result.status == ResponseStatus.ANSWERED
    assert result.appointments == response.appointments


def test_unretrieved_source_citation_is_rejected_before_validation(monkeypatch):
    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=(
            "Appointment requests remain pending until the clinic or booking "
            "system confirms the slot."
        ),
        sources=[
            SourceReference(
                source_id="unretrieved_source",
                title="Unretrieved source",
            )
        ],
    )

    result = _run_with_crew_output(
        monkeypatch,
        query="When is an appointment confirmed?",
        response=response,
        specialist_role="Practo Knowledge Retrieval Specialist",
        specialist_output=_retrieval_output(),
    )

    assert result.status == ResponseStatus.ABSTAINED
    assert result.sources == []
    assert "not present in the validated retrieval results" in result.reason


def test_validator_error_fails_closed(monkeypatch):
    class FailingValidator:
        def validate(self, answer, evidence):
            raise RuntimeError("Internal validator detail.")

    response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=(
            "Appointment requests remain pending until the clinic or booking "
            "system confirms the slot."
        ),
        sources=[
            SourceReference(
                source_id="appointment_booking",
                title="Appointment Booking",
            )
        ],
    )

    result = _run_with_crew_output(
        monkeypatch,
        query="When is an appointment confirmed?",
        response=response,
        specialist_role="Practo Knowledge Retrieval Specialist",
        specialist_output=_retrieval_output(),
        validator=FailingValidator(),
    )

    assert result.status == ResponseStatus.ABSTAINED
    assert result.sources == []
    assert result.reason == "Groundedness validation could not be completed."
    assert "Internal validator detail." not in result.answer
