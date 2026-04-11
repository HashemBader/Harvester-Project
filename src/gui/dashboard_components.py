"""Reusable dashboard widgets and standalone formatting helpers.

These pieces are kept separate from ``dashboard.py`` so the tab class can
focus on page-level state changes while the visual building blocks remain easy
to scan and reuse independently.

Contents:
- File utilities: ``write_csv_copy``, ``safe_filename``
- Text helpers: ``truncate_text``, ``normalize_recent_detail``,
  ``problems_button_label``
- Widgets: ``DashboardCard``, ``RecentResultsPanel``, ``ProfileSwitchCombo``

Usage notes:
- ``DashboardCard`` relies on the ``"Card"``, ``"CardTitle"``, ``"CardValue"``, and
  ``"CardHelper"`` QSS classes defined in ``styles.py``.
- ``RecentResultsPanel`` sets a fixed height after each data update via
  ``_fit_table_height`` so the enclosing scroll area always sees the correct size.
- ``ProfileSwitchCombo`` subclasses ``QComboBox`` solely to paint a custom chevron;
  all other combo behaviour is inherited unchanged.
"""

from __future__ import annotations  # Enables forward references in type hints (Python 3.7+ behavior)

import csv  # Used for reading and writing CSV/TSV files
import re   # Used for splitting and normalizing strings with regular expressions

from PyQt6.QtCore import Qt  # Core Qt enums and flags (focus, alignment, etc.)
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen  # GUI utilities (colors, painting, clipboard)
from PyQt6.QtWidgets import (
    QComboBox,          # Dropdown selection widget
    QFrame,             # Base container with styling support
    QHeaderView,        # Controls table header resizing behavior
    QHBoxLayout,        # Horizontal layout manager
    QLabel,             # Text display widget
    QMenu,              # Context (right-click) menu
    QTableWidget,       # Table widget for displaying tabular data
    QTableWidgetItem,   # Individual table cell item
    QVBoxLayout,        # Vertical layout manager
)

from .icons import get_pixmap  # Helper to render SVG icons as pixmaps


def write_csv_copy(tsv_path: str, csv_path: str) -> None:
    """Convert a TSV file to a UTF-8 CSV (with BOM) for spreadsheet apps."""
    # Open the TSV file for reading
    with open(tsv_path, newline="", encoding="utf-8") as source:
        # Read rows using tab delimiter
        rows = csv.reader(source, delimiter="\t")
        # Open the CSV file for writing with BOM encoding (Excel compatibility)
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as target:
            writer = csv.writer(target)
            # Write all rows directly into CSV format
            writer.writerows(rows)


def safe_filename(value: str) -> str:
    """Strip characters that are awkward or invalid in file names."""
    # Replace invalid filename characters and spaces with underscores
    cleaned = "".join("_" if c in '\\/:*?"<>| ' else c for c in (value or "").strip())
    # Remove leading/trailing underscores
    cleaned = cleaned.strip("_")
    # Ensure the filename is never empty
    return cleaned or "default"


def problems_button_label(
    profile_name: str | None,
    file_name: str | None = None,
    include_profile: bool = False,
) -> str:
    """Return the label used for the target-problems export button."""
    # Parameters intentionally unused (kept for API compatibility / future use)
    _ = profile_name, file_name, include_profile
    return "Open targets problems"


def truncate_text(text: str, limit: int = 110) -> str:
    """Trim *text* to *limit* characters, appending ``"..."`` when truncated."""
    # Normalize input to string and strip whitespace
    text = str(text or "").strip()
    # Return early if within limit
    if len(text) <= limit:
        return text
    # Truncate and append ellipsis
    return text[: max(0, limit - 3)].rstrip() + "..."


def normalize_recent_detail(text: str) -> str:
    """Collapse duplicate source labels in the recent-results table."""
    parts: list[str] = []
    # Split text using multiple separators
    for piece in re.split(r"[+,;|]", str(text or "")):
        cleaned = piece.strip()
        # Normalize common typo "UCB" to "UBC"
        if cleaned.upper() == "UCB":
            cleaned = "UBC"
        elif cleaned.upper() == "UBC":
            cleaned = "UBC"
        # Add unique, non-empty values only
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    # Join cleaned values or fallback to original/placeholder
    return " + ".join(parts) if parts else (str(text or "").strip() or "-")


