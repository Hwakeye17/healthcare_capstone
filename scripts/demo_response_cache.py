"""Demonstrate response-cache hits, misses, and context isolation offline."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "response_cache_demo.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from practo_agent.cache import ResponseCache
    from practo_agent.config import create_crewai_llm
    from practo_agent.agents import run_practo_query
    from practo_agent.schemas import ResponseStatus

    cache = ResponseCache()
    query = "What is the status of APT-0001?"
    invocation_count = 0

    def run_workflow():
        nonlocal invocation_count
        invocation_count += 1
        llm = create_crewai_llm(query=query)
        return run_practo_query(query, llm=llm)

    first_response, first_hit = cache.get_or_compute(
        query,
        run_workflow,
        scope="session-a",
    )
    equivalent_response, equivalent_hit = cache.get_or_compute(
        "  WHAT   IS THE STATUS OF apt-0001? ",
        run_workflow,
        scope="session-a",
    )
    other_context_response, other_context_hit = cache.get_or_compute(
        query,
        run_workflow,
        context="A different prior conversation.",
        scope="session-a",
    )
    other_session_response, other_session_hit = cache.get_or_compute(
        query,
        run_workflow,
        scope="session-b",
    )

    responses = (
        first_response,
        equivalent_response,
        other_context_response,
        other_session_response,
    )
    if any(response.status != ResponseStatus.ANSWERED for response in responses):
        raise RuntimeError("The offline appointment query did not answer.")
    if first_hit or not equivalent_hit or other_context_hit or other_session_hit:
        raise RuntimeError("Cache hit/miss behavior did not match expectations.")
    if invocation_count != 3:
        raise RuntimeError(
            f"Expected three workflow invocations, observed {invocation_count}."
        )

    report = {
        "demo": "context_aware_response_cache",
        "mock_llm": True,
        "query": query,
        "cases": {
            "initial_request": {"cache_hit": first_hit},
            "normalized_equivalent_request": {
                "cache_hit": equivalent_hit,
                "same_response": equivalent_response == first_response,
            },
            "different_context": {"cache_hit": other_context_hit},
            "different_session": {"cache_hit": other_session_hit},
        },
        "workflow_invocations": invocation_count,
        "cache_stats": cache.stats,
        "passed": True,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Response-cache demonstration passed.")
    print(
        f"Cache hits: {cache.stats['hits']}; misses: {cache.stats['misses']}; "
        f"workflow invocations: {invocation_count}."
    )
    print("Different contexts and sessions resulted in cache misses.")
    print(f"Transcript saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
