
import unittest

import chromadb

from src.practo_agent.rag.chunkers import TextChunk
from src.practo_agent.rag.embeddings import (
    DeterministicTestEmbeddings,
    create_embedding_model,
)
from src.practo_agent.rag.vectorstore import ChromaVectorStore


def make_chunk(
    chunk_id: str,
    text: str,
    strategy: str = "fixed_size",
) -> TextChunk:
    return TextChunk(
        chunk_id=chunk_id,
        source_id="test_policy",
        source_path="data/knowledge_base/test_policy.md",
        title="Test Policy",
        topic="test_policy",
        strategy=strategy,
        chunk_index=0,
        text=text,
        start_char=0,
        end_char=len(text),
    )


class TestEmbeddings(unittest.TestCase):

    def test_mock_mode_creates_deterministic_embeddings(self):
        embeddings = create_embedding_model(mock_mode=True)

        first = embeddings.embed_query("appointment booking")
        second = embeddings.embed_query("appointment booking")

        self.assertEqual(first, second)

    def test_document_embedding_rejects_empty_text(self):
        embeddings = DeterministicTestEmbeddings()

        with self.assertRaises(ValueError):
            embeddings.embed_documents(["valid text", ""])

    def test_query_embedding_rejects_empty_text(self):
        embeddings = DeterministicTestEmbeddings()

        with self.assertRaises(ValueError):
            embeddings.embed_query("   ")


class TestChromaVectorStore(unittest.TestCase):

    def setUp(self):
        self.client = chromadb.EphemeralClient()

        # Remove collections left behind by earlier tests.
        existing_collections = {
            getattr(collection, "name", collection)
            for collection in self.client.list_collections()
        }

        for name in ("practo_fixed_size", "practo_sentence"):
            if name in existing_collections:
                self.client.delete_collection(name)

        self.embeddings = DeterministicTestEmbeddings()

    def make_store(self, strategy="fixed_size"):
        return ChromaVectorStore(
            strategy,
            self.embeddings,
            client=self.client,
        )

    def test_add_and_search_chunks(self):
        store = self.make_store()

        store.add_chunks([
            make_chunk(
                "booking::fixed::0000",
                "Appointments are booked using the clinic booking channel.",
            ),
            make_chunk(
                "fees::fixed::0000",
                "The sample consultation fee is listed by specialty.",
            ),
        ])

        results = store.search("appointment booking", top_k=1)

        self.assertEqual(len(results), 1)
        self.assertIn("chunk_id", results[0])
        self.assertIn("metadata", results[0])
        self.assertIn("distance", results[0])

    def test_metadata_is_preserved(self):
        store = self.make_store()

        store.add_chunks([
            make_chunk(
                "booking::fixed::0000",
                "Appointment booking policy.",
            )
        ])

        result = store.search("appointment", top_k=1)[0]

        self.assertEqual(result["metadata"]["source_id"], "test_policy")
        self.assertEqual(result["metadata"]["strategy"], "fixed_size")

    def test_strategy_mismatch_is_rejected(self):
        store = self.make_store()

        with self.assertRaises(ValueError):
            store.add_chunks([
                make_chunk(
                    "booking::sentence::0000",
                    "Appointment booking policy.",
                    strategy="sentence",
                )
            ])

    def test_empty_query_is_rejected(self):
        store = self.make_store()

        with self.assertRaises(ValueError):
            store.search("  ")

    def test_nonpositive_top_k_is_rejected(self):
        store = self.make_store()

        with self.assertRaises(ValueError):
            store.search("appointment", top_k=0)

    
    def test_separate_strategies_use_separate_collections(self):
        fixed = ChromaVectorStore(
            "fixed_size",
            self.embeddings,
            client=self.client,
        )
        sentence = ChromaVectorStore(
            "sentence",
            self.embeddings,
            client=self.client,
        )

        fixed.add_chunks([
            make_chunk("fixed::0000", "Fixed chunk", "fixed_size")
        ])
        sentence.add_chunks([
            make_chunk("sentence::0000", "Sentence chunk", "sentence")
        ])

        self.assertEqual(fixed.count, 1)
        self.assertEqual(sentence.count, 1)

        self.assertEqual(fixed._collection.name, "practo_fixed_size")
        self.assertEqual(sentence._collection.name, "practo_sentence")


if __name__ == "__main__":
    unittest.main()
