"""
Module-level state management for the agent.

Holds the database session, detected language, and Telegram chat_id for the
current request.  All three are set once per request and accessed by tools
and the agent runner during execution.
"""
from typing import Optional
from sqlalchemy.orm import Session
from .prompts import Language


_db_session: Optional[Session] = None
_detected_language: Language = "en"
_chat_id: Optional[int] = None


def set_db_session(db: Session) -> None:
    """
    Set the database session for tools to use.

    Args:
        db: SQLAlchemy database session
    """
    global _db_session
    _db_session = db


def get_db_session() -> Session:
    """
    Get the current database session.

    Returns:
        The current SQLAlchemy database session

    Raises:
        RuntimeError: If no database session has been set
    """
    if _db_session is None:
        raise RuntimeError("Database session not set. Call set_db_session first.")
    return _db_session


def set_detected_language(language: Language) -> None:
    """
    Set the detected language for the current request.

    Args:
        language: Language code ('en' or 'es')
    """
    global _detected_language
    _detected_language = language


def get_detected_language() -> Language:
    """
    Get the currently detected language.

    Returns:
        Language code ('en' or 'es')
    """
    return _detected_language


def set_chat_id(chat_id: int) -> None:
    """
    Set the Telegram chat_id for the current request.

    Used by the agent runner to record which user triggered the invocation so
    that LangSmith traces can be grouped per user.

    Args:
        chat_id: Telegram chat/user ID for the active request
    """
    global _chat_id
    _chat_id = chat_id


def get_chat_id() -> Optional[int]:
    """
    Get the Telegram chat_id for the current request.

    Returns:
        The chat_id set by the most recent call to ``set_chat_id``,
        or ``None`` if it has not been set yet.
    """
    return _chat_id

