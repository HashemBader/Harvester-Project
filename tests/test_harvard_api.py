from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.harvard_api import HarvardApiClient


def test_harvard_extracts_lccn_from_items_mods_identifier() -> None:
    """identifier[@type='lccn'] is an LC control number (MARC 010), not a call
    number (MARC 050).  The Harvard client must not return it as a call number."""
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": 1},
        "items": {
            "mods": [
                {
                    "identifier": [
                        {"@type": "isbn", "#text": "9780451524935"},
                        {"@type": "lccn", "#text": "2017056545"},
                    ]
                }
            ]
        },
    }

    result = client.extract_call_numbers("9780451524935", payload)
    # A bare LC control number ("2017056545") is not an LC classification call
    # number, so the result should be not_found rather than a bogus lccn.
    assert result.status == "not_found"
    assert result.lccn is None


def test_harvard_extracts_classification_with_authority_lcc() -> None:
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": "1"},
        "items": {
            "mods": [
                {
                    "classification": [
                        {"@authority": "lcc", "#text": "PS3562.E353 T6 2002"}
                    ]
                }
            ]
        },
    }

    result = client.extract_call_numbers("0060935464", payload)
    assert result.status == "success"
    assert result.lccn == "PS3562.E353 T6 2002"


def test_harvard_items_mods_shape_detected_as_records() -> None:
    client = HarvardApiClient()
    payload = {"pagination": {"numFound": 1}, "items": {"mods": [{}]}}
    assert client._has_records(payload) is True


def test_harvard_build_fallback_uses_keyword_query() -> None:
    client = HarvardApiClient()
    url = client.build_fallback_url("9780451524935")
    assert "q=9780451524935" in url
    assert "identifier%3A" not in url


# ---------------------------------------------------------------------------
# NLM classification path
# ---------------------------------------------------------------------------


def test_harvard_extracts_nlm_classification() -> None:
    """classification[@authority='nlm'] must produce nlmcn, not lccn."""
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": 1},
        "items": {
            "mods": [
                {"classification": [{"@authority": "nlm", "#text": "WG 120.5"}]}
            ]
        },
    }
    result = client.extract_call_numbers("0000000000", payload)
    assert result.status == "success"
    assert result.nlmcn == "WG 120.5"
    assert result.lccn is None


def test_harvard_extracts_both_lc_and_nlm_classifications() -> None:
    """When both lcc and nlm classification fields are present, both are returned."""
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": 1},
        "items": {
            "mods": [
                {
                    "classification": [
                        {"@authority": "lcc", "#text": "PS3562.E353 T6 2002"},
                        {"@authority": "nlm", "#text": "WG 120.5"},
                    ]
                }
            ]
        },
    }
    result = client.extract_call_numbers("0060935464", payload)
    assert result.status == "success"
    assert result.lccn == "PS3562.E353 T6 2002"
    assert result.nlmcn == "WG 120.5"


# ---------------------------------------------------------------------------
# shelfLocator path
# ---------------------------------------------------------------------------


def test_harvard_shelf_locator_classified_as_lc() -> None:
    """A shelfLocator containing a value that looks like an LC call number is
    bucketed into the LC candidates list and returned as lccn."""
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": 1},
        "items": {
            "mods": [
                {"location": [{"shelfLocator": "PS3562.E353 T6 2002"}]}
            ]
        },
    }
    result = client.extract_call_numbers("0060935464", payload)
    assert result.status == "success"
    assert result.lccn == "PS3562.E353 T6 2002"


# ---------------------------------------------------------------------------
# lccn-named JSON keys are LC control numbers — must be ignored
# ---------------------------------------------------------------------------


def test_harvard_lccn_json_keys_ignored() -> None:
    """Fields named 'lccn' or 'number_lccn' in the MODS JSON carry LC control
    numbers (MARC 010), not call numbers.  They must not be returned as lccn."""
    client = HarvardApiClient()
    payload = {
        "pagination": {"numFound": 1},
        "items": {
            "mods": [
                {"lccn": "2007039987", "number_lccn": "2007039987"}
            ]
        },
    }
    result = client.extract_call_numbers("0000000000", payload)
    assert result.status == "not_found"
    assert result.lccn is None


# ---------------------------------------------------------------------------
# _has_records edge cases
# ---------------------------------------------------------------------------


def test_harvard_has_records_zero_num_found() -> None:
    client = HarvardApiClient()
    payload = {"pagination": {"numFound": 0}, "items": {"mods": []}}
    assert client._has_records(payload) is False


def test_harvard_has_records_list_shape() -> None:
    """Some Harvard responses use items as a plain list instead of a dict."""
    client = HarvardApiClient()
    payload = {"items": [{"id": "abc"}]}
    assert client._has_records(payload) is True


# ---------------------------------------------------------------------------
# None / empty payload
# ---------------------------------------------------------------------------


def test_harvard_none_payload_returns_not_found() -> None:
    client = HarvardApiClient()
    result = client.extract_call_numbers("0000000000", None)
    assert result.status == "not_found"
    assert result.lccn is None
    assert result.nlmcn is None


def test_harvard_empty_payload_returns_not_found() -> None:
    client = HarvardApiClient()
    result = client.extract_call_numbers("0000000000", {})
    assert result.status == "not_found"
