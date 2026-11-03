import pytest

from practo_agent.agents.routing import route_query


@pytest.mark.parametrize(
    ("query", "retrieval_enabled", "lookup_enabled", "record_id"),
    [
        ("How do I reschedule an appointment?", True, False, None),
        ("What is the status of APT-0001?", False, True, "APT-0001"),
        (
            "What is the status of APT-0001 and how do I reschedule?",
            True,
            True,
            "APT-0001",
        ),
        ("Who won the latest cricket world cup?", True, False, None),
    ],
)
def test_route_query_selects_only_relevant_capabilities(
    query,
    retrieval_enabled,
    lookup_enabled,
    record_id,
):
    route = route_query(query)

    assert route.retrieval_enabled is retrieval_enabled
    assert route.lookup_enabled is lookup_enabled
    assert route.record_id == record_id


@pytest.mark.parametrize("query", ["", "  ", None, 123])
def test_route_query_rejects_invalid_input(query):
    with pytest.raises(ValueError, match="query"):
        route_query(query)


def test_route_query_does_not_guess_when_multiple_record_ids_are_supplied():
    route = route_query(
        "Compare the status of APT-0001 and APT-0002."
    )

    assert route.retrieval_enabled is False
    assert route.lookup_enabled is False
    assert route.record_id is None
    assert route.clarification_required is True


def test_repeated_reference_to_same_record_id_is_not_ambiguous():
    route = route_query(
        "Earlier I asked about APT-0001. What is the status of APT-0001?"
    )

    assert route.lookup_enabled is True
    assert route.record_id == "APT-0001"
    assert route.clarification_required is False
