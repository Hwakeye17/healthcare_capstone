import json

import pytest

from practo_agent.observability.events import (
    JsonlEventLogger,
    current_trace_id,
    log_event,
    request_trace,
)


def test_request_trace_correlates_safe_jsonl_events(tmp_path, monkeypatch):
    log_path = tmp_path / "nested" / "events.jsonl"
    logger = JsonlEventLogger(log_path)
    monkeypatch.setenv("PRACTO_LOG_PATH", str(log_path))
    monkeypatch.setattr(
        "practo_agent.observability.events._default_logger",
        logger,
    )
    monkeypatch.setattr(
        "practo_agent.observability.events._default_logger_path",
        log_path,
    )
    query = "Contact 9876543210 about appointment APT-0001"

    with request_trace("http", "query") as trace:
        trace_id = current_trace_id()
        log_event(
            "workflow_routed",
            retrieval_enabled=True,
            lookup_enabled=True,
            clarification_required=False,
        )
        log_event(
            "tool_completed",
            tool_name="check_appointment_status",
            tool_status="success",
        )
        trace.complete(
            outcome="answered",
            status_code=200,
        )

    assert trace_id == trace.trace_id
    assert current_trace_id() is None

    lines = log_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 3
    assert all(record["trace_id"] == trace_id for record in records)
    request_record = records[-1]
    assert request_record["event"] == "request_completed"
    assert request_record["outcome"] == "answered"
    assert request_record["status_code"] == 200
    assert request_record["duration_ms"] >= 0
    assert query not in "\n".join(lines)
    assert "9876543210" not in "\n".join(lines)
    assert "APT-0001" not in "\n".join(lines)
    logger.close()


def test_logger_rejects_unapproved_fields_and_values(tmp_path):
    logger = JsonlEventLogger(tmp_path / "events.jsonl")

    with pytest.raises(ValueError, match="Unsupported fields"):
        logger.write(
            "request_completed",
            transport="http",
            operation="query",
            outcome="success",
            duration_ms=1.0,
            query="sensitive text",
        )

    with pytest.raises(ValueError, match="Invalid safe value"):
        logger.write(
            "request_completed",
            transport="http",
            operation="query",
            outcome="sensitive text",
            duration_ms=1.0,
        )

    logger.close()
    assert (tmp_path / "events.jsonl").read_text(encoding="utf-8") == ""
