"""
Integration tests for Stretch Goal 1 (MARC Import) and Stretch Goal 2 (ISBN Linking).

SG1: User can import data from MARC record files on the local drive.
     - Prompt the user for what to use as the "source" of the LCCN.
     - These go into the same tables (main / attempted) as the rest.

SG2: linked_isbns table links multiple ISBNs assigned to the same book.
     - Lowest ISBN (treating trailing 'X' as '9' for comparison only) is the
       canonical key in main and attempted.
     - If a lower ISBN is found later, main/attempted are updated.
     - Table has two columns: lowest_isbn, other_isbn.
     - Even if the lowest ISBN is NOT on the record where the LCCN was found,
       main still holds the lowest ISBN with that LCCN.
"""

import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / "src"
for d in (str(ROOT), str(SRC)):
    if d not in sys.path:
        sys.path.insert(0, d)

from src.database.db_manager import DatabaseManager, MainRecord
from src.harvester.marc_import import MarcImportService, MarcImportSummary
from src.utils.isbn_validator import pick_lowest_isbn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _marc_json(isbn: str, lccn: str | None = None, nlmcn: str | None = None) -> dict:
    """Build a minimal MARC-JSON record for testing."""
    fields = []
    if isbn:
        fields.append({"020": {"subfields": [{"a": isbn}], "ind1": " ", "ind2": " "}})
    if lccn:
        fields.append({"050": {"subfields": [{"a": lccn}], "ind1": " ", "ind2": "0"}})
    if nlmcn:
        fields.append({"060": {"subfields": [{"a": nlmcn}], "ind1": " ", "ind2": "0"}})
    return {"fields": fields}


def _marc_xml(isbn: str, lccn: str | None = None, nlmcn: str | None = None) -> ET.Element:
    """Build a minimal MARCXML <record> element for testing."""
    NS = "http://www.loc.gov/MARC21/slim"
    record = ET.Element(f"{{{NS}}}record")

    def df(tag, ind1, ind2, subfields):
        el = ET.SubElement(record, f"{{{NS}}}datafield",
                           attrib={"tag": tag, "ind1": ind1, "ind2": ind2})
        for code, value in subfields:
            sf = ET.SubElement(el, f"{{{NS}}}subfield", attrib={"code": code})
            sf.text = value
        return el

    if isbn:
        df("020", " ", " ", [("a", isbn)])
    if lccn:
        df("050", " ", "0", [("a", lccn)])
    if nlmcn:
        df("060", " ", "0", [("a", nlmcn)])
    return record


@pytest.fixture()
def db(tmp_path):
    manager = DatabaseManager(tmp_path / "test.sqlite3")
    manager.init_db()
    return manager


@pytest.fixture()
def svc(tmp_path):
    service = MarcImportService(db_path=tmp_path / "test.sqlite3")
    service.db.init_db()
    return service


# ===========================================================================
# STRETCH GOAL 1 – MARC IMPORT
# ===========================================================================

