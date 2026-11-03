
import json
import tempfile
import unittest
from pathlib import Path

from practo_agent.evaluation.cases import (
    EvaluationCase,
    load_evaluation_cases,
)


class TestEvaluationCases(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        self.kb_dir = self.root / "knowledge_base"
        self.kb_dir.mkdir()

        for source_id in ("booking", "fees", "privacy", "insurance", "lab"):
            (self.kb_dir / f"{source_id}.md").write_text(
                f"# {source_id}\nSample knowledge-base content.",
                encoding="utf-8",
            )

        self.cases_path = self.root / "cases.json"

        self.valid_cases = [
            {
                "query_id": f"TEST-{index:03d}",
                "query": f"Sample query {index}",
                "expected_relevant_sources": ["booking"],
            }
            for index in range(1, 26)
        ]

        self.write_cases(self.valid_cases)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_cases(self, cases):
        self.cases_path.write_text(
            json.dumps(cases, indent=2),
            encoding="utf-8",
        )

    def load_cases(self):
        return load_evaluation_cases(
            cases_path=self.cases_path,
            kb_dir=self.kb_dir,
        )

    def test_loads_valid_evaluation_cases(self):
        cases = self.load_cases()

        self.assertEqual(len(cases), 25)
        self.assertIsInstance(cases[0], EvaluationCase)

    def test_preserves_query_and_expected_sources(self):
        cases = self.load_cases()

        self.assertEqual(cases[0].query, "Sample query 1")
        self.assertEqual(
            cases[0].expected_relevant_sources,
            ("booking",),
        )

    def test_expected_sources_are_immutable(self):
        cases = self.load_cases()

        self.assertIsInstance(
            cases[0].expected_relevant_sources,
            tuple,
        )

        with self.assertRaises(AttributeError):
            cases[0].query = "Changed query"

    def test_rejects_fewer_than_25_cases(self):
        self.write_cases(self.valid_cases[:4])

        with self.assertRaisesRegex(ValueError, "At least 25"):
            self.load_cases()

    def test_rejects_duplicate_query_ids(self):
        cases = list(self.valid_cases)
        cases[1]["query_id"] = cases[0]["query_id"]
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "must be unique"):
            self.load_cases()

    def test_rejects_empty_query(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["query"] = "   "
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "non-empty query"):
            self.load_cases()

    def test_rejects_empty_query_id(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["query_id"] = ""
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "non-empty query_id"):
            self.load_cases()

    def test_rejects_missing_expected_sources(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["expected_relevant_sources"] = []
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "at least one expected source"):
            self.load_cases()

    def test_rejects_unknown_source_identifiers(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["expected_relevant_sources"] = ["unknown_document"]
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "unknown knowledge-base sources"):
            self.load_cases()

    def test_rejects_duplicate_source_identifiers(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["expected_relevant_sources"] = ["booking", "booking"]
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "duplicate source"):
            self.load_cases()

    def test_rejects_unexpected_json_fields(self):
        cases = list(self.valid_cases)
        cases[0] = dict(cases[0])
        cases[0]["unexpected"] = "value"
        self.write_cases(cases)

        with self.assertRaisesRegex(ValueError, "invalid fields"):
            self.load_cases()

    def test_rejects_non_array_json_root(self):
        self.cases_path.write_text(
            json.dumps({"cases": self.valid_cases}),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "JSON array"):
            self.load_cases()

    def test_rejects_invalid_json(self):
        self.cases_path.write_text(
            '{"query_id": ',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "Invalid JSON"):
            self.load_cases()

    def test_rejects_missing_knowledge_base_directory(self):
        with self.assertRaisesRegex(ValueError, "Knowledge-base directory"):
            load_evaluation_cases(
                cases_path=self.cases_path,
                kb_dir=self.root / "missing",
            )


if __name__ == "__main__":
    unittest.main()
