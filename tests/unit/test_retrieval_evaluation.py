
import unittest

from practo_agent.evaluation.cases import EvaluationCase
from practo_agent.evaluation.retrieval import (
    compare_strategies,
    evaluate_query,
    evaluate_strategy,
)


class FakeVectorStore:

    def __init__(self, results_by_query):
        self.results_by_query = results_by_query
        self.search_calls = []

    def search(self, query, top_k=3):
        self.search_calls.append((query, top_k))
        return self.results_by_query.get(query, [])[:top_k]


def make_chunk(chunk_id, source_id, distance=0.2):
    return {
        "chunk_id": chunk_id,
        "text": f"Content from {source_id}",
        "metadata": {"source_id": source_id},
        "distance": distance,
    }


class TestEvaluateQuery(unittest.TestCase):

    def setUp(self):
        self.case = EvaluationCase(
            query_id="TEST-001",
            query="How can an appointment be booked?",
            expected_relevant_sources=("booking", "fees"),
        )

    def test_calculates_precision_and_recall(self):
        chunks = [
            make_chunk("booking::0000", "booking"),
            make_chunk("other::0000", "other"),
            make_chunk("fees::0000", "fees"),
        ]

        result = evaluate_query(self.case, chunks)

        self.assertEqual(result["tp_count"], 2)
        self.assertEqual(result["fp_count"], 1)
        self.assertEqual(result["fn_count"], 0)
        self.assertAlmostEqual(result["precision"], 2 / 3)
        self.assertAlmostEqual(result["recall"], 1.0)

    def test_deduplicates_repeated_source_documents(self):
        chunks = [
            make_chunk("booking::0000", "booking"),
            make_chunk("booking::0001", "booking"),
            make_chunk("fees::0000", "fees"),
        ]

        result = evaluate_query(self.case, chunks)

        self.assertEqual(
            result["retrieved_source_ids"],
            ["booking", "fees"],
        )
        self.assertEqual(result["tp_count"], 2)
        self.assertEqual(result["fp_count"], 0)
        self.assertAlmostEqual(result["precision"], 1.0)

    def test_counts_missing_expected_sources_as_false_negatives(self):
        chunks = [
            make_chunk("booking::0000", "booking"),
        ]

        result = evaluate_query(self.case, chunks)

        self.assertEqual(result["fn_count"], 1)
        self.assertEqual(result["false_negatives"], ["fees"])
        self.assertAlmostEqual(result["recall"], 0.5)

    def test_returns_zero_recall_when_no_expected_source_is_found(self):
        chunks = [
            make_chunk("other::0000", "other"),
        ]

        result = evaluate_query(self.case, chunks)

        self.assertEqual(result["tp_count"], 0)
        self.assertEqual(result["fp_count"], 1)
        self.assertEqual(result["fn_count"], 2)
        self.assertEqual(result["precision"], 0.0)
        self.assertEqual(result["recall"], 0.0)

    def test_precision_is_undefined_when_nothing_is_retrieved(self):
        result = evaluate_query(self.case, [])

        self.assertIsNone(result["precision"])
        self.assertEqual(result["recall"], 0.0)

    def test_rejects_chunks_without_source_metadata(self):
        with self.assertRaisesRegex(ValueError, "source_id"):
            evaluate_query(
                self.case,
                [{"chunk_id": "invalid", "metadata": {}}],
            )

    def test_preserves_retrieval_distance_and_chunk_id(self):
        result = evaluate_query(
            self.case,
            [make_chunk("booking::0000", "booking", 0.15)],
        )

        self.assertEqual(
            result["retrieved_chunks"][0]["chunk_id"],
            "booking::0000",
        )
        self.assertEqual(
            result["retrieved_chunks"][0]["distance"],
            0.15,
        )


class TestEvaluateStrategy(unittest.TestCase):

    def setUp(self):
        self.cases = [
            EvaluationCase(
                query_id="TEST-001",
                query="Question one",
                expected_relevant_sources=("booking",),
            ),
            EvaluationCase(
                query_id="TEST-002",
                query="Question two",
                expected_relevant_sources=("fees",),
            ),
        ]

    def test_evaluates_every_case(self):
        store = FakeVectorStore({
            "Question one": [make_chunk("b1", "booking")],
            "Question two": [make_chunk("f1", "fees")],
        })

        result = evaluate_strategy(
            self.cases,
            store,
            "fixed_size",
            top_k=3,
        )

        self.assertEqual(result["query_count"], 2)
        self.assertEqual(len(result["queries"]), 2)

    def test_calculates_macro_averages(self):
        store = FakeVectorStore({
            "Question one": [make_chunk("b1", "booking")],
            "Question two": [
                make_chunk("f1", "fees"),
                make_chunk("x1", "other"),
            ],
        })

        result = evaluate_strategy(
            self.cases,
            store,
            "fixed_size",
            top_k=3,
        )

        self.assertAlmostEqual(
            result["macro_precision"],
            0.75,
        )
        self.assertAlmostEqual(
            result["macro_recall"],
            1.0,
        )

    def test_rejects_empty_case_list(self):
        store = FakeVectorStore({})

        with self.assertRaisesRegex(ValueError, "At least one"):
            evaluate_strategy([], store, "fixed_size")

    def test_rejects_nonpositive_top_k(self):
        store = FakeVectorStore({})

        with self.assertRaisesRegex(ValueError, "positive"):
            evaluate_strategy(
                self.cases,
                store,
                "fixed_size",
                top_k=0,
            )

    def test_passes_top_k_to_store(self):
        store = FakeVectorStore({
            "Question one": [make_chunk("b1", "booking")],
            "Question two": [make_chunk("f1", "fees")],
        })

        evaluate_strategy(
            self.cases,
            store,
            "fixed_size",
            top_k=5,
        )

        self.assertEqual(
            store.search_calls,
            [("Question one", 5), ("Question two", 5)],
        )


class TestCompareStrategies(unittest.TestCase):

    def test_uses_same_queries_for_both_strategies(self):
        cases = [
            EvaluationCase(
                query_id="TEST-001",
                query="Question one",
                expected_relevant_sources=("booking",),
            )
        ]

        fixed_store = FakeVectorStore({
            "Question one": [make_chunk("b1", "booking")]
        })

        sentence_store = FakeVectorStore({
            "Question one": [make_chunk("b2", "booking")]
        })

        result = compare_strategies(
            cases,
            fixed_store,
            sentence_store,
            top_k=3,
        )

        self.assertEqual(
            result["strategies"]["fixed_size"]["query_count"],
            1,
        )
        self.assertEqual(
            result["strategies"]["sentence"]["query_count"],
            1,
        )
        self.assertEqual(len(fixed_store.search_calls), 1)
        self.assertEqual(len(sentence_store.search_calls), 1)

    def test_both_strategies_use_same_top_k(self):
        cases = [
            EvaluationCase(
                query_id="TEST-001",
                query="Question one",
                expected_relevant_sources=("booking",),
            )
        ]

        fixed_store = FakeVectorStore({
            "Question one": [make_chunk("b1", "booking")]
        })

        sentence_store = FakeVectorStore({
            "Question one": [make_chunk("b2", "booking")]
        })

        compare_strategies(
            cases,
            fixed_store,
            sentence_store,
            top_k=2,
        )

        self.assertEqual(fixed_store.search_calls[0][1], 2)
        self.assertEqual(sentence_store.search_calls[0][1], 2)


if __name__ == "__main__":
    unittest.main()
