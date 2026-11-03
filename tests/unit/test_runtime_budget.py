import pytest

from practo_agent.config.runtime_budget import (
    RuntimeBudget,
    RuntimeBudgetConfig,
    RuntimeBudgetExceeded,
    estimate_tokens,
)


def test_request_input_is_checked_before_model_execution():
    budget = RuntimeBudget(
        RuntimeBudgetConfig(
            max_request_input_tokens=10,
            max_total_estimated_tokens=1100,
            max_completion_tokens_per_call=1024,
        )
    )

    with pytest.raises(RuntimeBudgetExceeded, match="request input"):
        budget.check_request("x" * 31)

    assert budget.stats["estimated_request_input_tokens"] == 11
    assert budget.stats["llm_calls"] == 0
    assert budget.stats["rejected"] is True


def test_call_reservation_uses_configured_rates_and_caps():
    budget = RuntimeBudget(
        RuntimeBudgetConfig(
            max_request_input_tokens=100,
            max_total_estimated_tokens=1500,
            max_completion_tokens_per_call=1000,
            input_cost_per_million_tokens_usd=0.80,
            output_cost_per_million_tokens_usd=4.00,
        )
    )
    messages = "x" * 300

    budget.reserve_llm_call(messages)

    expected_input_tokens = estimate_tokens(messages)
    assert budget.stats["estimated_llm_input_tokens"] == expected_input_tokens
    assert budget.stats["reserved_output_tokens"] == 1000
    assert budget.stats["estimated_cost_usd"] == pytest.approx(
        (expected_input_tokens * 0.80 + 1000 * 4.00) / 1_000_000
    )
    assert budget.stats["llm_calls"] == 1

    with pytest.raises(RuntimeBudgetExceeded, match="total token budget"):
        budget.reserve_llm_call(messages)

    assert budget.stats["llm_calls"] == 1
    assert budget.stats["rejected"] is True


def test_call_is_rejected_when_configured_cost_cap_would_be_exceeded():
    budget = RuntimeBudget(
        RuntimeBudgetConfig(
            max_request_input_tokens=100,
            max_total_estimated_tokens=2000,
            max_completion_tokens_per_call=1024,
            max_estimated_cost_usd=0.001,
        )
    )

    with pytest.raises(RuntimeBudgetExceeded, match="cost budget"):
        budget.reserve_llm_call("short prompt")

    assert budget.stats["llm_calls"] == 0
    assert budget.stats["rejected"] is True


def test_token_estimate_counts_utf8_bytes_and_empty_input():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 2
    assert estimate_tokens("é") == 1


def test_environment_values_are_loaded_and_validated(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_INPUT_TOKENS", "4096")
    monkeypatch.setenv("MAX_TOTAL_ESTIMATED_TOKENS", "8192")
    monkeypatch.setenv("MAX_COMPLETION_TOKENS_PER_CALL", "512")
    monkeypatch.setenv("MAX_ESTIMATED_COST_USD", "0.025")

    config = RuntimeBudgetConfig.from_environment()

    assert config.max_request_input_tokens == 4096
    assert config.max_total_estimated_tokens == 8192
    assert config.max_completion_tokens_per_call == 512
    assert config.max_estimated_cost_usd == 0.025
