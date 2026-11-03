import pytest

from practo_agent.guardrails import mask_contact_numbers


def test_masks_ten_digit_indian_mobile_and_preserves_surrounding_text():
    query = "Please call 9876543210 about my appointment."

    masked = mask_contact_numbers(query)

    assert masked == (
        "Please call [REDACTED_CONTACT_NUMBER] about my appointment."
    )


@pytest.mark.parametrize(
    "number",
    [
        "9876543210",
        "+91 98765 43210",
        "+91-98765-43210",
        "09876543210",
        "9 8 7 6 5 4 3 2 1 0",
    ],
)
def test_masks_supported_indian_mobile_formats(number):
    assert mask_contact_numbers(number) == "[REDACTED_CONTACT_NUMBER]"


def test_masks_multiple_contact_numbers():
    query = "Call 9876543210 or +91-87654-32109."

    masked = mask_contact_numbers(query)

    assert masked.count("[REDACTED_CONTACT_NUMBER]") == 2
    assert "9876543210" not in masked
    assert "87654-32109" not in masked


@pytest.mark.parametrize(
    "number",
    [
        "1234567890",
        "5123456789",
        "987654321",
        "98765432101",
        "APT-0001",
        "call9876543210now",
    ],
)
def test_does_not_mask_nonmatching_values(number):
    assert mask_contact_numbers(number) == number


def test_does_not_claim_to_detect_free_text_personal_information():
    query = "Contact Ruchir at 12 Elm Street about the insurance record."

    assert mask_contact_numbers(query) == query


def test_requires_string_input():
    with pytest.raises(TypeError, match="text must be a string"):
        mask_contact_numbers(None)
