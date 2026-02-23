"""
Database package.

Re-exports the most commonly used symbols so callers can do::

    from src.database import get_session_for_user, get_db_for_user
"""
from .models import (
    get_engine_for_user,
    get_session_for_user,
    get_db_for_user,
    get_metadata_engine,
    get_metadata_session,
    SessionLocal,
    init_db,
    get_db,
)

__all__ = [
    "get_engine_for_user",
    "get_session_for_user",
    "get_db_for_user",
    "get_metadata_engine",
    "get_metadata_session",
    "SessionLocal",
    "init_db",
    "get_db",
]
