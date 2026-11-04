"""Run live LLM-as-a-judge evaluation for the healthcare support assistant."""

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "src"
RESULTS_PATH = (
    PROJECT_ROOT
    / "evaluation"
    / "results"
    / "response_quality_results.json"
)
REPORT_PATH = PROJECT_ROOT / "reports" / "response_quality_report.md"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

os.environ["MOCK_LLM"] = "false"

from practo_agent.agents import run_practo_query
from practo_agent.config.llm import get_llm_config
from practo_agent.config.runtime_budget import RuntimeBudget
from practo_agent.evaluation.llm_judge import (
    GroqResponseJudge,
    load_quality_cases,
    run_quality_evaluation,
    validate_live_mode,
    write_quality_report,
)


def main() -> None:
    validate_live_mode()
    cases = load_quality_cases()
    judge = GroqResponseJudge()

    def run_assistant(query: str, budget: RuntimeBudget):
        return run_practo_query(query, runtime_budget=budget)

    results = run_quality_evaluation(
        cases,
        assistant=run_assistant,
        judge=judge,
    )
    results["assistant"] = {
        "provider": "groq",
        "model": get_llm_config()["model"],
    }
    results["case_file"] = "evaluation/cases/response_quality_cases.json"
    write_quality_report(results, RESULTS_PATH, REPORT_PATH)

    print("Response quality evaluation completed.")
    print(f"Queries evaluated: {results['query_count']}")
    for dimension, average in results["averages"].items():
        print(f"Average {dimension}: {average:.2f}/5")
    print(f"Machine-readable results: {RESULTS_PATH}")
    print(f"Readable report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
