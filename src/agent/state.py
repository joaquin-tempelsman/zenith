"""
Module-level state management for the agent.

Holds the database session, detected language, Telegram chat_id, and
per-chat conversation history for the current request.  All are set once
per request and accessed by tools and the agent runner during execution.
"""
from collections import deque
from typing import Optional

from langchain_core.messages import BaseMessage
from sqlalchemy.orm import Session

from .prompts import Language

MAX_HISTORY_MESSAGES: int = 10


_db_session: Optional[Session] = None
_meta_session: Optional[Session] = None
_detected_language: Language = "en"
_chat_id: Optional[int] = None
_chat_histories: dict[int, deque[BaseMessage]] = {}


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


def set_meta_session(meta: Session) -> None:
    """
    Set the shared metadata database session for linking tools.

    Args:
        meta: SQLAlchemy session connected to the metadata database
    """
    global _meta_session
    _meta_session = meta


def get_meta_session() -> Session:
    """
    Get the current shared metadata database session.

    Returns:
        The metadata SQLAlchemy database session

    Raises:
        RuntimeError: If no metadata session has been set
    """
    if _meta_session is None:
        raise RuntimeError("Metadata session not set. Call set_meta_session first.")
    return _meta_session


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


def get_chat_history(chat_id: int) -> list[BaseMessage]:
    """
    Return the conversation history for *chat_id* as a plain list.

    Args:
        chat_id: Telegram chat/user ID whose history is requested

    Returns:
        List of the most recent messages (up to ``MAX_HISTORY_MESSAGES``)
    """
    return list(_chat_histories.get(chat_id, []))


def append_chat_history(chat_id: int, messages: list[BaseMessage]) -> None:
    """
    Append *messages* to the conversation history for *chat_id*.

    Only the last ``MAX_HISTORY_MESSAGES`` messages are retained.

    Args:
        chat_id: Telegram chat/user ID whose history is being updated
        messages: New messages to append (e.g. a HumanMessage + AIMessage pair)
    """
    if chat_id not in _chat_histories:
        _chat_histories[chat_id] = deque(maxlen=MAX_HISTORY_MESSAGES)
    for msg in messages:
        _chat_histories[chat_id].append(msg)


def clear_chat_history(chat_id: int) -> None:
    """
    Remove all stored history for *chat_id*.

    Args:
        chat_id: Telegram chat/user ID whose history should be cleared
    """
    _chat_histories.pop(chat_id, None)

