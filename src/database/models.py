"""
Database models using SQLAlchemy ORM.
Defines the Items table for the inventory system.

Supports per-user SQLite databases: each Telegram user gets their own
.db file derived from the base DATABASE_URL directory.
"""
from pathlib import Path
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from ..config import settings

# Create SQLAlchemy Base
Base = declarative_base()


class Item(Base):
    """
    Item model representing inventory items.
    
    Attributes:
        id: Primary key, auto-incrementing integer
        name: Name of the item
        quantity: Current quantity in stock
        category: Category/type of the item
        expire_date: Expiration date of the item
        last_updated: Timestamp of last modification
    """
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    category = Column(String, nullable=False, index=True)
    expire_date = Column(Date, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', quantity={self.quantity}, category='{self.category}')>"
    
    def to_dict(self):
        """
        Convert the item to a dictionary representation.
        
        Returns:
            Dictionary containing all item attributes
        """
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "category": self.category,
            "expire_date": self.expire_date.isoformat() if self.expire_date else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }


# ---------------------------------------------------------------------------
# Per-user database helpers
# ---------------------------------------------------------------------------

# Cache of per-user engines keyed by Telegram chat_id
_user_engines: dict[int, Engine] = {}


def _get_user_db_path(chat_id: int) -> Path:
    """
    Derive the SQLite file path for a given Telegram chat_id.

    The path is placed in the same directory as the base DATABASE_URL
    and named ``inventory_<chat_id>.db``.

    Args:
        chat_id: Telegram chat/user ID

    Returns:
        Absolute Path to the user's SQLite database file
    """
    raw_path = settings.database_url.replace("sqlite:///", "")
    base_dir = Path(raw_path).parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"inventory_{chat_id}.db"


def get_engine_for_user(chat_id: int) -> Engine:
    """
    Return a cached SQLAlchemy engine for the given Telegram chat_id.

    On first call for a chat_id, the engine is created, the schema is
    initialised (tables created if absent), and the engine is cached for
    subsequent calls.

    Args:
        chat_id: Telegram chat/user ID

    Returns:
        SQLAlchemy Engine connected to that user's SQLite database
    """
    if chat_id not in _user_engines:
        db_path = _get_user_db_path(chat_id)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        Base.metadata.create_all(bind=engine)
        _user_engines[chat_id] = engine
    return _user_engines[chat_id]


def get_session_for_user(chat_id: int) -> Session:
    """
    Create and return a new SQLAlchemy session for the given Telegram chat_id.

    Callers are responsible for closing the session when done.

    Args:
        chat_id: Telegram chat/user ID

    Returns:
        New SQLAlchemy Session bound to that user's database
    """
    engine = get_engine_for_user(chat_id)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return factory()


def get_db_for_user(chat_id: int):
    """
    FastAPI-compatible dependency generator for per-user database sessions.

    Yields a session for the given chat_id and guarantees it is closed
    after the request completes.

    Args:
        chat_id: Telegram chat/user ID

    Yields:
        SQLAlchemy Session bound to that user's database
    """
    db = get_session_for_user(chat_id)
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Legacy global engine/session (kept for dashboard backward-compat)
# ---------------------------------------------------------------------------

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize the legacy global database by creating all tables.

    Should be called on application startup only for the admin/dashboard
    use-case.  Per-user tables are initialised automatically by
    ``get_engine_for_user``.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI dependency for the legacy global database session.

    Yields a database session and ensures it is closed after use.

    Yields:
        Database session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
