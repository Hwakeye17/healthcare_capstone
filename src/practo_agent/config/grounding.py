"""Configuration for validating retrieved evidence before generation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundingConfig:
    """Validated settings for retrieval evidence acceptance."""

    abstention_threshold: float = 0.6976266205310822

    def __post_init__(self) -> None:
        threshold = self.abstention_threshold

        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise ValueError("abstention_threshold must be a number.")

        if not 0.0 <= threshold <= 2.0:
            raise ValueError(
                "abstention_threshold must be between 0.0 and 2.0."
            )


DEFAULT_GROUNDING_CONFIG = GroundingConfig()