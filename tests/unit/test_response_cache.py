import pytest

from practo_agent.cache import ResponseCache
from practo_agent.cache.response import normalize_query
from practo_agent.schemas import AgentResponse, ResponseStatus


def _answered_response(answer="Supported answer."):
    return AgentResponse(
        status=ResponseStatus.ANSWERED,
        answer=answer,
        sources=[{"source_id": "booking", "title": "Booking"}],
    )


def _abstained_response():
    return AgentResponse(
        status=ResponseStatus.ABSTAINED,
        answer="I could not find a supported answer.",
        reason="Insufficient evidence.",
    )


def test_normalizes_case_and_whitespace():
    assert normalize_query("  HOW   can I book? \n") == "how can i book?"


def test_cache_key_is_deterministic_for_normalized_queries():
    first = ResponseCache.make_key(
        "How can I book?",
        context="Prior turn",
        scope="session-a",
    )
    second = ResponseCache.make_key(
        "  HOW can   I BOOK? ",
        context="Prior turn",
        scope="session-a",
    )

    assert first == second


def test_equivalent_query_returns_cached_response_without_recomputing():
    cache = ResponseCache()
    calls = []

    def compute():
        calls.append(True)
        return _answered_response()

    first, first_was_cached = cache.get_or_compute(
        "How can I book?",
        compute,
        context="prior context",
        scope="session-a",
    )
    second, second_was_cached = cache.get_or_compute(
        " HOW can I   BOOK? ",
        compute,
        context="prior context",
        scope="session-a",
    )

    assert first == second
    assert first_was_cached is False
    assert second_was_cached is True
    assert len(calls) == 1
    assert cache.stats == {
        "hits": 1,
        "misses": 1,
        "compute_invocations": 1,
        "entries": 1,
    }


@pytest.mark.parametrize(
    ("context", "scope"),
    [
        ("different prior context", "session-a"),
        ("prior context", "session-b"),
    ],
)
def test_cache_does_not_mix_contexts_or_sessions(context, scope):
    cache = ResponseCache()
    calls = []

    def compute():
        calls.append(True)
        return _answered_response(answer=f"Answer {len(calls)}.")

    cache.get_or_compute(
        "How can I book?",
        compute,
        context="prior context",
        scope="session-a",
    )
    response, was_cached = cache.get_or_compute(
        "How can I book?",
        compute,
        context=context,
        scope=scope,
    )

    assert was_cached is False
    assert response.answer == "Answer 2."
    assert len(calls) == 2
    assert cache.stats["entries"] == 2


def test_abstained_responses_are_not_cached():
    cache = ResponseCache()
    calls = []

    def compute():
        calls.append(True)
        return _abstained_response()

    cache.get_or_compute("Unsupported question?", compute)
    cache.get_or_compute("Unsupported question?", compute)

    assert len(calls) == 2
    assert cache.stats == {
        "hits": 0,
        "misses": 2,
        "compute_invocations": 2,
        "entries": 0,
    }


def test_failed_computation_is_not_cached_and_error_is_propagated():
    cache = ResponseCache()

    def fail():
        raise RuntimeError("workflow failed")

    with pytest.raises(RuntimeError, match="workflow failed"):
        cache.get_or_compute("Question?", fail)

    assert cache.stats["entries"] == 0
    assert cache.stats["compute_invocations"] == 1


def test_clear_removes_entries_and_resets_counters():
    cache = ResponseCache()
    cache.get_or_compute("Question?", _answered_response)
    cache.clear()

    assert cache.stats == {
        "hits": 0,
        "misses": 0,
        "compute_invocations": 0,
        "entries": 0,
    }
