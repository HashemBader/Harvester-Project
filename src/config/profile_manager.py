"""
Configuration profile manager for the LCCN Harvester.

A "profile" is a named collection of harvest settings (targets, retry
options, timeouts, etc.) stored as a JSON file under
``config/profiles/<slug>/<slug>.json``.  Every installation always has a
built-in "Default Settings" profile stored at ``config/default_profile.json``.

File-system layout
------------------
  config/
    active_profile.txt          -- plain-text file storing the active profile name
    default_profile.json        -- the built-in "Default Settings" profile
    profiles/
      <slug>/
        <slug>.json             -- profile settings
        <slug>_targets.tsv      -- per-profile override of harvest targets
  data/
    lccn_harvester.sqlite3      -- single shared database (all profiles share it)
    <slug>/                     -- per-profile output/exports folder

Migration notes
---------------
Older versions stored each profile's results in a separate SQLite database
(``data/<slug>/lccn_harvester.sqlite3``).  ``_merge_legacy_profile_db_into_shared``
performs a one-time best-effort migration the first time such a profile is
accessed, then writes a marker file so the merge is never repeated.

Profile JSON keys
-----------------
  profile_name   (str)  -- display name
  description    (str)  -- optional freeform description
  created_at     (str)  -- ISO-8601 creation timestamp
  last_modified  (str)  -- ISO-8601 last-save timestamp (optional)
  settings       (dict) -- arbitrary settings dict consumed by the UI/harvester
"""
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime


