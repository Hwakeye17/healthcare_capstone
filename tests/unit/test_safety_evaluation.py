"""Tests for the Milestone 4.4 zero-tolerance safety evaluation suite."""

import socket

import pytest

import practo_agent.evaluation.safety as safety_module
from practo_agent.evaluation import (
    REQUIRED_SAFETY_OBJECTIVES,
    SafetyScenarioResult,
    evaluate_safety_suite,
    format_safety_markdown_report,
)


@pytest.fixture
def block_network(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "true")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    original_connect = socket.socket.connect

    def _reject_external(sock, address):
        if address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(
                f"Safety evaluation attempted external network connection to {address[0]!r}."
            )
        return original_connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", _reject_external)


def test_safety_suite_passes_all_zero_tolerance_objectives(block_network):
    report = evaluate_safety_suite()

    assert report.mock_llm is True
    assert report.total_scenarios == 7
    assert report.passed_scenarios == 7
    assert report.failed_scenarios == 0
    assert report.pass_rate == 1.0
    assert report.unauthorized_appointment_tool_calls == 0
    assert report.unmasked_pii_in_logs == 0
    assert report.unsupported_medical_or_policy_leaks == 0
    assert report.missed_abstentions_or_injections == 0
    assert report.zero_tolerance_satisfied is True
    assert {item.objective for item in report.scenarios} == set(
        REQUIRED_SAFETY_OBJECTIVES
    )
    assert all(
        item.passed and item.zero_tolerance_violations == 0
        for item in report.scenarios
    )


def test_safety_report_serialization_and_markdown_rendering(block_network):
    report = evaluate_safety_suite()
    payload = report.to_dict()
    markdown = format_safety_markdown_report(report)

    assert payload["zero_tolerance_satisfied"] is True
    assert len(payload["scenarios"]) == 7
    assert "9876543210" not in str(payload)
    assert "+91-91234-56789" not in str(payload)
    assert "# Safety Evaluation Report" in markdown
    assert "**Zero-tolerance gate:** `PASSED`" in markdown
    for scenario in report.scenarios:
        assert scenario.scenario_id in markdown
        assert scenario.objective in markdown


def test_safety_suite_fails_closed_when_unauthorized_lookup_occurs(
    block_network,
    monkeypatch,
):
    monkeypatch.setattr(
        safety_module,
        "_check_unauthorized_appointment_access",
        lambda log_dir: SafetyScenarioResult(
            scenario_id="SAF-04",
            objective="no_unauthorized_appointment_data_access",
            description="Simulated unauthorized lookup breach.",
            passed=False,
            zero_tolerance_violations=1,
            evidence={
                "wiring_rejected_by_role": {},
                "crew_wiring_rejected": False,
                "unauthorized_tool_executions": 1,
                "blocked_event_logged": False,
                "record_id_in_log": False,
            },
            failure_reason="Simulated unauthorized appointment tool call.",
        ),
    )

    report = evaluate_safety_suite()

    assert report.zero_tolerance_satisfied is False
    assert report.failed_scenarios == 1
    assert report.unauthorized_appointment_tool_calls == 1
    assert "**Zero-tolerance gate:** `FAILED`" in format_safety_markdown_report(
        report
    )


def test_safety_suite_fails_closed_when_pii_reaches_logs(
    block_network,
    monkeypatch,
):
    monkeypatch.setattr(
        safety_module,
        "_check_pii_protection",
        lambda log_dir: SafetyScenarioResult(
            scenario_id="SAF-05",
            objective="no_unmasked_pii_in_logs",
            description="Simulated unmasked PII leak.",
            passed=False,
            zero_tolerance_violations=1,
            evidence={
                "redacted_routing_input": "",
                "unmasked_pii_in_logs": 1,
                "unmasked_pii_in_prompts_or_memory": 0,
                "log_record_count": 1,
                "all_log_records_have_trace_id": True,
            },
            failure_reason="Simulated unmasked PII in logs.",
        ),
    )

    report = evaluate_safety_suite()

    assert report.zero_tolerance_satisfied is False
    assert report.failed_scenarios == 1
    assert report.unmasked_pii_in_logs == 1


def test_safety_suite_rejects_missing_objective_coverage(
    block_network,
    monkeypatch,
):
    monkeypatch.setattr(
        safety_module,
        "_check_prompt_injection",
        lambda: SafetyScenarioResult(
            scenario_id="SAF-07",
            objective="duplicate_objective",
            description="Invalid objective label.",
            passed=True,
            zero_tolerance_violations=0,
            evidence={},
        ),
    )

    with pytest.raises(RuntimeError, match="missing required objectives"):
        evaluate_safety_suite()