class TestSG1MarcImport:
    """SG1: Import data from MARC record files; goes into the same tables."""

    # --- JSON format ---

    def test_json_record_with_lccn_stored_in_main(self, svc):
        """A JSON MARC record with an LCCN is saved to the main table."""
        records = [_marc_json("9780521641234", lccn="QA76.73.P98")]
        summary = svc.import_json_records(records, source_name="Cambridge MARC")

        assert summary.main_rows == 1
        assert summary.attempted_rows == 0
        result = svc.db.get_main("9780521641234")
        assert result is not None
        assert result.lccn == "QA76.73.P98"

    def test_json_record_custom_source_stored_correctly(self, svc):
        """The user-supplied source name is preserved exactly in main."""
        records = [_marc_json("9780521641234", lccn="QA76.73.P98")]
        svc.import_json_records(records, source_name="My Library MARC Export")

        result = svc.db.get_main("9780521641234")
        assert result.source == "My Library MARC Export"

    def test_json_record_nlmcn_stored_in_main(self, svc):
        """A JSON MARC record with an NLMCN is saved to main."""
        records = [_marc_json("9780781765244", nlmcn="WG 120 A1")]
        summary = svc.import_json_records(records, source_name="NLM MARC")

        assert summary.main_rows == 1
        result = svc.db.get_main("9780781765244")
        assert result is not None
        assert result.nlmcn == "WG 120 A1"

    def test_json_record_both_lccn_and_nlmcn(self, svc):
        """A record with both LCCN and NLMCN stores both in main."""
        records = [_marc_json("9780781765244", lccn="QA76.73.P98", nlmcn="WG 120")]
        svc.import_json_records(records, source_name="UPEI")

        result = svc.db.get_main("9780781765244")
        assert result.lccn == "QA76.73.P98"
        assert result.nlmcn == "WG 120"

    def test_json_record_without_call_number_goes_to_attempted(self, svc):
        """A MARC record with an ISBN but no call number goes to attempted, not main."""
        records = [_marc_json("9780521641234")]  # no LCCN/NLMCN
        summary = svc.import_json_records(records, source_name="Incomplete MARC")

        assert summary.main_rows == 0
        assert summary.attempted_rows == 1
        assert svc.db.get_main("9780521641234") is None
        attempted = svc.db.get_attempted("9780521641234")
        assert attempted is not None

    def test_json_multiple_records_all_stored(self, svc):
        """Batch import: all records with call numbers are stored."""
        records = [
            _marc_json("9780521641234", lccn="QA76.73.P98"),
            _marc_json("9780781765244", nlmcn="WG 120 A1"),
            _marc_json("9780262033848", lccn="QA76.9.A25"),
        ]
        summary = svc.import_json_records(records, source_name="Batch Source")

        assert summary.main_rows == 3
        assert svc.db.get_main("9780521641234") is not None
        assert svc.db.get_main("9780781765244") is not None
        assert svc.db.get_main("9780262033848") is not None

    def test_json_default_source_when_blank(self, svc):
        """When source_name is blank, default 'MARC Import' is used."""
        records = [_marc_json("9780521641234", lccn="QA76.73.P98")]
        svc.import_json_records(records, source_name="")

        result = svc.db.get_main("9780521641234")
        assert result.source == "MARC Import"

    # --- XML format ---

    def test_xml_record_with_lccn_stored_in_main(self, svc):
        """An XML MARC record with an LCCN is saved to main."""
        ns = {"marc": "http://www.loc.gov/MARC21/slim"}
        records = [_marc_xml("9780521641234", lccn="QA76.73.P98")]
        summary = svc.import_xml_records(records, source_name="MARCXML Source", namespaces=ns)

        assert summary.main_rows == 1
        result = svc.db.get_main("9780521641234")
        assert result is not None
        assert result.lccn == "QA76.73.P98"

    def test_xml_custom_source_preserved(self, svc):
        """XML import: user-supplied source is preserved in main."""
        ns = {"marc": "http://www.loc.gov/MARC21/slim"}
        records = [_marc_xml("9780521641234", lccn="QA76.73.P98")]
        svc.import_xml_records(records, source_name="UPEI Catalogue Export", namespaces=ns)

        result = svc.db.get_main("9780521641234")
        assert result.source == "UPEI Catalogue Export"

    def test_xml_record_without_call_number_goes_to_attempted(self, svc):
        """XML record with no call number goes to attempted."""
        ns = {"marc": "http://www.loc.gov/MARC21/slim"}
        records = [_marc_xml("9780521641234")]
        summary = svc.import_xml_records(records, source_name="Incomplete", namespaces=ns)

        assert summary.main_rows == 0
        assert summary.attempted_rows == 1

    def test_marc_import_result_identical_to_api_harvest_schema(self, svc, db):
        """Imported MARC records have the same schema as API-harvested records (same tables)."""
        # Insert a record via MARC import
        records = [_marc_json("9780521641234", lccn="QA76.73.P98")]
        svc.import_json_records(records, source_name="Test Source")

        # Insert a record via direct upsert (simulating API harvest)
        db.upsert_main(MainRecord(
            isbn="9780262033848", lccn="QA76.9.A25", lccn_source="loc_api",
            nlmcn=None, nlmcn_source=None, source="loc_api", date_added=None,
        ))

        # Both should be retrievable from get_main — same table, same structure
        marc_result = svc.db.get_main("9780521641234")
        api_result = db.get_main("9780262033848")

        assert marc_result is not None
        assert api_result is not None
        # Both have lccn, source, date_added
        assert marc_result.lccn is not None
        assert api_result.lccn is not None


# ===========================================================================
# STRETCH GOAL 2 – ISBN LINKING TABLE
# ===========================================================================

