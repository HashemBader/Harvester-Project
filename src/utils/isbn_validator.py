"""
isbn_validator.py

ISBN normalisation, validation, and comparison utilities.

Design
------
This module uses ``python-stdnum`` when available, because it provides
rigorous checksum validation for both ISBN-10 and ISBN-13.  When stdnum is
not installed, a lightweight built-in fallback is used that performs only
length-and-character checks (no checksum).  The ``STDNUM_AVAILABLE`` flag
controls which code path is active throughout the module.

Public API
----------
normalize_isbn(isbn_str)
    Strip non-alphanumeric characters and return a valid ISBN string, or
    ``""`` if the input is invalid.

validate_isbn(isbn_str)
    Return ``True`` if the string represents a structurally valid ISBN.

pick_lowest_isbn(isbns)
    Given an iterable of ISBN strings, return the one that sorts lowest
    numerically (useful for deterministic primary-key selection).

linked_isbns_match(left, right)
    Return ``True`` when two ISBN strings refer to the same book edition
    (compares via their canonical ISBN-13 forms).

compare_linked_isbns
    Backwards-compatibility alias for ``linked_isbns_match``.

Logging
-------
Invalid ISBNs encountered during normalisation or validation are appended to
``invalid_isbns.log`` in the current working directory for later review.

Part of the LCCN Harvester Project.
"""

from datetime import datetime
from pathlib import Path
from typing import Iterable
import re

try:
    from stdnum import isbn as _stdnum_isbn
except ImportError:
    # stdnum not installed — the fallback implementations below will be used.
    STDNUM_AVAILABLE = False
    stdnum_isbn = None
else:
    STDNUM_AVAILABLE = True
    stdnum_isbn = _stdnum_isbn

try:
    from . import messages
except ImportError:
    # Fallback when the module is used outside the package (e.g., standalone scripts).
    class messages:
        class GuiMessages:
            warn_title_invalid = "Invalid ISBN"

# Path to the append-only log file for invalid ISBNs encountered at runtime.
INVALID_ISBN_LOG = Path("invalid_isbns.log")


def strip_isbn_qualifier(isbn_str: str | None) -> str:
    """Return the ISBN portion before MARC-style qualifiers.

    MARC 020 $a values often append binding/volume notes after the ISBN, for
    example ``"0814792987 (cloth : acid-free paper)"``.  Harvard also exposes
    some identifiers with a leading ``"ISBN :"`` label.  Remove those wrappers
    before checksum validation so the valid ISBN itself is not discarded.
    """
    text = str(isbn_str or "").strip()
    if not text:
        return ""

    text = re.sub(r"^ISBN(?:-1[03])?\s*:?\s*", "", text, flags=re.IGNORECASE)

    for match in re.finditer(r"\s+|\(", text):
        start = match.start()
        if text[start] == "(":
            return text[:start].strip()

        remainder = text[match.end() :].lstrip()
        if not remainder or remainder[0] in "(:;[" or remainder[0].isalpha():
            return text[:start].strip()

    return text.strip()


def _isbn_chars_only(isbn_str: str) -> str:
    """Return only ISBN characters, preserving a possible ISBN-10 ``X``."""
    return re.sub(r"[^0-9Xx]", "", isbn_str).upper()


def _cleaned_prefix_shape(candidate: str, length: int) -> bool:
    """Return True when the prefix has characters allowed for that ISBN length."""
    if len(candidate) != length:
        return False
    if length == 13:
        return candidate.isdigit()
    return candidate[:9].isdigit() and (candidate[9].isdigit() or candidate[9] == "X")


def _valid_isbn_prefix(isbn_str: str) -> str:
    """Return the first valid 13- or 10-character ISBN prefix, if present.

    Some source records append qualifiers without a clean delimiter after the
    ISBN.  After removing punctuation such as hyphens, the useful ISBN is the
    first 10 or 13 characters and everything after that is descriptive text.
    """
    cleaned = _isbn_chars_only(strip_isbn_qualifier(isbn_str))

    for length in (13, 10):
        prefix = cleaned[:length]
        if not _cleaned_prefix_shape(prefix, length):
            continue
        if STDNUM_AVAILABLE:
            try:
                return stdnum_isbn.validate(prefix)
            except Exception:
                continue
        return prefix

    return ""


