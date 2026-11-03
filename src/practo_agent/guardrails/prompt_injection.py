"""Detect common prompt-injection and restricted-information requests."""

import re
from enum import Enum


class PromptInjectionCategory(str, Enum):
    """Categories of prompt-injection requests blocked by the input guardrail."""

    INSTRUCTION_OVERRIDE = "instruction_override"
    RESTRICTED_INFORMATION = "restricted_information"


_INSTRUCTION_OVERRIDE_PATTERNS = (
    re.compile(
        r"\b(?:ignore|disregard|forget|override|bypass)\s+"
        r"(?:(?:all|any|the|your)\s+)?"
        r"(?:(?:previous|prior|above|earlier|system|developer|"
        r"safety|security)\s+){0,2}"
        r"(?:instructions?|prompts?|rules?|policies)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:do not|don't|never)\s+(?:follow|obey|adhere to)\s+"
        r"(?:(?:the|your)\s+)?"
        r"(?:system|developer|safety|security)\s+"
        r"(?:instructions?|prompts?|rules?|policies)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you are now|act as|pretend to be)\s+"
        r"(?:an?\s+)?"
        r"(?:unrestricted|developer|system|administrator|admin|root|"
        r"jailbroken)\b",
        re.IGNORECASE,
    ),
)

_RESTRICTED_INFORMATION_PATTERNS = (
    re.compile(
        r"\b(?:reveal|show|print|display|repeat|provide|disclose|quote|"
        r"export|dump|share|tell me|what is)\b.{0,60}\b"
        r"(?:system|developer|hidden|internal)\s+"
        r"(?:prompt|instructions?|message|rules?|configuration|config)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:reveal|show|print|display|repeat|provide|disclose|quote|"
        r"export|dump|share|tell me|list|give me)\b.{0,60}\b"
        r"(?:api keys?|credentials?|passwords?|secrets?|access tokens?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(?:show|give|list|provide|search|retrieve|export|tell me|dump)"
        r"\b.{0,60}\b(?:all|other|another)\s+"
        r"(?:patients?|users?)(?:['’]s|['’])?\s+"
        r"(?:records?|data|details?|appointments?|contact information|"
        r"personal information)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)


def detect_prompt_injection(
    text: str,
) -> PromptInjectionCategory | None:
    """Return a category for a recognized injection, or ``None`` otherwise.

    This deterministic detector targets common explicit phrases. It is an
    input filter, not a general semantic classifier or a complete security
    boundary.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    if any(pattern.search(text) for pattern in _INSTRUCTION_OVERRIDE_PATTERNS):
        return PromptInjectionCategory.INSTRUCTION_OVERRIDE

    if any(
        pattern.search(text)
        for pattern in _RESTRICTED_INFORMATION_PATTERNS
    ):
        return PromptInjectionCategory.RESTRICTED_INFORMATION

    return None
