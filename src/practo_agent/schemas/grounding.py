
"""Pydantic contracts for generated-answer groundedness validation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClaimAssessment(BaseModel):
    """Assessment of whether one generated claim is supported by evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    claim: str = Field(min_length=1)
    supported: bool
    explanation: str = Field(min_length=1)


class GroundednessAssessment(BaseModel):
    """Structured assessment of all claims in a generated answer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    grounded: bool
    claim_assessments: list[ClaimAssessment] = Field(min_length=1)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_groundedness(self):
        if not self.claim_assessments:
            raise ValueError(
                "At least one claim assessment is required."
            )

        all_claims_supported = all(
            item.supported for item in self.claim_assessments
        )

        if self.grounded != all_claims_supported:
            raise ValueError(
                "grounded must be true only when every assessed claim "
                "is supported by the evidence."
            )

        return self
