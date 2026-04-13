"""
call_number_validators.py

Centralised entry point for validating LC and NLM call numbers before they
are stored in the database or returned as harvest results.

This module provides two styles of API:
- ``validate_call_numbers`` — validates an (lccn, nlmcn) pair together and
  returns a cleaned tuple; convenient for callers that hold both at once.
- ``validate_lccn`` / ``validate_nlmcn`` — validate a single call number;
  used by individual API clients after extraction.

All validation logic is delegated to the specialised validator modules:
- :mod:`src.utils.lccn_validator` — LC Classification (MARC 050) rules.
- :mod:`src.utils.nlmcn_validator` — NLM Classification (MARC 060) rules.

The ``source`` parameter accepted by every function is intentionally unused;
it is kept for API compatibility with older call sites that passed a source
label for logging.

Part of the LCCN Harvester Project.
"""

from typing import Optional, Tuple

# Import the specific validation functions for each classification system.
from src.utils.lccn_validator import is_valid_lccn
from src.utils.nlmcn_validator import is_valid_nlmcn


def validate_call_numbers(
    lccn: Optional[str] = None,
    nlmcn: Optional[str] = None,
    source: Optional[str] = None,
    strict: bool = False,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and clean LCCN and NLMCN call numbers.

    Parameters
    ----------
    lccn : str | None
        Library of Congress call number candidate.
    nlmcn : str | None
        National Library of Medicine call number candidate.
    source : str | None
        Source API name (unused, kept for compatibility).
    strict : bool
        If True, reject invalid formats. If False, return as-is for logging purposes.

    Returns
    -------
    tuple[str | None, str | None]
        Validated (lccn, nlmcn) pair. Invalid ones become None.
    """
    # Initialize result variables as None to signify "no valid data".
    validated_lccn = None
    validated_nlmcn = None

    # Handle LCCN validation if a candidate string was provided.
    if lccn:
        # Normalize by removing leading/trailing whitespace.
        lccn = lccn.strip()
        # Delegate to the specialized LCCN regex-based validator.
        if is_valid_lccn(lccn):
            validated_lccn = lccn

    # Handle NLMCN validation if a candidate string was provided.
    if nlmcn:
        # Normalize by removing leading/trailing whitespace.
        nlmcn = nlmcn.strip()
        # Delegate to the specialized NLMCN regex-based validator.
        if is_valid_nlmcn(nlmcn):
            validated_nlmcn = nlmcn

    # Return the clean pair. Callers can reliably use these without further checks.
    return validated_lccn, validated_nlmcn


def validate_lccn(call_number: Optional[str], source: Optional[str] = None) -> Optional[str]:
    """
    Validate a single LCCN.

    Parameters
    ----------
    call_number : str | None
        Call number to validate.
    source : str | None
        Source API name (unused, kept for compatibility).

    Returns
    -------
    str | None
        The call number if valid, None otherwise.
    """
    # Quick exit for null or empty input.
    if not call_number:
        return None

    # Common normalization step.
    call_number = call_number.strip()
    
    # Return the string only if it passes the classification-specific validation rules.
    if is_valid_lccn(call_number):
        return call_number

    # Explicitly return None if validation fails.
    return None


def validate_nlmcn(call_number: Optional[str], source: Optional[str] = None) -> Optional[str]:
    """
    Validate a single NLMCN.

    Parameters
    ----------
    call_number : str | None
        Call number to validate.
    source : str | None
        Source API name (unused, kept for compatibility).

    Returns
    -------
    str | None
        The call number if valid, None otherwise.
    """
    # Quick exit for null or empty input.
    if not call_number:
        return None

    # Common normalization step.
    call_number = call_number.strip()
    
    # Return the string only if it passes the classification-specific validation rules.
    if is_valid_nlmcn(call_number):
        return call_number

    # Explicitly return None if validation fails.
    return None
