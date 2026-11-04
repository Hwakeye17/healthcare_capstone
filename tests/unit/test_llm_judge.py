import json

import pytest

from practo_agent.config.runtime_budget import RuntimeBudget
from practo_agent.evaluation.llm_judge import (
    DEFAULT_CASES_PATH,
    DimensionScore,
    GroqResponseJudge,
    QualityEvaluationCase,
    ResponseQualityScores,
    load_quality_cases,
    run_quality_evaluation,
    validate_live_mode,
    write_quality_report,
)
from practo_agent.schemas import AgentResponse, ResponseStatus


def _scores(
    accuracy: int = 4,
    grounding: int = 5,
    completeness: int = 3,
    safety: int = 5,
) -> ResponseQualityScores:
    return ResponseQualityScores(
        accuracy=DimensionScore(
            score=accuracy,
            justification="The response matches the reference facts.",
        ),
        grounding=DimensionScore(
            score=grounding,
            justification="The factual claims are supported.",
        ),
        completeness=DimensionScore(
            score=completeness,
            justification="One requested detail is missing.",
        ),
        safety=DimensionScore(
            score=safety,
            justification="The response avoids unsafe advice.",
        ),
    )


def _case() -> QualityEvaluationCase:
    return QualityEvaluationCase(
        query_id="QUALITY-TEST",
        query="How can I book an appointment?",
        case_type="knowledge_base",
        expected_source_ids=("appointment_booking",),
        appointment_record_ids=(),
        expected_behavior="Describe the documented booking process.",
    )


def test_quality_cases_cover_all_topics_and_include_safety_edges():
    cases = load_quality_cases()

    assert len(cases) == 15
    assert {
        source_id
        for case in cases
        for source_id in case.expected_source_ids
    } == {
        "appointment_booking",
        "cancellation_rescheduling",
        "fee_structure",
        "insurance_claims",
        "prescription_refills",
        "lab_turnaround",
        "telemedicine",
        "emergency_visits",
        "privacy_policy",
        "follow_up_discounts",
        "second_opinions",
        "home_visits",
    }
    assert sum(
        case.case_type in {"out_of_scope", "edge_case"}
        for case in cases
    ) >= 2


def test_quality_case_loader_rejects_missing_knowledge_topic(tmp_path):
    case_path = (
        tmp_path
        / "response_quality_cases.json"
    )
    cases = json.loads(DEFAULT_CASES_PATH.read_text(encoding="utf-8"))
    home_visit_case = next(
        case
        for case in cases
        if case["expected_source_ids"] == ["home_visits"]
    )
    home_visit_case["expected_source_ids"] = ["appointment_booking"]
    case_path.write_text(json.dumps(cases), encoding="utf-8")

    with pytest.raises(ValueError, match="cover every knowledge-base topic"):
        load_quality_cases(case_path)


def test_judge_scores_are_bounded_and_require_justifications():
    with pytest.raises(ValueError):
        DimensionScore(score=0, justification="Out of range.")
    with pytest.raises(ValueError):
        DimensionScore(score=5, justification="")


def test_groq_judge_uses_json_mode_with_local_schema_validation(monkeypatch):
    import langchain_groq

    calls = {}

    class FakeChatGroq:
        def __init__(self, **kwargs):
            calls["client"] = kwargs

        def with_structured_output(self, schema, **kwargs):
            calls["schema"] = schema
            calls["structured_output"] = kwargs
            return object()

    monkeypatch.setattr(langchain_groq, "ChatGroq", FakeChatGroq)
    monkeypatch.setenv("MOCK_LLM", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    GroqResponseJudge()

    assert calls["schema"] is ResponseQualityScores
    assert calls["structured_output"] == {
        "method": "json_mode",
        "include_raw": True,
        "strict": False,
    }


def test_groq_judge_retries_once_when_json_does_not_match_schema():
    judge = GroqResponseJudge.__new__(GroqResponseJudge)

    class FakeStructuredClient:
        def __init__(self):
            self.results = [
                {"parsed": None, "parsing_error": ValueError("Invalid JSON shape.")},
                {"parsed": _scores(), "parsing_error": None},
            ]
            self.prompts = []

        def invoke(self, prompt):
            self.prompts.append(prompt)
            return self.results.pop(0)

    client = FakeStructuredClient()
    judge._llm = client
    budget = RuntimeBudget()
    scores = judge.evaluate(
        query=_case().query,
        expected_behavior=_case().expected_behavior,
        response=AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer="Please contact the clinic for assistance.",
            reason="Insufficient information is available.",
        ),
        reference_context={},
        runtime_budget=budget,
    )

    assert scores == _scores()
    assert len(client.prompts) == 2
    assert "Your previous JSON did not match" in client.prompts[1]
    assert budget.stats["llm_calls"] == 2


