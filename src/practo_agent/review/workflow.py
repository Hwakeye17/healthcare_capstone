"""Two-agent AutoGen review of grounded CrewAI responses."""

import asyncio
import json

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient, ModelFamily

from practo_agent.config.llm import GROQ_BASE_URL, get_llm_config
from practo_agent.config.runtime_budget import RuntimeBudget
from practo_agent.review.schemas import (
    FinalEditorOutput,
    ReviewFeedback,
    ReviewResult,
)
from practo_agent.schemas import (
    AgentResponse,
    RetrievedEvidence,
    ResponseStatus,
)


_REVIEWER_NAME = "response_reviewer"
_EDITOR_NAME = "final_editor"
_REVIEWER_SYSTEM_MESSAGE = """\
Review the proposed administrative support response against only the supplied
query and evidence. Check each factual claim for support, correctness, and
important omissions. You have no tools and must not infer missing facts.
Approve only if the answer is already accurate and adequately complete.
Otherwise list each unsupported claim or missing material information as a
specific issue. Return only the required structured review feedback.
"""
_EDITOR_SYSTEM_MESSAGE = """\
Produce the final administrative support response using only the supplied
evidence and reviewer feedback. If the reviewer approves, preserve the
proposed answer exactly. If revisions are required, correct or remove only
the identified unsupported claims and do not add unsupported facts. If no
safe, supported answer can be produced, abstain with a concise reason.
Preserve the provided response references; you have no tools or additional
appointment-system permissions. Return only the required structured output.
"""
_MODEL_INFO = {
    "vision": False,
    "function_calling": False,
    "json_output": True,
    "family": ModelFamily.UNKNOWN,
    "structured_output": True,
}


def review_response(
    response: AgentResponse,
    evidence: list[RetrievedEvidence],
    *,
    query: str = "",
    model_client: ChatCompletionClient | None = None,
    runtime_budget: RuntimeBudget | None = None,
) -> ReviewResult:
    """Review an answered draft in a two-turn, tool-free AutoGen group chat."""

    if response.status != ResponseStatus.ANSWERED:
        raise ValueError("Only answered responses can enter the review stage.")
    if not evidence:
        raise ValueError("At least one validated evidence item is required.")

    budget = runtime_budget if runtime_budget is not None else RuntimeBudget()
    task = _format_review_task(query, response.answer, evidence)
    _reserve_review_budget(budget, task)
    client = model_client or _create_model_client(response.answer, budget)
    result = asyncio.run(_run_review_team(client, task))

    agent_messages = [
        message
        for message in result.messages
        if message.source in {_REVIEWER_NAME, _EDITOR_NAME}
    ]
    if len(agent_messages) != 2:
        raise RuntimeError(
            "AutoGen review must complete exactly two agent turns."
        )

    reviewer_message, editor_message = agent_messages
    if (
        reviewer_message.source != _REVIEWER_NAME
        or not isinstance(reviewer_message, StructuredMessage)
        or not isinstance(reviewer_message.content, ReviewFeedback)
    ):
        raise RuntimeError("The reviewer did not return valid structured feedback.")
    if (
        editor_message.source != _EDITOR_NAME
        or not isinstance(editor_message, StructuredMessage)
        or not isinstance(editor_message.content, FinalEditorOutput)
    ):
        raise RuntimeError("The final editor did not return valid structured output.")

    feedback = reviewer_message.content
    editor_output = editor_message.content
    if feedback.approved and (
        editor_output.status != ResponseStatus.ANSWERED
        or editor_output.answer != response.answer
    ):
        raise RuntimeError(
            "The final editor changed a response that the reviewer approved."
        )
    if (
        not feedback.approved
        and editor_output.status == ResponseStatus.ANSWERED
        and editor_output.answer == response.answer
    ):
        raise RuntimeError(
            "The final editor returned a response rejected by the reviewer."
        )

    if editor_output.status == ResponseStatus.ANSWERED:
        reviewed_response = AgentResponse(
            status=ResponseStatus.ANSWERED,
            answer=editor_output.answer,
            sources=response.sources,
            appointments=response.appointments,
        )
    else:
        reviewed_response = AgentResponse(
            status=ResponseStatus.ABSTAINED,
            answer=editor_output.answer,
            reason=editor_output.reason,
        )

    return ReviewResult(
        response=reviewed_response,
        feedback=feedback,
        revised=editor_output.answer != response.answer,
        agent_turns=len(agent_messages),
    )


def _format_review_task(
    query: str,
    answer: str,
    evidence: list[RetrievedEvidence],
) -> str:
    return json.dumps(
        {
            "query": query,
            "proposed_answer": answer,
            "evidence": [
                {
                    "source_id": item.source_id,
                    "title": item.title,
                    "text": item.text,
                }
                for item in evidence
            ],
        },
        ensure_ascii=False,
    )


def _reserve_review_budget(budget: RuntimeBudget, task: str) -> None:
    """Reserve both model turns, including the reviewer's maximum output."""

    budget.reserve_llm_call(
        f"{_REVIEWER_SYSTEM_MESSAGE}\n{task}"
    )
    reviewer_output_reserve = (
        " " * budget.config.max_completion_tokens_per_call * 3
    )
    budget.reserve_llm_call(
        f"{_EDITOR_SYSTEM_MESSAGE}\n{task}\n{reviewer_output_reserve}"
    )


def _create_model_client(
    draft: str,
    budget: RuntimeBudget,
) -> ChatCompletionClient:
    config = get_llm_config()
    if config["mock_mode"]:
        from autogen_ext.models.replay import ReplayChatCompletionClient

        return ReplayChatCompletionClient(
            [
                ReviewFeedback(approved=True).model_dump_json(),
                FinalEditorOutput(
                    status=ResponseStatus.ANSWERED,
                    answer=draft,
                ).model_dump_json(),
            ],
            model_info=_MODEL_INFO,
        )

    import os

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required when MOCK_LLM=false.")

    from autogen_ext.models.openai import OpenAIChatCompletionClient

    return OpenAIChatCompletionClient(
        model=config["model"],
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        model_info=_MODEL_INFO,
        temperature=config["temperature"],
        max_tokens=budget.config.max_completion_tokens_per_call,
        max_retries=0,
    )


async def _run_review_team(
    model_client: ChatCompletionClient,
    task: str,
) -> TaskResult:
    reviewer = AssistantAgent(
        name=_REVIEWER_NAME,
        model_client=model_client,
        system_message=_REVIEWER_SYSTEM_MESSAGE,
        output_content_type=ReviewFeedback,
    )
    editor = AssistantAgent(
        name=_EDITOR_NAME,
        model_client=model_client,
        system_message=_EDITOR_SYSTEM_MESSAGE,
        output_content_type=FinalEditorOutput,
    )
    team = RoundRobinGroupChat(
        [reviewer, editor],
        max_turns=2,
        custom_message_types=[
            StructuredMessage[ReviewFeedback],
            StructuredMessage[FinalEditorOutput],
        ],
    )
    try:
        return await team.run(task=task)
    finally:
        await model_client.close()
