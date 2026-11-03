
"""CrewAI tool wrappers for the Practo support agent."""

import json

from crewai.tools import tool

from practo_agent.config import DEFAULT_RETRIEVAL_CONFIG
from practo_agent.rag.embeddings import create_embedding_model
from practo_agent.rag.evidence import assess_evidence
from practo_agent.rag.vectorstore import ChromaVectorStore
from practo_agent.schemas import (
    AppointmentDetails,
    LookupAgentOutput,
    LookupAgentStatus,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
)
from practo_agent.tools.appointment_lookup import check_appointment_status


# Lazily initialized so importing the tools does not load the embedding model.
_rag_store: ChromaVectorStore | None = None


def _get_rag_store() -> ChromaVectorStore:
    """Open the existing sentence-based collection without rebuilding it."""

    global _rag_store

    if _rag_store is None:
        # The persisted collection was built with the real SentenceTransformer
        # model. DeterministicTestEmbeddings must not be used to query it.
        embeddings = create_embedding_model(mock_mode=False)

        _rag_store = ChromaVectorStore(
            strategy=DEFAULT_RETRIEVAL_CONFIG.strategy,
            embeddings=embeddings,
        )

        if _rag_store.count == 0:
            raise RuntimeError(
                "The sentence-based knowledge-base collection is empty. "
                "Build the vector store before running the agents."
            )

    return _rag_store


@tool("search_practo_knowledge_base")
def search_practo_knowledge_base(query: str) -> str:
    """Search Practo administrative knowledge and return calibrated evidence.

    Use this tool for questions about appointment policies, cancellations,
    fees, insurance, prescriptions, lab turnaround, telemedicine, privacy,
    follow-ups, second opinions, home visits, and other documented topics.

    Do not use it to look up an individual appointment record.
    """

    try:
        assessment = assess_evidence(
            store=_get_rag_store(),
            query=query,
        )

        if assessment.accepted:
            output = RetrievalAgentOutput(
                used=True,
                status=RetrievalAgentStatus.SUCCESS,
                assessment=assessment,
            )
        else:
            output = RetrievalAgentOutput(
                used=True,
                status=RetrievalAgentStatus.NO_EVIDENCE,
                assessment=assessment,
                reason=assessment.reason,
            )

    except Exception:
        # Keep internal paths, configuration and exception details out of
        # the agent-visible tool result.
        output = RetrievalAgentOutput(
            used=True,
            status=RetrievalAgentStatus.ERROR,
            reason="Knowledge-base search failed.",
        )

    return json.dumps(output.model_dump(mode="json"), ensure_ascii=False)


@tool("check_appointment_status")
def lookup_appointment(record_id: str) -> str:
    """Look up an appointment using its appointment record ID.

    Returns the appointment status, consultation fee in INR and
    administrative escalation score. Use only when the user provides
    an appointment record ID. This tool is read-only.
    """

    try:
        result = check_appointment_status(record_id)

        if result["found"]:
            appointment = AppointmentDetails(
                record_id=result["record_id"],
                specialty=result["specialty"],
                status=result["status"],
                consultation_fee_inr=result["consultation_fee_inr"],
                days_since_created=result["days_since_created"],
                follow_up_required=result["follow_up_required"],
                escalation_score=result["escalation_score"],
                escalation_required=result["escalation_required"],
                escalation_reason=result["escalation_reason"],
            )

            output = LookupAgentOutput(
                used=True,
                status=LookupAgentStatus.SUCCESS,
                record_id=result["record_id"],
                appointment=appointment,
            )
        else:
            output = LookupAgentOutput(
                used=True,
                status=LookupAgentStatus.NOT_FOUND,
                record_id=result["record_id"],
                reason=result["error"],
            )

    except Exception:
        output = LookupAgentOutput(
            used=True,
            status=LookupAgentStatus.ERROR,
            reason="Appointment lookup failed.",
        )

    return json.dumps(output.model_dump(mode="json"), ensure_ascii=False)
