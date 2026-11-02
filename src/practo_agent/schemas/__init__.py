
"""Structured schemas used throughout the Practo support agent."""

from practo_agent.schemas.evidence import (
    EvidenceAssessment,
    RetrievedEvidence,
)
from practo_agent.schemas.response import (
    GroundedResponse,
    ResponseStatus,
    SourceReference,
)
from practo_agent.schemas.grounding import (
    ClaimAssessment,
    GroundednessAssessment,
)
from practo_agent.schemas.agent_outputs import (
    AgentResponse,
    AppointmentDetails,
    AppointmentReference,
    LookupAgentOutput,
    LookupAgentStatus,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
)

__all__ = [
    "EvidenceAssessment",
    "RetrievedEvidence",
    "GroundedResponse",
    "ResponseStatus",
    "SourceReference",
    "ClaimAssessment",
    "GroundednessAssessment",
    "AgentResponse",
    "AppointmentDetails",
    "AppointmentReference",
    "LookupAgentOutput",
    "LookupAgentStatus",
    "RetrievalAgentOutput",
    "RetrievalAgentStatus",
]
