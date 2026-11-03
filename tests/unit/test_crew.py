
"""Tests for Practo CrewAI orchestration."""

import pytest
from crewai import Process

from practo_agent.agents import create_practo_crew
from tests.fixtures.mock_crewai_llm import MockCrewAILLM


def _create_crew(
    *,
    retrieval_enabled=True,
    lookup_enabled=True,
):
    return create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )


def test_creates_practo_crew():
    crew = _create_crew()
    assert crew is not None


def test_crew_uses_sequential_process():
    crew = _create_crew()
    assert crew.process == Process.sequential


def test_crew_contains_three_agents_by_default():
    crew = _create_crew()
    assert len(crew.agents) == 3


def test_crew_contains_three_tasks_by_default():
    crew = _create_crew()
    assert len(crew.tasks) == 3


def test_crew_memory_is_disabled():
    crew = _create_crew()
    assert crew.memory is False


def test_crew_agent_order_by_default():
    crew = _create_crew()

    roles = [agent.role for agent in crew.agents]

    assert roles == [
        "Practo Knowledge Retrieval Specialist",
        "Practo Appointment Lookup Specialist",
        "Practo Support Response Composer",
    ]


def test_crew_task_order_by_default():
    crew = _create_crew()

    assert crew.tasks[0].agent is crew.agents[0]
    assert crew.tasks[1].agent is crew.agents[1]
    assert crew.tasks[2].agent is crew.agents[2]


@pytest.mark.parametrize(
    (
        "retrieval_enabled",
        "lookup_enabled",
        "expected_roles",
        "expected_task_keys",
    ),
    [
        (
            True,
            True,
            [
                "Practo Knowledge Retrieval Specialist",
                "Practo Appointment Lookup Specialist",
                "Practo Support Response Composer",
            ],
            ["retrieval", "lookup", "composition"],
        ),
        (
            True,
            False,
            [
                "Practo Knowledge Retrieval Specialist",
                "Practo Support Response Composer",
            ],
            ["retrieval", "composition"],
        ),
        (
            False,
            True,
            [
                "Practo Appointment Lookup Specialist",
                "Practo Support Response Composer",
            ],
            ["lookup", "composition"],
        ),
        (
            False,
            False,
            ["Practo Support Response Composer"],
            ["composition"],
        ),
    ],
)
def test_crew_includes_only_enabled_specialists_and_tasks(
    retrieval_enabled,
    lookup_enabled,
    expected_roles,
    expected_task_keys,
):
    crew = _create_crew(
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    assert [agent.role for agent in crew.agents] == expected_roles
    assert [task.agent for task in crew.tasks] == crew.agents
    assert len(crew.tasks) == len(expected_task_keys)


def test_appointment_only_crew_excludes_retrieval_agent_and_task():
    crew = _create_crew(
        retrieval_enabled=False,
        lookup_enabled=True,
    )

    roles = [agent.role for agent in crew.agents]

    assert "Practo Knowledge Retrieval Specialist" not in roles
    assert all(
        task.agent.role != "Practo Knowledge Retrieval Specialist"
        for task in crew.tasks
    )


def test_rag_only_crew_excludes_lookup_agent_and_task():
    crew = _create_crew(
        retrieval_enabled=True,
        lookup_enabled=False,
    )

    roles = [agent.role for agent in crew.agents]

    assert "Practo Appointment Lookup Specialist" not in roles
    assert all(
        task.agent.role != "Practo Appointment Lookup Specialist"
        for task in crew.tasks
    )


def test_composer_is_always_the_final_agent_and_task():
    crew = _create_crew(
        retrieval_enabled=False,
        lookup_enabled=False,
    )

    assert crew.agents[-1].role == "Practo Support Response Composer"
    assert crew.tasks[-1].agent is crew.agents[-1]


def test_no_agent_with_empty_tools_is_assigned_a_specialist_task():
    crew = _create_crew(
        retrieval_enabled=False,
        lookup_enabled=True,
    )

    for task in crew.tasks:
        if task.agent.role != "Practo Support Response Composer":
            assert task.agent.tools


def test_crew_construction_does_not_invoke_llm():
    llm = MockCrewAILLM()

    create_practo_crew(
        llm=llm,
        verbose=False,
    )

    assert llm.call_count == 0