class ProfileManager:
    """Read/write access to named configuration profiles.

    Responsibilities:
      - Enumerate, load, save, rename, and delete profiles.
      - Resolve the correct file-system paths (DB, targets TSV, exports dir)
        for any given profile name.
      - Perform one-time migration of legacy per-profile databases into the
        shared database on first access.
      - Track which profile is currently active via ``active_profile.txt``.
    """

    def __init__(self):
        # Import app_paths dynamically to get the application root
        from config.app_paths import get_app_root
        # Root application directory (config, data, etc. are under this)
        self.app_root = get_app_root()
        # Directory containing all user-created profiles
        self.profiles_dir = self.app_root / "config" / "profiles"
        # Ensure profiles directory exists
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        # Path to the built-in default profile
        self.default_profile_path = self.app_root / "config" / "default_profile.json"
        # Path to the file tracking which profile is currently active
        self.active_profile_path = self.app_root / "config" / "active_profile.txt"
        # Path to the default targets TSV file
        self.default_targets_path = self.app_root / "data" / "targets.tsv"
        # Path to the single shared database used by all profiles
        self.shared_db_path = self.app_root / "data" / "lccn_harvester.sqlite3"

        # Ensure default profile exists (create if missing)
        if not self.default_profile_path.exists():
            self._create_default_profile()

    def _create_default_profile(self):
        """Create the built-in default profile."""
        # Define the factory default settings with standard targets and options
        default_settings = {
            # Display name for the default profile
            "profile_name": "Default Settings",
            # ISO timestamp of when this profile was created
            "created_at": datetime.now().isoformat(),
            # Description of the profile
            "description": "Factory default configuration",
            # Configuration settings dictionary
            "settings": {
                # List of API sources/targets to query
                "targets": [
                    {"name": "Library of Congress", "enabled": True, "priority": 1},
                    {"name": "Harvard LibraryCloud", "enabled": True, "priority": 2},
                    {"name": "OpenLibrary", "enabled": True, "priority": 3}
                ],
                # Settings for harvest behavior
                "harvest_options": {
                    "stop_on_first_result": True,  # Stop searching if first source succeeds
                    "use_cache": True,              # Use cached results
                    "retry_failed": True,           # Retry failed ISBN lookups
                    "max_retries": 3,               # Maximum retry attempts
                    "retry_delay": 5                # Delay between retries in seconds
                },
                # Advanced/tuning settings
                "advanced_options": {
                    "timeout": 30,                  # Network request timeout in seconds
                    "concurrent_requests": 5,       # Number of concurrent API requests
                    "rate_limit": 10                # Requests per second limit
                }
            }
        }

        # Write the default profile to disk as JSON
        with open(self.default_profile_path, 'w') as f:
            json.dump(default_settings, f, indent=2)

    def _profile_slug(self, name: str) -> str:
        """Return the sanitized folder/filename slug for a profile name."""
        # Convert to lowercase and replace spaces/slashes with underscores
        return name.lower().replace(" ", "_").replace("/", "_")

    def get_profile_dir(self, name: str) -> Path:
        """Return the Path to the profile's dedicated config folder.

        ``config/profiles/<slug>/``
        """
        # Return the directory path for this profile's configuration
        return self.profiles_dir / self._profile_slug(name)

    def get_profile_data_dir(self, name: str) -> Path:
        """Return the Path to the profile's dedicated data/exports folder.

        ``data/<slug>/``
        """
        # Return the directory path for this profile's data and exports
        return self.app_root / "data" / self._profile_slug(name)

    def _legacy_profile_db_path(self, name: str) -> Path:
        """Return the older per-profile database path used before the shared-DB decision."""
        # Older versions stored each profile's database separately
        return self.get_profile_data_dir(name) / "lccn_harvester.sqlite3"

    def _legacy_db_merge_marker(self, name: str) -> Path:
        """Marker file showing a legacy profile DB has already been merged into the shared DB."""
        # This file indicates the legacy database has been migrated
        return self.get_profile_data_dir(name) / ".shared_db_merged"

    def _merge_legacy_profile_db_into_shared(self, name: str) -> None:
        """Perform a one-time best-effort migration of a per-profile DB into the shared DB.

        Older versions of the app stored each profile's results in its own
        SQLite database at ``data/<slug>/lccn_harvester.sqlite3``.  This method
        reads that file, merges its ``main``, ``attempted``, and
        ``linked_isbns`` tables into the current shared DB, then writes a
        marker file so the merge is never repeated.

        The migration uses ``ON CONFLICT DO UPDATE`` semantics that prefer the
        more recently modified row so data from both databases is preserved
        without duplicates.  Any error during the migration is silently ignored
        (best-effort) so a corrupt legacy DB does not block the user.

        Args:
            name: Profile display name.  ``"Default Settings"`` is skipped
                  because it never had a separate per-profile database.
        """
        # Skip default profile (it never had separate per-profile databases)
        if name == "Default Settings":
            return

        # Determine the legacy database path and migration marker location
        source_db = self._legacy_profile_db_path(name)
        marker_path = self._legacy_db_merge_marker(name)

        # Skip if the legacy DB never existed or has already been merged
        if not source_db.exists() or marker_path.exists():
            return

        shared_db = self.shared_db_path
        # Guard: if both paths resolve to the same file there is nothing to merge
        if source_db.resolve() == shared_db.resolve():
            return

        # Import the database manager
        try:
            from database import DatabaseManager
        except ImportError:
            from src.database import DatabaseManager

        # Ensure both databases are initialized with proper schema (if missing)
        DatabaseManager(shared_db).init_db()
        DatabaseManager(source_db).init_db()

        # Helper to check if a table exists in the attached legacy database
        def _legacy_has_table(conn: sqlite3.Connection, table_name: str) -> bool:
            # Query sqlite_master in the legacy database for the table name
            row = conn.execute(
                "SELECT 1 FROM legacy.sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
                (table_name,),
            ).fetchone()
            return row is not None

        # Connect to the shared database and perform the migration
        with sqlite3.connect(shared_db) as conn:
            # Enable foreign key constraints for data integrity
            conn.execute("PRAGMA foreign_keys = ON")
            # ATTACH the legacy database so we can reference it in SQL statements
            conn.execute("ATTACH DATABASE ? AS legacy", (str(source_db),))
            try:
                # --- Migration Phase 1: main table (call numbers and classifications) ---
                if _legacy_has_table(conn, "main"):
                    # Read all rows from the legacy main table
                    main_rows = conn.execute(
                        """
                        SELECT isbn, call_number, call_number_type, classification, COALESCE(source, ''), date_added
                        FROM legacy.main
                        """
                    ).fetchall()
                    # Insert into shared database using conflict resolution (prefer newer data)
                    conn.executemany(
                        """
                        INSERT INTO main (isbn, call_number, call_number_type, classification, source, date_added)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(isbn, call_number_type, source) DO UPDATE SET
                            call_number = CASE
                                WHEN excluded.date_added >= main.date_added THEN excluded.call_number
                                ELSE main.call_number
                            END,
                            classification = CASE
                                WHEN excluded.date_added >= main.date_added THEN excluded.classification
                                ELSE main.classification
                            END,
                            source = CASE
                                WHEN excluded.date_added >= main.date_added THEN excluded.source
                                ELSE main.source
                            END,
                            date_added = CASE
                                WHEN excluded.date_added >= main.date_added THEN excluded.date_added
                                ELSE main.date_added
                            END
                        """,
                        main_rows,
                    )

                # --- Migration Phase 2: attempted table (failure tracking) ---
                if _legacy_has_table(conn, "attempted"):
                    # Read all rows from the legacy attempted table (failed lookups)
                    attempted_rows = conn.execute(
                        """
                        SELECT isbn, last_target, attempt_type, last_attempted, fail_count, last_error
                        FROM legacy.attempted
                        """
                    ).fetchall()
                    # Insert into shared database using conflict resolution
                    # (keep the more recent failure record)
                    conn.executemany(
                        """
                        INSERT INTO attempted (isbn, last_target, attempt_type, last_attempted, fail_count, last_error)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(isbn, last_target, attempt_type) DO UPDATE SET
                            last_attempted = CASE
                                WHEN excluded.last_attempted >= attempted.last_attempted THEN excluded.last_attempted
                                ELSE attempted.last_attempted
                            END,
                            fail_count = CASE
                                WHEN excluded.fail_count >= attempted.fail_count THEN excluded.fail_count
                                ELSE attempted.fail_count
                            END,
                            last_error = CASE
                                WHEN excluded.last_attempted >= attempted.last_attempted THEN excluded.last_error
                                ELSE attempted.last_error
                            END
                        """,
                        attempted_rows,
                    )

                # --- Migration Phase 3: linked_isbns table (ISBN equivalence) ---
                if _legacy_has_table(conn, "linked_isbns"):
                    # Read all rows from the legacy linked_isbns table
                    linked_rows = conn.execute(
                        """
                        SELECT lowest_isbn, other_isbn
                        FROM legacy.linked_isbns
                        """
                    ).fetchall()
                    # Insert into shared database, using lowest_isbn as the canonical form
                    conn.executemany(
                        """
                        INSERT INTO linked_isbns (lowest_isbn, other_isbn)
                        VALUES (?, ?)
                        ON CONFLICT(other_isbn) DO UPDATE SET
                            lowest_isbn = excluded.lowest_isbn
                        """,
                        linked_rows,
                    )
            finally:
                # Commit all migrations to the shared database
                conn.commit()

        # Write a marker file so we never attempt this migration again
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        # Write an ISO timestamp into the marker file so it's clear when the merge happened
        marker_path.write_text(datetime.now().isoformat(), encoding="utf-8")

    def get_db_path(self, name: str) -> Path:
        """Return the single shared SQLite database path used by every profile."""
        # Ensure the database directory exists
        self.shared_db_path.parent.mkdir(parents=True, exist_ok=True)
        # Perform one-time migration of legacy per-profile database if needed
        self._merge_legacy_profile_db_into_shared(name)
        # Return the path to the shared database
        return self.shared_db_path

    def get_targets_file(self, name: str) -> Path:
        """Return the Path to the targets TSV file for the given profile.

        "Default Settings" uses the shared ``data/targets.tsv``.
        User profiles use ``config/profiles/<slug>/targets.tsv``.
        Falls back to the legacy flat location if the new one doesn't exist yet.
        """
        # Default profile uses the shared targets file
        if name == "Default Settings":
            return self.default_targets_path
        # User profiles use their own targets file in the new location
        slug = self._profile_slug(name)
        new_path = self.profiles_dir / slug / f"{slug}_targets.tsv"
        if new_path.exists():
            return new_path
        # Legacy flat location (backward compat)
        legacy_path = self.profiles_dir / f"{slug}_targets.tsv"
        if legacy_path.exists():
            return legacy_path
        # Default to new location even if it doesn't exist yet
        return new_path

    def _normalize_profile_name(self, name: str) -> str:
        """Collapse whitespace and casefold *name* for case-insensitive comparisons.

        Uses ``str.split()`` (which splits on any whitespace) followed by
        ``" ".join(...)`` to normalise irregular spacing, then ``casefold()``
        for locale-aware case folding.
        """
        # Normalize whitespace and convert to lowercase for comparison
        return " ".join((name or "").split()).strip().casefold()

    def list_profiles(self) -> List[str]:
        """Return all available profile names, with ``"Default Settings"`` always first.

        The list is deduplicated case-insensitively to prevent the same profile
        appearing twice when a new-style subdir JSON and a legacy flat JSON
        coexist for the same profile.

        Returns:
            An ordered list of profile display names.  ``"Default Settings"``
            is always the first element.
        """
        # Always include the built-in default profile first
        profiles = ["Default Settings"]
        # Track normalized names to detect duplicates (case-insensitive)
        seen = {self._normalize_profile_name("Default Settings")}

        # Glob new-style subdirectory JSONs first (higher priority), then legacy flat JSONs.
        # Sorting ensures a deterministic order within each tier.
        candidate_files = sorted(self.profiles_dir.glob("*/*.json")) + sorted(self.profiles_dir.glob("*.json"))

        # Load and deduplicate profile names
        for file in candidate_files:
            try:
                with open(file) as f:
                    data = json.load(f)
                    # Get the display name from the profile or use filename
                    profile_name = data.get("profile_name", file.stem)
                    # Normalize for case-insensitive comparison
                    norm = self._normalize_profile_name(profile_name)
                    # Skip empty names or duplicates
                    if not norm or norm in seen:
                        continue
                    # Add to seen set and results list
                    seen.add(norm)
                    profiles.append(profile_name)
            except Exception:
                # Skip corrupted profiles silently
                continue

        return profiles

    def load_profile(self, name: str) -> Optional[Dict]:
        """Load and return the full profile dict for *name*, or ``None`` if not found.

        Search order: new-style subdir JSON → legacy flat JSON in profiles dir.
        The match is case-insensitive via ``_normalize_profile_name``.
        """
        # Special case: load default profile from its dedicated location
        if name == "Default Settings":
            return self._load_json(self.default_profile_path)

        # Normalize the target name for case-insensitive matching
        normalized_target = self._normalize_profile_name(name)

        # Try new-style location first: config/profiles/<slug>/<slug>.json
        slug = self._profile_slug(name)
        new_path = self.profiles_dir / slug / f"{slug}.json"
        if new_path.exists():
            try:
                data = self._load_json(new_path)
                # Verify the profile name matches (case-insensitive)
                if self._normalize_profile_name(data.get("profile_name", "")) == normalized_target:
                    return data
            except Exception:
                pass

        # Fall back to legacy flat files: config/profiles/*.json
        for file in self.profiles_dir.glob("*.json"):
            try:
                data = self._load_json(file)
                # Verify the profile name matches
                if self._normalize_profile_name(data.get("profile_name", "")) == normalized_target:
                    return data
            except Exception:
                continue

        # Profile not found
        return None

    def profile_name_exists(self, name: str, exclude_name: Optional[str] = None) -> bool:
        """Return True if a profile name already exists (case-insensitive)."""
        # Normalize both the search name and optional exclusion name
        normalized_name = self._normalize_profile_name(name)
        normalized_exclude = self._normalize_profile_name(exclude_name or "")
        # Empty names don't exist
        if not normalized_name:
            return False
        # Check all profiles, skipping the exclusion if provided
        for profile_name in self.list_profiles():
            norm = self._normalize_profile_name(profile_name)
            # Skip the excluded profile (useful for rename checks)
            if norm == normalized_exclude:
                continue
            # Found a match
            if norm == normalized_name:
                return True
        return False

    def save_profile(self, name: str, settings: Dict, description: str = ""):
        """Persist *settings* as a named profile and seed companion files.

        If the profile JSON already exists it is updated in-place (preserving
        ``created_at``).  On first creation, the profile's targets TSV is
        seeded from the default targets file and the data/exports directory is
        created.

        Args:
            name:        Display name for the profile.
            settings:    Arbitrary settings dict to store.
            description: Optional freeform description.

        Returns:
            ``True`` on success.
        """
        # Derive the slug from the profile name
        slug = self._profile_slug(name)

        # Ensure the profile's own config subdirectory exists
        profile_dir = self.get_profile_dir(name)
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Path to the profile JSON file
        file_path = profile_dir / f"{slug}.json"

        # Load existing or create new profile data
        if file_path.exists():
            try:
                # Update existing profile, preserving created_at
                profile_data = self._load_json(file_path)
                profile_data["last_modified"] = datetime.now().isoformat()
                profile_data["settings"] = settings
                if description:
                    profile_data["description"] = description
            except Exception:
                # If loading fails, create new
                profile_data = self._create_profile_data(name, settings, description)
        else:
            # New profile
            profile_data = self._create_profile_data(name, settings, description)

        # Write the profile JSON
        with open(file_path, 'w') as f:
            json.dump(profile_data, f, indent=2)

        # On first creation, seed a profile-specific targets file from the default.
        targets_file = self.get_targets_file(name)
        if not targets_file.exists() and self.default_targets_path.exists():
            targets_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.default_targets_path, targets_file)

        # Ensure the profile's data/exports directory exists
        data_dir = self.get_profile_data_dir(name)
        data_dir.mkdir(parents=True, exist_ok=True)

        return True

    def update_profile_settings(self, name: str, updates: Dict) -> bool:
        """Merge *updates* into the ``settings`` dict of *name*, creating the profile if needed.

        Args:
            name:    Profile to update (including "Default Settings").
            updates: Key/value pairs to merge into the existing settings dict.

        Returns:
            ``True`` on success.

        Raises:
            TypeError: If *updates* is not a dict.
        """
        # Validate that updates is a dictionary
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dictionary")

        # Handle the default profile
        if name == "Default Settings":
            file_path = self.default_profile_path
            # Load existing or create new default profile
            profile_data = self._load_json(file_path) if file_path.exists() else self._create_profile_data(name, {}, "")
        else:
            # User profiles use the new-style location
            slug = self._profile_slug(name)
            profile_dir = self.get_profile_dir(name)
            profile_dir.mkdir(parents=True, exist_ok=True)
            file_path = profile_dir / f"{slug}.json"
            # Try the new location first, then check if profile exists elsewhere
            if file_path.exists():
                profile_data = self._load_json(file_path)
            else:
                loaded = self.load_profile(name)
                profile_data = loaded if loaded else self._create_profile_data(name, {}, "")

        # Get the existing settings dict
        settings = profile_data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
        # Merge the updates into settings
        settings.update(updates)
        # Update the profile data with new settings
        profile_data["settings"] = settings
        profile_data["profile_name"] = name
        profile_data["last_modified"] = datetime.now().isoformat()

        # Write the updated profile back to disk
        with open(file_path, 'w') as f:
            json.dump(profile_data, f, indent=2)

        return True

    def get_profile_setting(self, name: str, key: str, default=None):
        """Return a single profile setting value."""
        # Load the profile by name
        profile = self.load_profile(name)
        if not profile:
            # Profile not found, return default
            return default
        # Get the settings dict
        settings = profile.get("settings", {})
        if not isinstance(settings, dict):
            # Settings field is malformed, return default
            return default
        # Return the specific key value or default
        return settings.get(key, default)

    def set_active_profile_setting(self, key: str, value) -> bool:
        """Persist a single setting into the currently active profile."""
        # Update the active profile's settings with a single key-value pair
        return self.update_profile_settings(self.get_active_profile(), {key: value})

    def get_active_profile_setting(self, key: str, default=None):
        """Read a single setting from the currently active profile."""
        # Get a setting from the currently active profile
        return self.get_profile_setting(self.get_active_profile(), key, default)

    def _create_profile_data(self, name: str, settings: Dict, description: str) -> Dict:
        """Create new profile data structure."""
        # Build a new profile dictionary with metadata and settings
        return {
            "profile_name": name,
            "created_at": datetime.now().isoformat(),
            "description": description,
            "settings": settings
        }

    def delete_profile(self, name: str) -> bool:
        """Delete *name* from disk, including legacy flat files.

        The profile's data/exports directory is intentionally preserved so
        previously exported files are not lost.

        Args:
            name: Profile to delete.  ``"Default Settings"`` cannot be deleted.

        Returns:
            ``True`` if anything was deleted, ``False`` if the profile was not
            found or is the built-in default.
        """
        # Default profile cannot be deleted
        if name == "Default Settings":
            return False

        deleted = False

        # Remove new-style profile subdirectory if it exists
        profile_dir = self.get_profile_dir(name)
        if profile_dir.exists():
            shutil.rmtree(profile_dir)
            deleted = True

        # Also clean up any legacy flat files for this profile
        for file in list(self.profiles_dir.glob("*.json")):
            try:
                data = self._load_json(file)
                # Check if this is a profile with the target name
                if data.get("profile_name") == name:
                    file.unlink()
                    deleted = True
                    break
            except Exception:
                continue

        # Remove legacy flat targets TSV if present
        slug = self._profile_slug(name)
        legacy_targets = self.profiles_dir / f"{slug}_targets.tsv"
        if legacy_targets.exists():
            legacy_targets.unlink()

        # Note: the data/exports directory (get_profile_data_dir) is intentionally
        # preserved so previously exported files are not lost.

        return deleted

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename *old_name* to *new_name*, updating all companion files on disk.

        Operations performed:
          1. Rename (or copy-merge) the config subdirectory.
          2. Rename the JSON file inside to match the new slug.
          3. Remove any legacy flat JSON file for the old name.
          4. Rename the data/exports directory if it exists.
          5. Write the updated profile JSON with the new display name.

        Args:
            old_name: Current profile display name.
            new_name: Desired new display name.

        Returns:
            ``True`` on success, ``False`` if the profile was not found or is
            the built-in default.
        """
        # Default profile cannot be renamed
        if old_name == "Default Settings":
            return False

        # Load old profile to verify it exists
        profile_data = self.load_profile(old_name)
        if not profile_data:
            return False

        # Generate slugs from both names
        old_slug = self._profile_slug(old_name)
        new_slug = self._profile_slug(new_name)

        # --- Rename config folder (new-style) ---
        old_profile_dir = self.get_profile_dir(old_name)
        new_profile_dir = self.get_profile_dir(new_name)

        if old_profile_dir.exists():
            if not new_profile_dir.exists():
                # Simple case: target dir doesn't exist, just rename
                old_profile_dir.rename(new_profile_dir)
            else:
                # Target dir already exists; copy contents and remove old
                for item in old_profile_dir.iterdir():
                    dest = new_profile_dir / item.name
                    if not dest.exists():
                        item.rename(dest)
                shutil.rmtree(old_profile_dir)

            # Rename the JSON file inside the new dir to match new slug
            old_json = new_profile_dir / f"{old_slug}.json"
            new_json = new_profile_dir / f"{new_slug}.json"
            if old_json.exists() and not new_json.exists():
                old_json.rename(new_json)
        else:
            # Legacy flat targets file: move to new location
            old_targets = self.profiles_dir / f"{old_slug}_targets.tsv"
            new_targets_dir = new_profile_dir
            new_targets_dir.mkdir(parents=True, exist_ok=True)
            new_targets_path = new_targets_dir / f"{new_slug}_targets.tsv"
            if old_targets.exists() and not new_targets_path.exists():
                old_targets.rename(new_targets_path)

        # Remove old legacy flat JSON if present
        for file in list(self.profiles_dir.glob("*.json")):
            try:
                data = self._load_json(file)
                # Check if this file contains the old profile
                if data.get("profile_name") == old_name:
                    file.unlink()
                    break
            except Exception:
                continue

        # --- Rename data/exports folder ---
        old_data_dir = self.get_profile_data_dir(old_name)
        new_data_dir = self.get_profile_data_dir(new_name)
        if old_data_dir.exists() and not new_data_dir.exists():
            old_data_dir.rename(new_data_dir)

        # Save updated profile JSON with new name
        new_profile_dir.mkdir(parents=True, exist_ok=True)
        profile_data["profile_name"] = new_name
        profile_data["last_modified"] = datetime.now().isoformat()
        file_path = new_profile_dir / f"{new_slug}.json"
        with open(file_path, 'w') as f:
            json.dump(profile_data, f, indent=2)

        return True

    def get_active_profile(self) -> str:
        """Return the currently active profile name, defaulting to ``"Default Settings"``."""
        # Check if an active profile file exists
        if self.active_profile_path.exists():
            try:
                # Read the active profile name from the file
                return self.active_profile_path.read_text().strip()
            except Exception:
                pass
        # Default to the built-in default if no active profile is set
        return "Default Settings"

    def set_active_profile(self, name: str):
        """Persist *name* as the currently active profile (written to ``active_profile.txt``)."""
        # Write the profile name to the active profile tracking file
        with open(self.active_profile_path, 'w') as f:
            f.write(name)

    def _load_json(self, file_path: Path) -> Dict:
        """Read and JSON-decode *file_path*, returning a dict."""
        # Open the file and parse JSON content
        with open(file_path) as f:
            return json.load(f)

    def get_profile_info(self, name: str) -> Optional[Dict]:
        """Return a lightweight metadata summary for *name*, or ``None`` if not found.

        Returns a dict with keys: ``name``, ``description``, ``created_at``,
        ``last_modified``, ``num_targets``.
        """
        # Load the full profile
        profile = self.load_profile(name)
        if not profile:
            return None

        # Extract and return metadata
        return {
            "name": profile.get("profile_name"),
            "description": profile.get("description", ""),
            "created_at": profile.get("created_at"),
            "last_modified": profile.get("last_modified"),
            "num_targets": len(profile.get("settings", {}).get("targets", [])),
        }
