"""
Refactored inventory tools for LangGraph 1.0.
Uses structured tool definitions with proper typing and validation.
"""
from typing import Optional, Any
from datetime import date
from pydantic import BaseModel, Field

from langchain_core.tools import tool
from sqlalchemy.orm import Session

# Global database session holder - set by the agent before running
_db_session: Optional[Session] = None


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


# Tool Input Models for better validation
class AddItemInput(BaseModel):
    """Input model for add_item tool."""
    item_name: str = Field(..., description="Name of the item to add")
    quantity: int = Field(default=1, description="Quantity to add")
    category: Optional[str] = Field(default=None, description="Category for the item")
    expire_date: Optional[str] = Field(default=None, description="Expiration date in YYYY-MM-DD format")
    notes: Optional[str] = Field(default=None, description="Optional notes about the item")


class RemoveItemInput(BaseModel):
    """Input model for remove_item tool."""
    item_name: str = Field(..., description="Name of the item to remove from")
    quantity: Optional[int] = Field(default=None, description="Quantity to remove (None=remove all)")


class GetItemStockInput(BaseModel):
    """Input model for get_item_stock tool."""
    item_name: str = Field(..., description="Name of the item to check")


class ListItemsByCategoryInput(BaseModel):
    """Input model for list_items_by_category tool."""
    category: str = Field(..., description="Category name to filter by")


class GetItemHistoryInput(BaseModel):
    """Input model for get_item_history tool."""
    days: int = Field(default=7, description="Number of days to look back")
    item_name: Optional[str] = Field(default=None, description="Optional specific item to filter by")
    category: Optional[str] = Field(default=None, description="Optional category to filter by")


class RequestClarificationInput(BaseModel):
    """Input model for request_clarification tool."""
    message: str = Field(..., description="The clarification message to send to the user")


# Tool implementations
@tool(args_schema=AddItemInput)
def add_item(
    item_name: str,
    quantity: int = 1,
    category: Optional[str] = None,
    expire_date: Optional[str] = None,
    notes: Optional[str] = None
) -> str:
    """
    Add an item to the inventory or update quantity if it exists.
    
    Args:
        item_name: Name of the item to add (will be lowercased)
        quantity: Quantity to add (default 1 if not specified)
        category: Category for the item (will be inferred if not provided)
        expire_date: Optional expiration date in YYYY-MM-DD format
        notes: Optional notes about the item
        
    Returns:
        Message describing the result of the operation
    """
    from ..database import crud
    db = get_db_session()
    
    item_name = item_name.lower().strip()
    
    parsed_expire_date = None
    if expire_date:
        try:
            parsed_expire_date = date.fromisoformat(expire_date)
        except ValueError:
            pass
    
    existing_item = crud.get_item_by_name(db, item_name)
    
    if existing_item:
        if quantity and quantity > 0:
            updated_item = crud.update_item_by_name(db, item_name, quantity)
            return f"✅ Added {quantity} to '{item_name}'. New quantity: {updated_item.quantity} in category '{updated_item.category}'"
        else:
            return f"ℹ️ Item '{item_name}' already exists with quantity {existing_item.quantity} in category '{existing_item.category}'"
    else:
        final_quantity = quantity if quantity else 1
        final_category = category.lower().strip() if category else "general"
        
        new_item = crud.create_item(
            db,
            item_name,
            final_quantity,
            final_category,
            parsed_expire_date
        )
        expire_info = f", expires: {new_item.expire_date}" if new_item.expire_date else ""
        return f"✅ Created new item '{item_name}' with quantity {new_item.quantity} in category '{new_item.category}'{expire_info}"


@tool(args_schema=RemoveItemInput)
def remove_item(
    item_name: str,
    quantity: Optional[int] = None
) -> str:
    """
    Remove quantity from an item or remove all stock if quantity is not specified.
    
    Args:
        item_name: Name of the item to remove from
        quantity: Quantity to remove (None or 0 means remove all)
        
    Returns:
        Message describing the result of the operation
    """
    from ..database import crud
    db = get_db_session()
    
    item_name = item_name.lower().strip()
    existing_item = crud.get_item_by_name(db, item_name)
    
    if not existing_item:
        return f"❌ Item '{item_name}' not found in inventory"
    
    if quantity is None or quantity == 0:
        old_quantity = existing_item.quantity
        crud.set_item_quantity(db, existing_item.id, 0)
        return f"✅ Removed all {old_quantity} '{item_name}' from inventory"
    else:
        new_quantity = max(0, existing_item.quantity - quantity)
        actual_removed = existing_item.quantity - new_quantity
        crud.set_item_quantity(db, existing_item.id, new_quantity)
        return f"✅ Removed {actual_removed} '{item_name}'. Remaining: {new_quantity}"


