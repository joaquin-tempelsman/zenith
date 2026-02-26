"""
CRUD operations for database transactions.
Handles all database interactions for the inventory system.
"""
import secrets
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from .models import Item, UserCode, AccountLink, AuthorizedUser


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
        last_updated=datetime.now(timezone.utc)
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
        db_item.last_updated = datetime.now(timezone.utc)
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
        db_item.last_updated = datetime.now(timezone.utc)
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
        db_item.last_updated = datetime.now(timezone.utc)
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
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
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
            last_updated=datetime.now(timezone.utc)
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


# ---------------------------------------------------------------------------
# Account linking CRUD
# ---------------------------------------------------------------------------


def get_or_create_user_code(meta: Session, chat_id: int) -> str:
    """Return the existing link code for *chat_id*, creating one if needed.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        The user's permanent link code string
    """
    row = meta.query(UserCode).filter(UserCode.chat_id == chat_id).first()
    if row:
        return row.link_code
    code = secrets.token_urlsafe(6)
    row = UserCode(chat_id=chat_id, link_code=code)
    meta.add(row)
    meta.commit()
    meta.refresh(row)
    return row.link_code


def regenerate_user_code(meta: Session, chat_id: int) -> str:
    """Replace the existing link code with a freshly generated one.

    Existing account links are **not** broken — linked users continue to
    operate on this owner's database.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        The newly generated link code
    """
    row = meta.query(UserCode).filter(UserCode.chat_id == chat_id).first()
    new_code = secrets.token_urlsafe(6)
    if row:
        row.link_code = new_code
    else:
        row = UserCode(chat_id=chat_id, link_code=new_code)
        meta.add(row)
    meta.commit()
    meta.refresh(row)
    return row.link_code


def link_account(meta: Session, owner_code: str, requester_chat_id: int) -> dict:
    """Create an account link from *requester_chat_id* to the owner of *owner_code*.

    Args:
        meta: Metadata database session
        owner_code: Link code shared by the database owner
        requester_chat_id: Chat ID of the user who wants to link

    Returns:
        Dict with ``ok`` (bool) and ``msg`` (str).  On success the dict also
        contains ``owner_chat_id``.
    """
    code_row = meta.query(UserCode).filter(UserCode.link_code == owner_code).first()
    if not code_row:
        return {"ok": False, "msg": "invalid_code"}

    if code_row.chat_id == requester_chat_id:
        return {"ok": False, "msg": "self_link"}

    existing = meta.query(AccountLink).filter(
        AccountLink.linked_chat_id == requester_chat_id
    ).first()
    if existing:
        return {"ok": False, "msg": "already_linked"}

    link = AccountLink(
        owner_chat_id=code_row.chat_id,
        linked_chat_id=requester_chat_id,
    )
    meta.add(link)
    meta.commit()
    return {"ok": True, "msg": "linked", "owner_chat_id": code_row.chat_id}


def unlink_account(meta: Session, chat_id: int) -> dict:
    """Remove an active account link for *chat_id*.

    Args:
        meta: Metadata database session
        chat_id: Chat ID of the linked (non-owner) user

    Returns:
        Dict with ``ok`` (bool) and ``msg`` (str)
    """
    link = meta.query(AccountLink).filter(
        AccountLink.linked_chat_id == chat_id
    ).first()
    if not link:
        return {"ok": False, "msg": "not_linked"}
    meta.delete(link)
    meta.commit()
    return {"ok": True, "msg": "unlinked"}


def resolve_effective_chat_id(meta: Session, chat_id: int) -> int:
    """Return the effective chat_id whose database should be used.

    If *chat_id* is linked to another user, returns the owner's chat_id.
    Otherwise returns *chat_id* unchanged.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID to resolve

    Returns:
        The owner's chat_id if a link exists, else the original chat_id
    """
    link = meta.query(AccountLink).filter(
        AccountLink.linked_chat_id == chat_id
    ).first()
    if link:
        return link.owner_chat_id
    return chat_id


def get_linked_users(meta: Session, owner_chat_id: int) -> list[int]:
    """Return chat_ids of all users linked to *owner_chat_id*.

    Args:
        meta: Metadata database session
        owner_chat_id: Chat ID of the database owner

    Returns:
        List of linked user chat_ids (may be empty)
    """
    links = meta.query(AccountLink).filter(
        AccountLink.owner_chat_id == owner_chat_id
    ).all()
    return [link.linked_chat_id for link in links]


# ---------------------------------------------------------------------------
# Access control CRUD
# ---------------------------------------------------------------------------

MAX_ACCESS_ATTEMPTS = 5


def is_user_authorized(meta: Session, chat_id: int) -> bool:
    """Check whether a user has been granted authorized access.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        True if the user has already provided the correct secret code.
    """
    row = meta.query(AuthorizedUser).filter(AuthorizedUser.chat_id == chat_id).first()
    return row is not None and bool(row.is_authorized)


def authorize_user(meta: Session, chat_id: int) -> None:
    """Mark a user as authorized after they provide the correct secret code.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID
    """
    row = meta.query(AuthorizedUser).filter(AuthorizedUser.chat_id == chat_id).first()
    if row:
        row.is_authorized = 1
        row.authorized_at = datetime.now(timezone.utc)
    else:
        row = AuthorizedUser(
            chat_id=chat_id,
            is_authorized=1,
            authorized_at=datetime.now(timezone.utc),
        )
        meta.add(row)
    meta.commit()


def get_failed_attempts(meta: Session, chat_id: int) -> int:
    """Return the number of failed access attempts for a user.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        Number of failed attempts (0 if user has no record).
    """
    row = meta.query(AuthorizedUser).filter(AuthorizedUser.chat_id == chat_id).first()
    if row is None:
        return 0
    return row.attempts


def increment_failed_attempts(meta: Session, chat_id: int) -> int:
    """Record a failed access attempt and return the new total.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        Updated number of failed attempts.
    """
    row = meta.query(AuthorizedUser).filter(AuthorizedUser.chat_id == chat_id).first()
    if row:
        row.attempts += 1
    else:
        row = AuthorizedUser(chat_id=chat_id, attempts=1)
        meta.add(row)
    meta.commit()
    meta.refresh(row)
    return row.attempts


def is_user_blocked(meta: Session, chat_id: int) -> bool:
    """Check whether a user has exhausted their access attempts.

    Args:
        meta: Metadata database session
        chat_id: Telegram chat/user ID

    Returns:
        True if the user has reached or exceeded MAX_ACCESS_ATTEMPTS
        without providing the correct code.
    """
    row = meta.query(AuthorizedUser).filter(AuthorizedUser.chat_id == chat_id).first()
    if row is None:
        return False
    return not bool(row.is_authorized) and row.attempts >= MAX_ACCESS_ATTEMPTS
