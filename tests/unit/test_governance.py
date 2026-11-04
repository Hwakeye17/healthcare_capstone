"""Governance tests: least-autonomy tool permissions and risk classification."""

import json
import socket

import pytest
from crewai import Agent, Crew, Process, Task
from crewai.hooks import get_before_tool_call_hooks
from crewai.llms.base_llm import BaseLLM

import practo_agent.agents.specialists as specialists
import practo_agent.tools.crewai_tools as crewai_tools
from practo_agent.agents import (
    MockCrewAILLM,
    create_practo_crew,
    create_specialist_agents,
    run_practo_query,
)
from practo_agent.governance import (
    APPOINTMENT_LOOKUP_TOOL,
    COMPONENT_RISK_CLASSIFICATIONS,
    COMPOSER_AGENT_ROLE,
    KNOWLEDGE_BASE_TOOL,
    LOOKUP_AGENT_ROLE,
    RETRIEVAL_AGENT_ROLE,
    SYSTEM_RISK_CLASSIFICATION,
    TOOL_PERMISSIONS,
    RiskLevel,
    ToolPermissionError,
    authorize_agent_tools,
    enforce_crew_tool_permissions,
    highest_risk_level,
    install_tool_call_guard,
    is_tool_permitted,
    tool_call_guard,
)
from practo_agent.schemas import ResponseStatus


ALL_ROLES = (RETRIEVAL_AGENT_ROLE, LOOKUP_AGENT_ROLE, COMPOSER_AGENT_ROLE)


class UnauthorizedLookupLLM(BaseLLM):
    """Scripted model that makes a non-Lookup agent request the lookup tool."""

    def __init__(self) -> None:
        super().__init__(model="scripted-unauthorized-lookup", provider="openai")
        self.messages: list = []

    def call(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ) -> str:
        self.messages.append(messages)
        if len(self.messages) == 1:
            return (
                "Thought: I will look up the appointment myself.\n"
                f"Action: {APPOINTMENT_LOOKUP_TOOL}\n"
                'Action Input: {"record_id": "APT-0001"}'
            )
        return "Thought: I cannot use that tool.\nFinal Answer: lookup refused"

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False


@pytest.fixture
def event_log(tmp_path, monkeypatch):
    path = tmp_path / "governance.jsonl"
    monkeypatch.setenv("PRACTO_LOG_PATH", str(path))

    def read_events() -> list[dict]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    return read_events


@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    original_connect = socket.socket.connect

    def reject_external_connection(sock, address):
        if address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"Unexpected network access to {address[0]!r}.")
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", reject_external_connection)


@pytest.fixture
def lookup_executions(monkeypatch):
    """Record every execution of the underlying appointment lookup."""

    executed: list[str] = []
    original = crewai_tools.check_appointment_status

    def recording_lookup(record_id):
        executed.append(record_id)
        return original(record_id)

    monkeypatch.setattr(crewai_tools, "check_appointment_status", recording_lookup)
    return executed


# --- Policy -----------------------------------------------------------------


@pytest.mark.parametrize("role", ALL_ROLES)
def test_only_lookup_agent_may_use_appointment_lookup(role):
    assert is_tool_permitted(role, APPOINTMENT_LOOKUP_TOOL) is (
        role == LOOKUP_AGENT_ROLE
    )


@pytest.mark.parametrize("role", ALL_ROLES)
def test_only_retrieval_agent_may_use_knowledge_base(role):
    assert is_tool_permitted(role, KNOWLEDGE_BASE_TOOL) is (
        role == RETRIEVAL_AGENT_ROLE
    )


def test_lookup_tool_has_exactly_one_permitted_role():
    assert TOOL_PERMISSIONS[APPOINTMENT_LOOKUP_TOOL] == frozenset(
        {LOOKUP_AGENT_ROLE}
    )


@pytest.mark.parametrize(
    ("role", "tool_name"),
    [
        (LOOKUP_AGENT_ROLE, "rag_lookup"),
        ("Unregistered Agent", APPOINTMENT_LOOKUP_TOOL),
        (None, APPOINTMENT_LOOKUP_TOOL),
        (LOOKUP_AGENT_ROLE, None),
    ],
)
def test_unknown_roles_and_tools_are_denied_by_default(role, tool_name):
    assert is_tool_permitted(role, tool_name) is False


