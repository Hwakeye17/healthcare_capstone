
"""Tests for CrewAI specialist task definitions."""

import pytest

from practo_agent.agents import create_specialist_agents, create_specialist_tasks
from practo_agent.schemas import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
)
from tests.fixtures.mock_crewai_llm import MockCrewAILLM


def _create_tasks(
    *,
    retrieval_enabled=True,
    lookup_enabled=True,
):
    agents = create_specialist_agents(
        llm=MockCrewAILLM(),
        verbose=False,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )
    tasks = create_specialist_tasks(
        agents,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )
    return agents, tasks


def test_creates_all_three_tasks_by_default():
    _, tasks = _create_tasks()
    assert set(tasks) == {"retrieval", "lookup", "composition"}


def test_retrieval_task_uses_retrieval_agent_and_manual_schema_validation():
    agents, tasks = _create_tasks()
    task = tasks["retrieval"]

    assert task.agent is agents["retrieval"]
    assert task.output_json is None
    assert task.output_pydantic is None
    assert "RetrievalAgentOutput" in task.expected_output
    assert "properties" in task.expected_output


def test_lookup_task_uses_lookup_agent_and_manual_schema_validation():
    agents, tasks = _create_tasks()
    task = tasks["lookup"]

    assert task.agent is agents["lookup"]
    assert task.output_json is None
    assert task.output_pydantic is None
    assert "LookupAgentOutput" in task.expected_output
    assert "reason=null" in task.description
    assert "Do not add an explanatory reason" in task.description


def test_composition_task_uses_composer_and_manual_schema_validation():
    agents, tasks = _create_tasks()
    task = tasks["composition"]

    assert task.agent is agents["composer"]
    assert task.output_json is None
    assert task.output_pydantic is None
    assert "AgentResponse" in task.expected_output
    assert "properties" in task.expected_output
    assert "sources and appointments to empty arrays" in task.description
    assert "must never include any source or appointment references" in task.description


def test_composition_task_depends_on_both_enabled_specialists():
    _, tasks = _create_tasks()

    assert tasks["composition"].context == [
        tasks["retrieval"],
        tasks["lookup"],
    ]


@pytest.mark.parametrize(
    ("retrieval_enabled", "lookup_enabled", "expected_keys"),
    [
        (True, True, {"retrieval", "lookup", "composition"}),
        (True, False, {"retrieval", "composition"}),
        (False, True, {"lookup", "composition"}),
        (False, False, {"composition"}),
    ],
)
def test_only_enabled_specialist_tasks_are_created(
    retrieval_enabled,
    lookup_enabled,
    expected_keys,
):
    _, tasks = _create_tasks(
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    assert set(tasks) == expected_keys


@pytest.mark.parametrize(
    ("retrieval_enabled", "lookup_enabled", "expected_context_keys"),
    [
        (True, True, ["retrieval", "lookup"]),
        (True, False, ["retrieval"]),
        (False, True, ["lookup"]),
        (False, False, []),
    ],
)
def test_composer_context_contains_only_enabled_specialist_tasks(
    retrieval_enabled,
    lookup_enabled,
    expected_context_keys,
):
    _, tasks = _create_tasks(
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    expected_context = [
        tasks[key]
        for key in expected_context_keys
    ]

    assert tasks["composition"].context == expected_context


def test_composer_is_told_when_a_specialist_was_skipped():
    _, tasks = _create_tasks(
        retrieval_enabled=False,
        lookup_enabled=True,
    )

    description = tasks["composition"].description

    assert "Knowledge Retrieval" in description
    assert "were disabled and did not execute" in description
    assert "Do not treat a skipped specialist" in description


def test_composer_is_not_given_a_skipped_specialist_as_context():
    _, tasks = _create_tasks(
        retrieval_enabled=False,
        lookup_enabled=True,
    )

    assert tasks["composition"].context == [tasks["lookup"]]
    assert tasks["composition"].context[0] is tasks["lookup"]


def test_task_definitions_do_not_invoke_llm():
    llm = MockCrewAILLM()
    agents = create_specialist_agents(llm=llm, verbose=False)
    create_specialist_tasks(agents)

    assert llm.call_count == 0
