"""Fixed-format contact-number masking for user requests."""

import re


_INDIAN_MOBILE_PATTERN = re.compile(
    r"(?<!\w)(?:(?:\+?91|0)[ -]?)?[6-9](?:[ -]?[0-9]){9}(?!\w)"
)
_REDACTION = "[REDACTED_CONTACT_NUMBER]"


def mask_contact_numbers(text: str) -> str:
    """Redact Indian 10-digit mobile numbers while preserving other text.

    The accepted representation allows an optional +91 or 0 prefix and
    optional spaces or hyphens between digits.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    return _INDIAN_MOBILE_PATTERN.sub(_REDACTION, text)
