"""Groq-compatible CrewAI LLM configuration."""

from crewai.llms.providers.openai.completion import OpenAICompletion


class GroqReActLLM(OpenAICompletion):
    """Use CrewAI's ReAct tool parser instead of provider-native tool calls."""

    def supports_function_calling(self) -> bool:
        return False
