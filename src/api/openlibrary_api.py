"""
openlibrary_api.py

OpenLibrary Books API client.

Performs ISBN-based lookup using the OpenLibrary Books API and extracts
LC Classification call numbers when present.

API endpoint
------------
``https://openlibrary.org/isbn/{isbn}.json``

If that edition record has no usable classification, the client falls back to
``https://openlibrary.org/api/books`` with the exact ISBN bibkey, because that
endpoint can expose classification metadata for another OpenLibrary edition
record tied to the same ISBN.

The response is a JSON document representing the book edition.  Relevant fields:

- ``lc_classifications`` (list of str) â€” LC Classification call numbers such as
  ``["QA76.73.J38 L43 2003"]``.  This is the primary target field.
- ``classifications.lc_classifications`` â€” alternate nesting shape used by some
  older edition records.
- ``lccn`` / ``identifiers.lccn`` â€” LC *control* numbers (MARC 010), NOT
  LC classification call numbers (MARC 050).  These are intentionally ignored.

A 404 response means the ISBN is genuinely absent from OpenLibrary and is
treated as ``status="not_found"`` rather than a network error.

Notes
-----
- This module does NOT validate ISBN checksums (handled by isbn_validator).
- Call number validation is performed by call_number_validators before storing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import urllib.parse
from typing import Any, Optional

from src.api.base_api import ApiResult, BaseApiClient
from src.api.http_utils import urlopen_with_ca
from src.utils.call_number_validators import validate_lccn, validate_nlmcn
from src.utils.isbn_validator import normalize_isbn



class OpenLibraryApiClient(BaseApiClient):
    """
    OpenLibrary Books API client.

    Fetches edition JSON by ISBN and extracts LC Classification call numbers
    from the ``lc_classifications`` field (or its alternate nesting shape).

    Attributes
    ----------
    source_name : str
        Stable identifier returned by the ``source`` property.
    base_url : str
        Base URL for ISBN edition lookups; the full URL appends
        ``/{isbn}.json``.
    """

    # Stable identifier for this API source
    source_name = "openlibrary"
    # Base URL for OpenLibrary ISBN edition lookups
    base_url = "https://openlibrary.org/isbn"
    books_api_url = "https://openlibrary.org/api/books"

    @property
    def source(self) -> str:
        # Return the source identifier for this API client
        return self.source_name

    def _request_json(self, url: str) -> Any:
        """Fetch a JSON document from OpenLibrary using the standard headers."""
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "LCCNHarvester/0.1 (edu)")

        with urlopen_with_ca(req, timeout=self.timeout_seconds) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            return json.load(resp)

    def _fetch_edition(self, isbn: str) -> Any:
        """Fetch the direct ISBN edition record, returning ``None`` for 404."""
        try:
            return self._request_json(f"{self.base_url}/{isbn}.json")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def _fetch_books_api_data(self, isbn: str) -> Any:
        """Fetch exact-ISBN Books API metadata and return the inner bibkey payload."""
        query = urllib.parse.urlencode(
            {
                "bibkeys": f"ISBN:{isbn}",
                "format": "json",
                "jscmd": "data",
            }
        )
        payload = self._request_json(f"{self.books_api_url}?{query}")
        if not isinstance(payload, dict):
            return None
        return payload.get(f"ISBN:{isbn}") or None

    @staticmethod
    def _has_call_number_candidate(payload: Any) -> bool:
        """Return whether a raw OpenLibrary payload includes classification fields."""
        if not isinstance(payload, dict):
            return False
        if payload.get("lc_classifications") or payload.get("nlm_classifications"):
            return True
        classifications = payload.get("classifications")
        if isinstance(classifications, dict):
            return bool(
                classifications.get("lc_classifications")
                or classifications.get("nlm_classifications")
            )
        return False

    def fetch(self, isbn: str) -> Any:
        """
        Fetch the OpenLibrary edition JSON for an ISBN.

        Parameters
        ----------
        isbn : str
            Normalized ISBN string (no hyphens).

        Returns
        -------
        dict | None
            Parsed JSON payload, or ``None`` when the ISBN is not in
            OpenLibrary (HTTP 404).

        Raises
        ------
        urllib.error.HTTPError
            For non-404 HTTP errors (e.g., 500 server error).
        Exception
            For network-level failures.
        """
        # Fetch edition first, then the exact-ISBN Books API if needed.
        edition_payload = self._fetch_edition(isbn)
        if self._has_call_number_candidate(edition_payload):
            return edition_payload

        books_payload = self._fetch_books_api_data(isbn)
        if books_payload is not None:
            return books_payload

        return edition_payload


    def _extract_isbns(self, payload: Any) -> list[str]:
        """
        Extract and normalize all ISBNs embedded in an OpenLibrary edition payload.

        OpenLibrary stores ISBNs in two possible locations:
        - Top-level keys: ``isbn``, ``isbn_10``, ``isbn_13``
        - Nested under ``identifiers``: ``identifiers.isbn``, etc.

        Parameters
        ----------
        payload : Any
            Parsed OpenLibrary JSON response.

        Returns
        -------
        list[str]
            Deduplicated list of normalized ISBN strings (insertion order
            preserved via ``dict.fromkeys``).
        """
        # Return empty list if payload is not a dictionary
        if not isinstance(payload, dict):
            return []

        # Helper function to convert various value types to lists of strings
        def _collect_values(value: Any) -> list[str]:
            """Coerce a field value to a flat list of stripped strings."""
            if isinstance(value, list):
                # Convert list items to strings
                return [str(item).strip() for item in value if isinstance(item, str)]
            if isinstance(value, str):
                # Single string value
                return [value.strip()]
            # Empty result for other types
            return []

        # Initialize accumulator for ISBNs
        isbns: list[str] = []
        # Check top-level ISBN fields
        for key in ("isbn", "isbn_10", "isbn_13"):
            values = _collect_values(payload.get(key))
            for raw in values:
                # Normalize and store the ISBN
                normalized = normalize_isbn(raw)
                if normalized:
                    isbns.append(normalized)

        # Also check the nested identifiers dict (used by some OL records)
        identifiers = payload.get("identifiers")
        if isinstance(identifiers, dict):
            for key in ("isbn", "isbn_10", "isbn_13"):
                values = _collect_values(identifiers.get(key))
                for raw in values:
                    # Normalize and store the ISBN
                    normalized = normalize_isbn(raw)
                    if normalized:
                        isbns.append(normalized)

        # dict.fromkeys preserves insertion order while deduplicating
        return list(dict.fromkeys(isbns))

    def extract_call_numbers(self, isbn: str, payload: Any) -> ApiResult:
        """
        Extract LC Classification call numbers from an OpenLibrary edition payload.

        Parameters
        ----------
        isbn : str
            Normalized ISBN string used as the search key.
        payload : dict | None
            Parsed JSON returned by :meth:`fetch`.  ``None`` signals a 404
            response (ISBN not in OpenLibrary).

        Returns
        -------
        ApiResult
            - ``status="success"`` with ``lccn`` populated if a valid LC
              Classification call number was found.
            - ``status="not_found"`` if ``payload`` is ``None``, the
              ``lc_classifications`` field is absent/empty, or the extracted
              value fails validation.
        """
        # Handle 404 â€” ISBN not in OpenLibrary
        if payload is None:
            return ApiResult(
                isbn=isbn,
                source=self.source,
                status="not_found",
            )

        # Initialize call number placeholders
        lccn: Optional[str] = None
        nlmcn: Optional[str] = None

        # Primary field: lc_classifications holds actual LC call numbers (MARC 050),
        # e.g. "QA76.73.J38 L43 2003".  Take the first element if the list is non-empty.
        lccs = payload.get("lc_classifications", [])
        if isinstance(lccs, list) and lccs:
            lccn = str(lccs[0]).strip() or None

        nlmcs = payload.get("nlm_classifications", [])
        if isinstance(nlmcs, list) and nlmcs:
            nlmcn = str(nlmcs[0]).strip() or None

        # Alternate nesting shape used by some older OL edition records.
        if not lccn and isinstance(payload.get("classifications"), dict):
            alt = payload["classifications"].get("lc_classifications", [])
            if isinstance(alt, list) and alt:
                lccn = str(alt[0]).strip() or None
        if not nlmcn and isinstance(payload.get("classifications"), dict):
            alt = payload["classifications"].get("nlm_classifications", [])
            if isinstance(alt, list) and alt:
                nlmcn = str(alt[0]).strip() or None

        # Note: OpenLibrary's top-level "lccn" field and identifiers.lccn are
        # LC control numbers (MARC 010, e.g. "2001016794"), NOT LC classification
        # call numbers (MARC 050).  We do not fall back to those.

        # Validate extracted call numbers against format rules before storing.
        lccn = validate_lccn(lccn, source=self.source)
        nlmcn = validate_nlmcn(nlmcn, source=self.source)

        # Extract related ISBNs from the edition
        isbns = self._extract_isbns(payload)

        # Return success if at least one valid call number was found
        if lccn or nlmcn:
            return ApiResult(
                isbn=isbn,
                source=self.source,
                status="success",
                lccn=lccn,
                nlmcn=nlmcn,
                raw=payload,
                isbns=isbns,
            )

        # No usable call number found â€” treat as not_found for harvester purposes.
        return ApiResult(
            isbn=isbn,
            source=self.source,
            status="not_found",
            isbns=isbns,
        )
