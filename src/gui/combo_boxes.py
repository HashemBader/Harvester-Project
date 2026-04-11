"""Shared combo box widgets for the PyQt6 GUI.

Provides ``ConsistentComboBox``, a ``QComboBox`` subclass that:

* Replaces the default OS-native popup view with a styled ``QListView`` so
  the application stylesheet (``styles.py``) controls the popup appearance
  on all platforms.
* Limits accidental value changes from scroll-wheel events when the widget
  does not have keyboard focus.
* Normalises popup width so short combo boxes never show a truncated list.
"""

# Import Qt core features such as focus policies and widget attributes
from PyQt6.QtCore import Qt
# Import required widgets: base combo box, list view for popup, and frame styling
from PyQt6.QtWidgets import QComboBox, QListView, QFrame


class ConsistentComboBox(QComboBox):
    """``QComboBox`` subclass with a styled popup and scroll-wheel guard.

    The default Qt combo box uses a native OS popup that ignores the
    application stylesheet on macOS and certain Linux themes.  This subclass
    installs a custom ``QListView`` as the popup view (``setView``) so the
    ``QListView#<objectName>`` QSS rules defined in ``styles.py`` are applied
    consistently everywhere.

    Attributes:
        DEFAULT_POPUP_OBJECT_NAME: Fallback ``objectName`` for the popup
            ``QListView`` when none is supplied; must match a ``QListView``
            rule in the application stylesheet.
    """

    # Default object name used to match QSS styling rules
    DEFAULT_POPUP_OBJECT_NAME = "ComboPopup"

    def __init__(
        self,
        parent=None,
        *,
        popup_object_name: str | None = None,
        max_visible_items: int | None = None,
    ):
        """Initialise the combo box and install the custom popup view.

        Args:
            parent: Optional parent widget.
            popup_object_name: ``objectName`` assigned to the popup
                ``QListView``; used as the QSS selector.  Defaults to
                ``DEFAULT_POPUP_OBJECT_NAME``.
            max_visible_items: Maximum number of items shown before the popup
                scrolls.  ``None`` leaves the Qt default (10) unchanged.
        """
        # Call the parent QComboBox constructor
        super().__init__(parent)

        # Ensure the widget can receive strong focus (keyboard + mouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Prevent the user from accidentally inserting new items by typing.
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        # Replace the native popup with a custom QListView so the application
        # stylesheet can style it uniformly across platforms.
        popup_view = QListView(self)

        # Enable uniform item sizes for better rendering performance
        popup_view.setUniformItemSizes(True)

        # Remove the default frame/border around the popup
        popup_view.setFrameShape(QFrame.Shape.NoFrame)

        # WA_StyledBackground lets the stylesheet paint the QListView background.
        popup_view.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Disable horizontal scrollbar to avoid visual clutter
        popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # objectName is the QSS selector (e.g. QListView#RankComboPopup).
        popup_view.setObjectName(popup_object_name or self.DEFAULT_POPUP_OBJECT_NAME)

        # Apply this custom view as the dropdown popup
        self.setView(popup_view)

        # Optionally limit how many items are visible before scrolling is required
        if max_visible_items is not None:
            try:
                # Ensure value is at least 1 and convert to integer
                self.setMaxVisibleItems(max(1, int(max_visible_items)))
            except Exception:
                # Fallback to default if conversion fails
                self.setMaxVisibleItems(10)

    def showPopup(self):
        """Override popup display to normalise width across platforms.

        Qt's default popup can be narrower than the combo widget itself on some
        platforms, or narrower than its content.  This override computes a
        ``desired_width`` that is at least as wide as the combo and wide enough
        to show all item text without truncation, then applies it to the popup
        view before delegating to the Qt implementation.

        Each measurement is wrapped in a ``try/except`` so a view implementation
        that does not support a particular call never prevents the popup from
        opening.
        """
        # Get the currently assigned popup view (QListView)
        popup_view = self.view()

        if popup_view is not None:
            try:
                # Width required to display the longest item text in column 0.
                content_width = popup_view.sizeHintForColumn(0)
            except Exception:
                # If not supported, fallback to invalid width
                content_width = -1

            scrollbar_width = 0
            try:
                # Reserve space for the vertical scrollbar if it will appear.
                scrollbar_width = popup_view.verticalScrollBar().sizeHint().width()
            except Exception:
                # If scrollbar not available, ignore
                scrollbar_width = 0

            frame_width = 0
            try:
                # Account for the popup view's frame border on both sides.
                frame_width = popup_view.frameWidth() * 2
            except Exception:
                # If frame info unavailable, ignore
                frame_width = 0

            # 28 px of extra padding prevents text from touching the edges.
            # Ensure popup is at least as wide as the combo box itself
            desired_width = max(self.width(), content_width + scrollbar_width + frame_width + 28)

            # Apply the calculated minimum width to the popup
            popup_view.setMinimumWidth(desired_width)

        # Call the default Qt implementation to actually show the popup
        super().showPopup()

    def wheelEvent(self, event):
        """Ignore wheel changes unless the combo box already has focus."""
        # Only allow scroll-wheel changes if the widget currently has focus
        if self.hasFocus():
            super().wheelEvent(event)
            return

        # Otherwise ignore the event to prevent accidental value changes
        event.ignore()