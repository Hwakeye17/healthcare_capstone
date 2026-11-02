
import pytest
from pydantic import ValidationError

from practo_agent.schemas import (
    ClaimAssessment,
    GroundednessAssessment,
)


def test_accepts_fully_supported_claims():
    result = GroundednessAssessment(
        grounded=True,
        reason="All claims are supported.",
        claim_assessments=[
            ClaimAssessment(
                claim="Appointment confirmation is required.",
                supported=True,
                explanation="The evidence explicitly states this."
            )
        ],
    )

    assert result.grounded is True


def test_accepts_unsupported_claims():
    result = GroundednessAssessment(
        grounded=False,
        reason="One claim is unsupported.",
        claim_assessments=[
            ClaimAssessment(
                claim="Every patient receives a discount.",
                supported=False,
                explanation="The evidence describes conditional eligibility."
            )
        ],
    )

    assert result.grounded is False


def test_rejects_empty_claim_assessments():
    with pytest.raises(ValidationError):
        GroundednessAssessment(
            grounded=True,
            reason="No claims were checked.",
            claim_assessments=[],
        )


def test_rejects_inconsistent_grounded_flag():
    with pytest.raises(ValidationError):
        GroundednessAssessment(
            grounded=True,
            reason="Incorrect assessment.",
            claim_assessments=[
                ClaimAssessment(
                    claim="A guaranteed discount is available.",
                    supported=False,
                    explanation="The evidence does not guarantee it."
                )
            ],
        )


def test_rejects_empty_claim():
    with pytest.raises(ValidationError):
        ClaimAssessment(
            claim="",
            supported=True,
            explanation="Evidence supports the claim."
        )


def test_rejects_empty_explanation():
    with pytest.raises(ValidationError):
        ClaimAssessment(
            claim="Appointment confirmation is required.",
            supported=True,
            explanation=""
        )


def test_rejects_unexpected_fields():
    with pytest.raises(ValidationError):
        ClaimAssessment(
            claim="Appointment confirmation is required.",
            supported=True,
            explanation="Supported by evidence.",
            extra_field="unexpected",
        )
