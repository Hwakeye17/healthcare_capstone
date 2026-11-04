"""Behavioral acceptance test suite covering all 20 required capstone scenarios."""

import json
import pytest

import main as root_entrypoint
from practo_agent.evaluation import (
    REQUIRED_ACCEPTANCE_SCENARIOS,
    AcceptanceEvaluationReport,
    format_acceptance_markdown_report,
    run_acceptance_suite,
)
from practo_agent.schemas import AgentResponse, ResponseStatus


def test_all_twenty_acceptance_scenarios_pass_offline():
    report = run_acceptance_suite()

    assert report.all_passed is True
    assert report.mock_llm_mode is True
    assert report.keyless_execution is True
    assert report.zero_external_network_calls is True
    assert report.total_scenarios == 20
    assert report.passed_scenarios == 20
    assert report.failed_scenarios == 0

    by_id = {s.scenario_id: s for s in report.scenarios}
    assert set(by_id) == set(REQUIRED_ACCEPTANCE_SCENARIOS)

    for scenario_id in REQUIRED_ACCEPTANCE_SCENARIOS:
        scenario = by_id[scenario_id]
        assert scenario.passed is True, f"Scenario {scenario_id} failed: {scenario.evidence}"

    # Verify specific behavioral outcomes across key scenarios
    assert "cancellation_rescheduling" in by_id["in_scope_administrative_query"].evidence["sources"]
    assert by_id["out_of_scope_abstention"].evidence["status"] == "abstained"
    assert by_id["valid_appointment_lookup"].evidence["appointments"] == ["APT-0001"]
    assert by_id["valid_appointment_lookup"].evidence["escalation_score_present"] is True
    assert by_id["invalid_appointment_lookup"].evidence["status"] == "abstained"
    assert by_id["combined_rag_and_appointment_query"].evidence["tool_actions"] == [
        "search_practo_knowledge_base",
        "check_appointment_status",
    ]
    assert by_id["prompt_injection_rejection"].evidence["llm_call_count"] == 0
    assert by_id["contact_number_pii_masking"].evidence["raw_phone_in_memory"] is False
    assert by_id["multi_turn_conversation_memory"].evidence["stored_message_count"] == 4
    assert by_id["fresh_session_isolation"].evidence["messages_before_first_turn"] == 0
    assert by_id["response_cache_hit"].evidence["cache_stats"]["hits"] == 1
    assert by_id["response_cache_miss"].evidence["cache_stats"]["misses"] == 2
    assert by_id["oversized_input_budget_rejection"].evidence["budget_stats"]["rejected"] is True
    assert by_id["fastapi_http_endpoints"].evidence["trace_header_present"] is True
    assert by_id["fastapi_websocket_conversation"].evidence["stored_messages"] == 4
    assert by_id["graceful_websocket_disconnect"].evidence["subsequent_connection_status"] == "answered"
    assert by_id["autogen_approved_response"].evidence["approved"] is True
    assert by_id["autogen_approved_response"].evidence["revised"] is False
    assert by_id["autogen_revised_response"].evidence["revised"] is True
    assert by_id["governance_permission_enforcement"].evidence["unauthorized_wiring_blocked"] is True
    assert by_id["structured_jsonl_logging_and_traces"].evidence["raw_phone_in_logs"] is False
    assert by_id["clean_offline_mock_llm_execution"].evidence["external_network_calls"] == 0


def test_acceptance_report_rejects_missing_scenario_or_failed_flag():
    report = run_acceptance_suite()
    raw = report.model_dump(mode="json")

    # Dropping one scenario must fail validation
    missing_one = dict(raw)
    missing_one["scenarios"] = raw["scenarios"][:-1]
    missing_one["total_scenarios"] = 19
    missing_one["passed_scenarios"] = 19
    with pytest.raises(ValueError):
        AcceptanceEvaluationReport.model_validate(missing_one)

    # Claiming all_passed=True when a scenario failed must fail validation
    tampered = dict(raw)
    tampered_scenarios = [dict(item) for item in raw["scenarios"]]
    tampered_scenarios[0]["passed"] = False
    tampered["scenarios"] = tampered_scenarios
    tampered["passed_scenarios"] = 19
    tampered["failed_scenarios"] = 1
    tampered["all_passed"] = True
    with pytest.raises(ValueError, match="all_passed"):
        AcceptanceEvaluationReport.model_validate(tampered)


def test_acceptance_markdown_report_contains_all_twenty_scenarios():
    report = run_acceptance_suite()
    markdown = format_acceptance_markdown_report(report)

    assert "# End-to-End Acceptance Evaluation Report" in markdown
    assert "`20/20`" in markdown
    for scenario_id in REQUIRED_ACCEPTANCE_SCENARIOS:
        assert f"`{scenario_id}`" in markdown


def test_root_main_cli_executes_offline_without_api_keys(monkeypatch, capsys):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    root_entrypoint.main()
    captured = capsys.readouterr().out
    parsed = AgentResponse.model_validate(json.loads(captured))
    assert parsed.status == ResponseStatus.ANSWERED
    assert [a.record_id for a in parsed.appointments] == ["APT-0001"]

