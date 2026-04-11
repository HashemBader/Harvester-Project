"""
Public surface of the ``database`` package.

Exports are resolved lazily via ``__getattr__`` so that importing this
package does not trigger heavy imports (e.g. SQLite connections) unless
the caller actually uses one of the exported names.

Exported names:
    DatabaseManager  -- The main SQLite access class.
    MainRecord       -- DTO for a successful harvest result.
    AttemptedRecord  -- DTO for a failed/pending lookup with retry state.
    now_datetime_str -- Current local datetime as ``"YYYY-MM-DD HH:MM:SS"``.
    today_yyyymmdd   -- Today's date as an integer ``YYYYMMDD``.
"""

from typing import TYPE_CHECKING, Any

__all__ = ["DatabaseManager", "MainRecord", "AttemptedRecord", "now_datetime_str", "today_yyyymmdd"]

if TYPE_CHECKING:
    from .db_manager import DatabaseManager, MainRecord, AttemptedRecord, now_datetime_str, today_yyyymmdd


def __getattr__(name: str) -> Any:
    """Resolve exported names on first access (PEP 562 lazy module attributes).
    
    This implementation defers the import of submodules until the name is actually
    accessed. This pattern avoids heavy side effects (like SQLite connections) when
    the database package is merely imported but not yet used.
    
    Args:
        name: The attribute being accessed (e.g., "DatabaseManager").
        
    Returns:
        The requested exported name (class, function, or other object).
        
    Raises:
        AttributeError: If the name is not a recognized export.
    """
    # Resolve DatabaseManager class on first access
    if name == "DatabaseManager":
        from .db_manager import DatabaseManager
        return DatabaseManager
    # Resolve MainRecord dataclass on first access
    if name == "MainRecord":
        from .db_manager import MainRecord
        return MainRecord
    # Resolve AttemptedRecord dataclass on first access
    if name == "AttemptedRecord":
        from .db_manager import AttemptedRecord
        return AttemptedRecord
    # Resolve now_datetime_str function on first access
    if name == "now_datetime_str":
        from .db_manager import now_datetime_str
        return now_datetime_str
    # Legacy alias for today_yyyymmdd (kept for backward compatibility)
    if name == "today_yyyymmdd":
        from .db_manager import today_yyyymmdd
        return today_yyyymmdd
    # Legacy alias utc_now_iso maps to now_datetime_str (kept for compatibility)
    if name == "utc_now_iso":
        from .db_manager import now_datetime_str
        return now_datetime_str
    # Unrecognized attribute name: raise AttributeError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
