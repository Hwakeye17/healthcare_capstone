"""CrewAI orchestration for the Practo support agent."""

from crewai import Crew, Process

from practo_agent.agents.specialists import create_specialist_agents
from practo_agent.agents.tasks import create_specialist_tasks


def create_practo_crew(
    llm,
    *,
    verbose: bool = True,
) -> Crew:
    """Build the sequential Practo support crew.

    Execution order:
        1. Knowledge retrieval
        2. Appointment lookup
        3. Response composition

    Each agent receives only its explicitly assigned tools.
    Crew memory is disabled; session memory is handled separately.
    """

    agents = create_specialist_agents(
        llm=llm,
        verbose=verbose,
    )

    tasks = create_specialist_tasks(agents)

    crew = Crew(
        agents=[
            agents["retrieval"],
            agents["lookup"],
            agents["composer"],
        ],
        tasks=[
            tasks["retrieval"],
            tasks["lookup"],
            tasks["composition"],
        ],
        process=Process.sequential,
        verbose=verbose,
        memory=False,
    )

    return crew