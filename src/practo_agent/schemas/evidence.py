"""Pydantic contracts for retrieved evidence and evidence assessment."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetrievedEvidence(BaseModel):
    """A retrieved knowledge-base chunk and its provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    distance: float = Field(ge=0.0, le=2.0)


class EvidenceAssessment(BaseModel):
    """Deterministic decision about whether retrieved evidence is sufficient."""

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    best_distance: float | None = Field(default=None, ge=0.0, le=2.0)
    threshold: float = Field(ge=0.0, le=2.0)
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_assessment(self):
        if not self.evidence:
            if self.accepted:
                raise ValueError(
                    "Evidence cannot be accepted when no chunks were retrieved."
                )

            if self.best_distance is not None:
                raise ValueError(
                    "best_distance must be None when no evidence was retrieved."
                )

            return self

        actual_best_distance = min(
            item.distance for item in self.evidence
        )

        if self.best_distance != actual_best_distance:
            raise ValueError(
                "best_distance must match the minimum retrieved distance."
            )

        if self.accepted != (actual_best_distance <= self.threshold):
            raise ValueError(
                "accepted must agree with the distance threshold."
            )

        return self