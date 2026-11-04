import pytest
from autogen_core.models import ModelFamily
from autogen_ext.models.replay import ReplayChatCompletionClient

from practo_agent.config.llm import GROQ_BASE_URL
from practo_agent.review import review_response
from practo_agent.review.workflow import _GroqJSONModeClient
from practo_agent.review.schemas import FinalEditorOutput, ReviewFeedback
from practo_agent.config.runtime_budget import RuntimeBudget
from practo_agent.schemas import (
    AgentResponse,
    ResponseStatus,
    RetrievedEvidence,
    SourceReference,
)


_MODEL_INFO = {
    "vision": False,
    "function_calling": False,
    "json_output": True,
    "family": ModelFamily.UNKNOWN,
    "structured_output": True,
}
_EVIDENCE = RetrievedEvidence(
    chunk_id="appointment_booking::sentence::0001",
    text=(
        "Appointment requests remain pending until the clinic or booking "
        "system confirms the slot."
    ),
    source_id="appointment_booking",
    title="Appointment Booking",
    distance=0.25,
)


def _client(
    feedback: ReviewFeedback,
    output: FinalEditorOutput,
) -> ReplayChatCompletionClient:
    return ReplayChatCompletionClient(
        [feedback.model_dump_json(), output.model_dump_json()],
        model_info=_MODEL_INFO,
    )


def _response(answer: str) -> AgentResponse:
    return AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=answer,
        sources=[
            SourceReference(
                source_id=_EVIDENCE.source_id,
                title=_EVIDENCE.title,
            )
        ],
    )


def test_approved_draft_is_preserved_in_two_agent_turns():
    draft = (
        "Appointment requests remain pending until the clinic or booking "
        "system confirms the slot."
    )
    budget = RuntimeBudget()
    result = review_response(
        _response(draft),
        [_EVIDENCE],
        query="When is an appointment confirmed?",
        runtime_budget=budget,
        model_client=_client(
            ReviewFeedback(approved=True),
            FinalEditorOutput(
                status=ResponseStatus.ANSWERED,
                answer=draft,
            ),
        ),
    )

    assert result.response.answer == draft
    assert result.response.sources == _response(draft).sources
    assert result.feedback.approved is True
    assert result.revised is False
    assert result.agent_turns == 2
    assert budget.stats["llm_calls"] == 2


def test_unsupported_draft_is_revised_without_new_claims():
    draft = "Every appointment is automatically confirmed."
    corrected = (
        "Appointment requests remain pending until the clinic or booking "
        "system confirms the slot."
    )
    result = review_response(
        _response(draft),
        [_EVIDENCE],
        query="When is an appointment confirmed?",
        model_client=_client(
            ReviewFeedback(
                approved=False,
                issues=["The automatic-confirmation claim is unsupported."],
            ),
            FinalEditorOutput(
                status=ResponseStatus.ANSWERED,
                answer=corrected,
            ),
        ),
    )

    assert result.feedback.approved is False
    assert result.response.answer == corrected
    assert draft not in result.response.answer
    assert result.response.sources == _response(draft).sources
    assert result.revised is True
    assert result.agent_turns == 2


def test_final_editor_cannot_change_an_approved_draft():
    draft = _EVIDENCE.text
    with pytest.raises(RuntimeError, match="reviewer approved"):
        review_response(
            _response(draft),
            [_EVIDENCE],
            model_client=_client(
                ReviewFeedback(approved=True),
                FinalEditorOutput(
                    status=ResponseStatus.ANSWERED,
                    answer="A different answer.",
                ),
            ),
        )


def test_final_editor_cannot_return_a_response_rejected_by_reviewer():
    draft = "Every appointment is automatically confirmed."
    with pytest.raises(RuntimeError, match="rejected by the reviewer"):
        review_response(
            _response(draft),
            [_EVIDENCE],
            model_client=_client(
                ReviewFeedback(
                    approved=False,
                    issues=["The automatic-confirmation claim is unsupported."],
                ),
                FinalEditorOutput(
                    status=ResponseStatus.ANSWERED,
                    answer=draft,
                ),
            ),
        )


def test_reviewer_feedback_requires_issues_when_not_approved():
    with pytest.raises(ValueError, match="must identify review issues"):
        ReviewFeedback(approved=False)


def test_review_requires_evidence():
    with pytest.raises(ValueError, match="At least one validated evidence"):
        review_response(
            _response(_EVIDENCE.text),
            [],
        )


def test_groq_review_client_uses_json_mode_for_typed_output():
    client = _GroqJSONModeClient(
        model="qwen/qwen3.8-27b",
        api_key="test-key",
        base_url=GROQ_BASE_URL,
        model_info=_MODEL_INFO,
    )
    params = client._process_create_args(
        messages=[],
        tools=[],
        tool_choice="auto",
        json_output=ReviewFeedback,
        extra_create_args={},
    )

    assert params.create_args["response_format"] == {"type": "json_object"}
    assert params.response_format is None
