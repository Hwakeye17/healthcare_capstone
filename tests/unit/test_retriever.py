
import unittest
from unittest.mock import Mock

from practo_agent.config import RetrievalConfig
from practo_agent.rag.retriever import retrieve


class TestRetriever(unittest.TestCase):

    def setUp(self):
        self.store = Mock()
        self.store.strategy = "sentence"
        self.store.search.return_value = [
            {"chunk_id": "test::0001", "text": "Test result"}
        ]

    def test_default_configuration_uses_sentence_strategy(self):
        results = retrieve(self.store, "appointment booking")

        self.store.search.assert_called_once_with(
            "appointment booking",
            top_k=3,
        )
        self.assertEqual(len(results), 1)

    def test_custom_top_k_is_used(self):
        retrieve(
            self.store,
            "appointment booking",
            config=RetrievalConfig(top_k=5),
        )

        self.store.search.assert_called_once_with(
            "appointment booking",
            top_k=5,
        )

    def test_explicit_top_k_override_is_supported(self):
        retrieve(
            self.store,
            "appointment booking",
            top_k=2,
        )

        self.store.search.assert_called_once_with(
            "appointment booking",
            top_k=2,
        )

    def test_strategy_mismatch_is_rejected(self):
        self.store.strategy = "fixed_size"

        with self.assertRaises(ValueError):
            retrieve(
                self.store,
                "appointment booking",
                config=RetrievalConfig(strategy="sentence"),
            )

        self.store.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
