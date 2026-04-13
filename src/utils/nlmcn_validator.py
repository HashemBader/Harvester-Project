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

    parts = call_number.strip().split()
    if not parts:
        return False

    parsed_class = _parse_nlm_class(parts)
    if parsed_class is None:
        return False

    class_letters, class_number_part, first_supplement_index = parsed_class
    if class_letters.upper() not in VALID_NLM_CLASSES:
        return False

    if not _is_valid_nlm_class_number(class_number_part):
        return False

    return all(
        _is_valid_nlm_supplementary_token(part)
        for part in parts[first_supplement_index:]
    )


def _parse_nlm_class(parts: list[str]) -> tuple[str, str, int] | None:
    """Return ``(class_letters, class_number, first_supplement_index)``."""
    first = parts[0].strip()
    if not first:
        return None

    inline_match = re.fullmatch(r"([A-Za-z]+)(\d.*)", first)
    if inline_match:
        return inline_match.group(1), inline_match.group(2), 1

    if first.isalpha() and len(parts) >= 2:
        return first, parts[1], 2

    return None


def _is_valid_nlm_class_number(value: str) -> bool:
    """Return ``True`` for the numeric part of the NLM classification."""
    if not value or not value[0].isdigit():
        return False

    i = 0
    digit_count = 0
    while i < len(value) and value[i].isdigit() and digit_count < 3:
        digit_count += 1
        i += 1

    if digit_count == 0:
        return False

    remainder = value[i:]
    if remainder and not _is_valid_nlmcn_remainder(remainder):
        return False

    return True


def _is_valid_nlm_supplementary_token(part: str) -> bool:
    """Validate Cutter/workmark/date tokens after the NLM classification number."""
    if not part:
        return False

    # MARC 060 $b parts are not necessarily period-prefixed.
    if re.fullmatch(r"\.?[A-Za-z][A-Za-z0-9]*", part):
        return True

    # Dates sometimes include a trailing workmark letter, e.g. "1974i".
    if re.fullmatch(r"\d{4}[A-Za-z]?", part):
        return True

    # Keep short numeric volume/issue/supplement tokens.
    if re.fullmatch(r"\d{1,3}", part):
        return True

    return False


def _is_valid_nlmcn_remainder(remainder: str) -> bool:
    """Validate the inline decimal extension of an NLM class number token."""
    if not remainder:
        return True

    if not remainder.startswith("."):
        return False

    segments = remainder.split(".")
    for segment in segments[1:]:
        if not segment:
            continue
        if not segment.isalnum():
            return False

    return True
