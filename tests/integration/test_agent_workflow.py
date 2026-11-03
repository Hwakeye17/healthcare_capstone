import socket

from practo_agent.agents import run_practo_query
from practo_agent.config import create_crewai_llm
from practo_agent.schemas import ResponseStatus


def test_offline_workflow_uses_real_local_tools(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "true")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    outbound_addresses = []
    original_connect = socket.socket.connect

    def reject_external_connection(sock, address):
        host = address[0]
        if host not in {"127.0.0.1", "::1", "localhost"}:
            outbound_addresses.append(host)
            raise AssertionError(
                f"The offline workflow attempted to connect to {host!r}."
            )
        return original_connect(sock, address)

    monkeypatch.setattr(
        socket.socket,
        "connect",
        reject_external_connection,
    )

    examples = [
        (
            "How can I reschedule my existing doctor appointment?",
            "search_practo_knowledge_base",
            ResponseStatus.ANSWERED,
        ),
        (
            "What documents are required to submit an insurance claim?",
            "search_practo_knowledge_base",
            ResponseStatus.ANSWERED,
        ),
        (
            "How long does it usually take to receive lab test results?",
            "search_practo_knowledge_base",
            ResponseStatus.ANSWERED,
        ),
        (
            "What is the status of APT-0001?",
            "check_appointment_status",
            ResponseStatus.ANSWERED,
        ),
        (
            "What is the status of APT-0002?",
            "check_appointment_status",
            ResponseStatus.ANSWERED,
        ),
        (
            "What is the status of APT-0001, and how can I reschedule?",
            (
                "search_practo_knowledge_base",
                "check_appointment_status",
            ),
            ResponseStatus.ANSWERED,
        ),
        (
            "Can you diagnose my skin rash and recommend a suitable medicine?",
            "search_practo_knowledge_base",
            ResponseStatus.ABSTAINED,
        ),
        (
            "What is the status of APT-9999?",
            "check_appointment_status",
            ResponseStatus.ABSTAINED,
        ),
    ]

    for query, expected_tools, expected_status in examples:
        llm = create_crewai_llm(query=query)
        response = run_practo_query(query, llm=llm)

        assert response.status == expected_status
        if isinstance(expected_tools, str):
            expected_tools = (expected_tools,)
        assert llm.tool_actions == list(expected_tools)
        if "APT-0001" in query:
            assert "General Medicine" in response.answer
            assert "5 days old" in response.answer
            assert "follow-up-required flag is False" in response.answer
            assert "escalation score is 0.0667" in response.answer
        if "APT-9999" in query:
            assert "couldn't find appointment record APT-9999" in response.answer

    assert outbound_addresses == []
