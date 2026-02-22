"""
CRUD operations for database transactions.
Handles all database interactions for the inventory system.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Item


def get_item_by_id(db: Session, item_id: int) -> Optional[Item]:
    """
    Retrieve an item by its ID.
    
    Args:
        db: Database session
        item_id: ID of the item to retrieve
        
    Returns:
        Item object if found, None otherwise
    """
    return db.query(Item).filter(Item.id == item_id).first()


def get_item_by_name(db: Session, name: str) -> Optional[Item]:
    """
    Retrieve an item by its name (case-insensitive).
    
    Args:
        db: Database session
        name: Name of the item to retrieve
        
    Returns:
        Item object if found, None otherwise
    """
    return db.query(Item).filter(Item.name.ilike(name)).first()


def get_all_items(db: Session, skip: int = 0, limit: int = 100) -> List[Item]:
    """
    Retrieve all items with pagination support.
    
    Args:
        db: Database session
        skip: Number of items to skip
        limit: Maximum number of items to return
        
    Returns:
        List of Item objects
    """
    return db.query(Item).offset(skip).limit(limit).all()


def get_items_by_category(db: Session, category: str) -> List[Item]:
    """
    Retrieve all items in a specific category.
    
    Args:
        db: Database session
        category: Category name to filter by
        
    Returns:
        List of Item objects in the category
    """
    return db.query(Item).filter(Item.category.ilike(category)).all()


def create_item(db: Session, name: str, quantity: int, category: str, expire_date: Optional[date] = None) -> Item:
    """
    Create a new item in the inventory.
    
    Args:
        db: Database session
        name: Name of the item
        quantity: Initial quantity
        category: Category of the item
        expire_date: Optional expiration date
        
    Returns:
        Created Item object
    """
    db_item = Item(
        name=name,
        quantity=quantity,
        category=category,
        expire_date=expire_date,
        last_updated=datetime.utcnow()
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_item_quantity(db: Session, item_id: int, quantity_change: int) -> Optional[Item]:
    """
    Update an item's quantity by adding or subtracting a value.
    
    Args:
        db: Database session
        item_id: ID of the item to update
        quantity_change: Amount to add (positive) or subtract (negative)
        
    Returns:
        Updated Item object if found, None otherwise
    """
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db_item.quantity += quantity_change
        db_item.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(db_item)
    return db_item


def update_item_by_name(db: Session, name: str, quantity_change: int) -> Optional[Item]:
    """
    Update an item's quantity by name.
    
    Args:
        db: Database session
        name: Name of the item to update
        quantity_change: Amount to add (positive) or subtract (negative)
        
    Returns:
        Updated Item object if found, None otherwise
    """
    db_item = get_item_by_name(db, name)
    if db_item:
        db_item.quantity += quantity_change
        db_item.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(db_item)
    return db_item


def set_item_quantity(db: Session, item_id: int, quantity: int) -> Optional[Item]:
    """
    Set an item's quantity to a specific value.
    
    Args:
        db: Database session
        item_id: ID of the item to update
        quantity: New quantity value
        
    Returns:
        Updated Item object if found, None otherwise
    """
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db_item.quantity = quantity
        db_item.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> bool:
    """
    Delete an item from the inventory.
    
    Args:
        db: Database session
        item_id: ID of the item to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_item = get_item_by_id(db, item_id)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False


def delete_item_by_name(db: Session, name: str) -> bool:
    """
    Delete an item by name.
    
    Args:
        db: Database session
        name: Name of the item to delete
        
    Returns:
        True if deleted, False if not found
    """
    db_item = get_item_by_name(db, name)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False


def execute_raw_sql(db: Session, sql_query: str) -> List[Dict[str, Any]]:
    """
    Execute a raw SQL query and return results.
    
    Args:
        db: Database session
        sql_query: SQL query string to execute
        
    Returns:
        List of dictionaries containing query results
    """
    result = db.execute(text(sql_query))
    
    # Handle SELECT queries
    if result.returns_rows:
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    
    # Handle INSERT/UPDATE/DELETE queries
    db.commit()
    return [{"affected_rows": result.rowcount}]


def get_inventory_summary(db: Session) -> Dict[str, Any]:
    """
    Get a summary of the inventory including total items and categories.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with inventory statistics
    """
    total_items = db.query(Item).count()
    total_quantity = db.query(Item).with_entities(Item.quantity).all()
    total_quantity_sum = sum([q[0] for q in total_quantity]) if total_quantity else 0
    
    categories = db.query(Item.category).distinct().all()
    category_list = [cat[0] for cat in categories]
    
    return {
        "total_items": total_items,
        "total_quantity": total_quantity_sum,
        "categories": category_list,
        "category_count": len(category_list)
    }


def get_items_by_expiration(db: Session) -> List[Dict[str, Any]]:
    """
    Get items ordered by expiration date (recent to older).
    
    Args:
        db: Database session
        
    Returns:
        List of item dictionaries sorted by expiration date
    """
    items = db.query(Item).filter(Item.expire_date.isnot(None)).order_by(Item.expire_date.asc()).all()
    return [item.to_dict() for item in items]


def get_history(db: Session, days: int, item: Optional[str] = None, group: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get history of additions/extractions for the last N days.
    
    Note: This is a placeholder. Full implementation requires an audit/history table.
    For now, returns items that were recently updated.
    
    Args:
        db: Database session
        days: Number of days to look back
        item: Optional specific item name to filter
        group: Optional category/group to filter
        
    Returns:
        List of history records
    """
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Item).filter(Item.last_updated >= cutoff_date)
    
    if item:
        query = query.filter(Item.name.ilike(item))
    
    if group:
        query = query.filter(Item.category.ilike(group))
    
    items = query.order_by(Item.last_updated.desc()).all()
    
    # Format as history records
    history = []
    for item_obj in items:
        history.append({
            "date": item_obj.last_updated.strftime("%Y-%m-%d %H:%M"),
            "action": "updated",
            "quantity": item_obj.quantity,
            "item": item_obj.name
        })
    
    return history

def delete_all_items(db: Session) -> int:
    """
    Delete all items from the inventory.

    Args:
        db: Database session

    Returns:
        Number of items deleted
    """
    deleted_count = db.query(Item).delete()
    db.commit()
    return deleted_count


def create_items_batch(
    db: Session,
    items: list[dict],
) -> list[Item]:
    """
    Create multiple items in a single transaction.
    
    Args:
        db: Database session
        items: List of dicts with keys: name, quantity, category, expire_date (optional)
        
    Returns:
        List of created Item objects
    """
    created_items = []
    for item_data in items:
        db_item = Item(
            name=item_data["name"],
            quantity=item_data.get("quantity", 1),
            category=item_data.get("category", "general"),
            expire_date=item_data.get("expire_date"),
            last_updated=datetime.utcnow()
        )
        db.add(db_item)
        created_items.append(db_item)
    
    db.commit()
    for item in created_items:
        db.refresh(item)
    return created_items


def delete_items_batch(db: Session, names: list[str]) -> int:
    """
    Delete multiple items by name in a single transaction.
    
    Args:
        db: Database session
        names: List of item names to delete
        
    Returns:
        Number of items deleted
    """
    deleted_count = 0
    for name in names:
        item = get_item_by_name(db, name)
        if item:
            db.delete(item)
            deleted_count += 1
    db.commit()
    return deleted_count
