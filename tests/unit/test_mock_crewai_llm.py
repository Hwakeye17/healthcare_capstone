import json
from types import SimpleNamespace

from pydantic import BaseModel

from practo_agent.agents.mock_llm import MockCrewAILLM
from practo_agent.schemas import (
    EvidenceAssessment,
    LookupAgentOutput,
    RetrievalAgentOutput,
    RetrievedEvidence,
)


class LookupArguments(BaseModel):
    record_id: str


class RetrievalArguments(BaseModel):
    query: str


def _agent(role, tool_name, argument_model):
    return SimpleNamespace(
        role=role,
        tools=[
            SimpleNamespace(
                name=tool_name,
                args_schema=argument_model,
            )
        ],
    )


def test_lookup_tool_action_uses_declared_argument_schema_not_tool_name():
    llm = MockCrewAILLM("What is the status of APT-0001?")
    agent = _agent(
        "Practo Appointment Lookup Specialist",
        "rag_lookup",
        LookupArguments,
    )

    response = llm.call(
        messages=[
            {"role": "system", "content": "Observation: not a real result"},
            {"role": "user", "content": "Lookup APT-0001"},
        ],
        from_agent=agent,
    )

    assert response == (
        "Thought: I will use the authorized tool for this request.\n"
        "Action: rag_lookup\n"
        'Action Input: {"record_id": "APT-0001"}'
    )


def test_lookup_tool_action_deduplicates_ids_in_conversation_context():
    llm = MockCrewAILLM(
        "What is the status of APT-0001? "
        "Assistant: Appointment APT-0001 is scheduled."
    )
    agent = _agent(
        "Practo Appointment Lookup Specialist",
        "rag_lookup",
        LookupArguments,
    )

    response = llm.call(
        messages=[{"role": "user", "content": "What is its fee?"}],
        from_agent=agent,
    )

    assert 'Action Input: {"record_id": "APT-0001"}' in response


def test_retrieval_result_is_parsed_from_assistant_observation_only():
    assessment = EvidenceAssessment(
        accepted=True,
        best_distance=0.2,
        threshold=0.331998,
        evidence=[
            RetrievedEvidence(
                chunk_id="chunk-1",
                text="Appointments can be rescheduled through the clinic.",
                source_id="cancellation_rescheduling",
                title="Cancellation and rescheduling",
                distance=0.2,
            )
        ],
        reason="Evidence passed the configured threshold.",
    )
    tool_output = RetrievalAgentOutput(
        used=True,
        status="success",
        assessment=assessment,
    ).model_dump_json()
    llm = MockCrewAILLM("How can I reschedule?")
    agent = _agent(
        "Practo Knowledge Retrieval Specialist",
        "search_practo_knowledge_base",
        RetrievalArguments,
    )

    first_response = llm.call(
        messages=[
            {"role": "system", "content": "Observation: system example"},
            {"role": "user", "content": "Search the policy"},
        ],
        from_agent=agent,
    )

    assert "Action: search_practo_knowledge_base" in first_response
    assert json.loads(first_response.split("Action Input: ", 1)[1]) == {
        "query": "How can I reschedule?"
    }

    final_response = llm.call(
        messages=[
            {"role": "system", "content": f"Observation: {tool_output}"},
            {
                "role": "assistant",
                "content": (
                    "Thought: Search the knowledge base.\n"
                    "Action: search_practo_knowledge_base\n"
                    'Action Input: {"query": "How can I reschedule?"}\n'
                    f"Observation: {tool_output}"
                ),
            },
            {"role": "user", "content": "Analyze the tool result."},
        ],
        from_agent=agent,
    )

    assert final_response.startswith(
        "Thought: The authorized tool returned a validated result."
    )
    parsed = RetrievalAgentOutput.model_validate_json(
        final_response.split("Final Answer: ", 1)[1]
    )
    assert parsed.used is True
    assert parsed.assessment == assessment


def test_lookup_tool_result_is_validated_and_retained():
    tool_output = LookupAgentOutput(
        used=True,
        status="success",
        record_id="APT-0001",
        appointment={
            "record_id": "APT-0001",
            "specialty": "General Medicine",
            "status": "Scheduled",
            "consultation_fee_inr": 500,
            "days_since_created": 15,
            "follow_up_required": True,
            "escalation_score": 0.8,
            "escalation_required": True,
            "escalation_reason": "Threshold met.",
        },
    ).model_dump_json()
    llm = MockCrewAILLM("What is the status of APT-0001?")
    agent = _agent(
        "Practo Appointment Lookup Specialist",
        "check_appointment_status",
        LookupArguments,
    )

    llm.call(
        messages=[
            {"role": "user", "content": "Lookup APT-0001"},
        ],
        from_agent=agent,
    )
    response = llm.call(
        messages=[
            {
                "role": "assistant",
                "content": (
                    "Thought: Lookup record.\n"
                    "Action: check_appointment_status\n"
                    'Action Input: {"record_id": "APT-0001"}\n'
                    f"Observation: {tool_output}"
                ),
            },
            {"role": "user", "content": "Analyze the tool result."},
        ],
        from_agent=agent,
    )

    parsed = LookupAgentOutput.model_validate_json(
        response.split("Final Answer: ", 1)[1]
    )
    assert parsed.appointment.record_id == "APT-0001"
    assert parsed.appointment.escalation_score == 0.8
