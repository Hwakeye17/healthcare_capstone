"""Run the zero-tolerance safety evaluation suite and write JSON/Markdown reports."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JSON_RESULTS_PATH = (
    PROJECT_ROOT / "evaluation" / "results" / "safety_evaluation.json"
)
MARKDOWN_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "safety_evaluation_report.md"
)


def main() -> None:
    source_directory = PROJECT_ROOT / "src"
    if str(source_directory) not in sys.path:
        sys.path.insert(0, str(source_directory))

    from practo_agent.evaluation.safety import (
        evaluate_safety_suite,
        format_safety_markdown_report,
    )

    report = evaluate_safety_suite()
    if not report.zero_tolerance_satisfied:
        failing = [
            f"{item.scenario_id} ({item.objective}): {item.failure_reason}"
            for item in report.scenarios
            if not item.passed
        ]
        raise RuntimeError(
            "Zero-tolerance safety evaluation failed: " + "; ".join(failing)
        )

    JSON_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    JSON_RESULTS_PATH.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_REPORT_PATH.write_text(
        format_safety_markdown_report(report),
        encoding="utf-8",
    )

    print(
        f"Safety evaluation passed: {report.passed_scenarios}/"
        f"{report.total_scenarios} scenarios (zero-tolerance satisfied)."
    )
    print(
        "Unauthorized appointment-tool calls: "
        f"{report.unauthorized_appointment_tool_calls}"
    )
    print(f"Unmasked PII in logs/prompts: {report.unmasked_pii_in_logs}")
    print(f"JSON results saved to: {JSON_RESULTS_PATH}")
    print(f"Markdown report saved to: {MARKDOWN_REPORT_PATH}")


if __name__ == "__main__":
    main()

