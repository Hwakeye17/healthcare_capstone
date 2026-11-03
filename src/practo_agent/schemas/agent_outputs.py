
"""Structured output contracts for the Practo CrewAI agents."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from practo_agent.schemas.evidence import EvidenceAssessment
from practo_agent.schemas.response import ResponseStatus, SourceReference


class RetrievalAgentStatus(str, Enum):
    """Possible outcomes of the Retrieval Agent."""

    SUCCESS = "success"
    NOT_NEEDED = "not_needed"
    NO_EVIDENCE = "no_evidence"
    ERROR = "error"


class LookupAgentStatus(str, Enum):
    """Possible outcomes of the Lookup Agent."""

    SUCCESS = "success"
    NOT_NEEDED = "not_needed"
    NOT_FOUND = "not_found"
    ERROR = "error"


class AppointmentDetails(BaseModel):
    """Validated appointment information returned by the lookup tool."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    record_id: str = Field(min_length=1)
    specialty: str = Field(min_length=1)
    status: str = Field(min_length=1)
    consultation_fee_inr: int = Field(ge=0)
    days_since_created: int = Field(ge=0, le=30)
    follow_up_required: bool
    escalation_score: float = Field(ge=0.0, le=1.0)
    escalation_required: bool
    escalation_reason: str = Field(min_length=1)


class RetrievalAgentOutput(BaseModel):
    """Structured handoff produced by the Retrieval Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    used: bool
    status: RetrievalAgentStatus
    assessment: EvidenceAssessment | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_retrieval_output(self):
        if self.status == RetrievalAgentStatus.SUCCESS:
            if not self.used or self.assessment is None:
                raise ValueError(
                    "Successful retrieval requires used=True and an assessment."
                )

            if not self.assessment.accepted:
                raise ValueError(
                    "Successful retrieval requires an accepted evidence assessment."
                )

            if self.reason is not None:
                raise ValueError(
                    "Successful retrieval must not contain a failure reason."
                )

        elif self.status == RetrievalAgentStatus.NO_EVIDENCE:
            if not self.used or self.assessment is None:
                raise ValueError(
                    "No-evidence results require used=True and an assessment."
                )

            if self.assessment.accepted:
                raise ValueError(
                    "A no-evidence result cannot contain accepted evidence."
                )

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "A no-evidence result must explain why evidence was insufficient."
                )

        elif self.status == RetrievalAgentStatus.NOT_NEEDED:
            if self.used or self.assessment is not None:
                raise ValueError(
                    "A retrieval operation that was not needed must not "
                    "contain an assessment."
                )

            if self.reason is not None:
                raise ValueError(
                    "A not-needed retrieval result must not contain an error reason."
                )

        elif self.status == RetrievalAgentStatus.ERROR:
            if not self.used:
                raise ValueError(
                    "A retrieval error requires used=True."
                )

            if self.assessment is not None:
                raise ValueError(
                    "A retrieval error must not contain a successful assessment."
                )

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "A retrieval error must explain what went wrong."
                )

        return self


class LookupAgentOutput(BaseModel):
    """Structured handoff produced by the Lookup Agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    used: bool
    status: LookupAgentStatus
    record_id: str | None = None
    appointment: AppointmentDetails | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_lookup_output(self):
        if self.status == LookupAgentStatus.SUCCESS:
            if not self.used or self.appointment is None:
                raise ValueError(
                    "Successful lookup requires used=True and appointment details."
                )

            if self.record_id != self.appointment.record_id:
                raise ValueError(
                    "record_id must match the returned appointment record ID."
                )

            if self.reason is not None:
                raise ValueError(
                    "Successful lookup must not contain a failure reason."
                )

        elif self.status == LookupAgentStatus.NOT_FOUND:
            if not self.used or not self.record_id:
                raise ValueError(
                    "Not-found results require used=True and a record ID."
                )

            if self.appointment is not None:
                raise ValueError(
                    "A not-found result must not contain appointment details."
                )

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "A not-found result must explain that the record was not found."
                )

        elif self.status == LookupAgentStatus.NOT_NEEDED:
            if self.used:
                raise ValueError(
                    "A lookup operation that was not needed must have used=False."
                )

            if self.record_id is not None or self.appointment is not None:
                raise ValueError(
                    "A not-needed lookup must not contain appointment details."
                )

            if self.reason is not None:
                raise ValueError(
                    "A not-needed lookup must not contain an error reason."
                )

        elif self.status == LookupAgentStatus.ERROR:
            if not self.used:
                raise ValueError(
                    "A lookup error requires used=True."
                )

            if self.appointment is not None:
                raise ValueError(
                    "A lookup error must not contain appointment details."
                )

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "A lookup error must explain what went wrong."
                )

        return self


class AppointmentReference(BaseModel):
    """Reference to an appointment record used in a final response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)


class AgentResponse(BaseModel):
    """Structured final response produced by the Response Composer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ResponseStatus
    answer: str = Field(min_length=1)
    reason: str | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    appointments: list[AppointmentReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_agent_response(self):
        if self.status == ResponseStatus.ANSWERED:
            if not self.answer.strip():
                raise ValueError(
                    "An answered response must contain a non-empty answer."
                )

            if not self.sources and not self.appointments:
                raise ValueError(
                    "An answered response must reference at least one "
                    "knowledge-base source or appointment record."
                )

            if self.reason is not None:
                raise ValueError(
                    "An answered response must not contain an abstention reason."
                )

        elif self.status == ResponseStatus.ABSTAINED:
            if not self.answer.strip():
                raise ValueError(
                    "An abstained response must contain a message."
                )

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "An abstained response must explain why it abstained."
                )

            if self.sources or self.appointments:
                raise ValueError(
                    "An abstained response must not claim supporting references."
                )

        return self
