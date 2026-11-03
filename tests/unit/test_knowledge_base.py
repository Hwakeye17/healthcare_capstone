
import tempfile
import unittest
from pathlib import Path

from scripts.validate_knowledge_base import (
    MAX_SENTENCES,
    MIN_SENTENCES,
    REQUIRED_DOCUMENTS,
    count_sentences,
    validate_knowledge_base,
)


class TestKnowledgeBase(unittest.TestCase):

    def test_all_required_documents_exist_and_pass_validation(self):
        counts = validate_knowledge_base()

        self.assertEqual(set(counts), REQUIRED_DOCUMENTS)
        self.assertEqual(len(counts), 12)

        for filename, sentence_count in counts.items():
            with self.subTest(filename=filename):
                self.assertGreaterEqual(sentence_count, MIN_SENTENCES)
                self.assertLessEqual(sentence_count, MAX_SENTENCES)

    def test_sentence_counter_ignores_markdown_headings(self):
        text = """# Example Policy

This is the first sentence. This is the second sentence.
"""
        self.assertEqual(count_sentences(text), 2)

    def test_validator_rejects_missing_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_dir = Path(temp_dir)

            with self.assertRaisesRegex(
                ValueError,
                "Missing required knowledge-base documents",
            ):
                validate_knowledge_base(empty_dir)

    def test_validator_rejects_a_document_with_too_few_sentences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_dir = Path(temp_dir)

            for filename in REQUIRED_DOCUMENTS:
                (kb_dir / filename).write_text(
                    "# Sample Policy\nFirst sentence.",
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(
                ValueError,
                "expected 2 to 5 sentences",
            ):
                validate_knowledge_base(kb_dir)

    def test_validator_rejects_a_document_with_too_many_sentences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            kb_dir = Path(temp_dir)
            overlong_document = (
                "# Sample Policy\n"
                + " ".join(
                    f"Sentence {index}."
                    for index in range(MAX_SENTENCES + 1)
                )
            )

            for filename in REQUIRED_DOCUMENTS:
                (kb_dir / filename).write_text(
                    overlong_document,
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(
                ValueError,
                "expected 2 to 5 sentences",
            ):
                validate_knowledge_base(kb_dir)


if __name__ == "__main__":
    unittest.main()
