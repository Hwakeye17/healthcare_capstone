import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from practo_agent.api.app import create_app
from practo_agent.memory import ConversationMemory
from practo_agent.schemas import AgentResponse, ResponseStatus


@pytest.fixture(autouse=True)
def isolate_api_log_file(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "PRACTO_LOG_PATH",
        str(tmp_path / "api.jsonl"),
    )


def _abstained_response(answer="I could not find a supported answer."):
    return AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer=answer,
        reason="Test response.",
    )


def _memory_with_recorded_workflow(monkeypatch):
    calls = []

    def fake_run_practo_query(query, *, conversation_history=(), **kwargs):
        calls.append(
            {
                "query": query,
                "history": list(conversation_history),
                "kwargs": kwargs,
            }
        )
        return _abstained_response(f"Received: {query}")

    monkeypatch.setattr(
        "practo_agent.memory.conversation.run_practo_query",
        fake_run_practo_query,
    )
    return ConversationMemory(), calls


def test_health_endpoint_reports_api_liveness():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_http_query_returns_structured_response_and_uses_session(
    monkeypatch,
):
    conversations, calls = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))

    response = client.post(
        "/query",
        json={
            "query": "  How do I reschedule?  ",
            "session_id": "session-a",
        },
    )

    assert response.status_code == 200
    assert response.json() == _abstained_response(
        "Received: How do I reschedule?"
    ).model_dump(mode="json")
    assert calls[0]["query"] == "How do I reschedule?"
    assert calls[0]["history"] == []
    assert response.headers["X-Trace-ID"]


def test_http_logs_trace_timing_and_outcome_without_request_content(
    monkeypatch,
    tmp_path,
):
    conversations, _ = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))
    query = "Call 9876543210 about appointment APT-0001"

    response = client.post(
        "/query",
        json={"query": query, "session_id": "private-session"},
    )

    log_path = tmp_path / "api.jsonl"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    assert len(records) == 1
    assert records[0]["event"] == "request_completed"
    assert records[0]["trace_id"] == response.headers["X-Trace-ID"]
    assert records[0]["outcome"] == "abstained"
    assert records[0]["duration_ms"] >= 0
    assert query not in "\n".join(lines)
    assert "9876543210" not in "\n".join(lines)
    assert "APT-0001" not in "\n".join(lines)
    assert "private-session" not in "\n".join(lines)


def test_http_query_rejects_invalid_payload_without_running_workflow(
    monkeypatch,
    tmp_path,
):
    conversations, calls = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))

    empty_query = client.post(
        "/query",
        json={"query": " ", "session_id": "session-a"},
    )
    extra_field = client.post(
        "/query",
        json={
            "query": "Question?",
            "session_id": "session-a",
            "unexpected": True,
        },
    )
    empty_session = client.post(
        "/query",
        json={"query": "Question?", "session_id": " "},
    )

    assert empty_query.status_code == 422
    assert extra_field.status_code == 422
    assert empty_session.status_code == 422
    assert calls == []
    records = [
        json.loads(line)
        for line in (tmp_path / "api.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert len(records) == 3
    assert all(record["outcome"] == "client_error" for record in records)
    assert all(record["status_code"] == 422 for record in records)


def test_websocket_carries_session_context_and_isolates_sessions(
    monkeypatch,
):
    conversations, calls = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))

    with client.websocket_connect("/ws/session-a") as socket:
        socket.send_json({"query": "First turn"})
        first_response = socket.receive_json()
        socket.send_json({"query": "Second turn"})
        second_response = socket.receive_json()

    with client.websocket_connect("/ws/session-b") as socket:
        socket.send_json({"query": "Independent turn"})
        independent_response = socket.receive_json()

    assert first_response["status"] == "abstained"
    assert second_response["status"] == "abstained"
    assert independent_response["status"] == "abstained"
    assert calls[0]["history"] == []
    assert len(calls[1]["history"]) == 2
    assert calls[1]["history"][0].content == "First turn"
    assert calls[2]["history"] == []


def test_websocket_reports_invalid_messages_and_continues(
    monkeypatch,
):
    conversations, calls = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))

    with client.websocket_connect("/ws/session-a") as socket:
        socket.send_text("{invalid json")
        malformed_response = socket.receive_json()
        socket.send_json({"query": ""})
        invalid_payload_response = socket.receive_json()
        socket.send_json({"query": "Valid turn"})
        valid_response = socket.receive_json()

    assert malformed_response["error"]["code"] == "invalid_request"
    assert invalid_payload_response["error"]["code"] == "invalid_request"
    assert valid_response["status"] == "abstained"
    assert len(calls) == 1
    assert calls[0]["query"] == "Valid turn"


def test_websocket_handles_disconnect_after_a_response(monkeypatch):
    conversations, _ = _memory_with_recorded_workflow(monkeypatch)
    client = TestClient(create_app(conversations))

    with client.websocket_connect("/ws/session-a") as socket:
        socket.send_json({"query": "Question?"})
        assert socket.receive_json()["status"] == "abstained"
        socket.close()


def test_websocket_rejects_invalid_session_ids():
    client = TestClient(create_app())

    with client.websocket_connect("/ws/%20%20") as socket:
        response = socket.receive_json()
        try:
            socket.receive_json()
        except WebSocketDisconnect as exc:
            assert exc.code == 1008
        else:
            raise AssertionError("Invalid session did not close the socket.")

    assert response["error"]["code"] == "invalid_session"
