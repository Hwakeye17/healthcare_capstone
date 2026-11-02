
"""Tests for CrewAI specialist task definitions."""

from practo_agent.agents import (
    create_specialist_agents,
    create_specialist_tasks,
)
from practo_agent.schemas import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
)
from tests.fixtures.mock_crewai_llm import MockCrewAILLM


def test_creates_all_three_tasks():
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    tasks = create_specialist_tasks(agents)

    assert set(tasks) == {
        "retrieval",
        "lookup",
        "composition",
    }


def test_retrieval_task_uses_retrieval_agent_and_schema():
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
    )
    tasks = create_specialist_tasks(agents)

    task = tasks["retrieval"]

    assert task.agent is agents["retrieval"]
    assert task.output_pydantic is RetrievalAgentOutput


def test_lookup_task_uses_lookup_agent_and_schema():
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
    )
    tasks = create_specialist_tasks(agents)

    task = tasks["lookup"]

    assert task.agent is agents["lookup"]
    assert task.output_pydantic is LookupAgentOutput


def test_composition_task_uses_composer_and_schema():
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
    )
    tasks = create_specialist_tasks(agents)

    task = tasks["composition"]

    assert task.agent is agents["composer"]
    assert task.output_pydantic is AgentResponse


def test_composition_task_depends_on_both_specialist_tasks():
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
    )
    tasks = create_specialist_tasks(agents)

    context = tasks["composition"].context

    assert context == [
        tasks["retrieval"],
        tasks["lookup"],
    ]


def test_task_definitions_do_not_invoke_llm():
    llm = MockCrewAILLM()
    agents = create_specialist_agents(llm=llm, verbose=False)

    create_specialist_tasks(agents)

    assert llm.call_count == 0
