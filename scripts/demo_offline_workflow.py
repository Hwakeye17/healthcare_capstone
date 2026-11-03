"""Run deterministic end-to-end examples without external APIs."""

import json
import os

EXAMPLES = (
    "How can I reschedule my existing doctor appointment?",
    "What documents are required to submit an insurance claim?",
    "How long does it usually take to receive lab test results?",
    "What is the status of APT-0001?",
    "What is the status of APT-0002?",
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    from practo_agent.agents import run_practo_query
    from practo_agent.config import create_crewai_llm
    from practo_agent.schemas import ResponseStatus

    for query in EXAMPLES:
        llm = create_crewai_llm(query=query)
        response = run_practo_query(query, llm=llm)

        if response.status != ResponseStatus.ANSWERED:
            raise RuntimeError(
                f"Offline example unexpectedly abstained: {query!r} "
                f"({response.reason})"
            )

        print(
            json.dumps(
                {
                    "query": query,
                    "tool_actions": llm.tool_actions,
                    "response": response.model_dump(mode="json"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
