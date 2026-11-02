import pytest

from practo_agent.agents import create_specialist_agents
from tests.fixtures.mock_crewai_llm import MockCrewAILLM


@pytest.fixture
def fake_llm():
    return MockCrewAILLM()


@pytest.fixture
def agents(fake_llm):
    return create_specialist_agents(
        llm=fake_llm,
        verbose=False,
    )


def test_creates_all_three_specialist_agents(agents):
    assert set(agents) == {"retrieval", "lookup", "composer"}


def test_retrieval_agent_has_only_knowledge_base_tool(agents):
    tool_names = [tool.name for tool in agents["retrieval"].tools]

    assert tool_names == ["search_practo_knowledge_base"]


def test_lookup_agent_has_only_appointment_tool(agents):
    tool_names = [tool.name for tool in agents["lookup"].tools]

    assert tool_names == ["check_appointment_status"]


def test_response_composer_has_no_tools(agents):
    assert agents["composer"].tools == []


def test_agents_cannot_delegate(agents):
    assert all(
        agent.allow_delegation is False
        for agent in agents.values()
    )


def test_agent_construction_does_not_call_llm(fake_llm):
    create_specialist_agents(
        llm=fake_llm,
        verbose=False,
    )

    assert fake_llm.call_count == 0