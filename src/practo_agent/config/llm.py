
import os

from dotenv import load_dotenv

from practo_agent.config.runtime_budget import RuntimeBudget

load_dotenv()


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_llm_config() -> dict:
    """Return the shared LLM configuration."""

    mock_mode = os.getenv("MOCK_LLM", "true").lower() == "true"

    return {
        "mock_mode": mock_mode,
        "provider": "groq",
        "model": os.getenv(
            "GROQ_MODEL",
            "qwen/qwen3.8-27b",
        ),
        "temperature": float(
            os.getenv("GROQ_TEMPERATURE", "0")
        ),
    }


def create_crewai_llm(
    *,
    query: str | None = None,
    runtime_budget: RuntimeBudget | None = None,
):
    """Create the configured CrewAI model without network access in mock mode."""
    config = get_llm_config()
    budget = (
        runtime_budget
        if runtime_budget is not None
        else RuntimeBudget()
    )

    if config["mock_mode"]:
        from practo_agent.agents.mock_llm import MockCrewAILLM

        llm = MockCrewAILLM(query=query)
        llm.set_runtime_budget(budget)
        return llm

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is required when MOCK_LLM=false."
        )

    from practo_agent.config.groq_llm import GroqReActLLM

    llm = GroqReActLLM(
        model=config["model"],
        provider="openai",
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=config["temperature"],
        max_completion_tokens=budget.config.max_completion_tokens_per_call,
    )
    llm.set_runtime_budget(budget)
    return llm