class DashboardCard(QFrame):
    """A single KPI metric card with an icon, title label, large numeric value, and helper text."""

    def __init__(self, title, icon_svg, accent_color="#8aadf4"):
        super().__init__()
        # Apply QSS styling class for consistent card appearance
        self.setProperty("class", "Card")
        self.setMinimumWidth(220)  # Ensure consistent card width in layouts
        self._setup_ui(title, icon_svg, accent_color)

    def _setup_ui(self, title, icon_svg, accent_color):
        # Main vertical layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(5)

        # Header row (title + icon)
        header_layout = QHBoxLayout()

        lbl_title = QLabel(title)
        # Apply QSS class for styling
        lbl_title.setProperty("class", "CardTitle")

        icon_lbl = QLabel()
        # Render SVG icon with tint color and fixed size
        icon_lbl.setPixmap(get_pixmap(icon_svg, accent_color, 24))

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()  # Push icon to the right
        header_layout.addWidget(icon_lbl)

        layout.addLayout(header_layout)

        # Main value label
        self.lbl_value = QLabel("0")
        self.lbl_value.setProperty("class", "CardValue")
        layout.addWidget(self.lbl_value)

        # Helper text below value
        self.lbl_helper = QLabel("Total records")
        self.lbl_helper.setProperty("class", "CardHelper")
        layout.addWidget(self.lbl_helper)

    def set_data(self, value, helper_text=""):
        # Update main value
        self.lbl_value.setText(str(value))
        # Update helper text only if provided
        if helper_text:
            self.lbl_helper.setText(helper_text)


class RecentResultsPanel(QFrame):
    """Compact read-only table showing up to 10 of the most recent harvest results."""

    def __init__(self):
        super().__init__()
        # Apply card styling
        self.setProperty("class", "Card")
        # Cache to avoid unnecessary UI updates
        self._last_records_key = None
        # Prevent updates while context menu is open
        self._context_menu_open = False
        self._setup_ui()

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Section header
        header = QLabel("RECENT RESULTS")
        header.setProperty("class", "CardTitle")
        layout.addWidget(header)

        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ISBN", "Status", "Detail"])

        # Configure column resizing behavior
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Hide vertical header
        self.table.verticalHeader().setVisible(False)

        # Disable grid and editing
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Disable focus highlight
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Selection behavior
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Enable custom context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        # Disable scrollbars (height handled manually)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Text display settings
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setWordWrap(False)

        # Transparent background for styling
        self.table.setStyleSheet("background: transparent; border: none;")

        layout.addWidget(self.table)

    def update_data(self, records):
        # Create a comparable key to detect changes
        records_key = tuple(
            (
                str(record.get("isbn", "")),
                str(record.get("status", "")),
                str(record.get("detail", "")),
            )
            for record in (records or [])
        )

        # Skip update if unchanged or menu is open
        if self._context_menu_open or records_key == self._last_records_key:
            return

        self._last_records_key = records_key

        # Clear table
        self.table.setRowCount(0)

        for row_idx, record in enumerate(records):
            self.table.insertRow(row_idx)

            # ISBN column
            self.table.setItem(row_idx, 0, QTableWidgetItem(record["isbn"]))

            # Status column with color coding
            status = record["status"]
            item_status = QTableWidgetItem(status)

            if status in {"Successful", "Found", "Linked ISBN"}:
                item_status.setForeground(QColor("#2e7d32"))  # green
            else:
                item_status.setForeground(QColor("#c62828"))  # red

            self.table.setItem(row_idx, 1, item_status)

            # Detail column (normalized + truncated)
            detail_text = normalize_recent_detail(record.get("detail") or "-")

            item_detail = QTableWidgetItem(truncate_text(detail_text, 90))
            item_detail.setToolTip(detail_text)

            self.table.setItem(row_idx, 2, item_detail)

        # Adjust height to fit rows
        self._fit_table_height()

    def _show_context_menu(self, pos):
        # Get clicked item
        item = self.table.itemAt(pos)
        if item is None:
            return

        self.table.setCurrentItem(item)
        row = item.row()

        # Collect full row values (prefer tooltip text)
        row_values = [
            self.table.item(row, col).toolTip() or self.table.item(row, col).text()
            for col in range(self.table.columnCount())
            if self.table.item(row, col) is not None
        ]

        # Build context menu
        menu = QMenu(self.table)
        copy_cell = menu.addAction("Copy")
        copy_row = menu.addAction("Copy row")

        self._context_menu_open = True
        try:
            action = menu.exec(self.table.viewport().mapToGlobal(pos))
        finally:
            self._context_menu_open = False

        # Copy selected data to clipboard
        if action == copy_cell:
            QGuiApplication.clipboard().setText(item.toolTip() or item.text())
        elif action == copy_row:
            QGuiApplication.clipboard().setText("\t".join(row_values))

    def _fit_table_height(self):
        # Calculate header and row heights
        header_height = self.table.horizontalHeader().height() or 34
        row_height = self.table.verticalHeader().defaultSectionSize() or 26

        # Always show space for at least 10 rows
        visible_rows = max(10, self.table.rowCount())

        # Set fixed height
        self.table.setFixedHeight(header_height + (row_height * visible_rows) + 8)


class ProfileSwitchCombo(QComboBox):
    """Dashboard profile switcher that paints its own chevron arrow."""

    def paintEvent(self, event):
        # Draw default combo box first
        super().paintEvent(event)

        # Custom painter for chevron
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set pen color and thickness
        painter.setPen(QPen(QColor("#e6eaf6"), 2))

        # Calculate chevron position
        cx = self.width() - 21
        cy = self.height() // 2 + 1
        size = 5

        # Draw chevron lines
        painter.drawLine(cx - size, cy - 2, cx, cy + 3)
        painter.drawLine(cx, cy + 3, cx + size, cy - 2)

        painter.end()