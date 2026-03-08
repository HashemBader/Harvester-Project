"""
Tests for src/z3950/marc_decoder.py

Covers:
- pymarc >= 5.x Subfield namedtuple path in _extract_subfields_from_pymarc_field
- Legacy flat-list path in _extract_subfields_from_pymarc_field
- pymarc_record_to_json: single field, both fields, ind2 preference, no fields
- extract_call_numbers_from_pymarc: end-to-end pipeline with real pymarc Records
"""

from unittest.mock import MagicMock

import pytest
from pymarc import Field, Record, Subfield

from src.z3950.marc_decoder import (
    _extract_subfields_from_pymarc_field,
    extract_call_numbers_from_pymarc,
    pymarc_record_to_json,
)


def _field(tag: str, ind2: str, *pairs: tuple) -> Field:
    """Helper: build a pymarc 5.x Field from (code, value) pairs."""
    return Field(
        tag=tag,
        indicators=[" ", ind2],
        subfields=[Subfield(code, val) for code, val in pairs],
    )


# ---------------------------------------------------------------------------
# _extract_subfields_from_pymarc_field
# ---------------------------------------------------------------------------


def test_extract_subfields_namedtuple_pymarc5():
    """pymarc >= 5.x stores subfields as Subfield(code, value) namedtuples."""
    f = _field("050", "0", ("a", "QA76.73"), ("b", "P38"))
    result = _extract_subfields_from_pymarc_field(f)
    assert result == [{"a": "QA76.73"}, {"b": "P38"}]


def test_extract_subfields_legacy_flat_list():
    """pymarc >= 5.1 removed the old flat [code, val, ...] list format entirely;
    Field.__init__ now raises ValueError when strings are passed.  The legacy
    branch in marc_decoder was dead code and has been removed.  This test
    documents that a mock object with a plain list of strings is handled
    gracefully (AttributeError on sf.code is caught) rather than crashing."""
    mock_field = MagicMock()
    # Plain strings don't have .code / .value attributes — the loop will hit
    # AttributeError on the first iteration, which is caught by the try/except.
    mock_field.subfields = ["a", "QA76.73", "b", "P38"]
    result = _extract_subfields_from_pymarc_field(mock_field)
    # No crash; returns empty list because strings have no .code attribute.
    assert result == []


def test_extract_subfields_strips_whitespace():
    """Values with surrounding whitespace are stripped."""
    f = _field("050", "0", ("a", "  QA76.73  "), ("b", " P38 "))
    result = _extract_subfields_from_pymarc_field(f)
    assert result == [{"a": "QA76.73"}, {"b": "P38"}]


# ---------------------------------------------------------------------------
# pymarc_record_to_json
# ---------------------------------------------------------------------------


def test_pymarc_record_to_json_single_050():
    r = Record()
    r.add_field(_field("050", "0", ("a", "QA76.73"), ("b", "P38")))
    result = pymarc_record_to_json(r)
    f050 = [f["050"] for f in result["fields"] if "050" in f]
    assert len(f050) == 1
    assert f050[0]["subfields"] == [{"a": "QA76.73"}, {"b": "P38"}]
    assert f050[0]["ind2"] == "0"


def test_pymarc_record_to_json_single_060():
    r = Record()
    r.add_field(_field("060", " ", ("a", "WG 120.5")))
    result = pymarc_record_to_json(r)
    f060 = [f["060"] for f in result["fields"] if "060" in f]
    assert len(f060) == 1
    assert f060[0]["subfields"] == [{"a": "WG 120.5"}]


def test_pymarc_record_to_json_both_050_and_060():
    r = Record()
    r.add_field(_field("050", "0", ("a", "QA76.73"), ("b", "P38")))
    r.add_field(_field("060", " ", ("a", "WG 120.5")))
    result = pymarc_record_to_json(r)
    tags = [list(f.keys())[0] for f in result["fields"]]
    assert "050" in tags
    assert "060" in tags
    assert len(result["fields"]) == 2


