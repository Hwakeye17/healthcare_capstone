"""Offline test LLM compatible with CrewAI BaseLLM."""

from crewai.llms.base_llm import BaseLLM


class MockCrewAILLM(BaseLLM):
    """A test double that must never make an external LLM request."""

    def __init__(self):
        super().__init__(
            model="mock-practo-llm",
            provider="openai",
        )
        self.call_count = 0

    def call(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ):
        self.call_count += 1

        raise RuntimeError(
            "MockCrewAILLM does not generate responses. "
            "An unexpected LLM invocation occurred during this test."
        )