def log_invalid_isbn(isbn_value: str, reason: str = messages.GuiMessages.warn_title_invalid) -> None:
    """
    Append an invalid ISBN entry to the invalid ISBN log file.

    Each entry is a tab-separated line: ``<ISO timestamp>\\t<isbn_value>``.
    The ``reason`` parameter is accepted for API compatibility but is not
    currently written to the log.

    Parameters
    ----------
    isbn_value : str
        The raw ISBN string that failed validation.
    reason : str
        Human-readable reason (unused in the current log format).
    """
    timestamp = datetime.now().isoformat()
    with INVALID_ISBN_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp}\t{isbn_value}\n")


def _simple_normalize_isbn(isbn_str: str) -> str:
    """
    Normalise an ISBN string without using stdnum (fallback implementation).

    Strips all characters that cannot appear in a valid ISBN (keeps digits and
    the ISBN-10 check character ``X``), then verifies the length is 10 or 13.
    No checksum is verified.

    Parameters
    ----------
    isbn_str : str
        Raw ISBN string, possibly containing hyphens or spaces.

    Returns
    -------
    str
        Uppercased digit-only string of length 10 or 13, or ``""`` if the
        cleaned string is not a valid length.
    """
    # Strip everything except digits and the letter X (ISBN-10 check character).
    cleaned = _isbn_chars_only(strip_isbn_qualifier(isbn_str))

    # ISBN-10 is 10 characters; ISBN-13 is 13 characters.
    if len(cleaned) in (10, 13):
        return cleaned.upper()
    for length in (13, 10):
        prefix = cleaned[:length]
        if _cleaned_prefix_shape(prefix, length):
            return prefix
    return ""


def _simple_validate_isbn(isbn_str: str) -> bool:
    """
    Validate an ISBN by length only (fallback, no checksum).

    Returns ``True`` if the cleaned string has 10 or 13 characters.
    """
    cleaned = _simple_normalize_isbn(isbn_str)
    return len(cleaned) in (10, 13)


def _isbn_sort_key(isbn_str: str) -> str:
    """
    Return a lexicographic sort key that orders ISBNs numerically ascending.

    The ISBN-10 check character ``X`` (which represents the value 10) is
    replaced with ``"9"`` so that ``X``-suffixed ISBNs sort *after* those
    ending in ``9`` but before the next numeric block — a pragmatic
    approximation that keeps the sort stable and predictable.

    Parameters
    ----------
    isbn_str : str
        Raw or normalised ISBN string.

    Returns
    -------
    str
        Sort key string.
    """
    normalized = _simple_normalize_isbn(isbn_str).upper()
    if normalized.endswith("X"):
        # Replace trailing X with "9" for numeric sort ordering.
        normalized = normalized[:-1] + "9"
    return normalized or isbn_str.strip().upper()


def pick_lowest_isbn(isbns: Iterable[str]) -> str:
    """
    Return the numerically lowest ISBN from a sequence of ISBN strings.

    "Lowest" is determined by :func:`_isbn_sort_key`, which gives a
    consistent numeric ordering.  This is used to select a deterministic
    primary ISBN when a record carries multiple linked ISBNs.

    Parameters
    ----------
    isbns : Iterable[str]
        One or more ISBN strings (raw or normalised).

    Returns
    -------
    str
        The ISBN that sorts lowest.

    Raises
    ------
    ValueError
        If the iterable is empty or contains only blank strings.
    """
    candidates = [isbn for isbn in isbns if isbn and str(isbn).strip()]
    if not candidates:
        raise ValueError("At least one ISBN is required")
    return min(candidates, key=_isbn_sort_key)


def normalize_isbn(isbn_str: str) -> str:
    """
    Normalise an ISBN string to a canonical digit-only form.

    Uses ``python-stdnum`` when available (full checksum validation), or the
    lightweight fallback otherwise.  Invalid ISBNs are logged and ``""`` is
    returned.

    Parameters
    ----------
    isbn_str : str
        Raw ISBN string (may include hyphens, spaces, qualifying text).

    Returns
    -------
    str
        Normalised ISBN string (digits + optional ``X``), or ``""`` on
        failure.
    """
    candidate = strip_isbn_qualifier(isbn_str)

    if STDNUM_AVAILABLE:
        try:
            normalized_isbn_str = stdnum_isbn.validate(candidate)
            return normalized_isbn_str
        except Exception:
            prefix = _valid_isbn_prefix(candidate)
            if prefix:
                return prefix
            log_invalid_isbn(isbn_str, messages.GuiMessages.warn_title_invalid)
            return ""
    else:
        result = _simple_normalize_isbn(isbn_str)
        if not result:
            log_invalid_isbn(isbn_str, messages.GuiMessages.warn_title_invalid)
        return result


