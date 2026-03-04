"""
Database models using SQLAlchemy ORM.
Defines the Items table for the inventory system.

Supports per-user SQLite databases: each Telegram user gets their own
.db file derived from the base DATABASE_URL directory.
"""
import secrets
from pathlib import Path
from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from ..config import settings


def _enable_wal(engine: Engine) -> None:
    """Enable WAL journal mode on a SQLite engine via a connect event.

    WAL (Write-Ahead Logging) allows concurrent reads during writes and
    produces safer backups.  The pragma is a no-op on non-SQLite engines.

    Args:
        engine: SQLAlchemy engine to configure.
    """
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

# Create SQLAlchemy Base (per-user inventory tables)
Base = declarative_base()

# Separate base for shared metadata tables (account linking)
MetadataBase = declarative_base()


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
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
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
# Shared metadata models (account linking)
# ---------------------------------------------------------------------------


class UserCode(MetadataBase):
    """Stores the permanent link code assigned to each user.

    Attributes:
        chat_id: Telegram chat/user ID (primary key)
        link_code: Unique URL-safe token used for account linking
        created_at: Timestamp when the code was first generated
    """

    __tablename__ = "user_codes"

    chat_id = Column(Integer, primary_key=True)
    link_code = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    links = relationship("AccountLink", back_populates="owner", foreign_keys="AccountLink.owner_chat_id")

    def __repr__(self):
        return f"<UserCode(chat_id={self.chat_id}, link_code='{self.link_code}')>"


class AuthorizedUser(MetadataBase):
    """Tracks users who have been granted access via the secret code.

    Attributes:
        chat_id: Telegram chat/user ID (primary key)
        attempts: Number of failed access attempts before authorization
        is_authorized: Whether the user has provided the correct secret code
        created_at: Timestamp of the first interaction
        authorized_at: Timestamp when access was granted (None if not yet authorized)
    """

    __tablename__ = "authorized_users"

    chat_id = Column(Integer, primary_key=True)
    attempts = Column(Integer, nullable=False, default=0)
    is_authorized = Column(Integer, nullable=False, default=0)  # SQLite boolean
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    authorized_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<AuthorizedUser(chat_id={self.chat_id}, "
            f"authorized={bool(self.is_authorized)}, attempts={self.attempts})>"
        )


class AdminUser(MetadataBase):
    """Tracks users who have been granted admin access.

    Admin users receive daily reports with usage statistics.

    Attributes:
        chat_id: Telegram chat/user ID (primary key)
        granted_at: Timestamp when admin access was granted
    """

    __tablename__ = "admin_users"

    chat_id = Column(Integer, primary_key=True)
    granted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<AdminUser(chat_id={self.chat_id})>"


class MessageLog(MetadataBase):
    """Logs each incoming Telegram message for usage reporting.

    Attributes:
        id: Auto-incrementing primary key
        chat_id: Telegram chat/user ID that sent the message
        timestamp: When the message was received (UTC)
    """

    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f"<MessageLog(id={self.id}, chat_id={self.chat_id})>"


class TokenUsage(MetadataBase):
    """Records LLM token consumption per agent invocation.

    Attributes:
        id: Auto-incrementing primary key
        chat_id: Telegram chat/user ID that triggered the invocation
        input_tokens: Number of prompt/input tokens consumed
        output_tokens: Number of completion/output tokens consumed
        timestamp: When the invocation occurred (UTC)
    """

    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False, index=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return (
            f"<TokenUsage(id={self.id}, chat_id={self.chat_id}, "
            f"in={self.input_tokens}, out={self.output_tokens})>"
        )


class AccountLink(MetadataBase):
    """Maps a linked user to an owner whose database they share.

    Attributes:
        id: Auto-incrementing primary key
        owner_chat_id: Chat ID of the database owner
        linked_chat_id: Chat ID of the user operating on the owner's DB (unique)
        created_at: Timestamp when the link was established
    """

    __tablename__ = "account_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_chat_id = Column(Integer, ForeignKey("user_codes.chat_id"), nullable=False)
    linked_chat_id = Column(Integer, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("UserCode", back_populates="links", foreign_keys=[owner_chat_id])

    def __repr__(self):
        return f"<AccountLink(owner={self.owner_chat_id}, linked={self.linked_chat_id})>"


# ---------------------------------------------------------------------------
# Metadata (shared) database helpers
# ---------------------------------------------------------------------------

_metadata_engine: Engine | None = None


def _get_metadata_db_path() -> Path:
    """Return the path for the shared metadata SQLite database.

    The file is placed alongside the per-user inventory databases.

    Returns:
        Absolute Path to ``metadata.db``
    """
    raw_path = settings.database_url.replace("sqlite:///", "")
    base_dir = Path(raw_path).parent
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "metadata.db"


def get_metadata_engine() -> Engine:
    """Return a cached SQLAlchemy engine for the shared metadata database.

    On first call the engine is created and the metadata schema is
    initialised (tables created if absent).

    Returns:
        SQLAlchemy Engine connected to ``metadata.db``
    """
    global _metadata_engine
    if _metadata_engine is None:
        db_path = _get_metadata_db_path()
        _metadata_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        _enable_wal(_metadata_engine)
        MetadataBase.metadata.create_all(bind=_metadata_engine)
    return _metadata_engine


def get_metadata_session() -> Session:
    """Create and return a new session for the shared metadata database.

    Callers are responsible for closing the session when done.

    Returns:
        New SQLAlchemy Session bound to the metadata engine
    """
    engine = get_metadata_engine()
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return factory()


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
        _enable_wal(engine)
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
if "sqlite" in settings.database_url:
    _enable_wal(engine)

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
