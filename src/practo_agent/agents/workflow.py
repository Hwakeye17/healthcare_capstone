"""Validated entry point for the Practo CrewAI support workflow."""

from practo_agent.agents.crew import create_practo_crew
from practo_agent.agents.mock_llm import MockCrewAILLM
from practo_agent.agents.routing import route_query
from practo_agent.config.llm import create_crewai_llm
from practo_agent.guardrails import (
    detect_prompt_injection,
    mask_contact_numbers,
)
from practo_agent.schemas import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
    ResponseStatus,
)


_OUTPUT_MODELS = {
    "Practo Knowledge Retrieval Specialist": RetrievalAgentOutput,
    "Practo Appointment Lookup Specialist": LookupAgentOutput,
}


def run_practo_query(
    query: str,
    *,
    llm=None,
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

    route = route_query(normalized_query)

    if route.clarification_required:
        return AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer="Please provide one appointment record ID at a time.",
            reason="The request contains multiple appointment record IDs.",
        )

    crew_llm = (
        llm
        if llm is not None
        else create_crewai_llm(query=normalized_query)
    )
    if isinstance(crew_llm, MockCrewAILLM):
        crew_llm.set_query(normalized_query)

    crew = create_practo_crew(
        llm=crew_llm,
        verbose=verbose,
        retrieval_enabled=route.retrieval_enabled,
        lookup_enabled=route.lookup_enabled,
    )
    result = crew.kickoff(inputs={"user_query": normalized_query})

    if len(result.tasks_output) != len(crew.tasks):
        raise RuntimeError(
            "CrewAI returned a different number of task outputs than tasks."
        )

    for task, task_output in zip(crew.tasks, result.tasks_output):
        model = _OUTPUT_MODELS.get(task.agent.role)
        if model is not None:
            model.model_validate_json(task_output.raw)

    return AgentResponse.model_validate_json(result.raw)
