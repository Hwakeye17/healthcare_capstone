"""Demonstrate approval and correction in the offline AutoGen review stage."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "autogen_review_demo.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from autogen_core.models import ModelFamily
    from autogen_ext.models.replay import ReplayChatCompletionClient

    from practo_agent.review import review_response
    from practo_agent.review.schemas import (
        FinalEditorOutput,
        ReviewFeedback,
    )
    from practo_agent.rag.groundedness import MockGroundednessValidator
    from practo_agent.schemas import (
        AgentResponse,
        ResponseStatus,
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
    model_info = {
        "vision": False,
        "function_calling": False,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
    }

    def run_case(
        *,
        query: str,
        draft: str,
        feedback: ReviewFeedback,
        final_answer: str,
    ):
        model_client = ReplayChatCompletionClient(
            [
                feedback.model_dump_json(),
                FinalEditorOutput(
                    status=ResponseStatus.ANSWERED,
                    answer=final_answer,
                ).model_dump_json(),
            ],
            model_info=model_info,
        )
        response = AgentResponse(
            status=ResponseStatus.ANSWERED,
            answer=draft,
            sources=[
                SourceReference(
                    source_id=evidence.source_id,
                    title=evidence.title,
                )
            ],
        )
        result = review_response(
            response,
            [evidence],
            query=query,
            model_client=model_client,
        )
        if result.response.status != ResponseStatus.ANSWERED:
            raise RuntimeError("The review unexpectedly abstained.")
        groundedness = MockGroundednessValidator().validate(
            result.response.answer,
            [evidence],
        )
        if not groundedness.grounded:
            raise RuntimeError("The final response is not supported by evidence.")
        if result.agent_turns != 2:
            raise RuntimeError("The review did not use exactly two agent turns.")
        return result

    approved_answer = evidence.text
    approved_result = run_case(
        query="When is an appointment confirmed?",
        draft=approved_answer,
        feedback=ReviewFeedback(approved=True),
        final_answer=approved_answer,
    )

    unsupported_draft = "Every appointment is automatically confirmed."
    corrected_answer = evidence.text
    revised_result = run_case(
        query="When is an appointment confirmed?",
        draft=unsupported_draft,
        feedback=ReviewFeedback(
            approved=False,
            issues=[
                "The claim of automatic confirmation is not supported by "
                "the evidence."
            ],
        ),
        final_answer=corrected_answer,
    )
    if approved_result.response.answer != approved_answer:
        raise RuntimeError("The approved response was unnecessarily revised.")
    if unsupported_draft in revised_result.response.answer:
        raise RuntimeError("The unsupported claim remained in the final answer.")
    if revised_result.response.answer != corrected_answer:
        raise RuntimeError("The unsupported response was not corrected.")

    report = {
        "demo": "autogen_two_agent_response_review",
        "mock_llm": True,
        "cases": [
            {
                "name": "approved_unchanged",
                "query": "When is an appointment confirmed?",
                "reviewer_approved": approved_result.feedback.approved,
                "issues": approved_result.feedback.issues,
                "draft": approved_answer,
                "final_answer": approved_result.response.answer,
                "preserved_unchanged": not approved_result.revised,
                "agent_turns": approved_result.agent_turns,
            },
            {
                "name": "unsupported_draft_revised",
                "query": "When is an appointment confirmed?",
                "reviewer_approved": revised_result.feedback.approved,
                "issues": revised_result.feedback.issues,
                "draft": unsupported_draft,
                "final_answer": revised_result.response.answer,
                "preserved_unchanged": not revised_result.revised,
                "agent_turns": revised_result.agent_turns,
            },
        ],
        "final_outputs_grounded": True,
        "passed": True,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Offline AutoGen review demonstration passed.")
    print("Approved response was preserved without revision.")
    print("Unsupported response was corrected and grounded in evidence.")
    print(f"Transcript saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
