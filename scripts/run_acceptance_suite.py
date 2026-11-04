"""Run the 20-scenario offline acceptance suite and persist final artifacts."""

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "src"
RESULTS_PATH = (
    PROJECT_ROOT / "evaluation" / "results" / "acceptance_results.json"
)
TRACES_PATH = (
    PROJECT_ROOT / "evaluation" / "traces" / "acceptance_traces.jsonl"
)
REPORT_PATH = PROJECT_ROOT / "reports" / "acceptance_report.md"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

os.environ["MOCK_LLM"] = "true"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from practo_agent.evaluation import (  # noqa: E402
    format_acceptance_markdown_report,
    run_acceptance_suite,
)


def main() -> None:
    report = run_acceptance_suite()
    if not report.all_passed:
        raise RuntimeError(
            f"Acceptance suite failed: {report.passed_scenarios}/"
            f"{report.total_scenarios} passed."
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRACES_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = report.model_dump(mode="json")
    trace_events = payload.pop("trace_events")
    payload["trace_event_count"] = len(trace_events)
    payload["traces_file"] = "evaluation/traces/acceptance_traces.jsonl"

    RESULTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    TRACES_PATH.write_text(
        "\n".join(
            json.dumps(event, ensure_ascii=False) for event in trace_events
        )
        + "\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(
        format_acceptance_markdown_report(report) + "\n",
        encoding="utf-8",
    )

    print(
        f"Acceptance suite passed: {report.passed_scenarios}/"
        f"{report.total_scenarios} scenarios."
    )
    print(f"Keyless MOCK_LLM execution: {report.keyless_execution}")
    print(f"Zero external network calls: {report.zero_external_network_calls}")
    print(f"JSON results saved to: {RESULTS_PATH}")
    print(f"JSONL traces saved to: {TRACES_PATH}")
    print(f"Markdown report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()

