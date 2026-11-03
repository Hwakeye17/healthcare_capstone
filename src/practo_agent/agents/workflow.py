"""Validated entry point for the Practo CrewAI support workflow."""

from collections.abc import Sequence

from langchain_core.messages import BaseMessage

from practo_agent.agents.crew import create_practo_crew
from practo_agent.agents.mock_llm import MockCrewAILLM
from practo_agent.agents.routing import route_query
from practo_agent.config.llm import create_crewai_llm
from practo_agent.config.runtime_budget import (
    RuntimeBudget,
    RuntimeBudgetExceeded,
)
from practo_agent.rag.groundedness import (
    GroundednessValidator,
    create_groundedness_validator,
)
from practo_agent.guardrails import (
    detect_prompt_injection,
    mask_contact_numbers,
)
from practo_agent.schemas import (
    AppointmentDetails,
    AgentResponse,
    GroundednessAssessment,
    LookupAgentOutput,
    LookupAgentStatus,
    RetrievedEvidence,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
    ResponseStatus,
)


_OUTPUT_MODELS = {
    "Practo Knowledge Retrieval Specialist": RetrievalAgentOutput,
    "Practo Appointment Lookup Specialist": LookupAgentOutput,
}

_GROUNDEDNESS_ABSTENTION = (
    "I couldn't verify the generated response against the available "
    "information. Please contact the relevant clinic or Practo support."
)


