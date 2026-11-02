"""Tests for Practo CrewAI orchestration."""

from crewai import Process

from practo_agent.agents import create_practo_crew
from tests.fixtures.mock_crewai_llm import MockCrewAILLM


def test_creates_practo_crew():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert crew is not None


def test_crew_uses_sequential_process():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert crew.process == Process.sequential


def test_crew_contains_three_agents():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert len(crew.agents) == 3


def test_crew_contains_three_tasks():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert len(crew.tasks) == 3


def test_crew_memory_is_disabled():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert crew.memory is False


def test_crew_agent_order():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    roles = [agent.role for agent in crew.agents]

    assert roles == [
        "Practo Knowledge Retrieval Specialist",
        "Practo Appointment Lookup Specialist",
        "Practo Support Response Composer",
    ]


def test_crew_task_order():
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
    )

    assert crew.tasks[0].agent is crew.agents[0]
    assert crew.tasks[1].agent is crew.agents[1]
    assert crew.tasks[2].agent is crew.agents[2]


def test_crew_construction_does_not_invoke_llm():
    llm = MockCrewAILLM()

    create_practo_crew(
        llm=llm,
        verbose=False,
    )

    assert llm.call_count == 0