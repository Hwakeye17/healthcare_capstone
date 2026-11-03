from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from practo_agent.agents import workflow
from practo_agent.schemas import AgentResponse, ResponseStatus


def test_multiple_appointment_ids_return_a_clarification_without_running_crew(
    monkeypatch,
):
    def fail_if_called(**kwargs):
        raise AssertionError("A crew must not run for an ambiguous lookup.")

    monkeypatch.setattr(workflow, "create_practo_crew", fail_if_called)

    response = workflow.run_practo_query(
        "Compare APT-0001 with APT-0002."
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert "one appointment record ID" in response.answer


def test_invalid_specialist_output_is_rejected(monkeypatch):
    retrieval_task = SimpleNamespace(
        agent=SimpleNamespace(
            role="Practo Knowledge Retrieval Specialist",
        )
    )
    composition_task = SimpleNamespace(
        agent=SimpleNamespace(
            role="Practo Support Response Composer",
        )
    )

    class InvalidIntermediateCrew:
        tasks = [retrieval_task, composition_task]

        def kickoff(self, inputs):
            return SimpleNamespace(
                tasks_output=[
                    SimpleNamespace(raw="not valid retrieval JSON"),
                    SimpleNamespace(
                        raw=AgentResponse(
                            status=ResponseStatus.ABSTAINED,
                            answer="I cannot answer.",
                            reason="No evidence.",
                        ).model_dump_json()
                    ),
                ],
                raw=AgentResponse(
                    status=ResponseStatus.ABSTAINED,
                    answer="I cannot answer.",
                    reason="No evidence.",
                ).model_dump_json(),
            )

    monkeypatch.setattr(
        workflow,
        "create_practo_crew",
        lambda **kwargs: InvalidIntermediateCrew(),
    )

    with pytest.raises(ValidationError):
        workflow.run_practo_query("How do I reschedule an appointment?")


def test_invalid_final_response_is_rejected(monkeypatch):
    composition_task = SimpleNamespace(
        agent=SimpleNamespace(
            role="Practo Support Response Composer",
        )
    )

    class InvalidFinalCrew:
        tasks = [composition_task]

        def kickoff(self, inputs):
            return SimpleNamespace(
                tasks_output=[SimpleNamespace(raw="not valid JSON")],
                raw="not valid JSON",
            )

    monkeypatch.setattr(
        workflow,
        "create_practo_crew",
        lambda **kwargs: InvalidFinalCrew(),
    )

    with pytest.raises(ValidationError):
        workflow.run_practo_query("Who won the latest cricket world cup?")
