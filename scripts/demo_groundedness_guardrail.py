"""Demonstrate rejection of unsupported CrewAI response claims."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "groundedness_guardrail_demo.json"
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
    from practo_agent.rag.groundedness import MockGroundednessValidator
    from practo_agent.schemas import (
        AgentResponse,
        EvidenceAssessment,
        ResponseStatus,
        RetrievalAgentOutput,
        RetrievalAgentStatus,
        RetrievedEvidence,
        SourceReference,
    )

    evidence = RetrievedEvidence(
        chunk_id="appointment_booking::sentence::0001",
        text=(
            "Appointment requests remain pending until the clinic or booking "
            "system confirms the slot."
        ),
        source_id="appointment_booking",
        title="Appointment Booking",
        distance=0.25,
    )
    retrieval_output = RetrievalAgentOutput(
        used=True,
        status=RetrievalAgentStatus.SUCCESS,
        assessment=EvidenceAssessment(
            accepted=True,
            best_distance=evidence.distance,
            threshold=0.6976266205310822,
            evidence=[evidence],
            reason="Evidence passed the configured threshold.",
        ),
    )
    unsupported_claim = "Every appointment is automatically confirmed."
    generated_response = AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=unsupported_claim,
        sources=[
            SourceReference(
                source_id=evidence.source_id,
                title=evidence.title,
            )
        ],
    )
    retrieval_task = SimpleNamespace(
        agent=SimpleNamespace(
            role="Practo Knowledge Retrieval Specialist",
        )
    )
    composition_task = SimpleNamespace(
        agent=SimpleNamespace(
            role="Practo Support Response Composer",
        )
    )

    class AdversarialDemoCrew:
        tasks = [retrieval_task, composition_task]

        def kickoff(self, inputs):
            return SimpleNamespace(
                tasks_output=[
                    SimpleNamespace(raw=retrieval_output.model_dump_json()),
                    SimpleNamespace(raw=generated_response.model_dump_json()),
                ],
                raw=generated_response.model_dump_json(),
            )

    validator = MockGroundednessValidator()
    with patch.object(
        workflow,
        "create_practo_crew",
        return_value=AdversarialDemoCrew(),
    ):
        response = workflow.run_practo_query(
            "When is an appointment confirmed?",
            groundedness_validator=validator,
        )

    if response.status != ResponseStatus.ABSTAINED:
        raise RuntimeError("The unsupported response was not rejected.")
    if response.answer == unsupported_claim:
        raise RuntimeError("The unsupported claim escaped the guardrail.")
    if response.sources or response.appointments:
        raise RuntimeError("Rejected response retained supporting references.")

    report = {
        "demo": "crew_response_groundedness_guardrail",
        "mock_llm": True,
        "test_claim": unsupported_claim,
        "evidence_source": evidence.source_id,
        "response_status": response.status.value,
        "unsupported_claim_returned": False,
        "response": response.model_dump(mode="json"),
        "passed": True,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("CrewAI groundedness guardrail demonstration passed.")
    print("An unsupported generated claim was rejected.")
    print(f"Transcript saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