def _simple_isbn13_checksum(first_twelve: str) -> str:
    """
    Compute the ISBN-13 check digit for a 12-digit prefix string.

    The ISBN-13 check digit algorithm alternates weights of 1 and 3 across
    the first 12 digits, sums them, and derives the check digit as
    ``(10 - (sum % 10)) % 10``.

    Parameters
    ----------
    first_twelve : str
        Exactly 12 digit characters (the prefix before the check digit).

    Returns
    -------
    str
        Single digit character ``"0"``–``"9"``.
    """
    total = 0
    for index, char in enumerate(first_twelve):
        digit = int(char)
        # Odd-indexed positions (0-based) are weighted by 3; even by 1.
        total += digit if index % 2 == 0 else digit * 3
    # The final modulo ensures a result of 0 when total is already divisible by 10.
    return str((10 - (total % 10)) % 10)


def _canonical_linked_isbn(isbn_str: str) -> str:
    """
    Return a canonical ISBN-13 string for equality comparison between editions.

    ISBN-10 values are converted to their ISBN-13 equivalents (``978``
    prefix) so that an ISBN-10 and its linked ISBN-13 compare as equal.

    Parameters
    ----------
    isbn_str : str
        Raw or normalised ISBN-10 or ISBN-13 string.

    Returns
    -------
    str
        13-digit ISBN string, or ``""`` if the input is invalid.
    """
    if STDNUM_AVAILABLE:
        try:
            validated = stdnum_isbn.validate(isbn_str)
            return stdnum_isbn.to_isbn13(validated)
        except Exception:
            return ""

    cleaned = _simple_normalize_isbn(isbn_str)
    if not cleaned:
        return ""
    if len(cleaned) == 13:
        return cleaned
    if len(cleaned) == 10:
        # Convert ISBN-10 to ISBN-13: prepend "978" and recompute the check digit.
        # The ISBN-10 check digit (last character) is dropped before prefixing.
        prefix = "978" + cleaned[:-1]
        return prefix + _simple_isbn13_checksum(prefix)
    return ""


def linked_isbns_match(left: str, right: str) -> bool:
    """
    Return ``True`` when two ISBN strings refer to the same linked book.

    Comparison is done via canonical ISBN-13 form, so an ISBN-10 and its
    corresponding ISBN-13 are treated as equal.  Returns ``False`` if either
    value cannot be converted to a valid ISBN-13.

    Parameters
    ----------
    left : str
        First ISBN string.
    right : str
        Second ISBN string.

    Returns
    -------
    bool
    """
    left_canonical = _canonical_linked_isbn(left)
    right_canonical = _canonical_linked_isbn(right)
    return bool(left_canonical) and left_canonical == right_canonical


# Backwards-compatibility alias — prefer linked_isbns_match in new code.
compare_linked_isbns = linked_isbns_match


def validate_isbn(isbn_str: str) -> bool:
    """
    Return ``True`` if ``isbn_str`` is a structurally valid ISBN-10 or ISBN-13.

    Hyphens and spaces are stripped before validation.  Uses stdnum's
    checksum validator when available, otherwise falls back to length-only
    checking.  Invalid ISBNs are logged to :data:`INVALID_ISBN_LOG`.

    Parameters
    ----------
    isbn_str : str
        Raw ISBN string to validate.

    Returns
    -------
    bool
    """
    candidate = strip_isbn_qualifier(isbn_str)

    if STDNUM_AVAILABLE:
        try:
            stdnum_isbn.validate(candidate)
            return True
        except Exception:
            if _valid_isbn_prefix(candidate):
                return True
            log_invalid_isbn(isbn_str, messages.GuiMessages.warn_title_invalid)
            return False
    else:
        result = _simple_validate_isbn(isbn_str)
        if not result:
            log_invalid_isbn(isbn_str, messages.GuiMessages.warn_title_invalid)
        return result
