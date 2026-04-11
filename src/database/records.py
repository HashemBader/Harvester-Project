"""
Typed record structures shared across the database and harvester layers.

This module defines the data-transfer objects (DTOs) that flow between the
harvester, the database manager, and the GUI.  Keeping them in a dedicated
module avoids circular imports because both ``db_manager`` and the harvester
orchestrator depend on these types.

Classes:
    MainRecord      -- A successful harvest result (ISBN + call number(s)).
    AttemptedRecord -- A failed/pending lookup with retry metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MainRecord:
    """Combined call-number record exposed to the UI and harvester layers.

    Represents a successful harvest for a single ISBN.  One record can carry
    both an LC call number (``lccn``) and an NLM call number (``nlmcn``) when
    multiple sources were queried.

    Note: The database stores one row per ``(isbn, call_number_type, source)``
    triple; ``DatabaseManager._aggregate_main_rows`` collapses those rows into
    this combined view. This frozen dataclass is immutable and hashable,
    making it safe to use in sets or as dict keys.

    Attributes:
        isbn:            The 10- or 13-digit ISBN (stored as a string).
        lccn:            Library of Congress call number, if found (e.g., "QA76.73").
        lccn_source:     Which harvesting target provided the LCCN (e.g., "LoC").
        nlmcn:           National Library of Medicine call number, if found.
        nlmcn_source:    Which harvesting target provided the NLM CN (e.g., "Harvard").
        classification:  Leading LoC subject letters derived from ``lccn`` (e.g., "QA").
        source:          Comma/plus-separated string of all contributing sources.
        date_added:      Harvest date as an ISO date string or ``YYYYMMDD`` integer.
    """

    # The ISBN being cataloged (required field)
    isbn: str
    # Library of Congress call number, if any of the sources found one
    lccn: Optional[str] = None
    # Which source provided the LCCN (e.g., "LoC", "Harvard")
    lccn_source: Optional[str] = None
    # National Library of Medicine call number, if any source found one
    nlmcn: Optional[str] = None
    # Which source provided the NLMCN
    nlmcn_source: Optional[str] = None
    # Subject classification extracted from the LCCN (e.g., "QA" for math)
    classification: Optional[str] = None
    # Aggregated list of all sources that contributed data (e.g., "LoC + Harvard")
    source: Optional[str] = None
    # When the harvest was performed (flexible format for UI presentation)
    date_added: Optional[int | str] = None


@dataclass(frozen=True)
class AttemptedRecord:
    """Retry-tracking row for a single ISBN/target/call-number-type key.

    Mirrors the ``attempted`` database table and is used throughout the
    harvester to decide whether to skip or retry a lookup. Stores failure
    metadata so the harvester can implement exponential backoff and avoid
    repeatedly querying unresponsive targets. This frozen dataclass is
    immutable and hashable, making it safe for caching or set operations.

    Attributes:
        isbn:           The ISBN that was attempted (required).
        last_target:    Identifier of the last lookup target tried (e.g., "LoC").
        attempt_type:   ``'lccn'``, ``'nlmcn'``, or ``'both'`` (controls which
                        call-number types were attempted).
        last_attempted: Date of most recent attempt as ``YYYYMMDD`` integer or ISO string.
        fail_count:     Running total of consecutive failures for this key.
        last_error:     Human-readable message from the most recent failure.
    """

    # The ISBN that was attempted (required field)
    isbn: str
    # The target that was queried (e.g., "LoC", "Harvard", "OpenLibrary")
    last_target: Optional[str] = None
    # Which call-number types were requested (lccn, nlmcn, or both)
    attempt_type: str = "both"
    # When the last attempt was made (YYYYMMDD int or ISO string for compatibility)
    last_attempted: Optional[int | str] = None
    # How many consecutive failures have occurred for this ISBN/target/type
    fail_count: int = 1
    # Error message from the most recent failure (e.g., "Timeout", "Invalid ISBN")
    last_error: Optional[str] = None
