
"""CrewAI task definitions for the Practo support workflow."""

import json

from crewai import Task

from practo_agent.schemas import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
)


def _json_contract(model: type) -> str:
    """Describe the Pydantic contract without enabling provider-native output parsing."""
    schema = json.dumps(model.model_json_schema(), indent=2)
    return (
        "Return exactly one valid JSON object matching this schema. "
        "Do not use Markdown fences, prose, or tool calls to represent the schema.\n"
        f"{schema}"
    )


def create_specialist_tasks(
    agents: dict,
    *,
    retrieval_enabled: bool = True,
    lookup_enabled: bool = True,
) -> dict[str, Task]:
    """Create enabled specialist tasks and the final composition task.

    Only enabled specialist tasks are created. The composer receives context
    from those tasks only. Disabled specialists are not represented as having
    executed or returned a NOT_NEEDED result.
    """

    tasks: dict[str, Task] = {}
    specialist_context: list[Task] = []
    skipped_specialists: list[str] = []

    if retrieval_enabled:
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
                "return NOT_NEEDED with used=false, assessment=null, and "
                "reason=null. Do not call the tool.\n\n"
                "If the tool reports insufficient evidence, preserve that "
                "outcome as NO_EVIDENCE. Do not invent or supplement policies "
                "using general knowledge. Include the complete assessment "
                "returned by the tool when one is available.\n\n"
                "Return only one JSON object matching the required schema."
            ),
            expected_output=_json_contract(RetrievalAgentOutput),
            agent=agents["retrieval"],
        )
        tasks["retrieval"] = retrieval_task
        specialist_context.append(retrieval_task)
    else:
        skipped_specialists.append("Knowledge Retrieval")

    if lookup_enabled:
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
                "record ID is supplied, return NOT_NEEDED with used=false, "
                "record_id=null, appointment=null, and reason=null. Do not call "
                "the tool. Do not add an explanatory reason. Do not search for "
                "an appointment using a person's name, phone number, or other "
                "personal information.\n\n"
                "If the tool cannot find the supplied record, return NOT_FOUND. "
                "Do not invent appointment details or claim that a lookup "
                "succeeded.\n\n"
                "Return only one JSON object matching the required schema."
            ),
            expected_output=_json_contract(LookupAgentOutput),
            agent=agents["lookup"],
        )
        tasks["lookup"] = lookup_task
        specialist_context.append(lookup_task)
    else:
        skipped_specialists.append("Appointment Lookup")

    skipped_note = ""
    if skipped_specialists:
        skipped_names = " and ".join(skipped_specialists)
        skipped_note = (
            f"\n\nExecution note: {skipped_names} specialist task(s) "
            "were disabled and did not execute. They produced no output. "
            "Do not treat a skipped specialist as having searched and found "
            "no evidence, and do not describe a skipped specialist as "
            "returning NOT_NEEDED. Do not mention internal execution details "
            "to the user."
        )

    composition_task = Task(
        description=(
            "Compose the final response to the user's request: {user_query}\n\n"
            "Use the outputs of the enabled Retrieval Agent and Lookup Agent "
            "supplied in the task context. These outputs are the only permitted "
            "sources for Practo policies and appointment-specific facts.\n\n"
            "Rules:\n"
            "1. Use only facts supported by the specialist outputs.\n"
            "2. Never invent policies, fees, appointment statuses, or record IDs.\n"
            "3. If retrieval returned NO_EVIDENCE, do not provide an "
            "unsupported policy answer.\n"
            "4. If lookup returned NOT_FOUND, clearly state that the "
            "appointment record could not be found.\n"
            "5. If an enabled specialist returned NOT_NEEDED, do not fabricate "
            "an answer for that part of the request.\n"
            "6. Include source references only when supported by accepted "
            "retrieval evidence. Include appointment references only when "
            "supported by a successful lookup.\n"
            "7. Do not provide medical diagnosis, treatment advice, or "
            "clinical recommendations.\n\n"
            "Return only one JSON object matching the required schema. "
            "Use ANSWERED only when the response contains supported "
            "information and the required source or appointment references. "
            "Otherwise use ABSTAINED with a clear reason."
            + skipped_note
        ),
        expected_output=_json_contract(AgentResponse),
        agent=agents["composer"],
        context=specialist_context,
    )
    tasks["composition"] = composition_task

    return tasks
