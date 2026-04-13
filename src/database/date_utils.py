"""
Date and formatting helpers shared by the database layer.

The database stores all date values as ``YYYYMMDD`` integers (e.g. 20240315)
for easy sorting and range queries without relying on SQLite's text-based
date functions.  This module provides the conversion utilities needed to move
between that integer format, ISO-8601 strings, and Python ``datetime`` objects.

Public API:
    now_datetime_str()           -- current local time as ``"YYYY-MM-DD HH:MM:SS"``
    today_yyyymmdd()             -- today as an integer ``YYYYMMDD``
    normalize_to_datetime_str()  -- any supported date value → ISO datetime string
    normalize_to_yyyymmdd_int()  -- any supported date value → ``YYYYMMDD`` integer
    yyyymmdd_to_iso_date()       -- any supported date value → ``"YYYY-MM-DD"``
    classification_from_call_number() -- extract leading class letters from a call number
    classification_from_lccn()        -- backward-compatible alias for LC call numbers
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def now_datetime_str() -> str:
    """Return current local datetime as an ISO-8601 string.
    
    Returns the current local time in the canonical database storage format,
    without microseconds. Used to timestamp database records.
    
    Returns:
        A string like ``"2024-03-15 14:30:45"`` representing now in local time.
    """
    # Get current local time, strip microseconds for cleaner storage, format as ISO string
    return datetime.now().replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def today_yyyymmdd() -> int:
    """Return today's local date as an integer in ``YYYYMMDD`` format.
    
    Used to populate date fields in the database when no explicit date is given.
    The compact integer format enables efficient range queries and sorting.
    
    Returns:
        Today's date as an 8-digit integer like ``20240315``.
    """
    # Format today's date as YYYYMMDD string and convert to integer
    return int(datetime.now().strftime("%Y%m%d"))


def normalize_to_datetime_str(value: Optional[int | str]) -> Optional[str]:
    """Convert supported date values to an ISO-8601 datetime string.

    Accepted input formats:
      - ``None`` or ``""`` → returns ``None``
      - ``"YYYY-MM-DD HH:MM:SS"`` (already normalised) → returned as-is
      - ``"YYYYMMDD"`` digit string → ``"YYYY-MM-DD 00:00:00"``
      - Any ISO-8601 string (with optional ``Z`` suffix) → converted to local time
      - Integer ``YYYYMMDD`` (8 digits) → ``"YYYY-MM-DD 00:00:00"``
      - Anything else → coerced via ``str()``
      
    This function enables flexible date input while ensuring all database storage
    uses a canonical format for consistent queries and ordering.

    Returns:
        An ISO datetime string ``"YYYY-MM-DD HH:MM:SS"`` or ``None``.
    """
    # Handle None and empty strings: return None
    if value in (None, ""):
        return None
    if isinstance(value, str):
        text = value.strip()
        # Empty string after stripping: return None
        if not text:
            return None
        # Fast-path: already in the canonical storage format "YYYY-MM-DD HH:MM:SS"
        if len(text) == 19 and text[4] == "-" and text[10] == " " and text[13] == ":":
            return text
        # Compact date-only format used in the DB (e.g. "20240315")
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:8]} 00:00:00"

        try:
            # Handle ISO-8601 variants including UTC "Z" suffix
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            # Convert to local timezone and format
            return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            # If parsing fails, return the text as-is (fallback)
            return text

    if isinstance(value, int):
        # Check if this is an 8-digit YYYYMMDD integer
        digits = str(value)
        if len(digits) == 8:
            return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]} 00:00:00"

    # Fallback: convert to string
    return str(value)


def yyyymmdd_to_iso_date(value: Optional[int | str]) -> Optional[str]:
    """Convert supported date values into a ``YYYY-MM-DD`` date-only string.

    Delegates to ``normalize_to_datetime_str`` and strips the time component,
    leaving just the date portion. Useful for UI display where time is not needed.

    Args:
        value: Any date value supported by ``normalize_to_datetime_str`` (int,
               string in various formats, None, etc.).

    Returns:
        A ``"YYYY-MM-DD"`` string, or ``None`` if *value* is empty/None.
    """
    # Use the main conversion function to handle all date formats
    normalized = normalize_to_datetime_str(value)
    # If no value was converted, return None
    if not normalized:
        return normalized
    # Extract just the date portion (first 10 characters: "YYYY-MM-DD")
    return normalized[:10]


def normalize_to_yyyymmdd_int(value: Optional[int | str]) -> int:
    """Convert supported date values into a ``YYYYMMDD`` integer.

    Falls back to today's date when *value* cannot be parsed, so every row in
    the database always has a valid date. This ensures the database never
    contains NULL or invalid date values which would break sorting and queries.

    Args:
        value: A date value in any format accepted by
               ``normalize_to_datetime_str``, or an integer already in
               ``YYYYMMDD`` form.

    Returns:
        An 8-digit integer like ``20240315``.
    """
    # Fast-path: if already an 8-digit YYYYMMDD integer, return it
    if isinstance(value, int):
        digits = str(value)
        if len(digits) == 8:
            # Already in YYYYMMDD form; skip further parsing
            return value

    # Convert to normalized datetime string first, then extract the date portion
    normalized = normalize_to_datetime_str(value)
    if normalized:
        # Extract date portion (first 10 chars "YYYY-MM-DD") and remove dashes
        digits = normalized[:10].replace("-", "")
        # Validate it's an 8-digit number
        if len(digits) == 8 and digits.isdigit():
            return int(digits)

    # Fallback: if parsing failed, use today's date rather than NULL
    # This ensures every database row has a valid date for sorting and filtering
    # Unrecognised format — use today so we don't store a NULL-equivalent zero
    return today_yyyymmdd()


def classification_from_call_number(call_number: Optional[str]) -> Optional[str]:
    """Best-effort derivation of leading classification letters from a call number.

    Reads the leading alphabetic prefix of a Library of Congress or National
    Library of Medicine call number (up to 3 letters), such as ``"QA"`` for
    mathematics or ``"WR"`` for an NLM dermatology schedule.
    
    The extracted classification is stored separately in the ``main`` table so
    results can be filtered or faceted by subject (e.g., all call numbers in
    the ``"QA"`` mathematics category).

    Args:
        call_number: A raw call number string such as ``"QA76.73.P98"`` or
            ``"WR 140 D435172 2001"``.

    Returns:
        The uppercase leading letter(s) like ``"QA"`` or ``"WR"``, or ``None``
        if *call_number* is empty or starts with a non-alphabetic character.
    """
    # Return None for empty or missing values
    if not call_number:
        return None
    # Collect leading alphabetic characters
    letters: list[str] = []
    for char in call_number.strip():
        if char.isalpha():
            # Append uppercase letter and count them
            letters.append(char.upper())
            # Stop after 3 letters (max LoC classification length)
            if len(letters) == 3:  # LoC classes are at most 3 letters (e.g. "KFX")
                break
        else:
            # First non-letter marks the end of the classification prefix
            break  # First non-letter marks the end of the classification prefix
    # Return the collected letters as a string, or None if no letters found
    return "".join(letters) if letters else None


def classification_from_lccn(lccn: Optional[str]) -> Optional[str]:
    """Backward-compatible wrapper for LC call-number classification extraction."""
    return classification_from_call_number(lccn)
