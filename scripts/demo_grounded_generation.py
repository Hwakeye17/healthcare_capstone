"""Demonstrate grounded offline answers for all labeled retrieval queries."""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "grounded_generation_results.json"
)


def main() -> None:
    os.environ["MOCK_LLM"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import sys

    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from practo_agent.agents import run_practo_query
    from practo_agent.config import (
        DEFAULT_GROUNDING_CONFIG,
        DEFAULT_RETRIEVAL_CONFIG,
        create_crewai_llm,
    )
    from practo_agent.evaluation.abstention import load_abstention_cases
    from practo_agent.evaluation.cases import load_evaluation_cases
    from practo_agent.schemas import ResponseStatus

    cases = load_evaluation_cases()
    out_of_scope = next(
        case
        for case in load_abstention_cases(
            PROJECT_ROOT
            / "evaluation"
            / "cases"
            / "abstention_cases.json"
        )
        if not case["expected_in_scope"]
        and case["query_id"] == "ABS-004"
    )

    results = []

    for case in cases:
        llm = create_crewai_llm(query=case.query)
        response = run_practo_query(case.query, llm=llm)

        cited_sources = {source.source_id for source in response.sources}
        expected_sources = set(case.expected_relevant_sources)
        if response.status != ResponseStatus.ANSWERED:
            raise RuntimeError(
                f"{case.query_id} did not produce an answer: "
                f"{response.reason}"
            )
        if not expected_sources.issubset(cited_sources):
            raise RuntimeError(
                f"{case.query_id} did not cite all expected sources. "
                f"Expected {sorted(expected_sources)}, "
                f"received {sorted(cited_sources)}."
            )
        if "search_practo_knowledge_base" not in llm.tool_actions:
            raise RuntimeError(
                f"{case.query_id} did not invoke the knowledge-base tool."
            )

        results.append({
            "query_id": case.query_id,
            "query": case.query,
            "status": response.status.value,
            "expected_sources": sorted(expected_sources),
            "cited_sources": sorted(cited_sources),
            "tool_actions": llm.tool_actions,
            "answer": response.answer,
        })

    out_of_scope_llm = create_crewai_llm(query=out_of_scope["query"])
    out_of_scope_response = run_practo_query(
        out_of_scope["query"],
        llm=out_of_scope_llm,
    )
    if out_of_scope_response.status != ResponseStatus.ABSTAINED:
        raise RuntimeError(
            "The out-of-scope query did not trigger an abstention."
        )

    results.append({
        "query_id": out_of_scope["query_id"],
        "query": out_of_scope["query"],
        "status": out_of_scope_response.status.value,
        "expected_sources": [],
        "cited_sources": [],
        "tool_actions": out_of_scope_llm.tool_actions,
        "answer": out_of_scope_response.answer,
    })

    report = {
        "configuration": {
            "mock_llm": True,
            "retrieval_strategy": DEFAULT_RETRIEVAL_CONFIG.strategy,
            "collection": DEFAULT_RETRIEVAL_CONFIG.collection_name,
            "top_k": DEFAULT_RETRIEVAL_CONFIG.top_k,
            "abstention_threshold": (
                DEFAULT_GROUNDING_CONFIG.abstention_threshold
            ),
            "in_scope_query_count": len(cases),
            "out_of_scope_query_count": 1,
        },
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Grounded generation passed for {len(cases)} in-scope queries "
        "and one out-of-scope abstention."
    )
    print(f"Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
