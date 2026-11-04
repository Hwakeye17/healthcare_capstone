"""Root entry point for the Practo Healthcare Support Agent."""

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIRECTORY = PROJECT_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("MOCK_LLM", "true")

from practo_agent.api import app, create_app  # noqa: E402
from practo_agent.memory import ConversationMemory  # noqa: E402

__all__ = ["app", "create_app", "main"]


def main() -> None:
    """Run an end-to-end offline smoke check through the shared conversation lifecycle."""

    conversations = ConversationMemory()
    response = conversations.run_turn(
        "What is the status of APT-0001, and how can I reschedule?",
        session_id="main-entrypoint-check",
    )
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

