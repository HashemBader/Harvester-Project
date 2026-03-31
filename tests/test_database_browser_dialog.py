import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
PROJECT_ROOT = SRC_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PyQt6.QtWidgets import QApplication

from database import DatabaseManager
from gui.database_browser_dialog import DatabaseBrowserDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_database_browser_shows_only_database_tables(qapp, tmp_path):
    dialog = DatabaseBrowserDialog(db=DatabaseManager(tmp_path / "browser.sqlite3"))
    labels = [dialog.tab_widget.tabText(i) for i in range(dialog.tab_widget.count())]
    assert labels == ["main", "attempted", "linked_isbns"]
    dialog.close()