def run_practo_query(
    query: str,
    *,
    llm=None,
    groundedness_validator: GroundednessValidator | None = None,
    conversation_history: Sequence[BaseMessage] = (),
    runtime_budget: RuntimeBudget | None = None,
    verbose: bool = False,
) -> AgentResponse:
    """Run the routed CrewAI workflow and validate every structured result."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    normalized_query = mask_contact_numbers(query.strip())
    if detect_prompt_injection(normalized_query) is not None:
        return AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer=(
                "I can help with Practo administrative questions, but cannot "
                "follow requests to override instructions or disclose "
                "restricted information."
            ),
            reason="The request was rejected by the prompt-injection input guardrail.",
        )

    conversation_context = _format_conversation_history(
        conversation_history
    )
    contextual_query = (
        f"{conversation_context}\n\nCurrent user request: {normalized_query}"
        if conversation_context
        else normalized_query
    )
    if detect_prompt_injection(contextual_query) is not None:
        return AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer=(
                "I can help with Practo administrative questions, but cannot "
                "follow requests to override instructions or disclose "
                "restricted information."
            ),
            reason="The request was rejected by the prompt-injection input guardrail.",
        )

    budget = runtime_budget if runtime_budget is not None else RuntimeBudget()
    try:
        budget.check_request(
            normalized_query,
            conversation_context=conversation_context,
        )
    except RuntimeBudgetExceeded as exc:
        return _budget_abstention(str(exc))

    route = route_query(contextual_query)

    if route.clarification_required:
        return AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer="Please provide one appointment record ID at a time.",
            reason="The request contains multiple appointment record IDs.",
        )

    crew_llm = (
        llm
        if llm is not None
        else create_crewai_llm(
            query=normalized_query,
            runtime_budget=budget,
        )
    )
    if llm is not None:
        set_runtime_budget = getattr(crew_llm, "set_runtime_budget", None)
        if set_runtime_budget is None:
            raise TypeError(
                "The configured LLM must support runtime budget enforcement."
            )
        set_runtime_budget(budget)
    if isinstance(crew_llm, MockCrewAILLM):
        crew_llm.set_query(contextual_query)

    crew = create_practo_crew(
        llm=crew_llm,
        verbose=verbose,
        retrieval_enabled=route.retrieval_enabled,
        lookup_enabled=route.lookup_enabled,
    )
    try:
        result = crew.kickoff(
            inputs={
                "user_query": normalized_query,
                "conversation_context": conversation_context,
            }
        )
    except RuntimeBudgetExceeded as exc:
        return _budget_abstention(str(exc))

    if len(result.tasks_output) != len(crew.tasks):
        raise RuntimeError(
            "CrewAI returned a different number of task outputs than tasks."
        )

    evidence: list[RetrievedEvidence] = []
    retrieved_source_ids: set[str] = set()
    appointment_record_ids: set[str] = set()

    for task, task_output in zip(crew.tasks, result.tasks_output):
        model = _OUTPUT_MODELS.get(task.agent.role)
        if model is None:
            continue

        specialist_output = model.model_validate_json(task_output.raw)

        if (
            isinstance(specialist_output, RetrievalAgentOutput)
            and specialist_output.status == RetrievalAgentStatus.SUCCESS
        ):
            assessment = specialist_output.assessment
            if assessment is None:
                raise RuntimeError(
                    "A successful retrieval has no evidence assessment."
                )
            evidence.extend(assessment.evidence)
            retrieved_source_ids.update(
                item.source_id
                for item in assessment.evidence
            )
        elif (
            isinstance(specialist_output, LookupAgentOutput)
            and specialist_output.status == LookupAgentStatus.SUCCESS
        ):
            appointment = specialist_output.appointment
            if appointment is None:
                raise RuntimeError(
                    "A successful appointment lookup has no appointment."
                )
            evidence.append(_appointment_as_evidence(appointment))
            appointment_record_ids.add(appointment.record_id)

    response = AgentResponse.model_validate_json(result.raw)
    if response.status == ResponseStatus.ABSTAINED:
        return response

    if not evidence:
        return _groundedness_abstention(
            "No validated specialist evidence was available to verify the response."
        )

    if not {item.source_id for item in response.sources}.issubset(
        retrieved_source_ids
    ):
        return _groundedness_abstention(
            "The response cited a source that was not present in the "
            "validated retrieval results."
        )

    if not {item.record_id for item in response.appointments}.issubset(
        appointment_record_ids
    ):
        return _groundedness_abstention(
            "The response cited an appointment that was not present in the "
            "validated lookup results."
        )

    try:
        validator = (
            groundedness_validator
            if groundedness_validator is not None
            else create_groundedness_validator(
                runtime_budget=budget,
            )
        )
        validation = GroundednessAssessment.model_validate(
            validator.validate(response.answer, evidence)
        )
    except RuntimeBudgetExceeded as exc:
        return _budget_abstention(str(exc))
    except Exception:
        return _groundedness_abstention(
            "Groundedness validation could not be completed."
        )

    if not validation.grounded:
        return _groundedness_abstention(
            "Groundedness validation found one or more unsupported claims."
        )

    return response


def _appointment_as_evidence(
    appointment: AppointmentDetails,
) -> RetrievedEvidence:
    """Represent validated lookup fields as evidence for response checking."""

    text = (
        f"Appointment {appointment.record_id} is in specialty "
        f"{appointment.specialty} with status {appointment.status}. "
        f"The consultation fee is INR "
        f"{appointment.consultation_fee_inr}. The record is "
        f"{appointment.days_since_created} days old and its "
        f"follow-up-required flag is {appointment.follow_up_required}. "
        f"Its administrative escalation score is "
        f"{appointment.escalation_score:.4f}; escalation required: "
        f"{appointment.escalation_required}. "
        f"{appointment.escalation_reason}"
    )
    return RetrievedEvidence(
        chunk_id=f"appointment_lookup::{appointment.record_id}",
        text=text,
        source_id=f"appointment_lookup::{appointment.record_id}",
        title=f"Appointment lookup {appointment.record_id}",
        distance=0.0,
    )


def _groundedness_abstention(reason: str) -> AgentResponse:
    return AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer=_GROUNDEDNESS_ABSTENTION,
        reason=reason,
    )


def _budget_abstention(reason: str) -> AgentResponse:
    return AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer=(
            "I couldn't process this request within the configured usage "
            "budget. Please shorten it or try again later."
        ),
        reason=reason,
    )


def _format_conversation_history(
    history: Sequence[BaseMessage],
) -> str:
    """Render prior turns as context while retaining their speaker labels."""

    if not isinstance(history, Sequence) or isinstance(history, str):
        raise TypeError("conversation_history must be a sequence of messages.")

    lines = []
    for message in history:
        if not isinstance(message, BaseMessage):
            raise TypeError(
                "conversation_history must contain LangChain messages."
            )
        content = message.content
        if isinstance(content, str) and content.strip():
            lines.append(f"{message.type}: {content.strip()}")

    return "\n".join(lines)
