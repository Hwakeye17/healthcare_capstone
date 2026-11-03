"""Demonstrate contact-number masking before routing and LLM execution."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "input_guardrail_demo.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from practo_agent.agents import workflow
    from practo_agent.agents.mock_llm import MockCrewAILLM
    from practo_agent.agents.routing import route_query
    from practo_agent.config import create_crewai_llm
    from practo_agent.schemas import ResponseStatus

    contact_number = "9876543210"
    raw_query = (
        f"My contact number is {contact_number}. "
        "How can I reschedule my existing doctor appointment?"
    )
    routed_queries = []

    def record_route(query: str):
        routed_queries.append(query)
        return route_query(query)

    llm = create_crewai_llm(query=raw_query)
    if not isinstance(llm, MockCrewAILLM):
        raise TypeError("The offline demonstration did not create MockCrewAILLM.")

    with patch.object(
        workflow,
        "route_query",
        side_effect=record_route,
    ):
        response = workflow.run_practo_query(raw_query, llm=llm)

    if len(routed_queries) != 1:
        raise RuntimeError(
            f"Expected one routing decision; observed {len(routed_queries)}."
        )

    routing_input = routed_queries[0]
    mock_llm_input = llm.query
    expected_masked_query = (
        "My contact number is [REDACTED_CONTACT_NUMBER]. "
        "How can I reschedule my existing doctor appointment?"
    )

    if routing_input != expected_masked_query:
        raise RuntimeError(
            "The router did not receive the expected sanitized request."
        )
    if mock_llm_input != expected_masked_query:
        raise RuntimeError(
            "The mock LLM did not receive the expected sanitized request."
        )
    if contact_number in response.answer:
        raise RuntimeError(
            "The final response contains the unmasked synthetic number."
        )
    if "search_practo_knowledge_base" not in llm.tool_actions:
        raise RuntimeError(
            "The offline Crew did not execute its expected retrieval tool."
        )
    if response.status != ResponseStatus.ANSWERED:
        raise RuntimeError(
            f"The demonstration query was not answered: {response.reason}"
        )

    report = {
        "demo": "input_contact_number_masking",
        "mock_llm": True,
        "synthetic_input": (
            f"My contact number is [SYNTHETIC_CONTACT_NUMBER]. "
            "How can I reschedule my existing doctor appointment?"
        ),
        "raw_synthetic_number_persisted": False,
        "routing_input": routing_input,
        "mock_llm_input": mock_llm_input,
        "tool_actions": llm.tool_actions,
        "response": response.model_dump(mode="json"),
        "passed": True,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized_report = json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    )
    if contact_number in serialized_report:
        raise RuntimeError(
            "The demonstration report must not persist the raw test number."
        )
    RESULTS_PATH.write_text(serialized_report + "\n", encoding="utf-8")

    print("Contact-number masking demonstration passed.")
    print(f"Routing received: {routing_input}")
    print(f"Mock LLM received: {mock_llm_input}")
    print(f"Tool actions: {', '.join(llm.tool_actions)}")
    print(f"Transcript saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
