"""
nlmcn_validator.py

Validates National Library of Medicine (NLM) Classification call numbers
against the MARC 060 field format.

The NLM Classification uses the QS-QZ and W-WZ schedules. Call numbers may
store the class letters and class number in the same token, as in "W3", or in
separate tokens, as in "WG 120". MARC 060 item/Cutter parts are stored in $b
and, unlike LC practice, do not need a leading period.

Examples of valid NLM call numbers:
    W3 I324 1974i
    WG 120
    WG 120.5
    WG 120.5 .A1
    QV 55 .B45 2001
    QZ 200

Part of the LCCN Harvester Project.
"""

from __future__ import annotations

import re

# Set of valid NLM classification classes according to the NLM schedule.
# Any call number starting with letters not in this set is considered invalid.
VALID_NLM_CLASSES = {
    "QS", "QT", "QU", "QV", "QW", "QX", "QY", "QZ",
    "W", "WA", "WB", "WC", "WD", "WE", "WF", "WG", "WH", "WI",
    "WJ", "WK", "WL", "WM", "WN", "WO", "WP", "WQ", "WR", "WS",
    "WT", "WU", "WV", "WW", "WX", "WY", "WZ",
}


def is_valid_nlmcn(call_number: str) -> bool:
    """Return ``True`` if ``call_number`` is a structurally valid NLM call number."""
    if not call_number:
        return False

    # Split the call number into whitespace-separated tokens.
    parts = call_number.strip().split()
    if not parts:
        return False

    # Attempt to parse the primary classification letter/number combination.
    parsed_class = _parse_nlm_class(parts)
    if parsed_class is None:
        return False

    class_letters, class_number_part, first_supplement_index = parsed_class
    
    # Check 1: The leading letters must be defined in the NLM schedule.
    if class_letters.upper() not in VALID_NLM_CLASSES:
        return False

    # Check 2: The numeric part of the classification must follow NLM formatting rules.
    if not _is_valid_nlm_class_number(class_number_part):
        return False

    # Check 3: All subsequent tokens (Cutter numbers, dates, issue info) must be valid.
    return all(
        _is_valid_nlm_supplementary_token(part)
        for part in parts[first_supplement_index:]
    )


def _parse_nlm_class(parts: list[str]) -> tuple[str, str, int] | None:
    """Return ``(class_letters, class_number, first_supplement_index)``."""
    # Ensure the first token has content.
    first = parts[0].strip()
    if not first:
        return None

    # Handle "inline" format: letters and numbers in one token, e.g. "W3" or "WG120".
    inline_match = re.fullmatch(r"([A-Za-z]+)(\d.*)", first)
    if inline_match:
        return inline_match.group(1), inline_match.group(2), 1

    # Handle "spaced" format: letters and numbers in separate tokens, e.g. "WG 120".
    # This requires at least two tokens to be present.
    if first.isalpha() and len(parts) >= 2:
        return first, parts[1], 2

    return None


def _is_valid_nlm_class_number(value: str) -> bool:
    """Return ``True`` for the numeric part of the NLM classification."""
    # NLM class numbers must start with a digit.
    if not value or not value[0].isdigit():
        return False

    i = 0
    digit_count = 0
    # Walk the first segment and count digits; standard NLM class numbers usually have 1-3 digits.
    while i < len(value) and value[i].isdigit() and digit_count < 3:
        digit_count += 1
        i += 1

    if digit_count == 0:
        return False

    # Parts after the digits (e.g., decimal extensions like ".5") are validated as a "remainder".
    remainder = value[i:]
    if remainder and not _is_valid_nlmcn_remainder(remainder):
        return False

    return True


def _is_valid_nlm_supplementary_token(part: str) -> bool:
    """Validate Cutter/workmark/date tokens after the NLM classification number."""
    if not part:
        return False

    # MARC 060 $b parts are not necessarily period-prefixed.
    # This regex matches standard Cutters like "B45" or ".A1".
    if re.fullmatch(r"\.?[A-Za-z][A-Za-z0-9]*", part):
        return True

    # Dates: exactly 4 digits, potentially followed by a single lowercase workmark letter (e.g., "1974i").
    if re.fullmatch(r"\d{4}[A-Za-z]?", part):
        return True

    # Short numeric tokens: used for volumes, issues, or supplements.
    if re.fullmatch(r"\d{1,3}", part):
        return True

    return False


def _is_valid_nlmcn_remainder(remainder: str) -> bool:
    """Validate the inline decimal extension of an NLM class number token."""
    if not remainder:
        return True

    # If there is a remainder, it must start with a decimal point.
    if not remainder.startswith("."):
        return False

    # Split by periods to handle multi-level extensions.
    segments = remainder.split(".")
    # Each segment after the first decimal must be alphanumeric.
    for segment in segments[1:]:
        if not segment:
            continue
        if not segment.isalnum():
            return False

    return True
