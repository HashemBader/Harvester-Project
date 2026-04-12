"""
File-system path resolver for the LCCN Harvester.

Abstracts the difference between a development checkout (where the project
root is both the bundle root and the writable data directory) and a frozen
PyInstaller build (where read-only bundled resources live under
``sys._MEIPASS`` and writable user data lives in a platform-specific
application-support folder).

Public API:
    get_bundle_root()         -- Root of read-only bundled resources.
    get_user_data_dir()       -- Writable directory for config, DB, exports.
    get_app_root()            -- Alias for ``get_user_data_dir()``.
    ensure_user_data_setup()  -- Sync bundled defaults into user data (frozen only).

Path layout (frozen build):
    macOS:   ~/Library/Application Support/LCCN Harvester/
    Windows: %APPDATA%/LCCN Harvester/
    Linux:   ~/.lccn_harvester/

Path layout (development):
    Both ``get_bundle_root()`` and ``get_app_root()`` return the project root
    (two levels above ``src/config/``).
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

# Detect whether the app is running as a frozen PyInstaller executable
# True = frozen executable, False = development/script mode
_IS_FROZEN: bool = getattr(sys, "frozen", False)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_bundle_root() -> Path:
    """Return the root directory that contains *read-only* bundled resources.

    * Frozen : ``sys._MEIPASS`` (the extraction temp-dir)
    * Dev    : project root (two levels above this file's ``src/config/``)
    """
    if _IS_FROZEN:
        # Frozen app: read-only resources are in the PyInstaller temp directory
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # Development mode: project root is two levels up from src/config/app_paths.py
    return Path(__file__).resolve().parent.parent.parent


def _find_local_workspace_root() -> Path | None:
    """Detect a developer-local frozen build running inside the project workspace.

    When the packaged app is launched from ``<project>/dist/...``, we want it
    to behave exactly like running ``src/gui_launcher.py`` directly and reuse
    the project's live ``config/`` and ``data/`` files instead of copying
    defaults into a separate app-support folder.

    Detection strategy: walk the executable's ancestor directories looking for
    the sentinel file ``src/gui_launcher.py``.

    Returns:
        The project root ``Path``, or ``None`` if not running inside a workspace.
    """
    if not _IS_FROZEN:
        # Only applies to frozen builds; dev mode always uses project root
        return None

    # Get the path to the running executable
    executable = Path(sys.executable).resolve()
    # Walk up the directory tree until we find the project root sentinel
    for candidate in executable.parents:
        if (candidate / "src" / "gui_launcher.py").exists():
            return candidate
    # Not running inside the project workspace
    return None


def get_user_data_dir() -> Path:
    """Return a *writable* directory for user data (config, output, settings).

    The directory is created if it does not exist.
    """
    if _IS_FROZEN:
        # Check if this is a developer local build running from the project
        workspace_root = _find_local_workspace_root()
        if workspace_root is not None:
            # Use the project root for consistency with development mode
            return workspace_root

        # Frozen build outside the project: use platform-specific app-support folders
        system = platform.system()
        if system == "Darwin":
            # macOS: ~/Library/Application Support/LCCN Harvester/
            base = Path.home() / "Library" / "Application Support" / "LCCN Harvester"
        elif system == "Windows":
            # Windows: %APPDATA%/LCCN Harvester/
            appdata = os.environ.get("APPDATA") or str(Path.home())
            base = Path(appdata) / "LCCN Harvester"
        else:
            # Linux and other Unix-like systems: ~/.lccn_harvester/
            base = Path.home() / ".lccn_harvester"
        # Create the directory if it doesn't exist
        base.mkdir(parents=True, exist_ok=True)
        return base
    # In development the project root *is* the user-data dir
    return get_bundle_root()


def get_app_root() -> Path:
    """Convenience alias: the writable root expected by ProfileManager, ThemeManager, etc."""
    # Simply delegate to the user data directory for convenience
    return get_user_data_dir()


def _sync_bundle_entry(src: Path, dst: Path) -> None:
    """Copy a bundled file or directory into user data, overwriting managed defaults.

    This keeps packaged builds aligned with the current shipped app defaults while
    still allowing user-generated files outside the managed set to persist.
    """
    # Do nothing if the source doesn't exist
    if not src.exists():
        return
    # Handle directory copy
    if src.is_dir():
        # Copy entire directory structure, allowing existing dirs to be merged
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        return
    # For file: ensure parent directory exists, then copy the file
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))


def _replace_bundle_directory(src: Path, dst: Path) -> None:
    """Replace a managed directory entirely with the bundled version."""
    # Delete the old directory completely
    if dst.exists():
        shutil.rmtree(dst)
    # Copy the new version from the bundle (or create empty if source missing)
    if not src.exists():
        dst.mkdir(parents=True, exist_ok=True)
        return
    shutil.copytree(str(src), str(dst))


def ensure_user_data_setup() -> None:
    """Sync bundled defaults into writable user data for frozen builds.

    Managed defaults are refreshed from the application bundle so the packaged
    app stays in step with the currently built version instead of remaining
    stuck on whatever an older sprint copied into the user's data directory.
    User-created outputs such as databases and exports are left alone.
    """
    if not _IS_FROZEN:
        # Development mode: no need to sync, project root is used directly
        return

    # A bundle launched directly from this repository's ``dist/`` folder should
    # share the same writable files as ``gui_launcher.py`` for exact parity
    # during local testing and review.
    if _find_local_workspace_root() is not None:
        return

    # Get the paths to the bundle and user directories
    bundle_root = get_bundle_root()
    user_dir = get_user_data_dir()

    # These entries are always overwritten from the bundle so the packaged app
    # stays in sync with the currently shipped defaults.  User-generated files
    # (databases, export outputs) are intentionally absent from this list.
    # Each tuple is (source_in_bundle, destination_in_user_dir)
    managed_entries = (
        ("config/active_profile.txt", "config/active_profile.txt"),
        ("config/default_profile.json", "config/default_profile.json"),
        ("data/gui_settings.json", "data/gui_settings.json"),
        ("data/targets.json", "data/targets.json"),
        ("data/targets.tsv", "data/targets.tsv"),
        ("data/sample", "data/sample"),
    )

    # Sync each managed entry from the bundle to user data
    for bundle_rel, user_rel in managed_entries:
        _sync_bundle_entry(bundle_root / bundle_rel, user_dir / user_rel)

    # Profiles directory is fully replaced (not merged) so profiles removed
    # from the bundle do not linger in the user's data directory across rebuilds.
    _replace_bundle_directory(bundle_root / "config/profiles", user_dir / "config/profiles")

    # Ensure the data directory exists for new installs before the DB is created
    (user_dir / "data").mkdir(parents=True, exist_ok=True)
