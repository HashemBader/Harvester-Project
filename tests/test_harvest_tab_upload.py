import sys
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication, QSizePolicy


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
for path in (str(PROJECT_ROOT), str(SRC_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def harvest_tab(qapp):
    from src.gui.harvest_tab import HarvestTab, UIState

    tab = HarvestTab()
    tab.show()
    qapp.processEvents()
    assert tab.current_state == UIState.IDLE
    yield tab
    tab.close()


def test_set_input_file_enables_start_for_valid_tsv(harvest_tab, qapp, tmp_path):
    """Uploading a valid ISBN file should leave the tab ready to harvest."""
    input_path = tmp_path / "isbns.tsv"
    input_path.write_text("isbn\n9780131103627\n", encoding="utf-8")

    harvest_tab.set_input_file(str(input_path))
    qapp.processEvents()

    assert harvest_tab.input_file == str(input_path)
    assert harvest_tab.btn_start.isEnabled()
    assert harvest_tab.current_state.name == "READY"
    assert harvest_tab.log_output.text() == "Ready to harvest 1 unique ISBNs."
    assert harvest_tab.lbl_val_loaded.text() == "1"


def test_completed_layout_keeps_top_cards_pinned(harvest_tab, qapp):
    """The completion banner should not stretch the top cards out of place."""
    from src.gui.harvest_tab import UIState

    harvest_tab._transition_state(UIState.COMPLETED)
    qapp.processEvents()

    margins = harvest_tab.content_grid.contentsMargins()
    assert margins.top() == 6
    assert harvest_tab.content_grid.rowStretch(0) == 0
    assert harvest_tab.content_grid.rowStretch(1) == 1
    assert harvest_tab.input_card.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred
    assert harvest_tab.stats_card.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Preferred


def test_clear_input_resets_file_preview(harvest_tab, qapp, tmp_path):
    """Clearing the loaded file should restore the preview widget to its empty state."""
    input_path = tmp_path / "isbns.tsv"
    input_path.write_text("isbn\n9780131103627\n9780306406157\n", encoding="utf-8")

    harvest_tab.set_input_file(str(input_path))
    qapp.processEvents()

    assert harvest_tab.preview_table.rowCount() > 0
    assert harvest_tab.lbl_preview_filename.text() != "No file selected"

    harvest_tab._clear_input()
    qapp.processEvents()

    assert harvest_tab.preview_table.columnCount() == 2
    assert harvest_tab.preview_table.rowCount() == 0
    assert harvest_tab.preview_table.horizontalHeaderItem(0).text() == "ISBN"
    assert harvest_tab.preview_table.horizontalHeaderItem(1).text() == "Status"
    assert harvest_tab.lbl_preview_filename.text() == "No file selected"


def test_running_harvest_locks_and_preserves_input_file(harvest_tab, qapp, tmp_path):
    """Clear/Browse must not reset the harvest setup while the worker is active."""
    from src.gui.harvest_tab import UIState

    first_path = tmp_path / "first.tsv"
    first_path.write_text("isbn\n9780131103627\n", encoding="utf-8")
    second_path = tmp_path / "second.tsv"
    second_path.write_text("isbn\n9780306406157\n", encoding="utf-8")

    harvest_tab.set_input_file(str(first_path))
    harvest_tab._transition_state(UIState.RUNNING)
    qapp.processEvents()

    assert not harvest_tab.btn_browse.isEnabled()
    assert not harvest_tab.btn_clear_file.isEnabled()

    harvest_tab._clear_input()
    harvest_tab.set_input_file(str(second_path))
    qapp.processEvents()

    assert harvest_tab.current_state == UIState.RUNNING
    assert harvest_tab.input_file == str(first_path)
    assert harvest_tab.file_path_edit.text() == first_path.name


def test_paused_harvest_keeps_input_controls_locked(harvest_tab, qapp, tmp_path):
    """Pause is still an active harvest state, so file controls stay locked."""
    from src.gui.harvest_tab import UIState

    input_path = tmp_path / "isbns.tsv"
    input_path.write_text("isbn\n9780131103627\n", encoding="utf-8")

    harvest_tab.set_input_file(str(input_path))
    harvest_tab._transition_state(UIState.PAUSED)
    qapp.processEvents()

    assert not harvest_tab.btn_browse.isEnabled()
    assert not harvest_tab.btn_clear_file.isEnabled()


def test_browse_after_completed_resets_harvest_setup_without_dashboard_reset(harvest_tab, qapp, tmp_path):
    """Loading a new file after a terminal run clears setup state but not dashboard state."""
    from src.gui.harvest_tab import UIState

    first_path = tmp_path / "first.tsv"
    first_path.write_text("isbn\n9780131103627\n", encoding="utf-8")
    second_path = tmp_path / "second.tsv"
    second_path.write_text("isbn\n9780306406157\n", encoding="utf-8")
    reset_events = []
    harvest_tab.harvest_reset.connect(lambda: reset_events.append(True))

    harvest_tab.set_input_file(str(first_path))
    harvest_tab._transition_state(UIState.COMPLETED)
    harvest_tab.progress_bar.setValue(100)
    harvest_tab.log_output.setText("Harvest complete. View results in Dashboard.")

    harvest_tab.set_input_file(str(second_path))
    qapp.processEvents()

    assert reset_events == []
    assert harvest_tab.current_state == UIState.READY
    assert harvest_tab.input_file == str(second_path)
    assert harvest_tab.lbl_val_loaded.text() == "1"
    assert harvest_tab.log_output.text() == "Ready to harvest 1 unique ISBNs."


def test_retry_window_dates_format_compact_and_legacy_values():
    """Retry popup details should calculate dates for current and legacy DB formats."""
    from src.gui.harvest_tab import HarvestTab

    assert HarvestTab._format_retry_window_dates(20260411, 7) == ("2026-04-11", "2026-04-18")
    assert HarvestTab._format_retry_window_dates("2026-04-11 14:56:28", 3) == (
        "2026-04-11",
        "2026-04-14",
    )
