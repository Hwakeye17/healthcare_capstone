"""Structured contracts for the AutoGen response-review agents."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from practo_agent.schemas import AgentResponse, ResponseStatus


class ReviewFeedback(BaseModel):
    """Reviewer decision and concrete issues for the final editor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    issues: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_issues(self):
        if self.approved and self.issues:
            raise ValueError("An approved response must not have review issues.")
        if not self.approved and not self.issues:
            raise ValueError("A rejected response must identify review issues.")
        return self


class FinalEditorOutput(BaseModel):
    """Structured final answer produced by the AutoGen editor agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ResponseStatus
    answer: str = Field(min_length=1)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_response(self):
        if self.status == ResponseStatus.ANSWERED:
            if not self.answer.strip():
                raise ValueError("An answered response must contain an answer.")
            if self.reason is not None:
                raise ValueError("An answered response must not include a reason.")
        elif self.status == ResponseStatus.ABSTAINED:
            if not self.answer.strip():
                raise ValueError("An abstained response must contain a message.")
            if not self.reason or not self.reason.strip():
                raise ValueError("An abstained response must include a reason.")
        return self


class ReviewResult(BaseModel):
    """Validated review output and its recorded reviewer decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response: AgentResponse
    feedback: ReviewFeedback
    revised: bool
    agent_turns: int = Field(ge=2, le=2)
