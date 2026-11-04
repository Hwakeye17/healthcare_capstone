"""Definitions of the three specialist CrewAI agents."""

from crewai import Agent

from practo_agent.governance import authorize_agent_tools
from practo_agent.tools.crewai_tools import (
    lookup_appointment,
    search_practo_knowledge_base,
)


def create_specialist_agents(
    llm,
    *,
    verbose: bool = True,
    retrieval_enabled: bool = True,
    lookup_enabled: bool = True,
) -> dict[str, Agent]:
    """Create the Retrieval, Lookup and Response Composer agents.

    Tool access is assigned explicitly here and checked against the
    governance policy, so wiring a tool to an unauthorized agent fails.
    Agents cannot delegate work to other agents; coordination is handled
    by the sequential Crew tasks.
    """

    retrieval_agent = Agent(
        role="Practo Knowledge Retrieval Specialist",
        goal=(
            "Find relevant information in the Practo administrative "
            "knowledge base and determine whether the retrieved evidence "
            "passes the configured evidence threshold."
        ),
        backstory=(
            "You are a knowledge retrieval specialist for an administrative "
            "healthcare support service. You answer questions only by using "
            "the approved knowledge-base search tool. You do not invent "
            "policies, provide medical diagnosis, or give treatment advice. "
            "If evidence is insufficient, clearly report that no supported "
            "answer is available."
        ),
        tools=(
            [search_practo_knowledge_base]
            if retrieval_enabled
            else []
        ),
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )

    lookup_agent = Agent(
        role="Practo Appointment Lookup Specialist",
        goal=(
            "Retrieve accurate administrative details for an appointment "
            "when the user provides an appointment record ID."
        ),
        backstory=(
            "You are a read-only appointment lookup specialist. You use "
            "only the approved appointment lookup tool. You report the "
            "returned appointment status, consultation fee and administrative "
            "escalation score without modifying records or inventing details. "
            "If no appointment is found, report that clearly."
        ),
        tools=[lookup_appointment] if lookup_enabled else [],
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )

    response_composer = Agent(
        role="Practo Support Response Composer",
        goal=(
            "Compose a clear, concise and accurate administrative support "
            "response using only the structured outputs provided by the "
            "Retrieval Agent and Lookup Agent."
        ),
        backstory=(
            "You are the final response composer for a healthcare "
            "administrative support assistant. You do not have access to "
            "external tools and must not independently retrieve information. "
            "Use only the specialist results supplied to you. Do not invent "
            "policies, appointment details, or unsupported claims. If the "
            "specialist results do not support an answer, communicate the "
            "limitation clearly. Never provide diagnosis or treatment advice."
        ),
        tools=[],
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )

    agents = {
        "retrieval": retrieval_agent,
        "lookup": lookup_agent,
        "composer": response_composer,
    }
    for agent in agents.values():
        authorize_agent_tools(agent.role, agent.tools)

    return agents
