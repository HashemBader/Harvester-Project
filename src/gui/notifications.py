"""Desktop notifications and system tray integration for LCCN Harvester.

Provides ``NotificationManager``, which wraps ``QSystemTrayIcon`` and falls back
to native OS notification mechanisms when the tray is not available:

- macOS: ``osascript`` ``display notification`` command.
- Windows: ``QSystemTrayIcon.showMessage`` balloon tooltips (no extra library).
- Linux: ``notify-send`` command.

Error notifications are always shown as modal ``QMessageBox.warning`` dialogs
for maximum visibility, regardless of tray availability.

``NotificationPreferences`` handles loading/saving per-user preferences from
``data/notification_prefs.json``.
"""
import logging           # Standard library logging for error/info messages
import platform          # Detects the current OS (Darwin/Windows/Linux)
import subprocess        # Spawns osascript / notify-send for native OS notifications
from pathlib import Path  # OS-independent filesystem path handling

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox  # Tray icon, context menu, and modal error dialogs
from PyQt6.QtGui import QIcon, QAction                           # App icon and menu actions
from PyQt6.QtCore import QObject, pyqtSignal                     # Base QObject and custom signal support

logger = logging.getLogger(__name__)


class NotificationManager(QObject):
    """Manages desktop notifications and system tray for the application.

    Owns the ``QSystemTrayIcon`` (if the platform supports it) and exposes
    convenience methods for each notification event type.  All notification
    delivery is conditional on ``notifications_enabled``.

    Signals:
        notification_clicked(): Reserved for future use when the user clicks
            a tray notification.
    """

    notification_clicked = pyqtSignal()

    def __init__(self, main_window=None):
        """Initialise the manager and detect the host OS.

        Args:
            main_window: The application's main window; used as parent for
                modal error dialogs and tray icon ownership.
        """
        super().__init__()
        self.main_window = main_window
        self.system = platform.system()  # Cached once; used by _show_native_notification
        self.tray_icon = None            # Created lazily in setup_system_tray
        self.notifications_enabled = True

    def setup_system_tray(self):
        """Create the system-tray icon, load its image, and attach a context menu.

        Exits early without error if the platform does not support a system tray
        (e.g. some minimal Linux desktop environments).
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray not available.")
            return

        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self.main_window)

        # Try to load icon, fall back to default
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Use default Qt icon
            self.tray_icon.setIcon(self.main_window.style().standardIcon(
                self.main_window.style().StandardPixmap.SP_ComputerIcon
            ))

        self.tray_icon.setToolTip("LCCN Harvester")

        # Create context menu
        menu = QMenu()

        show_action = QAction("Show Window", self.main_window)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        menu.addSeparator()

        notifications_action = QAction("Enable Notifications", self.main_window)
        notifications_action.setCheckable(True)
        notifications_action.setChecked(True)
        notifications_action.triggered.connect(self._toggle_notifications)
        menu.addAction(notifications_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self.main_window)
        quit_action.triggered.connect(self.main_window.close)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

        # Connect double-click to show window
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Show tray icon
        self.tray_icon.show()

    def _show_window(self):
        """Show and raise the main window."""
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def _on_tray_activated(self, reason):
        """Handle tray icon activation events (single click, double-click, etc.).

        Args:
            reason: The ``QSystemTrayIcon.ActivationReason`` enum value describing
                how the icon was activated.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _toggle_notifications(self, checked):
        """Toggle global notification delivery on or off.

        Args:
            checked: ``True`` to enable notifications; ``False`` to suppress them.
        """
        self.notifications_enabled = checked

    def show_notification(self, title, message, notification_type="info", duration=5000):
        """
        Show a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, success, warning, error)
            duration: Duration in milliseconds (default 5000 = 5 seconds)
        """
        if not self.notifications_enabled:
            return

        # Always show errors as modal popups for visibility
        if notification_type == "error" and self.main_window:
            QMessageBox.warning(self.main_window, title, message)
            return

        # Map notification types to icons
        icon_map = {
            "info": QSystemTrayIcon.MessageIcon.Information,
            "success": QSystemTrayIcon.MessageIcon.Information,
            "warning": QSystemTrayIcon.MessageIcon.Warning,
            "error": QSystemTrayIcon.MessageIcon.Critical
        }

        icon = icon_map.get(notification_type, QSystemTrayIcon.MessageIcon.Information)

        # Try system tray notification first (works on all platforms with Qt)
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, duration)
        else:
            # Fall back to native notifications
            self._show_native_notification(title, message, notification_type)

    def _show_native_notification(self, title, message, notification_type):
        """Show native OS notification as fallback."""
        try:
            if self.system == "Darwin":  # macOS
                self._show_macos_notification(title, message)
            elif self.system == "Windows":
                self._show_windows_notification(title, message)
            elif self.system == "Linux":
                self._show_linux_notification(title, message)
        except Exception:
            logger.exception("Failed to show native notification.")

    def _show_macos_notification(self, title, message):
        """Show macOS notification using osascript."""
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=False)

    def _show_windows_notification(self, title, message):
        """Show Windows notification via system tray (no additional library required on Windows)."""
        # Windows system-tray balloon tooltips are handled by QSystemTrayIcon.showMessage(),
        # which is called in show_notification(). No extra work needed on this platform.

    def _show_linux_notification(self, title, message):
        """Show Linux notification using notify-send."""
        subprocess.run(["notify-send", title, message], check=False)

    # Convenience methods for common notification types

    def notify_harvest_started(self, isbn_count):
        """Show an info notification indicating a harvest has begun.

        Args:
            isbn_count: Number of ISBNs queued for the run.
        """
        self.show_notification(
            "Harvest Started",
            f"Processing {isbn_count} ISBNs...",
            "info"
        )

    def notify_harvest_completed(self, stats):
        """Show a success notification summarising the completed harvest run.

        Args:
            stats: Dict containing at least ``found``, ``failed``, and ``total``
                integer counts from the harvest result.
        """
        found = stats.get('found', 0)
        failed = stats.get('failed', 0)
        total = stats.get('total', 0)

        message = f"✓ Found: {found}\n✗ Failed: {failed}\n━ Total: {total}"

        self.show_notification(
            "Harvest Complete!",
            message,
            "success",
            duration=8000
        )

    def notify_harvest_error(self, error_message):
        """Show an error dialog for a fatal harvest failure.

        Args:
            error_message: Human-readable description of the error.
        """
        self.show_notification(
            "Harvest Error",
            f"An error occurred: {error_message}",
            "error",
            duration=10000
        )

    def notify_milestone(self, milestone_type, value):
        """Milestone notifications are intentionally suppressed (disabled by client request)."""

    def notify_isbn_found(self, isbn, lccn):
        """Show a brief success notification for a single ISBN-to-LCCN resolution.

        Intended for interactive use; callers should suppress this during
        bulk runs to avoid notification spam.

        Args:
            isbn: The ISBN that was looked up.
            lccn: The LCCN that was resolved.
        """
        self.show_notification(
            "LCCN Found",
            f"ISBN {isbn}\n→ {lccn}",
            "success",
            duration=2000
        )

    def notify_cache_hit(self, count):
        """Show an info notification reporting the number of cache hits.

        Args:
            count: Number of results served from the local cache.
        """
        self.show_notification(
            "Cache Hit",
            f"⚡ {count} results loaded from cache",
            "info",
            duration=2000
        )

    def notify_api_error(self, api_name, error):
        """Show a warning notification for a recoverable API failure.

        Args:
            api_name: Display name of the API target that failed.
            error: Short error description or exception message.
        """
        self.show_notification(
            f"{api_name} Error",
            f"API temporarily unavailable: {error}",
            "warning",
            duration=5000
        )

    def notify_export_complete(self, filename, record_count):
        """Show a success notification confirming a data export finished.

        Args:
            filename: Path or name of the exported file.
            record_count: Number of records written to the file.
        """
        self.show_notification(
            "Export Complete",
            f"✓ Exported {record_count} records\n→ {filename}",
            "success",
            duration=5000
        )


