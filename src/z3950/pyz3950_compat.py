"""
Module: pyz3950_compat.py
Purpose: Compatibility shim that verifies PyZ3950 is importable and ready.
         Includes a robust regex hotfix for Python 3.11+.
"""

from __future__ import annotations

import logging
import re
import sys

logger = logging.getLogger(__name__)

# Module-level cache for the import probe result to avoid repeated heavy checks.
_cached_result: tuple[bool, str] | None = None
# Tracks whether the monkey-patch has been applied globally.
_hotfix_applied = False


def _apply_python_311_regex_hotfix() -> None:
    """
    Monkey-patch re.compile to handle legacy regexes with global flags (?, etc.) in the middle.
    Introduced to fix PyZ3950/PLY incompatibilities on Python 3.11+.
    """
    global _hotfix_applied
    # Only apply once and only on Python 3.11 or newer where the legacy behavior changed.
    if _hotfix_applied or sys.version_info < (3, 11):
        return

    orig_compile = re.compile

    def patched_compile(pattern, flags=0):
        # We only need to check patterns that are string or bytes.
        if isinstance(pattern, (str, bytes)):
            is_bytes = isinstance(pattern, bytes)
            # Normalize to string for regex manipulation.
            p_str = pattern.decode("utf-8", "ignore") if is_bytes else pattern

            # Robust detection of any inline global flags (e.g., (?imsux)) 
            # that might be embedded in the middle of a string.
            flag_ptrn = orig_compile(r'\(\?[imsux]+\)')
            all_flags = flag_ptrn.findall(p_str)
            
            if all_flags:
                # Python 3.11+ strictly requires global flags at the very start of the string.
                # Remove them from the middle and move them to the beginning.
                p_clean = flag_ptrn.sub('', p_str)
                # Combine all found flags and deduplicate them.
                unique_flags = "".join(sorted(set(all_flags)))
                p_final = unique_flags + p_clean
                # Restore original type (bytes if it was bytes).
                pattern = p_final.encode("utf-8") if is_bytes else p_final

        # Fall back to the original re.compile with the modified (or original) pattern.
        return orig_compile(pattern, flags)

    # Replace the standard library re.compile with our patched version.
    re.compile = patched_compile
    _hotfix_applied = True
    logger.debug("Applied robust Python 3.11+ regex hotfix for PyZ3950 compatibility.")


def ensure_pyz3950_importable() -> tuple[bool, str]:
    """
    Check that PyZ3950's zoom module can be imported and is ready to use.
    
    This function applies the Python 3.11 compatibility hotfix before the first import.
    """
    global _cached_result
    # Use the cached result if this function has already been called in the current process.
    if _cached_result is not None:
        return _cached_result

    # CRITICAL: Apply the regex hotfix before attempting any PyZ3950 imports,
    # because PyZ3950 triggers PLY lexer generation which uses re.compile.
    _apply_python_311_regex_hotfix()

    try:
        # Attempt a dummy import to verify that the library and its dependencies are present.
        from PyZ3950 import zoom as _zoom  # noqa: F401
        # Success: cache the result.
        _cached_result = (True, "")
        return _cached_result
    except ImportError as exc:
        # Expected failure if the package is missing.
        msg = f"PyZ3950 is not installed: {exc}"
        logger.warning(msg)
        _cached_result = (False, msg)
        return _cached_result
    except Exception as exc:
        # Unexpected failure (e.g., broken installation).
        msg = f"PyZ3950 import error: {exc}"
        logger.warning(msg)
        _cached_result = (False, msg)
        return _cached_result