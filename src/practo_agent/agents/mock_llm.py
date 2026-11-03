"""Deterministic CrewAI LLM for the required offline acceptance path."""

import json
import os
import re
from typing import Any

from crewai.llms.base_llm import BaseLLM

from practo_agent.schemas import (
    AgentResponse,
    AppointmentReference,
    LookupAgentOutput,
    LookupAgentStatus,
    RetrievalAgentOutput,
    RetrievalAgentStatus,
    ResponseStatus,
    SourceReference,
)


_RETRIEVAL_ROLE = "Practo Knowledge Retrieval Specialist"
_LOOKUP_ROLE = "Practo Appointment Lookup Specialist"
_COMPOSER_ROLE = "Practo Support Response Composer"
_RECORD_ID_PATTERN = re.compile(r"\b[A-Z]{3,5}-\d{4}\b", re.IGNORECASE)


class MockCrewAILLM(BaseLLM):
    """Run CrewAI tool workflows deterministically without model requests."""

    def __init__(self, query: str | None = None) -> None:
        os.environ["OTEL_SDK_DISABLED"] = "true"
        super().__init__(
            model="mock-practo-llm",
            provider="openai",
        )
        self.query = query
        self.call_count = 0
        self.tool_actions: list[str] = []
        self._retrieval_output: RetrievalAgentOutput | None = None
        self._lookup_output: LookupAgentOutput | None = None

    def call(
        self,
        messages: str | list[Any],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        self.call_count += 1
        role = getattr(from_agent, "role", None)

        if self.query is None:
            raise RuntimeError(
                "MockCrewAILLM requires the current user query."
            )

        if role in (_RETRIEVAL_ROLE, _LOOKUP_ROLE):
            observation = self._assistant_tool_observation(messages)
            if observation is None:
                return self._tool_action(from_agent)
            return self._finish_specialist(role, observation)

        if role == _COMPOSER_ROLE:
            return self._finish_composition()

        raise RuntimeError(
            f"MockCrewAILLM received an unsupported agent role: {role!r}."
        )

    def _tool_action(self, agent: Any) -> str:
        role = agent.role
        argument_name = (
            "query" if role == _RETRIEVAL_ROLE else "record_id"
        )
        candidates = []

        for candidate in agent.tools:
            argument_schema = getattr(candidate, "args_schema", None)
            fields = getattr(argument_schema, "model_fields", {})
            if argument_name in fields:
                candidates.append(candidate)

        if len(candidates) != 1:
            raise RuntimeError(
                f"Expected exactly one {argument_name!r} tool for "
                f"{role!r}; found {len(candidates)}."
            )

        if argument_name == "query":
            value = self.query
        else:
            matches = _RECORD_ID_PATTERN.findall(self.query)
            if len(matches) != 1:
                raise RuntimeError(
                    "Appointment lookup requires exactly one record ID."
                )
            value = matches[0].upper()

        tool = candidates[0]
        self.tool_actions.append(tool.name)
        tool_input = json.dumps({argument_name: value})
        return (
            "Thought: I will use the authorized tool for this request.\n"
            f"Action: {tool.name}\n"
            f"Action Input: {tool_input}"
        )

    @staticmethod
    def _assistant_tool_observation(
        messages: str | list[Any],
    ) -> str | None:
        """Read a tool result only from the assistant's generated action."""

        if not isinstance(messages, list):
            return None

        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") != "assistant":
                continue

            content = message.get("content")
            if not isinstance(content, str):
                continue

            action_index = content.find("\nAction:")
            observation_index = content.find("\nObservation:")
            if action_index < 0 or observation_index <= action_index:
                continue

            observation = content[observation_index + len("\nObservation:"):]
            observation = observation.strip().splitlines()[0]
            if observation:
                return observation

        return None

    def _finish_specialist(self, role: str, observation: str) -> str:
        try:
            result = json.loads(observation)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{role} tool returned invalid JSON."
            ) from exc

        if role == _RETRIEVAL_ROLE:
            parsed = RetrievalAgentOutput.model_validate(result)
            self._retrieval_output = parsed
            summary = parsed.model_dump(mode="json")
        else:
            parsed = LookupAgentOutput.model_validate(result)
            self._lookup_output = parsed
            summary = parsed.model_dump(mode="json")

        return (
            "Thought: The authorized tool returned a validated result.\n"
            f"Final Answer: {json.dumps(summary, ensure_ascii=False)}"
        )

    def _finish_composition(self) -> str:
        answer_parts: list[str] = []
        sources: dict[str, SourceReference] = {}
        appointments: dict[str, AppointmentReference] = {}
        failure_reasons: list[str] = []

        retrieval = self._retrieval_output
        if retrieval is not None:
            if retrieval.status == RetrievalAgentStatus.SUCCESS:
                for evidence in retrieval.assessment.evidence:
                    answer_parts.append(
                        f"According to {evidence.title}: {evidence.text}"
                    )
                    sources.setdefault(
                        evidence.source_id,
                        SourceReference(
                            source_id=evidence.source_id,
                            title=evidence.title,
                        ),
                    )
            elif retrieval.status == RetrievalAgentStatus.NO_EVIDENCE:
                answer_parts.append(
                    "I couldn't find supported policy information in the "
                    "available knowledge base."
                )
                if retrieval.reason:
                    failure_reasons.append(retrieval.reason)
            elif retrieval.status == RetrievalAgentStatus.ERROR:
                answer_parts.append(
                    "The knowledge-base search did not complete successfully."
                )
                if retrieval.reason:
                    failure_reasons.append(retrieval.reason)
            elif retrieval.reason:
                failure_reasons.append(retrieval.reason)

        lookup = self._lookup_output
        if lookup is not None:
            if lookup.status == LookupAgentStatus.SUCCESS:
                appointment = lookup.appointment
                answer_parts.append(
                    f"Appointment {appointment.record_id} is in specialty "
                    f"{appointment.specialty} with status {appointment.status}. "
                    f"The consultation fee is INR "
                    f"{appointment.consultation_fee_inr}. The record is "
                    f"{appointment.days_since_created} days old and its "
                    f"follow-up-required flag is "
                    f"{appointment.follow_up_required}. Its administrative "
                    f"escalation score is {appointment.escalation_score:.4f}; "
                    f"escalation required: "
                    f"{appointment.escalation_required}. "
                    f"{appointment.escalation_reason}"
                )
                appointments[appointment.record_id] = AppointmentReference(
                    record_id=appointment.record_id,
                )
            elif lookup.status == LookupAgentStatus.NOT_FOUND:
                answer_parts.append(
                    f"I couldn't find appointment record {lookup.record_id}."
                )
                if lookup.reason:
                    failure_reasons.append(lookup.reason)
            elif lookup.status == LookupAgentStatus.ERROR:
                answer_parts.append(
                    "The appointment lookup did not complete successfully."
                )
                if lookup.reason:
                    failure_reasons.append(lookup.reason)
            elif lookup.reason:
                failure_reasons.append(lookup.reason)

        if answer_parts and (sources or appointments):
            response = AgentResponse(
                status=ResponseStatus.ANSWERED,
                answer="\n\n".join(answer_parts),
                sources=list(sources.values()),
                appointments=list(appointments.values()),
            )
        else:
            reason = (
                "; ".join(failure_reasons)
                if failure_reasons
                else "No supported administrative information was available."
            )
            abstention_answer = (
                "\n\n".join(answer_parts)
                if answer_parts
                else (
                    "I can't provide a supported answer from the available "
                    "information."
                )
            )
            response = AgentResponse(
                status=ResponseStatus.ABSTAINED,
                answer=abstention_answer,
                reason=reason,
            )

        return (
            "Thought: I will return only the validated specialist results.\n"
            f"Final Answer: {response.model_dump_json()}"
        )

    def supports_function_calling(self) -> bool:
        """CrewAI uses ReAct text actions for this offline adapter."""

        return False

    def supports_stop_words(self) -> bool:
        return False
