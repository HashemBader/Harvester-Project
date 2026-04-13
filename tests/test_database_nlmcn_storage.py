import sqlite3

from src.database.db_manager import DatabaseManager
from src.database.records import MainRecord
from src.harvester.export_main_tsv import export_main_to_tsv


def test_upsert_main_rejects_invalid_nlmcn_and_classifies_valid_nlmcn(tmp_path):
    db = DatabaseManager(tmp_path / "harvester.sqlite3")
    db.init_db()

    with db.transaction() as conn:
        db.upsert_main_many(
            conn,
            [
                MainRecord(isbn="9780000000001", nlmcn="W3 I324 1974i", nlmcn_source="OCLC"),
                MainRecord(isbn="9780000000002", nlmcn="2000 K-526", nlmcn_source="OCLC"),
            ],
        )

    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT isbn, call_number, call_number_type, classification, source
            FROM main
            ORDER BY isbn
            """
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {
            "isbn": "9780000000001",
            "call_number": "W3 I324 1974i",
            "call_number_type": "nlmcn",
            "classification": "W",
            "source": "OCLC",
        }
    ]


def test_init_db_repairs_existing_nlmcn_rows(tmp_path):
    db_path = tmp_path / "harvester.sqlite3"
    db = DatabaseManager(db_path)
    db.init_db()

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO main (isbn, call_number, call_number_type, classification, source, date_added)
            VALUES
                ('9780000000001', 'WR 140 D435172 2001', 'nlmcn', NULL, 'OCLC', 20260413),
                ('9780000000002', '1999 D-317', 'nlmcn', NULL, 'OCLC', 20260413)
            """
        )

    db.init_db()

    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT isbn, call_number, classification
            FROM main
            ORDER BY isbn
            """
        ).fetchall()

    assert [dict(row) for row in rows] == [
        {
            "isbn": "9780000000001",
            "call_number": "WR 140 D435172 2001",
            "classification": "WR",
        }
    ]


def test_main_tsv_export_includes_separate_nlm_classification(tmp_path):
    db_path = tmp_path / "harvester.sqlite3"
    db = DatabaseManager(db_path)
    db.init_db()

    with db.transaction() as conn:
        db.upsert_main_many(
            conn,
            [
                MainRecord(
                    isbn="9780000000001",
                    lccn="QA76.73.P98",
                    lccn_source="LoC",
                    nlmcn="WK 810 H438 2021",
                    nlmcn_source="OCLC",
                )
            ],
        )

    out_path = export_main_to_tsv(db_path, tmp_path / "main.tsv")
    lines = out_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].split("\t") == [
        "ISBN",
        "LCCN",
        "NLMCN",
        "Classification",
        "NLM Classification",
        "Source",
        "Date Added",
    ]
    assert lines[1].split("\t")[:5] == [
        "9780000000001",
        "QA76.73.P98",
        "WK 810 H438 2021",
        "QA",
        "WK",
    ]
