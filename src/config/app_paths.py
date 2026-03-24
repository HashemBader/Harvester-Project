"""
Module: app_paths.py
Resolves file-system paths for both development and frozen (PyInstaller) builds.

Usage
-----
    from config.app_paths import get_app_root, get_bundle_root, ensure_user_data_setup

In development
    get_bundle_root()  -> project root   (read-only resources live here)
    get_app_root()     -> project root   (writable data also lives here)

When frozen (PyInstaller)
    get_bundle_root()  -> sys._MEIPASS   (read-only bundled resources)
    get_app_root()     -> platform user-data dir  (writable)
                          macOS:   ~/Library/Application Support/LCCN Harvester/
                          Windows: %APPDATA%/LCCN Harvester/
                          Linux:   ~/.lccn_harvester/
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

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
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # src/config/app_paths.py  → parent = config, parent.parent = src, .parent = project root
    return Path(__file__).resolve().parent.parent.parent


def _find_local_workspace_root() -> Path | None:
    """Detect a developer-local frozen build inside the project workspace.

    When the packaged app is launched from ``<project>/dist/...``, we want it to
    behave exactly like ``src/gui_launcher.py`` and reuse the project's live
    ``config/`` and ``data/`` files instead of a separate app-support folder.
    """
    if not _IS_FROZEN:
        return None

    executable = Path(sys.executable).resolve()
    for candidate in executable.parents:
        if (candidate / "src" / "gui_launcher.py").exists():
            return candidate
    return None


def get_user_data_dir() -> Path:
    """Return a *writable* directory for user data (config, output, settings).

    The directory is created if it does not exist.
    """
    if _IS_FROZEN:
        workspace_root = _find_local_workspace_root()
        if workspace_root is not None:
            return workspace_root

        system = platform.system()
        if system == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "LCCN Harvester"
        elif system == "Windows":
            appdata = os.environ.get("APPDATA") or str(Path.home())
            base = Path(appdata) / "LCCN Harvester"
        else:
            base = Path.home() / ".lccn_harvester"
        base.mkdir(parents=True, exist_ok=True)
        return base
    # In development the project root *is* the user-data dir
    return get_bundle_root()


def get_app_root() -> Path:
    """Convenience alias: the writable root expected by ProfileManager, ThemeManager, etc."""
    return get_user_data_dir()


def _sync_bundle_entry(src: Path, dst: Path) -> None:
    """Copy a bundled file or directory into user data, overwriting managed defaults.

    This keeps packaged builds aligned with the current shipped app defaults while
    still allowing user-generated files outside the managed set to persist.
    """
    if not src.exists():
        return
    if src.is_dir():
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))


def _replace_bundle_directory(src: Path, dst: Path) -> None:
    """Replace a managed directory entirely with the bundled version."""
    if dst.exists():
        shutil.rmtree(dst)
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
        return

    # A bundle launched directly from this repository's ``dist/`` folder should
    # share the same writable files as ``gui_launcher.py`` for exact parity
    # during local testing and review.
    if _find_local_workspace_root() is not None:
        return

    bundle_root = get_bundle_root()
    user_dir = get_user_data_dir()

    managed_entries = (
        ("config/active_profile.txt", "config/active_profile.txt"),
        ("config/default_profile.json", "config/default_profile.json"),
        ("data/gui_settings.json", "data/gui_settings.json"),
        ("data/targets.json", "data/targets.json"),
        ("data/targets.tsv", "data/targets.tsv"),
        ("data/sample", "data/sample"),
    )

    for bundle_rel, user_rel in managed_entries:
        _sync_bundle_entry(bundle_root / bundle_rel, user_dir / user_rel)

    # Profiles are app-managed defaults; replace the whole directory so removed
    # bundled profiles do not linger in user data across rebuilds.
    _replace_bundle_directory(bundle_root / "config/profiles", user_dir / "config/profiles")

    (user_dir / "data").mkdir(parents=True, exist_ok=True)
