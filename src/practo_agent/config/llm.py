import os
from dotenv import load_dotenv

load_dotenv()


def get_llm_config() -> dict:
    mock_mode = os.getenv("MOCK_LLM", "true").lower() == "true"

    return {
        "mock_mode": mock_mode,
        "provider": "groq",
        "model": os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        ),
        "temperature": float(
            os.getenv("GROQ_TEMPERATURE", "0")
        ),
    }