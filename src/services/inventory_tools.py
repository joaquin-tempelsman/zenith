"""
Inventory management tools for the LangGraph agent.
Simple input/output Python functions without LLM logic.
"""
from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session


def get_all_categories(db: Session) -> List[str]:
    """
    Get all existing categories from the database.
    
    Args:
        db: Database session
        
    Returns:
        List of category names
    """
    from ..database import crud
    summary = crud.get_inventory_summary(db)
    return summary.get("categories", [])


def add_item(
    db: Session,
    item_name: str,
    quantity: Optional[int] = None,
    category: Optional[str] = None,
    expire_date: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add an item to the inventory or update quantity if it exists.
    
    Args:
        db: Database session
        item_name: Name of the item to add (lowercase)
        quantity: Quantity to add (default 1 if not specified)
        category: Category for the item (will be inferred if not provided)
        expire_date: Optional expiration date in YYYY-MM-DD format
        notes: Optional notes about the item
        
    Returns:
        Dictionary with operation result
    """
    from ..database import crud
    
    item_name = item_name.lower().strip()
    
    # Parse expire_date if provided
    parsed_expire_date = None
    if expire_date:
        try:
            parsed_expire_date = date.fromisoformat(expire_date)
        except ValueError:
            pass
    
    existing_item = crud.get_item_by_name(db, item_name)
    
    if existing_item:
        if quantity is not None and quantity > 0:
            updated_item = crud.update_item_by_name(db, item_name, quantity)
            return {
                "success": True,
                "action": "updated",
                "item": item_name,
                "quantity_added": quantity,
                "new_quantity": updated_item.quantity,
                "category": updated_item.category
            }
        else:
            return {
                "success": True,
                "action": "exists",
                "item": item_name,
                "current_quantity": existing_item.quantity,
                "category": existing_item.category
            }
    else:
        final_quantity = quantity if quantity is not None else 1
        final_category = category.lower().strip() if category else "general"
        
        new_item = crud.create_item(
            db,
            item_name,
            final_quantity,
            final_category,
            parsed_expire_date
        )
        return {
            "success": True,
            "action": "created",
            "item": item_name,
            "quantity": new_item.quantity,
            "category": new_item.category,
            "expire_date": str(new_item.expire_date) if new_item.expire_date else None
        }


def remove_item(
    db: Session,
    item_name: str,
    quantity: Optional[int] = None
) -> Dict[str, Any]:
    """
    Remove quantity from an item or remove all stock.
    
    Args:
        db: Database session
        item_name: Name of the item to remove from
        quantity: Quantity to remove (None means remove all)
        
    Returns:
        Dictionary with operation result
    """
    from ..database import crud
    
    item_name = item_name.lower().strip()
    existing_item = crud.get_item_by_name(db, item_name)
    
    if not existing_item:
        return {
            "success": False,
            "error": f"Item '{item_name}' not found in inventory"
        }
    
    if quantity is None:
        crud.set_item_quantity(db, existing_item.id, 0)
        return {
            "success": True,
            "action": "removed_all",
            "item": item_name,
            "quantity_removed": existing_item.quantity,
            "remaining_quantity": 0
        }
    else:
        new_quantity = max(0, existing_item.quantity - quantity)
        actual_removed = existing_item.quantity - new_quantity
        crud.set_item_quantity(db, existing_item.id, new_quantity)
        return {
            "success": True,
            "action": "removed",
            "item": item_name,
            "quantity_removed": actual_removed,
            "remaining_quantity": new_quantity
        }


def get_item_stock(db: Session, item_name: str) -> Dict[str, Any]:
    """
    Get the current stock information for a specific item.
    
    Args:
        db: Database session
        item_name: Name of the item to check
        
    Returns:
        Dictionary with item stock information
    """
    from ..database import crud
    
    item_name = item_name.lower().strip()
    item = crud.get_item_by_name(db, item_name)
    
    if not item:
        return {
            "success": False,
            "error": f"Item '{item_name}' not found in inventory"
        }
    
    return {
        "success": True,
        "item": item.name,
        "quantity": item.quantity,
        "category": item.category,
        "expire_date": str(item.expire_date) if item.expire_date else None,
        "last_updated": str(item.last_updated) if item.last_updated else None
    }


def list_items_by_category(db: Session, category: str) -> Dict[str, Any]:
    """
    List all items in a specific category.
    
    Args:
        db: Database session
        category: Category name to filter by
        
    Returns:
        Dictionary with list of items in the category
    """
    from ..database import crud
    
    category = category.lower().strip()
    items = crud.get_items_by_category(db, category)
    
    if not items:
        return {
            "success": True,
            "category": category,
            "items": [],
            "count": 0
        }
    
    return {
        "success": True,
        "category": category,
        "items": [item.to_dict() for item in items],
        "count": len(items)
    }


def list_expiring_items(db: Session) -> Dict[str, Any]:
    """
    List all items ordered by expiration date (soonest first).
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with list of items sorted by expiration
    """
    from ..database import crud
    
    items = crud.get_items_by_expiration(db)
    
    return {
        "success": True,
        "items": items,
        "count": len(items)
    }


def get_item_history(
    db: Session,
    days: int = 7,
    item_name: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the history of item changes.
    
    Args:
        db: Database session
        days: Number of days to look back (default 7)
        item_name: Optional specific item to filter by
        category: Optional category to filter by
        
    Returns:
        Dictionary with history records
    """
    from ..database import crud
    
    if item_name:
        item_name = item_name.lower().strip()
    if category:
        category = category.lower().strip()
    
    history = crud.get_history(db, days, item_name, category)
    
    return {
        "success": True,
        "days": days,
        "filter_item": item_name,
        "filter_category": category,
        "history": history,
        "count": len(history)
    }


def get_inventory_summary(db: Session) -> Dict[str, Any]:
    """
    Get a summary of the entire inventory.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with inventory statistics
    """
    from ..database import crud
    
    summary = crud.get_inventory_summary(db)
    
    return {
        "success": True,
        "total_unique_items": summary["total_items"],
        "total_quantity": summary["total_quantity"],
        "categories": summary["categories"],
        "category_count": summary["category_count"]
    }


def request_clarification(message: str) -> Dict[str, Any]:
    """
    Return a clarification request when the user input is unclear.
    
    Args:
        message: The clarification message to send to the user
        
    Returns:
        Dictionary with clarification request
    """
    return {
        "success": True,
        "needs_clarification": True,
        "message": message
    }
