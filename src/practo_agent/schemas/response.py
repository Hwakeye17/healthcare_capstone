"""Structured response contracts for the Practo support agent."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResponseStatus(str, Enum):
    """Possible outcomes of a support-agent request."""

    ANSWERED = "answered"
    ABSTAINED = "abstained"


class SourceReference(BaseModel):
    """Reference to a knowledge-base document used as evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class GroundedResponse(BaseModel):
    """Validated response returned by the Practo support agent."""

    model_config = ConfigDict(extra="forbid")

    status: ResponseStatus

    answer: str = Field(
        description="The administrative support answer or abstention message."
    )

    reason: str | None = Field(
        default=None,
        description="Explanation for abstaining, when applicable.",
    )

    sources: list[SourceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_response_consistency(self):
        if self.status == ResponseStatus.ANSWERED:
            if not self.answer.strip():
                raise ValueError("An answered response must contain an answer.")

            if not self.sources:
                raise ValueError(
                    "An answered response must include at least one source."
                )

            if self.reason is not None:
                raise ValueError(
                    "An answered response must not contain an abstention reason."
                )

        elif self.status == ResponseStatus.ABSTAINED:
            if not self.answer.strip():
                raise ValueError("An abstained response must contain a message.")

            if not self.reason or not self.reason.strip():
                raise ValueError(
                    "An abstained response must explain why it abstained."
                )

            if self.sources:
                raise ValueError(
                    "An abstained response must not claim supporting sources."
                )

        return self