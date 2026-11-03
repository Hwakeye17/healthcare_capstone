"""Configurable per-request token and estimated-cost budget enforcement."""

import math
import os
from dataclasses import dataclass
from typing import Any


class RuntimeBudgetExceeded(RuntimeError):
    """Raised when a request would exceed its configured runtime budget."""


@dataclass(frozen=True)
class RuntimeBudgetConfig:
    """Limits and model rates used by the per-request budget guard."""

    max_request_input_tokens: int = 8192
    max_total_estimated_tokens: int = 32768
    max_completion_tokens_per_call: int = 1024
    max_estimated_cost_usd: float = 0.05
    input_cost_per_million_tokens_usd: float = 0.80
    output_cost_per_million_tokens_usd: float = 4.00

    def __post_init__(self) -> None:
        integer_fields = (
            self.max_request_input_tokens,
            self.max_total_estimated_tokens,
            self.max_completion_tokens_per_call,
        )
        if any(value <= 0 for value in integer_fields):
            raise ValueError("Token budgets must be positive integers.")
        if (
            self.max_total_estimated_tokens
            < self.max_completion_tokens_per_call
        ):
            raise ValueError(
                "The total token budget must allow one maximum completion."
            )
        if (
            not math.isfinite(self.max_estimated_cost_usd)
            or self.max_estimated_cost_usd <= 0
        ):
            raise ValueError("The estimated cost budget must be positive.")
        if (
            not math.isfinite(self.input_cost_per_million_tokens_usd)
            or not math.isfinite(self.output_cost_per_million_tokens_usd)
            or self.input_cost_per_million_tokens_usd < 0
            or self.output_cost_per_million_tokens_usd < 0
        ):
            raise ValueError("Configured token rates cannot be negative.")

    @classmethod
    def from_environment(cls) -> "RuntimeBudgetConfig":
        """Load validated budget caps and model prices from environment."""

        return cls(
            max_request_input_tokens=_environment_int(
                "MAX_REQUEST_INPUT_TOKENS",
                8192,
            ),
            max_total_estimated_tokens=_environment_int(
                "MAX_TOTAL_ESTIMATED_TOKENS",
                32768,
            ),
            max_completion_tokens_per_call=_environment_int(
                "MAX_COMPLETION_TOKENS_PER_CALL",
                1024,
            ),
            max_estimated_cost_usd=_environment_float(
                "MAX_ESTIMATED_COST_USD",
                0.05,
            ),
            input_cost_per_million_tokens_usd=_environment_float(
                "INPUT_COST_PER_MILLION_TOKENS_USD",
                0.80,
            ),
            output_cost_per_million_tokens_usd=_environment_float(
                "OUTPUT_COST_PER_MILLION_TOKENS_USD",
                4.00,
            ),
        )


class RuntimeBudget:
    """Estimate and enforce token/cost caps across one agent request."""

    def __init__(self, config: RuntimeBudgetConfig | None = None) -> None:
        self.config = (
            config
            if config is not None
            else RuntimeBudgetConfig.from_environment()
        )
        self._request_input_tokens = 0
        self._estimated_input_tokens = 0
        self._reserved_output_tokens = 0
        self._llm_calls = 0
        self._rejected = False

    def check_request(
        self,
        query: str,
        *,
        conversation_context: str = "",
    ) -> int:
        """Reject an oversized user request before routing or model creation."""

        request_text = f"{query}\n{conversation_context}"
        estimated_tokens = estimate_tokens(request_text)
        self._request_input_tokens = estimated_tokens

        if estimated_tokens > self.config.max_request_input_tokens:
            self._rejected = True
            raise RuntimeBudgetExceeded(
                "Estimated request input exceeds the configured token limit "
                f"({estimated_tokens} > "
                f"{self.config.max_request_input_tokens})."
            )
        return estimated_tokens

    def reserve_llm_call(self, messages: Any) -> None:
        """Reserve estimated prompt and maximum completion usage pre-call."""

        input_tokens = estimate_tokens(_serialize_messages(messages))
        projected_input_tokens = self._estimated_input_tokens + input_tokens
        projected_output_tokens = (
            self._reserved_output_tokens
            + self.config.max_completion_tokens_per_call
        )
        projected_total_tokens = (
            projected_input_tokens + projected_output_tokens
        )
        projected_cost = self._estimate_cost(
            projected_input_tokens,
            projected_output_tokens,
        )

        if projected_total_tokens > self.config.max_total_estimated_tokens:
            self._rejected = True
            raise RuntimeBudgetExceeded(
                "Estimated request usage exceeds the configured total token "
                f"budget ({projected_total_tokens} > "
                f"{self.config.max_total_estimated_tokens})."
            )
        if projected_cost > self.config.max_estimated_cost_usd:
            self._rejected = True
            raise RuntimeBudgetExceeded(
                "Estimated request usage exceeds the configured cost budget "
                f"(${projected_cost:.6f} > "
                f"${self.config.max_estimated_cost_usd:.6f})."
            )

        self._estimated_input_tokens = projected_input_tokens
        self._reserved_output_tokens = projected_output_tokens
        self._llm_calls += 1

    @property
    def stats(self) -> dict[str, int | float | bool]:
        """Return a snapshot of estimates and budget decisions."""

        return {
            "estimated_request_input_tokens": self._request_input_tokens,
            "estimated_llm_input_tokens": self._estimated_input_tokens,
            "reserved_output_tokens": self._reserved_output_tokens,
            "estimated_total_tokens": (
                self._estimated_input_tokens + self._reserved_output_tokens
            ),
            "max_request_input_tokens": (
                self.config.max_request_input_tokens
            ),
            "max_total_estimated_tokens": (
                self.config.max_total_estimated_tokens
            ),
            "max_completion_tokens_per_call": (
                self.config.max_completion_tokens_per_call
            ),
            "estimated_cost_usd": self._estimate_cost(
                self._estimated_input_tokens,
                self._reserved_output_tokens,
            ),
            "max_estimated_cost_usd": self.config.max_estimated_cost_usd,
            "llm_calls": self._llm_calls,
            "rejected": self._rejected,
        }

    def _estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        return (
            input_tokens * self.config.input_cost_per_million_tokens_usd
            + output_tokens * self.config.output_cost_per_million_tokens_usd
        ) / 1_000_000


def estimate_tokens(text: str) -> int:
    """Estimate text tokens at roughly one per three UTF-8 bytes.

    This tokenizer-independent approximation is for preflight protection,
    not provider billing. The configured output allowance is reserved per call.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")
    if not text:
        return 0
    return math.ceil(len(text.encode("utf-8")) / 3)


def _serialize_messages(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    return repr(messages)


def _environment_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _environment_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number.") from exc