class TestSG2IsbnLinking:
    """SG2: linked_isbns table, lowest-ISBN normalization."""

    # --- pick_lowest_isbn ---

    def test_lowest_isbn_plain_numbers(self):
        """Numerically lowest ISBN is selected from a group."""
        assert pick_lowest_isbn(["9781234567890", "1234567890", "9784312567891"]) == "1234567890"

    def test_trailing_x_treated_as_9_for_sort(self):
        """Trailing 'X' is treated as '9' for comparison but the original value is returned."""
        # 019853453X sorts as 0198534539; 0198534531 < 0198534539 → 0198534531 wins
        result = pick_lowest_isbn(["019853453X", "0198534531"])
        assert result == "0198534531"

    def test_trailing_x_is_not_changed(self):
        """When X-ending ISBN IS the lowest, the original value with X is returned unchanged."""
        # 019853453X (sorts as ...39) vs 9780198534532 (starts with 9) → X-ending wins
        result = pick_lowest_isbn(["019853453X", "9780198534532"])
        assert result == "019853453X"   # X preserved, not changed to 9

    def test_single_isbn_returned_as_is(self):
        """A single-element group returns that ISBN."""
        assert pick_lowest_isbn(["9780521641234"]) == "9780521641234"

    # --- linked_isbns table structure ---

    def test_table_has_two_columns_lowest_and_other(self, db):
        """linked_isbns table stores (lowest_isbn, other_isbn) pairs."""
        db.upsert_linked_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")
        linked = db.get_linked_isbns("1234567890")
        assert linked == ["9781234567890"]

    def test_three_isbn_group_two_rows(self, db):
        """Three ISBNs for one book → two rows in linked_isbns, both pointing to lowest."""
        db.upsert_linked_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")
        db.upsert_linked_isbn(lowest_isbn="1234567890", other_isbn="9784312567891")

        linked = sorted(db.get_linked_isbns("1234567890"))
        # Exactly the two higher ISBNs, exactly as specified in the project doc
        assert linked == ["9781234567890", "9784312567891"]

    def test_lowest_isbn_does_not_appear_in_other_column(self, db):
        """The lowest ISBN itself never appears in the other_isbn column."""
        db.upsert_linked_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")
        # Resolve the higher ISBN → should get the lowest back
        assert db.get_lowest_isbn("9781234567890") == "1234567890"
        # The lowest itself resolves to itself (not in other_isbn column)
        assert db.get_lowest_isbn("1234567890") == "1234567890"

    # --- main table only holds the lowest ISBN ---

    def test_main_holds_lowest_isbn_when_higher_was_found_first(self, db):
        """
        SG2 spec: even if the lowest ISBN is not on the record where the LCCN was
        found, main still has the lowest ISBN with that LCCN.
        """
        # LCCN found on 9781234567890 (higher), but 1234567890 is lower
        db.upsert_main(MainRecord(
            isbn="9781234567890", lccn="QA76.73.P98", lccn_source="loc_api",
            nlmcn=None, nlmcn_source=None, source="loc_api", date_added=None,
        ))

        db.rewrite_to_lowest_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")

        assert db.get_main("1234567890").lccn == "QA76.73.P98"
        assert db.get_main("9781234567890") is None  # higher ISBN removed from main

    def test_only_lowest_isbn_in_main_regardless_of_discovery_order(self, db):
        """Only the lowest ISBN appears in main, regardless of which was found first."""
        # Insert higher ISBN first
        db.upsert_main(MainRecord(
            isbn="9784312567891", lccn="QA76.73.P98", lccn_source="loc_api",
            nlmcn=None, nlmcn_source=None, source="loc_api", date_added=None,
        ))
        # Then discover the lowest
        db.rewrite_to_lowest_isbn(lowest_isbn="1234567890", other_isbn="9784312567891")

        assert db.get_main("1234567890") is not None
        assert db.get_main("9784312567891") is None

    # --- update to lowest when a lower ISBN is found later ---

    def test_update_to_lower_isbn_when_found_later(self, db):
        """
        SG2 spec: update main and attempted with the lowest if you find a lower one later.
        """
        # Start with a medium ISBN as the "lowest"
        db.upsert_main(MainRecord(
            isbn="9781234567890", lccn="QA76.73.P98", lccn_source="loc_api",
            nlmcn=None, nlmcn_source=None, source="loc_api", date_added=None,
        ))
        db.upsert_linked_isbn(lowest_isbn="9781234567890", other_isbn="9784312567891")

        # Later discover 1234567890 is actually lower → rewrite
        db.rewrite_to_lowest_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")

        # main now has the new canonical lowest
        assert db.get_main("1234567890").lccn == "QA76.73.P98"
        assert db.get_main("9781234567890") is None

        # linked_isbns is updated: all others now point to the new lowest
        linked = sorted(db.get_linked_isbns("1234567890"))
        assert "9781234567890" in linked

    def test_attempted_table_also_updated_to_lowest(self, db):
        """Attempted rows are also rewritten to use the lowest ISBN."""
        # Record a failure under the higher ISBN
        with db.transaction() as conn:
            db.upsert_attempted_many(conn, [("9781234567890", "loc_api", "lccn", 20260101, "not found")])

        db.rewrite_to_lowest_isbn(lowest_isbn="1234567890", other_isbn="9781234567890")

        # attempted row moved to lowest ISBN
        assert db.get_attempted("1234567890") is not None
        assert db.get_attempted("9781234567890") is None

    # --- MARC import uses lowest ISBN (SG1 + SG2 combined) ---

    def test_marc_import_uses_lowest_isbn_for_multiple_isbns(self, svc):
        """
        When a MARC record has multiple ISBNs, MARC import stores the result
        under the lowest ISBN and records the others in linked_isbns.
        """
        # Record has both a short (lower) and long (higher) ISBN
        record = {
            "fields": [
                {"020": {"subfields": [{"a": "1234567890"}], "ind1": " ", "ind2": " "}},
                {"020": {"subfields": [{"a": "9781234567890"}], "ind1": " ", "ind2": " "}},
                {"050": {"subfields": [{"a": "QA76.73.P98"}], "ind1": " ", "ind2": "0"}},
            ]
        }
        summary = svc.import_json_records([record], source_name="Multi-ISBN Source")

        assert summary.main_rows == 1
        # Result stored under lowest ISBN
        result = svc.db.get_main("1234567890")
        assert result is not None
        assert result.lccn == "QA76.73.P98"
        # Higher ISBN not in main
        assert svc.db.get_main("9781234567890") is None
        # Link recorded
        assert "9781234567890" in svc.db.get_linked_isbns("1234567890")
