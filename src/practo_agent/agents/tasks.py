
"""CrewAI task definitions for the Practo support workflow."""

from crewai import Task

from practo_agent.schemas import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
)


def create_specialist_tasks(
    agents: dict,
) -> dict[str, Task]:
    """Create the retrieval, lookup, and response-composition tasks.

    The tasks run sequentially. The composer receives both specialist
    outputs as context and has no independent tool access.
    """

    retrieval_task = Task(
        description=(
            "Evaluate the user's request: {user_query}\n\n"
            "Determine whether the request requires information from the "
            "Practo administrative knowledge base, such as appointment "
            "booking, cancellation, fees, insurance, prescriptions, lab "
            "turnaround, telemedicine, privacy, follow-ups, second opinions, "
            "or home visits.\n\n"
            "If knowledge-base information is relevant, call "
            "search_practo_knowledge_base using a focused search query. "
            "Use the tool result as the source of truth.\n\n"
            "If the request does not require knowledge-base information, "
            "return NOT_NEEDED and do not call the tool.\n\n"
            "If the tool reports insufficient evidence, preserve that "
            "outcome as NO_EVIDENCE. Do not invent or supplement policies "
            "using general knowledge.\n\n"
            "Return only the RetrievalAgentOutput contract. Include the "
            "complete assessment returned by the tool when one is available."
        ),
        expected_output=(
            "A valid RetrievalAgentOutput Pydantic object. It must accurately "
            "indicate whether retrieval was used, whether evidence was "
            "accepted, and why retrieval was not successful when applicable."
        ),
        agent=agents["retrieval"],
        output_pydantic=RetrievalAgentOutput,
    )

    lookup_task = Task(
        description=(
            "Evaluate the user's request: {user_query}\n\n"
            "Determine whether the user explicitly requests an appointment "
            "status lookup and provides an appointment record ID.\n\n"
            "If an appointment lookup is required and a record ID is "
            "available, call check_appointment_status with that exact ID. "
            "Do not modify, invent, or guess the record ID. Use the returned "
            "record and status exactly as provided by the tool.\n\n"
            "If the request does not require an appointment lookup, or no "
            "record ID is supplied, return NOT_NEEDED and do not call the "
            "tool. Do not search for an appointment using a person's name, "
            "phone number, or other personal information.\n\n"
            "If the tool cannot find the supplied record, return NOT_FOUND. "
            "Do not invent appointment details or claim that a lookup "
            "succeeded.\n\n"
            "Return only the LookupAgentOutput contract."
        ),
        expected_output=(
            "A valid LookupAgentOutput Pydantic object. It must preserve "
            "the exact record ID and appointment details returned by the "
            "lookup tool, or clearly indicate NOT_NEEDED, NOT_FOUND, or ERROR."
        ),
        agent=agents["lookup"],
        output_pydantic=LookupAgentOutput,
    )

    composition_task = Task(
        description=(
            "Compose the final response to the user's request: {user_query}\n\n"
            "Use the outputs of the Retrieval Agent and Lookup Agent supplied "
            "in the task context. These outputs are the only permitted "
            "sources for Practo policies and appointment-specific facts.\n\n"
            "Rules:\n"
            "1. Use only facts supported by the specialist outputs.\n"
            "2. Never invent policies, fees, appointment statuses, or record IDs.\n"
            "3. If retrieval returned NO_EVIDENCE, do not provide an "
            "unsupported policy answer.\n"
            "4. If lookup returned NOT_FOUND, clearly state that the "
            "appointment record could not be found.\n"
            "5. If both specialists returned NOT_NEEDED, do not fabricate "
            "an answer. Ask the user for the missing information or clarify "
            "what kind of administrative help is required.\n"
            "6. Include source references only when supported by accepted "
            "retrieval evidence. Include appointment references only when "
            "supported by a successful lookup.\n"
            "7. Do not provide medical diagnosis, treatment advice, or "
            "clinical recommendations.\n\n"
            "Return a structured AgentResponse. Use ANSWERED only when the "
            "response contains supported information and the required "
            "source or appointment references. Otherwise use ABSTAINED "
            "with a clear reason."
        ),
        expected_output=(
            "A valid AgentResponse Pydantic object containing the final "
            "administrative support answer or an explicit abstention."
        ),
        agent=agents["composer"],
        context=[retrieval_task, lookup_task],
        output_pydantic=AgentResponse,
    )

    return {
        "retrieval": retrieval_task,
        "lookup": lookup_task,
        "composition": composition_task,
    }
