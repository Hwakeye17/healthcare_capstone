"""Demonstrate HTTP and multi-turn WebSocket access in offline mode."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "api_demo.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["GROQ_API_KEY"] = ""

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from fastapi.testclient import TestClient

    from practo_agent.api.app import create_app
    from practo_agent.schemas import ResponseStatus

    app = create_app()
    session_id = "api-appointment-follow-up"
    first_query = "What is the status of APT-0001?"
    follow_up_query = "What is its consultation fee?"

    with TestClient(app) as client:
        health_response = client.get("/health")
        http_response = client.post(
            "/query",
            json={
                "query": first_query,
                "session_id": session_id,
            },
        )

        with client.websocket_connect(f"/ws/{session_id}") as socket:
            socket.send_json({"query": follow_up_query})
            websocket_response = socket.receive_json()

    if health_response.status_code != 200:
        raise RuntimeError("The API health endpoint did not return HTTP 200.")
    if http_response.status_code != 200:
        raise RuntimeError(
            f"The HTTP query failed: {http_response.status_code} "
            f"{http_response.text}"
        )

    first_result = http_response.json()
    follow_up_result = websocket_response
    if first_result["status"] != ResponseStatus.ANSWERED.value:
        raise RuntimeError(
            f"The HTTP query was not answered: {first_result.get('reason')}"
        )
    if follow_up_result["status"] != ResponseStatus.ANSWERED.value:
        raise RuntimeError(
            "The WebSocket follow-up was not answered: "
            f"{follow_up_result.get('reason')}"
        )
    if not any(
        item["record_id"] == "APT-0001"
        for item in follow_up_result["appointments"]
    ):
        raise RuntimeError(
            "The WebSocket response did not preserve appointment context."
        )

    history = app.state.conversations.get_messages(session_id=session_id)
    if len(history) != 4:
        raise RuntimeError(
            f"Expected two turns in shared history, got {len(history)} messages."
        )

    report = {
        "demo": "offline_fastapi_and_websocket",
        "mock_llm": True,
        "health_status_code": health_response.status_code,
        "http_query": {
            "status_code": http_response.status_code,
            "query": first_query,
            "response": first_result,
        },
        "websocket_follow_up": {
            "query": follow_up_query,
            "response": follow_up_result,
        },
        "session_message_count": len(history),
        "follow_up_retained_appointment_context": True,
        "websocket_closed_gracefully": True,
        "passed": True,
    }

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Offline API demonstration passed.")
    print("HTTP query and WebSocket follow-up shared session context.")
    print("WebSocket disconnected cleanly.")
    print(f"Transcript: {RESULT_PATH}")


if __name__ == "__main__":
    main()
