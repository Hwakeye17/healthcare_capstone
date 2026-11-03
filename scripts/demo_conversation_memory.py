"""Demonstrate session memory, multi-turn context, and session isolation."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIRECTORY = PROJECT_ROOT / "evaluation" / "results"
MULTI_TURN_PATH = RESULTS_DIRECTORY / "conversation_memory_demo.json"
FRESH_SESSION_PATH = (
    RESULTS_DIRECTORY / "conversation_memory_fresh_session.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from practo_agent.memory import ConversationMemory
    from practo_agent.schemas import ResponseStatus

    conversations = ConversationMemory()
    session_id = "appointment-follow-up"

    first_query = "What is the status of APT-0001?"
    first_response = conversations.run_turn(
        first_query,
        session_id=session_id,
    )
    if first_response.status != ResponseStatus.ANSWERED:
        raise RuntimeError(
            f"The first offline turn was not answered: {first_response.reason}"
        )

    second_query = "What is its consultation fee?"
    second_response = conversations.run_turn(
        second_query,
        session_id=session_id,
    )
    if second_response.status != ResponseStatus.ANSWERED:
        raise RuntimeError(
            f"The follow-up turn was not answered: {second_response.reason}"
        )
    if not any(
        item.record_id == "APT-0001"
        for item in second_response.appointments
    ):
        raise RuntimeError(
            "The follow-up did not retain the appointment context."
        )

    session_messages = conversations.get_messages(session_id=session_id)
    if len(session_messages) != 4:
        raise RuntimeError(
            f"Expected two turns in history; got {len(session_messages)} messages."
        )

    multi_turn_report = {
        "demo": "session_conversation_memory",
        "mock_llm": True,
        "session_id": session_id,
        "turns": [
            {
                "query": first_query,
                "response": first_response.model_dump(mode="json"),
            },
            {
                "query": second_query,
                "response": second_response.model_dump(mode="json"),
            },
        ],
        "stored_message_count": len(session_messages),
        "follow_up_includes_prior_appointment": True,
        "passed": True,
    }

    fresh_session_id = "fresh-conversation"
    fresh_messages_before = conversations.get_messages(
        session_id=fresh_session_id,
    )
    if fresh_messages_before:
        raise RuntimeError("The new session unexpectedly has prior history.")

    fresh_query = "What is its consultation fee?"
    fresh_response = conversations.run_turn(
        fresh_query,
        session_id=fresh_session_id,
    )
    if any("APT-0001" in str(message.content) for message in fresh_messages_before):
        raise RuntimeError("The new session inherited another session's data.")
    if any(
        item.record_id == "APT-0001"
        for item in fresh_response.appointments
    ):
        raise RuntimeError(
            "The fresh session returned an appointment from another session."
        )

    fresh_report = {
        "demo": "fresh_session_isolation",
        "mock_llm": True,
        "session_id": fresh_session_id,
        "history_before_first_turn": [],
        "query": fresh_query,
        "response": fresh_response.model_dump(mode="json"),
        "prior_session_appointment_leaked": False,
        "passed": True,
    }

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    MULTI_TURN_PATH.write_text(
        json.dumps(multi_turn_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    FRESH_SESSION_PATH.write_text(
        json.dumps(fresh_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Conversation-memory demonstration passed.")
    print("Two-turn session retained the appointment context.")
    print("Fresh session started with no prior appointment context.")
    print(f"Multi-turn transcript: {MULTI_TURN_PATH}")
    print(f"Fresh-session transcript: {FRESH_SESSION_PATH}")


if __name__ == "__main__":
    main()