def test_groq_judge_fails_when_correction_attempt_is_still_invalid():
    judge = GroqResponseJudge.__new__(GroqResponseJudge)

    class InvalidStructuredClient:
        def invoke(self, prompt):
            return {
                "parsed": None,
                "parsing_error": ValueError("Invalid JSON shape."),
            }

    judge._llm = InvalidStructuredClient()
    with pytest.raises(ValueError, match="after one format-correction attempt"):
        judge.evaluate(
            query=_case().query,
            expected_behavior=_case().expected_behavior,
            response=AgentResponse(
                status=ResponseStatus.ABSTAINED,
                answer="Please contact the clinic for assistance.",
                reason="Insufficient information is available.",
            ),
            reference_context={},
            runtime_budget=RuntimeBudget(),
        )


def test_live_evaluation_rejects_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")

    with pytest.raises(ValueError, match="cannot run in MOCK_LLM mode"):
        validate_live_mode()


def test_quality_evaluation_uses_judge_scores_and_computes_averages():
    response = AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer="Please contact the clinic for assistance.",
        reason="Insufficient information is available.",
    )

    class FakeAssistant:
        def __init__(self):
            self.queries = []

        def __call__(self, query: str, budget: RuntimeBudget):
            self.queries.append(query)
            return response

    class FakeJudge:
        def __init__(self):
            self.reference_contexts = []

        def evaluate(
            self,
            *,
            query,
            expected_behavior,
            response,
            reference_context,
            runtime_budget,
        ):
            self.reference_contexts.append(reference_context)
            runtime_budget.reserve_llm_call("controlled test judge call")
            return _scores()

    assistant = FakeAssistant()
    judge = FakeJudge()
    results = run_quality_evaluation(
        [_case()],
        assistant=assistant,
        judge=judge,
        reference_loader=lambda case: {
            "knowledge_sources": [],
            "appointment_records": [],
        },
    )

    assert assistant.queries == [_case().query]
    assert results["query_count"] == 1
    assert results["averages"] == {
        "accuracy": 4.0,
        "grounding": 5.0,
        "completeness": 3.0,
        "safety": 5.0,
    }
    assert results["queries"][0]["scores"]["grounding"]["justification"]
    assert results["queries"][0]["estimated_usage"]["llm_calls"] == 1


def test_quality_evaluation_rejects_invalid_assistant_output():
    class FakeJudge:
        def evaluate(self, **kwargs):
            return _scores()

    with pytest.raises(TypeError, match="invalid response"):
        run_quality_evaluation(
            [_case()],
            assistant=lambda query, budget: "not an AgentResponse",
            judge=FakeJudge(),
            reference_loader=lambda case: {},
        )


def test_quality_report_contains_per_query_scores_and_justifications(tmp_path):
    response = AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer="Please contact the clinic for assistance.",
        reason="Insufficient information is available.",
    )

    class FakeJudge:
        def evaluate(self, **kwargs):
            return _scores()

    results = run_quality_evaluation(
        [_case()],
        assistant=lambda query, budget: response,
        judge=FakeJudge(),
        reference_loader=lambda case: {},
    )
    json_path = tmp_path / "response_quality_results.json"
    markdown_path = tmp_path / "response_quality_report.md"
    write_quality_report(results, json_path, markdown_path)

    saved_results = json.loads(json_path.read_text(encoding="utf-8"))
    report = markdown_path.read_text(encoding="utf-8")
    assert saved_results["queries"][0]["query_id"] == "QUALITY-TEST"
    assert "Accuracy (4/5)" in report
    assert "The response matches the reference facts." in report
    assert "Average" not in report
