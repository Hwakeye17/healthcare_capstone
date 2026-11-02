"""Centralized application configuration."""

from practo_agent.config.grounding import (
    DEFAULT_GROUNDING_CONFIG,
    GroundingConfig,
)
from practo_agent.config.retrieval import (
    DEFAULT_RETRIEVAL_CONFIG,
    RetrievalConfig,
)

__all__ = [
    "DEFAULT_GROUNDING_CONFIG",
    "DEFAULT_RETRIEVAL_CONFIG",
    "GroundingConfig",
    "RetrievalConfig",
]