@tool(args_schema=GetItemStockInput)
def get_item_stock(item_name: str) -> str:
    """
    Get the current stock information for a specific item.
    
    Args:
        item_name: Name of the item to check
        
    Returns:
        Stock information for the item
    """
    from ..database import crud
    db = get_db_session()
    
    item_name = item_name.lower().strip()
    item = crud.get_item_by_name(db, item_name)
    
    if not item:
        return f"❌ Item '{item_name}' not found in inventory"
    
    expire_info = f", Expires: {item.expire_date}" if item.expire_date else ""
    return f"📊 {item.name}: {item.quantity} units in stock (Category: {item.category}{expire_info})"


@tool(args_schema=ListItemsByCategoryInput)
def list_items_by_category(category: str) -> str:
    """
    List all items in a specific category.
    
    Args:
        category: Category name to filter by
        
    Returns:
        List of items in the category with their quantities
    """
    from ..database import crud
    db = get_db_session()
    
    category = category.lower().strip()
    items = crud.get_items_by_category(db, category)
    
    if not items:
        return f"ℹ️ No items found in '{category}' category"
    
    items_list = "\n".join([f"- {item.name}: {item.quantity} units" for item in items[:10]])
    return f"📦 Items in '{category}' category:\n{items_list}"


@tool
def list_expiring_items() -> str:
    """
    List all items ordered by expiration date (soonest first).
    
    Returns:
        List of items sorted by expiration date
    """
    from ..database import crud
    db = get_db_session()
    
    items = crud.get_items_by_expiration(db)
    
    if not items:
        return "ℹ️ No items with expiration dates found"
    
    items_list = "\n".join([f"- {item['name']}: {item['expire_date']}" for item in items[:10]])
    return f"📅 Items by expiration (soonest first):\n{items_list}"


@tool(args_schema=GetItemHistoryInput)
def get_item_history(
    days: int = 7,
    item_name: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    Get the history of item changes.
    
    Args:
        days: Number of days to look back (default 7)
        item_name: Optional specific item to filter by
        category: Optional category to filter by
        
    Returns:
        History of inventory changes
    """
    from ..database import crud
    db = get_db_session()
    
    if item_name:
        item_name = item_name.lower().strip()
    if category:
        category = category.lower().strip()
    
    history = crud.get_history(db, days, item_name, category)
    
    target = item_name or category or "all items"
    
    if not history:
        return f"ℹ️ No history found for {target} in the last {days} days"
    
    history_list = "\n".join([
        f"- {h['date']}: {h['action']} {h['quantity']} {h['item']}"
        for h in history[:10]
    ])
    return f"📜 History for {target} (last {days} days):\n{history_list}"


@tool
def get_all_categories() -> str:
    """
    Get all existing categories from the inventory database.
    
    Returns:
        Comma-separated list of category names or 'none' if empty
    """
    from ..database import crud
    db = get_db_session()
    summary = crud.get_inventory_summary(db)
    categories = summary.get("categories", [])
    return ", ".join(categories) if categories else "none"


@tool
def get_inventory_summary() -> str:
    """
    Get a summary of the entire inventory including statistics.
    
    Returns:
        Summary with total items, quantities, and categories
    """
    from ..database import crud
    db = get_db_session()
    
    summary = crud.get_inventory_summary(db)
    
    total_items = summary["total_items"]
    total_quantity = summary["total_quantity"]
    categories = summary["categories"]
    
    categories_str = ", ".join(categories) if categories else "none"
    return f"📊 Inventory Summary:\n- Unique items: {total_items}\n- Total quantity: {total_quantity}\n- Categories ({len(categories)}): {categories_str}"


@tool(args_schema=RequestClarificationInput)
def request_clarification(message: str) -> str:
    """
    Return a clarification request when the user input is unclear.
    Use this when you need more information to complete a request.
    
    Args:
        message: The clarification message to send to the user
        
    Returns:
        The clarification message
    """
    return f"❓ {message}"


# Export all tools
inventory_tools = [
    add_item,
    remove_item,
    get_item_stock,
    list_items_by_category,
    list_expiring_items,
    get_item_history,
    get_all_categories,
    get_inventory_summary,
    request_clarification,
]
