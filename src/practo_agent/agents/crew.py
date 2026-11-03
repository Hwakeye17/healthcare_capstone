
"""CrewAI orchestration for the Practo support agent."""

from crewai import Crew, Process

from practo_agent.agents.specialists import create_specialist_agents
from practo_agent.agents.tasks import create_specialist_tasks


def create_practo_crew(
    llm,
    *,
    verbose: bool = True,
    retrieval_enabled: bool = True,
    lookup_enabled: bool = True,
) -> Crew:
    """Build a sequential crew using only enabled specialist tasks.

    Execution order:
        1. Knowledge retrieval, when enabled
        2. Appointment lookup, when enabled
        3. Response composition, always

    Each specialist receives only its explicitly assigned tools.
    Crew memory is disabled; session memory is handled separately.
    """

    agents = create_specialist_agents(
        llm=llm,
        verbose=verbose,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    tasks = create_specialist_tasks(
        agents,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    crew_agents = []
    crew_tasks = []

    if retrieval_enabled:
        crew_agents.append(agents["retrieval"])
        crew_tasks.append(tasks["retrieval"])

    if lookup_enabled:
        crew_agents.append(agents["lookup"])
        crew_tasks.append(tasks["lookup"])

    # The Response Composer always runs last.
    crew_agents.append(agents["composer"])
    crew_tasks.append(tasks["composition"])

    return Crew(
        agents=crew_agents,
        tasks=crew_tasks,
        process=Process.sequential,
        verbose=verbose,
        memory=False,
    )
