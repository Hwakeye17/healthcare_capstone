"""Demonstrate oversized-request rejection without making model calls."""

import json
from pathlib import Path

from practo_agent.agents.mock_llm import MockCrewAILLM
from practo_agent.agents.workflow import run_practo_query
from practo_agent.config.runtime_budget import RuntimeBudget
from practo_agent.schemas import ResponseStatus


def main() -> None:
    query = "oversized " * 3000
    llm = MockCrewAILLM(query=query)
    budget = RuntimeBudget()
    response = run_practo_query(
        query,
        llm=llm,
        runtime_budget=budget,
    )

    assert response.status == ResponseStatus.ABSTAINED
    assert "request input exceeds" in response.reason
    assert llm.call_count == 0
    assert budget.stats["rejected"] is True

    report = {
        "status": response.status.value,
        "reason": response.reason,
        "query_characters": len(query),
        "budget": budget.stats,
        "llm_call_count": llm.call_count,
        "expected": {
            "status": ResponseStatus.ABSTAINED.value,
            "rejected_before_llm": True,
            "llm_call_count": 0,
        },
        "result_matches_expectation": True,
    }
    report_path = (
        Path(__file__).resolve().parents[1]
        / "evaluation"
        / "results"
        / "runtime_budget_demo.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