class NotificationPreferences:
    """Persist and retrieve per-user notification preferences.

    Preferences are stored as JSON in ``data/notification_prefs.json``.  If the
    file is absent or unreadable the hard-coded defaults are used instead.
    """

    def __init__(self):
        """Initialise and load preferences from disk, falling back to defaults."""
        self.preferences_file = Path("data/notification_prefs.json")
        self.prefs = self._load_preferences()

    def _load_preferences(self):
        """Load preferences from disk, merging over hard-coded defaults.

        Returns:
            A dict of preference keys with their current or default values.
        """
        import json  # Imported locally to avoid a module-level dependency

        defaults = {
            "enabled": True,
            "show_milestones": True,
            "show_individual_finds": False,  # Disabled by default for bulk
            "show_cache_hits": False,
            "show_api_errors": True,
            "sound_enabled": False,
            "min_duration": 2000,
            "max_duration": 10000
        }

        try:
            if self.preferences_file.exists():
                with open(self.preferences_file) as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
        except Exception:
            pass

        return defaults

    def save_preferences(self):
        """Persist the current in-memory preferences dict to the JSON file."""
        import json  # Imported locally to avoid a module-level dependency

        try:
            self.preferences_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.preferences_file, 'w') as f:
                json.dump(self.prefs, f, indent=2)
        except Exception:
            logger.exception("Failed to save notification preferences.")

    def set_preference(self, key, value):
        """Update a single preference and immediately persist the change.

        Args:
            key: The preference key to update.
            value: The new value to store.
        """
        self.prefs[key] = value
        self.save_preferences()

    def get_preference(self, key, default=None):
        """Return the value for *key*, or *default* if it is not set.

        Args:
            key: The preference key to look up.
            default: Fallback value returned when the key is absent.

        Returns:
            The stored preference value, or *default*.
        """
        return self.prefs.get(key, default)
