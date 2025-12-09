"""
Database models using SQLAlchemy ORM.
Defines the Items table for the inventory system.
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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


# Create engine and session
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize the database by creating all tables.
    Should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    
    Yields:
        Database session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
