from pathlib import Path

from src.gui.harvest_support import _prepare_marc_import_records
from src.gui.harvest_tab import HarvestTab
from src.harvester.marc_import import ParsedMarcImportRecord


def test_prepare_marc_import_records_skips_missing_isbn_rows_from_export():
    selected_rows, parsed_records, written, skipped, no_isbn = _prepare_marc_import_records(
        [
            ParsedMarcImportRecord(
                isbns=("0887600859", "0715373277"),
                lccn="FC75.W38",
                source="sru",
            ),
            ParsedMarcImportRecord(
                isbns=tuple(),
                lccn="FC51.T67 1967",
                source="sru",
            ),
        ],
        mode="both",
        source_name="sru",
    )

    assert selected_rows == [("0715373277", "FC75.W38", None)]
    assert parsed_records == [
        ParsedMarcImportRecord(
            isbns=("0887600859", "0715373277"),
            lccn="FC75.W38",
            nlmcn=None,
            source="sru",
        )
    ]
    assert written == 1
    assert skipped == 0
    assert no_isbn == 1


def test_parse_marc_records_keeps_all_valid_isbns_in_xml_record(tmp_path):
    xml_path = tmp_path / "sample.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<collection xmlns="http://www.loc.gov/MARC21/slim">
  <record>
    <leader>01076cam a2200313   4500</leader>
    <controlfield tag="001">1443931</controlfield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">0887600859</subfield>
    </datafield>
    <datafield tag="020" ind1=" " ind2=" ">
      <subfield code="a">0715373277</subfield>
    </datafield>
    <datafield tag="050" ind1=" " ind2=" ">
      <subfield code="a">FC75.W38</subfield>
    </datafield>
  </record>
</collection>
""",
        encoding="utf-8",
    )

    records = HarvestTab._parse_marc_records(None, str(xml_path))

    assert len(records) == 1
    assert records[0] == ParsedMarcImportRecord(
        isbns=("0887600859", "0715373277"),
        lccn="FC75.W38",
        nlmcn=None,
        source=None,
    )
