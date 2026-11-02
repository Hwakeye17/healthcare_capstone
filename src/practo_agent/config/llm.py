
import os

from dotenv import load_dotenv

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
            "openai/gpt-oss-120b",
        ),
        "temperature": float(
            os.getenv("GROQ_TEMPERATURE", "0")
        ),
    }


def create_crewai_llm():
    """Create CrewAI's native LLM using Groq's OpenAI-compatible API."""

    from crewai import LLM

    config = get_llm_config()
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is required to create the CrewAI LLM."
        )

    return LLM(
        model=config["model"],
        provider="openai",
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=config["temperature"],
    )