def test_policy_cannot_be_modified_at_runtime():
    with pytest.raises(TypeError):
        TOOL_PERMISSIONS[APPOINTMENT_LOOKUP_TOOL] = frozenset(ALL_ROLES)


# --- Wiring-time enforcement --------------------------------------------------


def test_lookup_agent_is_authorized_for_lookup_tool():
    authorize_agent_tools(LOOKUP_AGENT_ROLE, [crewai_tools.lookup_appointment])


@pytest.mark.parametrize("role", [RETRIEVAL_AGENT_ROLE, COMPOSER_AGENT_ROLE])
def test_wiring_lookup_tool_to_other_agent_is_rejected(role):
    with pytest.raises(ToolPermissionError, match=APPOINTMENT_LOOKUP_TOOL):
        authorize_agent_tools(role, [crewai_tools.lookup_appointment])


def test_factory_agent_roles_match_governance_policy():
    agents = create_specialist_agents(llm=MockCrewAILLM(), verbose=False)

    assert agents["retrieval"].role == RETRIEVAL_AGENT_ROLE
    assert agents["lookup"].role == LOOKUP_AGENT_ROLE
    assert agents["composer"].role == COMPOSER_AGENT_ROLE
    holders = [
        agent.role
        for agent in agents.values()
        if APPOINTMENT_LOOKUP_TOOL in {tool.name for tool in agent.tools}
    ]
    assert holders == [LOOKUP_AGENT_ROLE]


def test_factory_rejects_lookup_tool_wired_to_retrieval_agent(monkeypatch):
    monkeypatch.setattr(
        specialists,
        "search_practo_knowledge_base",
        crewai_tools.lookup_appointment,
    )

    with pytest.raises(ToolPermissionError) as error:
        create_specialist_agents(llm=MockCrewAILLM(), verbose=False)

    assert RETRIEVAL_AGENT_ROLE in str(error.value)


def test_crew_check_rejects_composer_holding_lookup_tool():
    composer = Agent(
        role=COMPOSER_AGENT_ROLE,
        goal="Compose answers.",
        backstory="Composer without tool rights.",
        tools=[crewai_tools.lookup_appointment],
        llm=MockCrewAILLM(),
        allow_delegation=False,
    )
    task = Task(description="Compose.", expected_output="Text.", agent=composer)
    crew = Crew(agents=[composer], tasks=[task], process=Process.sequential)

    with pytest.raises(ToolPermissionError, match=COMPOSER_AGENT_ROLE):
        enforce_crew_tool_permissions(crew)


def test_crew_check_rejects_task_level_lookup_tool_override():
    composer = Agent(
        role=COMPOSER_AGENT_ROLE,
        goal="Compose answers.",
        backstory="Composer without tool rights.",
        tools=[],
        llm=MockCrewAILLM(),
        allow_delegation=False,
    )
    task = Task(
        description="Compose.",
        expected_output="Text.",
        agent=composer,
        tools=[crewai_tools.lookup_appointment],
    )
    crew = Crew(agents=[composer], tasks=[task], process=Process.sequential)

    with pytest.raises(ToolPermissionError, match=APPOINTMENT_LOOKUP_TOOL):
        enforce_crew_tool_permissions(crew)


@pytest.mark.parametrize(
    ("retrieval_enabled", "lookup_enabled"),
    [(True, True), (True, False), (False, True), (False, False)],
)
def test_project_crews_pass_governance_and_install_call_guard(
    retrieval_enabled,
    lookup_enabled,
):
    crew = create_practo_crew(
        llm=MockCrewAILLM(),
        verbose=False,
        retrieval_enabled=retrieval_enabled,
        lookup_enabled=lookup_enabled,
    )

    enforce_crew_tool_permissions(crew)
    assert get_before_tool_call_hooks().count(tool_call_guard) == 1


def test_call_guard_installation_is_idempotent():
    install_tool_call_guard()
    install_tool_call_guard()

    assert get_before_tool_call_hooks().count(tool_call_guard) == 1


# --- Call-time enforcement ----------------------------------------------------


class _Context:
    def __init__(self, role, tool_name):
        self.agent = type("AgentStub", (), {"role": role})()
        self.tool_name = tool_name
        self.tool_input = {"record_id": "APT-0001"}


