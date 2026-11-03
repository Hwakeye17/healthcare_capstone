
"""Demonstrate the Practo CrewAI support agents with live Groq calls."""

import re
import sys
from pathlib import Path

from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from practo_agent.agents.crew import create_practo_crew
from practo_agent.config.llm import create_crewai_llm, get_llm_config
from practo_agent.schemas.agent_outputs import (
    AgentResponse,
    LookupAgentOutput,
    RetrievalAgentOutput,
)
from practo_agent.schemas.response import ResponseStatus


SCENARIOS = [
    {
        "name": "RAG ONLY",
        "query": "How can I reschedule my existing doctor appointment?",
        "retrieval_enabled": True,
        "lookup_enabled": False,
        "expected_answer_fragments": ("24 hours",),
    },
    {
        "name": "APPOINTMENT LOOKUP ONLY",
        "query": (
            "Please check the status and consultation fee "
            "for appointment APT-0001."
        ),
        "retrieval_enabled": False,
        "lookup_enabled": True,
        "expected_answer_fragments": ("cancelled", "500"),
    },
    {
        "name": "COMBINED QUERY",
        "query": (
            "How can I reschedule my existing doctor appointment? "
            "Also check the status and consultation fee for APT-0001."
        ),
        "retrieval_enabled": True,
        "lookup_enabled": True,
        "expected_answer_fragments": ("24 hours", "cancelled", "500"),
    },
]


def validate_task_output(task_output, model):
    """Parse raw task JSON and validate it against the Pydantic contract."""

    raw_output = task_output.raw

    if not isinstance(raw_output, str) or not raw_output.strip():
        raise ValueError("Task did not produce a non-empty text output.")

    cleaned_output = re.sub(
        r"^\s*```(?:json)?\s*|\s*```\s*$",
        "",
        raw_output.strip(),
        flags=re.IGNORECASE,
    )

    try:
        return model.model_validate_json(cleaned_output)
    except ValidationError as exc:
        raise ValueError(
            f"{model.__name__} validation failed. "
            f"Raw task output:\n{raw_output}"
        ) from exc


def print_output(label: str, value) -> None:
    """Print a validated Pydantic model."""

    print(f"\n{'-' * 80}")
    print(label)
    print("-" * 80)
    print(value.model_dump_json(indent=2))


def get_expected_output_models(scenario: dict) -> list:
    """Return expected task output schemas in Crew execution order."""

    models = []

    if scenario["retrieval_enabled"]:
        models.append(RetrievalAgentOutput)

    if scenario["lookup_enabled"]:
        models.append(LookupAgentOutput)

    # The Response Composer always executes last.
    models.append(AgentResponse)

    return models


def run_scenario(llm, scenario: dict) -> AgentResponse:
    """Run one scenario using a fresh Crew instance."""

    print("\n" + "=" * 80)
    print(f"SCENARIO: {scenario['name']}")
    print(f"USER QUERY: {scenario['query']}")
    print("=" * 80)

    print(
        "RETRIEVAL TASK: "
        f"{'ENABLED' if scenario['retrieval_enabled'] else 'DISABLED'}"
    )
    print(
        "LOOKUP TASK: "
        f"{'ENABLED' if scenario['lookup_enabled'] else 'DISABLED'}"
    )

    crew = create_practo_crew(
        llm=llm,
        verbose=False,
        retrieval_enabled=scenario["retrieval_enabled"],
        lookup_enabled=scenario["lookup_enabled"],
    )

    expected_models = get_expected_output_models(scenario)

    print(f"EXPECTED TASK OUTPUTS: {len(expected_models)}")

    result = crew.kickoff(
        inputs={"user_query": scenario["query"]}
    )

    actual_outputs = result.tasks_output

    if len(actual_outputs) != len(expected_models):
        raise ValueError(
            "Unexpected number of task outputs. "
            f"Expected {len(expected_models)}, "
            f"received {len(actual_outputs)}."
        )

    validated_outputs = []

    for index, (task_output, model) in enumerate(
        zip(actual_outputs, expected_models),
        start=1,
    ):
        validated_output = validate_task_output(
            task_output,
            model,
        )

        validated_outputs.append(validated_output)

        print_output(
            f"TASK {index}: {model.__name__}",
            validated_output,
        )

    final_response = validated_outputs[-1]

    if not isinstance(final_response, AgentResponse):
        raise TypeError(
            "The final task did not produce an AgentResponse."
        )

    if final_response.status != ResponseStatus.ANSWERED:
        raise RuntimeError(
            f"{scenario['name']} did not produce a supported answer: "
            f"{final_response.reason}"
        )

    actual_sources = {source.source_id for source in final_response.sources}
    retrieval_output = next(
        (
            output
            for output in validated_outputs
            if isinstance(output, RetrievalAgentOutput)
        ),
        None,
    )
    if retrieval_output is None or retrieval_output.assessment is None:
        supported_sources = set()
    else:
        supported_sources = {
            evidence.source_id
            for evidence in retrieval_output.assessment.evidence
        }
    if not actual_sources.issubset(supported_sources):
        raise RuntimeError(
            f"{scenario['name']} cited sources not present in the validated "
            f"retrieval evidence: {sorted(actual_sources - supported_sources)}."
        )

    lookup_output = next(
        (
            output
            for output in validated_outputs
            if isinstance(output, LookupAgentOutput)
        ),
        None,
    )
    expected_appointments = (
        {lookup_output.appointment.record_id}
        if lookup_output is not None and lookup_output.appointment is not None
        else set()
    )
    actual_appointments = {
        appointment.record_id for appointment in final_response.appointments
    }
    if actual_appointments != expected_appointments:
        raise RuntimeError(
            f"{scenario['name']} returned unexpected appointment references. "
            f"Expected {sorted(expected_appointments)}, "
            f"got {sorted(actual_appointments)}."
        )

    answer = final_response.answer.casefold()
    missing_fragments = [
        fragment
        for fragment in scenario["expected_answer_fragments"]
        if fragment.casefold() not in answer
    ]
    if missing_fragments:
        raise RuntimeError(
            f"{scenario['name']} omitted expected answer details: "
            f"{missing_fragments}."
        )

    print_output(
        "FINAL VALIDATED CREW RESPONSE",
        final_response,
    )

    return final_response


def main() -> None:
    """Run all demonstration scenarios using the configured live LLM."""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="backslashreplace",
        )

    config = get_llm_config()

    if config["mock_mode"]:
        raise RuntimeError(
            "This demonstration requires live Groq calls. "
            "Set MOCK_LLM=false in the current PowerShell session."
        )

    print("=" * 80)
    print("PRACTO SUPPORT AGENT DEMONSTRATION")
    print(f"LLM MODEL: {config['model']}")
    print("=" * 80)

    print("\nInitializing CrewAI with the configured Groq model...")
    llm = create_crewai_llm()

    for scenario in SCENARIOS:
        run_scenario(llm, scenario)

    print("\n" + "=" * 80)
    print("ALL DEMONSTRATION SCENARIOS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()
