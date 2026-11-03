"""In-process, session-isolated conversation memory for Practo requests."""

from typing import Any

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory

from practo_agent.agents.workflow import run_practo_query
from practo_agent.guardrails import (
    detect_prompt_injection,
    mask_contact_numbers,
)
from practo_agent.schemas import AgentResponse


class ConversationMemory:
    """Run requests with LangChain message history isolated by session ID.

    Histories exist only for this manager instance and process lifetime.
    Contact numbers are masked before the request is stored in history.
    """

    def __init__(self) -> None:
        self._histories: dict[str, InMemoryChatMessageHistory] = {}
        self._chain = RunnableWithMessageHistory(
            RunnableLambda(self._run_with_history),
            self._get_session_history,
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="history_output",
        )

    def run_turn(self, query: str, *, session_id: str) -> AgentResponse:
        """Run one user turn and retain it only in its session history."""

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")
        session_id = session_id.strip()

        sanitized_query = mask_contact_numbers(query.strip())
        if detect_prompt_injection(sanitized_query) is not None:
            return run_practo_query(sanitized_query)

        result = self._chain.invoke(
            {"input": sanitized_query},
            config={"configurable": {"session_id": session_id}},
        )
        response = result.get("response")
        if not isinstance(response, AgentResponse):
            raise TypeError("Conversation chain did not return an AgentResponse.")
        return response

    def get_messages(self, *, session_id: str) -> list[BaseMessage]:
        """Return a snapshot of stored messages for one session."""

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string.")
        session_id = session_id.strip()

        history = self._histories.get(session_id)
        return list(history.messages) if history is not None else []

    def _get_session_history(
        self,
        session_id: str,
    ) -> InMemoryChatMessageHistory:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string.")

        if session_id not in self._histories:
            self._histories[session_id] = InMemoryChatMessageHistory()
        return self._histories[session_id]

    def _run_with_history(self, inputs: dict[str, Any]) -> dict[str, Any]:
        query = inputs.get("input")
        history = inputs.get("chat_history", [])
        if not isinstance(query, str):
            raise TypeError("input must be a string.")

        response = run_practo_query(
            query,
            conversation_history=history,
        )
        return {
            "response": response,
            "history_output": mask_contact_numbers(response.answer),
        }
