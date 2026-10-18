
import unittest
from dataclasses import replace

from src.practo_agent.rag.document_loader import (
    KnowledgeDocument,
    load_knowledge_documents,
)
from src.practo_agent.rag.chunkers import (
    fixed_size_chunk,
    sentence_based_chunk,
    split_sentences,
)


class TestDocumentLoader(unittest.TestCase):

    def test_loads_all_12_knowledge_base_documents(self):
        documents = load_knowledge_documents()

        self.assertEqual(len(documents), 12)

    def test_source_metadata_is_populated(self):
        documents = load_knowledge_documents()

        for document in documents:
            with self.subTest(source=document.source_id):
                self.assertTrue(document.source_id)
                self.assertTrue(document.source_path)
                self.assertTrue(document.title)
                self.assertTrue(document.topic)
                self.assertTrue(document.text.strip())

    def test_documents_are_loaded_in_deterministic_order(self):
        first = load_knowledge_documents()
        second = load_knowledge_documents()

        self.assertEqual(
            [doc.source_id for doc in first],
            [doc.source_id for doc in second],
        )


class TestFixedSizeChunking(unittest.TestCase):

    def setUp(self):
        self.document = KnowledgeDocument(
            source_id="sample_policy",
            source_path="data/knowledge_base/sample_policy.md",
            title="Sample Policy",
            topic="sample_policy",
            text="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        )

    def test_respects_chunk_size(self):
        chunks = fixed_size_chunk(
            self.document,
            chunk_size=10,
            overlap=3,
        )

        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), 10)

    def test_preserves_original_text_and_offsets(self):
        chunks = fixed_size_chunk(
            self.document,
            chunk_size=10,
            overlap=3,
        )

        for chunk in chunks:
            with self.subTest(chunk=chunk.chunk_id):
                self.assertEqual(
                    chunk.text,
                    self.document.text[
                        chunk.start_char:chunk.end_char
                    ],
                )

    def test_adjacent_chunks_overlap_by_configured_amount(self):
        chunks = fixed_size_chunk(
            self.document,
            chunk_size=10,
            overlap=3,
        )

        self.assertGreaterEqual(len(chunks), 2)

        for previous, current in zip(chunks, chunks[1:]):
            self.assertEqual(
                previous.text[-3:],
                current.text[:3],
            )

    def test_invalid_chunk_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            fixed_size_chunk(self.document, chunk_size=0, overlap=0)

        with self.assertRaises(ValueError):
            fixed_size_chunk(self.document, chunk_size=10, overlap=-1)

        with self.assertRaises(ValueError):
            fixed_size_chunk(self.document, chunk_size=10, overlap=10)

    def test_chunk_ids_are_unique(self):
        chunks = fixed_size_chunk(
            self.document,
            chunk_size=10,
            overlap=3,
        )

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))


class TestSentenceBasedChunking(unittest.TestCase):

    def setUp(self):
        self.document = KnowledgeDocument(
            source_id="sample_policy",
            source_path="data/knowledge_base/sample_policy.md",
            title="Sample Policy",
            topic="sample_policy",
            text=(
                "# Sample Policy\n\n"
                "First sentence. Second sentence. Third sentence. "
                "Fourth sentence. Fifth sentence. Sixth sentence."
            ),
        )

    def test_splits_into_complete_sentences(self):
        sentences = split_sentences(self.document.text)

        self.assertEqual(
            sentences,
            [
                "First sentence.",
                "Second sentence.",
                "Third sentence.",
                "Fourth sentence.",
                "Fifth sentence.",
                "Sixth sentence.",
            ],
        )

    def test_groups_sentences_using_configured_limit(self):
        chunks = sentence_based_chunk(
            self.document,
            sentences_per_chunk=3,
            overlap_sentences=1,
        )

        self.assertEqual(len(chunks), 3)

        for chunk in chunks:
            with self.subTest(chunk=chunk.chunk_id):
                self.assertLessEqual(
                    len(split_sentences(chunk.text)),
                    3,
                )

    def test_adjacent_chunks_overlap_by_one_sentence(self):
        chunks = sentence_based_chunk(
            self.document,
            sentences_per_chunk=3,
            overlap_sentences=1,
        )

        first_sentences = split_sentences(chunks[0].text)
        second_sentences = split_sentences(chunks[1].text)

        self.assertEqual(first_sentences[-1], second_sentences[0])

    def test_all_sentences_are_covered_in_order(self):
        original = split_sentences(self.document.text)
        chunks = sentence_based_chunk(
            self.document,
            sentences_per_chunk=3,
            overlap_sentences=1,
        )

        reconstructed = []

        for index, chunk in enumerate(chunks):
            chunk_sentences = split_sentences(chunk.text)

            # Remove the sentence repeated from the preceding chunk.
            if index > 0:
                chunk_sentences = chunk_sentences[1:]

            reconstructed.extend(chunk_sentences)

        self.assertEqual(reconstructed, original)

    def test_invalid_sentence_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            sentence_based_chunk(
                self.document,
                sentences_per_chunk=0,
                overlap_sentences=0,
            )

        with self.assertRaises(ValueError):
            sentence_based_chunk(
                self.document,
                sentences_per_chunk=3,
                overlap_sentences=-1,
            )

        with self.assertRaises(ValueError):
            sentence_based_chunk(
                self.document,
                sentences_per_chunk=3,
                overlap_sentences=3,
            )

    def test_empty_document_body_produces_no_sentence_chunks(self):
        empty_body = replace(
            self.document,
            text="# Sample Policy\n\n",
        )

        chunks = sentence_based_chunk(empty_body)

        self.assertEqual(chunks, [])


if __name__ == "__main__":
    unittest.main()