def test_call_guard_allows_lookup_agent_without_logging(event_log):
    assert tool_call_guard(_Context(LOOKUP_AGENT_ROLE, APPOINTMENT_LOOKUP_TOOL)) is None
    assert event_log() == []


@pytest.mark.parametrize("role", [RETRIEVAL_AGENT_ROLE, COMPOSER_AGENT_ROLE])
def test_call_guard_blocks_other_agents_and_logs_safely(role, event_log):
    assert tool_call_guard(_Context(role, APPOINTMENT_LOOKUP_TOOL)) is False

    events = event_log()
    assert len(events) == 1
    assert events[0]["event"] == "tool_call_blocked"
    assert events[0]["agent_role"] == role
    assert events[0]["tool_name"] == APPOINTMENT_LOOKUP_TOOL
    assert "APT-0001" not in json.dumps(events[0])


def test_call_guard_blocks_unknown_agent_and_tool_without_logging_names(event_log):
    assert tool_call_guard(_Context("Injected Agent", "export_all_records")) is False

    assert event_log()[0] == {
        "timestamp": event_log()[0]["timestamp"],
        "event": "tool_call_blocked",
        "agent_role": "unknown",
    }


def test_kickoff_blocks_lookup_call_from_miswired_composer(
    offline,
    event_log,
    lookup_executions,
):
    llm = UnauthorizedLookupLLM()
    composer = Agent(
        role=COMPOSER_AGENT_ROLE,
        goal="Compose answers.",
        backstory="Deliberately mis-wired outside the project factory.",
        tools=[crewai_tools.lookup_appointment],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(description="Answer.", expected_output="Text.", agent=composer)
    crew = Crew(
        agents=[composer],
        tasks=[task],
        process=Process.sequential,
        memory=False,
        verbose=False,
    )
    install_tool_call_guard()

    result = crew.kickoff()

    assert lookup_executions == []
    assert result.raw == "lookup refused"
    observation = llm.messages[-1][-2]["content"]
    assert "Tool execution blocked by hook" in observation
    assert '"found"' not in observation
    events = event_log()
    assert [event["event"] for event in events] == ["tool_call_blocked"]
    assert events[0]["agent_role"] == COMPOSER_AGENT_ROLE


def test_lookup_agent_call_is_permitted_end_to_end(
    offline,
    event_log,
    lookup_executions,
):
    query = "What is the status of APT-0001?"
    llm = MockCrewAILLM(query=query)

    response = run_practo_query(query, llm=llm)

    assert response.status == ResponseStatus.ANSWERED
    assert [item.record_id for item in response.appointments] == ["APT-0001"]
    assert llm.tool_actions == [APPOINTMENT_LOOKUP_TOOL]
    assert lookup_executions == ["APT-0001"]
    events = [event["event"] for event in event_log()]
    assert "tool_call_blocked" not in events
    assert "tool_completed" in events


# --- Risk classification ------------------------------------------------------


def test_system_is_classified_high_risk_with_justification():
    assert SYSTEM_RISK_CLASSIFICATION.level is RiskLevel.HIGH
    assert "medical" in SYSTEM_RISK_CLASSIFICATION.justification


def test_system_level_matches_highest_component_risk():
    assert (
        highest_risk_level(COMPONENT_RISK_CLASSIFICATIONS)
        is SYSTEM_RISK_CLASSIFICATION.level
    )


def test_every_tool_has_a_justified_risk_classification():
    subjects = " ".join(item.subject for item in COMPONENT_RISK_CLASSIFICATIONS)

    assert all(tool in subjects for tool in TOOL_PERMISSIONS)
    assert all(
        isinstance(item.level, RiskLevel) and len(item.justification) > 80
        for item in COMPONENT_RISK_CLASSIFICATIONS
    )


def test_appointment_lookup_is_high_risk():
    lookup = next(
        item
        for item in COMPONENT_RISK_CLASSIFICATIONS
        if APPOINTMENT_LOOKUP_TOOL in item.subject
    )

    assert lookup.level is RiskLevel.HIGH


def test_highest_risk_level_requires_classifications():
    with pytest.raises(ValueError):
        highest_risk_level([])

