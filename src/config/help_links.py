"""Configurable Help-page link targets and resolvers.

The constants below are intentionally easy to find and edit:

- Use a normal web URL like ``https://example.com/help`` to open an external page.
- Use ``repo:docs/user_guide.md`` to open the repository-hosted document in the
  browser. When a Git checkout is present, the app derives the current fork and
  branch from ``origin`` and ``HEAD`` so downstream forks point at their own docs.
- Use a plain repo-relative path like ``docs/user_guide.md`` only if you
  explicitly want local-file behaviour.
"""

from __future__ import annotations

import configparser
from pathlib import Path
from urllib.parse import urlparse

from .app_paths import get_app_root, get_bundle_root

# Client-editable Help-page destinations. Use ``repo:...`` to force a browser page.
# Support guidance page link
SUPPORT_GUIDANCE_URL = "repo:docs/README.md"
# User guide documentation link
USER_GUIDE_URL = "repo:docs/user_guide.md"
# Web accessibility statement link
ACCESSIBILITY_STATEMENT_URL = "repo:docs/wcag.md"
# Default repository URL (used if Git is not available)
REPOSITORY_WEB_URL = "https://github.com/HashemBader/LCCN-Harvester-Project"
# Default Git branch (used if current branch cannot be detected)
REPOSITORY_DEFAULT_REF = "main"


def _git_dir_from_root(root: Path) -> Path | None:
    """Return the Git metadata directory for *root*, if available."""
    # Check for .git as a directory (normal repository)
    git_entry = root / ".git"
    if git_entry.is_dir():
        return git_entry
    # Check for .git as a file (worktree, submodule, or linked repository)
    if not git_entry.is_file():
        # Neither a directory nor a file, so not a Git repo
        return None

    # Read the .git file to get the actual metadata directory
    try:
        text = git_entry.read_text(encoding="utf-8").strip()
    except OSError:
        # Cannot read .git file
        return None

    # .git file format: "gitdir: <path>"
    prefix = "gitdir:"
    if not text.lower().startswith(prefix):
        # File doesn't follow expected format
        return None

    # Extract and resolve the path
    raw_path = text[len(prefix):].strip()
    git_dir = Path(raw_path)
    if not git_dir.is_absolute():
        # Relative paths are relative to the repo root
        git_dir = (root / git_dir).resolve()
    return git_dir


def _normalize_repository_web_url(remote_url: str) -> str | None:
    """Convert a Git remote URL into a browser-friendly repository URL."""
    # Clean up whitespace
    remote_url = remote_url.strip()
    if not remote_url:
        return None

    # Handle SSH URLs: git@github.com:user/repo.git
    if remote_url.startswith("git@"):
        host_and_path = remote_url[4:]
        if ":" not in host_and_path:
            # Malformed SSH URL
            return None
        host, repo_path = host_and_path.split(":", 1)
        # Convert to HTTPS URL and remove .git suffix
        return f"https://{host}/{repo_path.removesuffix('.git')}".rstrip("/")

    # Handle standard HTTP/HTTPS URLs
    parsed = urlparse(remote_url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        # Remove .git suffix and trailing slashes
        return remote_url.removesuffix(".git").rstrip("/")

    # Handle SSH URLs with explicit scheme: ssh://user@host/path
    if parsed.scheme == "ssh" and parsed.hostname and parsed.path:
        # Convert to HTTPS URL
        clean_path = parsed.path.lstrip("/").removesuffix(".git")
        return f"https://{parsed.hostname}/{clean_path}".rstrip("/")

    # Unknown or unsupported URL format
    return None


def _detect_repository_web_url() -> str | None:
    """Return the current checkout's browser repository URL, if discoverable."""
    # Get the application root (where .git should be)
    root = get_app_root()
    git_dir = _git_dir_from_root(root)
    if git_dir is None:
        # Not a Git repository
        return None

    # Read the Git config file to get the remote URL
    config_path = git_dir / "config"
    if not config_path.exists():
        return None

    # Parse the Git config file
    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
    except (configparser.Error, OSError):
        # Cannot read or parse config
        return None

    # Extract the URL from the origin remote section
    section = 'remote "origin"'
    if not parser.has_section(section):
        # No origin remote configured
        return None
    # Get the remote URL and normalize it to a browser-friendly format
    remote_url = parser.get(section, "url", fallback="").strip()
    return _normalize_repository_web_url(remote_url)


def _detect_repository_ref() -> str | None:
    """Return the current branch name from Git metadata, if available."""
    # Get the application root (where .git should be)
    root = get_app_root()
    git_dir = _git_dir_from_root(root)
    if git_dir is None:
        # Not a Git repository
        return None

    # Read the HEAD file which contains the current branch reference
    head_path = git_dir / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        # Cannot read HEAD file
        return None

    # HEAD format: "ref: refs/heads/<branch_name>"
    prefix = "ref: refs/heads/"
    if head.startswith(prefix):
        # Extract the branch name from the reference
        return head[len(prefix):]
    # HEAD is in detached state or unrecognized format
    return None


def build_repository_file_url(repo_relative_path: str) -> str:
    """Return a browser URL for a repository-hosted file."""
    # Get the repository URL (either from Git or use the default)
    repo_base = _detect_repository_web_url() or REPOSITORY_WEB_URL
    # Get the current branch name (either from Git or use the default)
    repo_ref = _detect_repository_ref() or REPOSITORY_DEFAULT_REF
    # Construct the raw content URL: https://github.com/owner/repo/blob/branch/path
    clean_path = repo_relative_path.lstrip("/")
    return f"{repo_base}/blob/{repo_ref}/{clean_path}"


def resolve_help_link_target(target: str) -> Path | str | None:
    """Resolve a Help-page target into either a URL string or a local file path."""
    # Check if this is already a full absolute URL
    parsed = urlparse(target)
    if parsed.scheme and parsed.netloc:
        # It's a URL, return as-is
        return target
    # Check if this is a repository-hosted file (repo:path/file)
    if target.startswith("repo:"):
        # Convert to a browser-friendly repository URL
        return build_repository_file_url(target[len("repo:"):])

    # Try to resolve as a local file
    normalized = Path(target)
    search_roots: list[Path] = []
    # Search in both the app root and bundle root for the file
    for root in (get_app_root(), get_bundle_root()):
        if root not in search_roots:
            search_roots.append(root)

    # Check each search root for the file
    for root in search_roots:
        candidate = (root / normalized).resolve()
        if candidate.exists():
            # Found the file, return its path
            return candidate

    # Could not resolve the target
    return None
