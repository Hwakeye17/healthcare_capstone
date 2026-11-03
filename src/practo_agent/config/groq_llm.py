"""Groq-compatible CrewAI LLM configuration."""

from typing import Any

from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llms.providers.openai.completion import OpenAICompletion
from crewai.task import Task
from crewai.tools.base_tool import BaseTool
from crewai.utilities.types import LLMMessage
from pydantic import BaseModel, PrivateAttr

from practo_agent.config.runtime_budget import RuntimeBudget


class GroqReActLLM(OpenAICompletion):
    """Use CrewAI's ReAct tool parser instead of provider-native tool calls."""

    _runtime_budget: RuntimeBudget | None = PrivateAttr(default=None)

    def supports_function_calling(self) -> bool:
        return False

    def set_runtime_budget(self, runtime_budget: RuntimeBudget) -> None:
        """Attach the request budget shared by the workflow's model calls."""

        self._runtime_budget = runtime_budget

    def call(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict[str, BaseTool]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Task | None = None,
        from_agent: BaseAgent | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        if self._runtime_budget is not None:
            self._runtime_budget.reserve_llm_call(messages)
        return super().call(
            messages=messages,
            tools=tools,
            callbacks=callbacks,
            available_functions=available_functions,
            from_task=from_task,
            from_agent=from_agent,
            response_model=response_model,
        )
