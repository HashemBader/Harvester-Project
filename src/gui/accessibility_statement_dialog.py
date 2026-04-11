"""Accessibility statement helpers and legacy dialog view.

The shared ``load_accessibility_statement`` helper resolves the markdown file
used by both the Help page's embedded statement view and the legacy dialog
class in this module. If the statement file cannot be loaded, a short fallback
message is returned so the UI always has something meaningful to display.
"""
# Import Path to work with filesystem paths in an OS-independent way
from pathlib import Path

# Import required PyQt6 widgets for building the dialog UI
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QPushButton, QHBoxLayout
# Import Qt core features (used here for alignment flags)
from PyQt6.QtCore import Qt

# Import custom theme manager to determine current theme (dark/light)
from .theme_manager import ThemeManager
# Import stylesheet generator and predefined color palettes
from .styles import generate_stylesheet, CATPPUCCIN_DARK, CATPPUCCIN_LIGHT


def load_accessibility_statement() -> str:
    """Read and return the accessibility statement Markdown text.

    The preferred source is ``docs/wcag.md``. The legacy packaged path
    ``docs/WCAG_ACCESSIBILITY.md`` is still supported so existing builds and
    packaging rules continue to work without changes.
    """
    # Determine the root directory of the project by going up 3 levels from this file
    root = Path(__file__).resolve().parent.parent.parent

    # Define possible file locations (new preferred + legacy fallback)
    statement_paths = [
        root / "docs" / "wcag.md",
        root / "docs" / "WCAG_ACCESSIBILITY.md",
    ]

    # Iterate through possible paths and return the first valid file found
    for statement_path in statement_paths:
        # Skip if the file does not exist
        if not statement_path.exists():
            continue
        try:
            # Attempt to read the file contents using UTF-8 encoding
            return statement_path.read_text(encoding="utf-8")
        except Exception:
            # If reading fails (e.g., permission issue), try the next path
            continue

    # Fallback content if no file could be loaded
    return (
        "# Accessibility Statement\n\n"
        "The accessibility statement file could not be loaded.\n\n"
        "Expected file: `docs/wcag.md` or `docs/WCAG_ACCESSIBILITY.md`.\n"
    )


class AccessibilityStatementDialog(QDialog):
    """Modal dialog that renders the project's WCAG accessibility statement.

    The statement is loaded from ``docs/wcag.md`` (or the legacy path
    ``docs/WCAG_ACCESSIBILITY.md``) relative to the project root.  The dialog
    is read-only and external hyperlinks inside the document open in the
    default browser (``setOpenExternalLinks(True)``).
    """

    def __init__(self, parent=None):
        """Initialise the dialog, build the layout, and apply the current theme.

        Args:
            parent: Optional parent widget for modal positioning.
        """
        # Call the parent class constructor (QDialog)
        super().__init__(parent)

        # Set the window title shown at the top of the dialog
        self.setWindowTitle("Accessibility Statement")

        # Set a minimum size for the dialog window (width x height)
        self.setMinimumSize(760, 560)

        # Build and arrange all UI components
        self._setup_ui()

        # Apply the current theme styling (dark/light)
        self._apply_theme()

    def _apply_theme(self):
        """Apply the full application stylesheet matching the current theme."""
        # Create a theme manager instance
        theme_mgr = ThemeManager()

        # Get the current theme mode ("dark" or "light")
        mode = theme_mgr.get_theme()

        # Select the appropriate color palette based on the theme
        palette = CATPPUCCIN_DARK if mode == "dark" else CATPPUCCIN_LIGHT

        # Apply the generated stylesheet to the dialog
        self.setStyleSheet(generate_stylesheet(palette))

    def _setup_ui(self):
        """Build the dialog layout: title label, subtitle, scrollable QTextBrowser, close button.

        The ``QTextBrowser`` renders the loaded Markdown content.
        ``setOpenExternalLinks(True)`` allows any hyperlinks inside the
        statement to open the system default browser without additional
        signal handling.
        """
        # Create the main vertical layout for the dialog
        layout = QVBoxLayout(self)

        # Create and configure the header label (title)
        header = QLabel("Accessibility Statement")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text
        header.setObjectName("DialogHeader")  # Used for styling via QSS
        layout.addWidget(header)

        # Create and configure a subtitle/helper text label
        sub = QLabel("This information helps users understand keyboard use and accessibility coverage.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align text
        sub.setProperty("class", "HelperText")  # Custom styling class
        layout.addWidget(sub)

        # Create a QTextBrowser to display the accessibility statement
        viewer = QTextBrowser()
        viewer.setReadOnly(True)  # Prevent user editing
        viewer.setOpenExternalLinks(True)   # allow links in the statement to open a browser

        # "TerminalViewport" class applies the monospace terminal-style QSS rule.
        viewer.setProperty("class", "TerminalViewport")

        # Load and display the markdown content from file
        viewer.setMarkdown(load_accessibility_statement())

        # Add the viewer to the layout and allow it to expand (stretch=1)
        layout.addWidget(viewer, stretch=1)

        # Create a horizontal layout for the button row
        btn_row = QHBoxLayout()

        # Add stretchable space to center the button
        btn_row.addStretch()

        # Create the close button
        close_btn = QPushButton("Close")
        close_btn.setProperty("class", "PrimaryButton")  # Apply styling class

        # Connect the button click to the dialog's accept() method (closes dialog)
        close_btn.clicked.connect(self.accept)

        # Add button to the layout
        btn_row.addWidget(close_btn)

        # Add stretchable space on the other side for centering
        btn_row.addStretch()

        # Add the button row to the main layout
        layout.addLayout(btn_row)