
import unittest

from practo_agent.config import (
    DEFAULT_RETRIEVAL_CONFIG,
    RetrievalConfig,
)


class TestRetrievalConfig(unittest.TestCase):

    def test_default_strategy_is_sentence(self):
        config = DEFAULT_RETRIEVAL_CONFIG

        self.assertEqual(config.strategy, "sentence")

    def test_default_top_k_is_three(self):
        config = DEFAULT_RETRIEVAL_CONFIG

        self.assertEqual(config.top_k, 3)

    def test_default_collection_is_sentence_collection(self):
        config = DEFAULT_RETRIEVAL_CONFIG

        self.assertEqual(
            config.collection_name,
            "practo_sentence",
        )

    def test_default_similarity_metric_is_cosine(self):
        config = DEFAULT_RETRIEVAL_CONFIG

        self.assertEqual(config.similarity_metric, "cosine")

    def test_fixed_size_configuration_is_supported(self):
        config = RetrievalConfig(strategy="fixed_size")

        self.assertEqual(
            config.collection_name,
            "practo_fixed_size",
        )

    def test_custom_top_k_is_supported(self):
        config = RetrievalConfig(top_k=5)

        self.assertEqual(config.top_k, 5)

    def test_invalid_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(strategy="semantic")

    def test_zero_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(top_k=0)

    def test_negative_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(top_k=-1)

    def test_non_integer_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(top_k=2.5)

    def test_boolean_top_k_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(top_k=True)

    def test_unsupported_similarity_metric_is_rejected(self):
        with self.assertRaises(ValueError):
            RetrievalConfig(similarity_metric="euclidean")

    def test_configuration_is_immutable(self):
        config = RetrievalConfig()

        with self.assertRaises(AttributeError):
            config.top_k = 5


if __name__ == "__main__":
    unittest.main()