def test_pymarc_record_to_json_prefers_ind2_0_over_ind2_4():
    """Multiple 050 fields: ind2='0' (LC-assigned) must be chosen over ind2='4' (institution)."""
    r = Record()
    r.add_field(_field("050", "4", ("a", "PZ7.C6837"), ("b", "BadCopy 1999")))
    r.add_field(_field("050", "0", ("a", "PZ7.C6837"), ("b", "LCCopy 2008")))
    result = pymarc_record_to_json(r)
    f050 = [f["050"] for f in result["fields"] if "050" in f]
    assert len(f050) == 1
    b_vals = [sf["b"] for sf in f050[0]["subfields"] if "b" in sf]
    assert b_vals[0] == "LCCopy 2008"


def test_pymarc_record_to_json_falls_back_to_first_when_no_ind2_0():
    """When no ind2='0' exists at all, use the first 050 occurrence."""
    r = Record()
    r.add_field(_field("050", "4", ("a", "PZ7.C6837"), ("b", "First 1999")))
    r.add_field(_field("050", "4", ("a", "PZ7.C6837"), ("b", "Second 2008")))
    result = pymarc_record_to_json(r)
    f050 = [f["050"] for f in result["fields"] if "050" in f]
    assert len(f050) == 1
    b_vals = [sf["b"] for sf in f050[0]["subfields"] if "b" in sf]
    assert b_vals[0] == "First 1999"


def test_pymarc_record_to_json_no_050_060():
    """A record with no 050 or 060 fields returns an empty fields list."""
    r = Record()
    r.add_field(_field("020", " ", ("a", "0451524934")))  # ISBN only
    result = pymarc_record_to_json(r)
    assert result == {"fields": []}


def test_pymarc_record_to_json_invalid_object():
    """An object that lacks get_fields returns an empty fields dict gracefully."""
    result = pymarc_record_to_json("not_a_record")
    assert result == {"fields": []}


# ---------------------------------------------------------------------------
# extract_call_numbers_from_pymarc  (end-to-end pipeline)
# ---------------------------------------------------------------------------


def test_extract_call_numbers_lccn_and_nlmcn():
    r = Record()
    r.add_field(_field("050", "0", ("a", "QA76.73"), ("b", "P38")))
    r.add_field(_field("060", " ", ("a", "WG 120.5")))
    lccn, nlmcn = extract_call_numbers_from_pymarc(r)
    assert lccn == "QA76.73 P38"
    assert nlmcn == "WG 120.5"


def test_extract_call_numbers_lccn_only():
    r = Record()
    r.add_field(_field("050", "0", ("a", "QA76.73"), ("b", "P38")))
    lccn, nlmcn = extract_call_numbers_from_pymarc(r)
    assert lccn == "QA76.73 P38"
    assert nlmcn is None


def test_extract_call_numbers_nlmcn_only():
    r = Record()
    r.add_field(_field("060", " ", ("a", "WG 120.5")))
    lccn, nlmcn = extract_call_numbers_from_pymarc(r)
    assert lccn is None
    assert nlmcn == "WG 120.5"


def test_extract_call_numbers_no_fields():
    r = Record()
    lccn, nlmcn = extract_call_numbers_from_pymarc(r)
    assert lccn is None
    assert nlmcn is None


def test_extract_call_numbers_four_digit_class():
    """Regression: 4-digit LC class numbers (PS, HF, etc.) are extracted correctly."""
    r = Record()
    r.add_field(_field("050", "0", ("a", "PS3562.E353"), ("b", "T6 2002")))
    lccn, nlmcn = extract_call_numbers_from_pymarc(r)
    assert lccn == "PS3562.E353 T6 2002"
    assert nlmcn is None


def test_extract_call_numbers_ind2_preference_end_to_end():
    """End-to-end: ind2='0' field is used when multiple 050 fields exist."""
    r = Record()
    r.add_field(_field("050", "4", ("a", "PZ7.C6837"), ("b", "WrongCopy 1999")))
    r.add_field(_field("050", "0", ("a", "PZ7.C6837"), ("b", "RightCopy 2008")))
    lccn, _ = extract_call_numbers_from_pymarc(r)
    assert lccn == "PZ7.C6837 RightCopy 2008"
