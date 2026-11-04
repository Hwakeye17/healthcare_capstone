"""Demonstrate least-autonomy governance for the appointment lookup tool.

Runs offline (MOCK_LLM, no API key, no network) and records:

1. The tool-permission policy and the Low/Medium/High risk classification.
2. Permitted access: the Lookup Agent calls check_appointment_status
   through the normal workflow.
3. Prohibited wiring: assigning the lookup tool to the Retrieval Agent or
   Response Composer is rejected before a crew can run.
4. Prohibited call: an agent deliberately mis-wired outside the project
   factories requests the lookup tool during kickoff(); the call-time guard
   blocks it before the tool executes.
"""

import json
import os
import tempfile
from pathlib import Path


def _read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    log_dir = Path(tempfile.mkdtemp(prefix="practo_governance_"))

    from crewai import Agent, Crew, Process, Task
    from crewai.llms.base_llm import BaseLLM

    from practo_agent.agents import MockCrewAILLM, run_practo_query
    from practo_agent.governance import (
        APPOINTMENT_LOOKUP_TOOL,
        COMPONENT_RISK_CLASSIFICATIONS,
        COMPOSER_AGENT_ROLE,
        RETRIEVAL_AGENT_ROLE,
        SYSTEM_RISK_CLASSIFICATION,
        TOOL_PERMISSIONS,
        ToolPermissionError,
        authorize_agent_tools,
        enforce_crew_tool_permissions,
        install_tool_call_guard,
    )
    from practo_agent.schemas import ResponseStatus
    from practo_agent.tools.crewai_tools import lookup_appointment

    class UnauthorizedLookupLLM(BaseLLM):
        """Scripted model that makes the Composer request the lookup tool."""

        def __init__(self) -> None:
            super().__init__(model="scripted-unauthorized-lookup", provider="openai")
            self.messages: list = []

        def call(self, messages, tools=None, callbacks=None,
                 available_functions=None, from_task=None, from_agent=None,
                 response_model=None) -> str:
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

    # 1. Permitted access through the normal routed workflow.
    permitted_log = log_dir / "permitted.jsonl"
    os.environ["PRACTO_LOG_PATH"] = str(permitted_log)
    query = "What is the status of APT-0001?"
    llm = MockCrewAILLM(query=query)
    response = run_practo_query(query, llm=llm)
    permitted_events = _read_events(permitted_log)
    lookup_completions = [
        event for event in permitted_events
        if event["event"] == "tool_completed"
        and event.get("tool_name") == APPOINTMENT_LOOKUP_TOOL
    ]
    assert response.status == ResponseStatus.ANSWERED
    assert llm.tool_actions == [APPOINTMENT_LOOKUP_TOOL]
    assert len(lookup_completions) == 1
    assert not any(e["event"] == "tool_call_blocked" for e in permitted_events)

    # 2. Prohibited wiring is rejected before any crew runs.
    wiring_attempts = []
    for role in (RETRIEVAL_AGENT_ROLE, COMPOSER_AGENT_ROLE):
        try:
            authorize_agent_tools(role, [lookup_appointment])
        except ToolPermissionError as exc:
            wiring_attempts.append({"agent_role": role, "rejected": True, "error": str(exc)})
        else:
            raise AssertionError(f"Lookup tool wiring was not rejected for {role!r}.")

    # 3. A deliberately mis-wired agent assembled outside the factories.
    blocked_log = log_dir / "blocked.jsonl"
    os.environ["PRACTO_LOG_PATH"] = str(blocked_log)
    rogue_llm = UnauthorizedLookupLLM()
    composer = Agent(
        role=COMPOSER_AGENT_ROLE,
        goal="Compose answers.",
        backstory="Deliberately mis-wired with the lookup tool for this test.",
        tools=[lookup_appointment],
        llm=rogue_llm,
        verbose=False,
        allow_delegation=False,
    )
    task = Task(description="Answer the user.", expected_output="Text.", agent=composer)
    crew = Crew(agents=[composer], tasks=[task], process=Process.sequential,
                memory=False, verbose=False)

    try:
        enforce_crew_tool_permissions(crew)
    except ToolPermissionError as exc:
        crew_check_error = str(exc)
    else:
        raise AssertionError("The mis-wired crew passed the wiring check.")

    # Skip the wiring check on purpose to exercise the call-time guard.
    install_tool_call_guard()
    result = crew.kickoff()
    observation = rogue_llm.messages[-1][-2]["content"].split("Observation:", 1)[1].strip()
    blocked_events = _read_events(blocked_log)
    assert result.raw == "lookup refused"
    assert observation.startswith("Tool execution blocked by hook")
    assert [e["event"] for e in blocked_events] == ["tool_call_blocked"], blocked_events

    report = {
        "policy": {tool: sorted(roles) for tool, roles in TOOL_PERMISSIONS.items()},
        "risk_classification": {
            "system": {
                "subject": SYSTEM_RISK_CLASSIFICATION.subject,
                "level": SYSTEM_RISK_CLASSIFICATION.level.value,
                "justification": SYSTEM_RISK_CLASSIFICATION.justification,
            },
            "components": [
                {"subject": item.subject, "level": item.level.value,
                 "justification": item.justification}
                for item in COMPONENT_RISK_CLASSIFICATIONS
            ],
        },
        "permitted_lookup_agent_call": {
            "query": query,
            "status": response.status.value,
            "tool_actions": llm.tool_actions,
            "appointments": [item.record_id for item in response.appointments],
            "log_events": [
                {k: v for k, v in event.items() if k not in {"timestamp", "trace_id"}}
                for event in permitted_events
            ],
        },
        "prohibited_wiring": {
            "authorize_agent_tools": wiring_attempts,
            "enforce_crew_tool_permissions": {"rejected": True, "error": crew_check_error},
        },
        "prohibited_runtime_call": {
            "agent_role": COMPOSER_AGENT_ROLE,
            "requested_tool": APPOINTMENT_LOOKUP_TOOL,
            "tool_observation": observation,
            "final_answer": result.raw,
            "lookup_tool_executed": False,
            "log_events": [
                {k: v for k, v in event.items() if k not in {"timestamp", "trace_id"}}
                for event in blocked_events
            ],
        },
        "result_matches_expectation": True,
    }
    report_path = (
        Path(__file__).resolve().parents[1]
        / "evaluation" / "results" / "governance_demo.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

