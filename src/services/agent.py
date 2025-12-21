"""
LangChain 1.0 Agent implementation for inventory management.
Uses create_agent with structured tools for parse_intent, modify_db, and query_db.
"""
from typing import Optional, Any
from sqlalchemy.orm import Session
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config import settings
from ..prompts import load_prompt
from ..database import crud
from ..models import (
    AgentConfig,
    ModifyIntentRequest,
    ListIntentRequest,
    ParsedIntent,
)


# Module-level database session holder
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


# ============================================================================
# Tool Input Schemas
# ============================================================================


class ParseIntentInput(BaseModel):
    """Input schema for the parse_intent tool."""

    user_message: str = Field(
        ...,
        description="The user's natural language message to parse into structured intent",
    )


class ModifyDBInput(BaseModel):
    """Input schema for the modify_db tool - modifies inventory items."""

    action: str = Field(
        ..., description="Action to perform: 'add' or 'remove'"
    )
    item: str = Field(..., description="Item name (lowercase)")
    quantity: Optional[int] = Field(
        None, description="Quantity to add/remove. None means all stock for remove."
    )
    category: Optional[str] = Field(
        None, description="Category for the item (optional, lowercase)"
    )
    expire_date: Optional[str] = Field(
        None, description="Expiration date in YYYY-MM-DD format"
    )


class QueryDBInput(BaseModel):
    """Input schema for the query_db tool - queries inventory data."""

    list_type: str = Field(
        ...,
        description="Type of query: 'expire', 'group', 'item', 'history', or 'summary'",
    )
    item: Optional[str] = Field(
        None, description="Item name for item/history queries (lowercase)"
    )
    group: Optional[str] = Field(
        None, description="Category/group name for group/history queries (lowercase)"
    )
    days: Optional[int] = Field(
        7, description="Number of days for history queries"
    )


# ============================================================================
# Tool Implementations
# ============================================================================


@tool(args_schema=ParseIntentInput)
def parse_intent(user_message: str) -> str:
    """
    Parse user's natural language message into structured intent.

    This tool analyzes the user message and determines:
    - Whether it's a modify action (add/remove items) or query action (list/check)
    - The specific parameters like item name, quantity, category, etc.

    Args:
        user_message: The user's natural language message

    Returns:
        JSON string with structured intent data
    """
    import json
    from openai import OpenAI
    from pathlib import Path

    client = OpenAI(api_key=settings.openai_api_key)

    prompt_path = Path(__file__).parent.parent / "prompts" / "tool_intent_parser.txt"
    system_prompt = prompt_path.read_text()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content.strip()


@tool(args_schema=ModifyDBInput)
def modify_db(
    action: str,
    item: str,
    quantity: Optional[int] = None,
    category: Optional[str] = None,
    expire_date: Optional[str] = None,
) -> str:
    """
    Modify inventory items by adding or removing stock.

    Use this tool after parsing intent to execute inventory modifications:
    - Add new items or increase quantity of existing items
    - Remove items or decrease quantity

    Args:
        action: 'add' or 'remove'
        item: Item name (will be lowercased)
        quantity: Amount to add/remove (None means all for remove)
        category: Item category (optional, will be lowercased)
        expire_date: Expiration date (format from settings)

    Returns:
        Result message describing the operation outcome
    """
    from datetime import date as date_type
    from ..settings import parse_date, format_date

    db = get_db_session()
    item_name = item.lower().strip()

    parsed_expire_date = None
    if expire_date:
        iso_date = parse_date(expire_date)
        if iso_date:
            parsed_expire_date = date_type.fromisoformat(iso_date)
        else:
            try:
                parsed_expire_date = date_type.fromisoformat(expire_date)
            except ValueError:
                pass

    if action == "add":
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
                db, item_name, final_quantity, final_category, parsed_expire_date
            )
            expire_info = (
                f", expires: {new_item.expire_date}" if new_item.expire_date else ""
            )
            return f"✅ Created new item '{item_name}' with quantity {new_item.quantity} in category '{new_item.category}'{expire_info}"

    elif action == "remove":
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

    return f"❌ Unknown action: {action}"


@tool(args_schema=QueryDBInput)
def query_db(
    list_type: str,
    item: Optional[str] = None,
    group: Optional[str] = None,
    days: Optional[int] = 7,
) -> str:
    """
    Query inventory data for listing and checking stock.

    Use this tool after parsing intent to execute inventory queries:
    - List items by expiration date
    - List items by category/group
    - Check specific item stock
    - View history of changes
    - Get inventory summary

    Args:
        list_type: Query type - 'expire', 'group', 'item', 'history', or 'summary'
        item: Item name for item/history queries
        group: Category name for group/history queries
        days: Number of days for history queries

    Returns:
        Formatted query results
    """
    db = get_db_session()

    if item:
        item = item.lower().strip()
    if group:
        group = group.lower().strip()

    if list_type == "expire":
        items = crud.get_items_by_expiration(db)
        if not items:
            return "ℹ️ No items with expiration dates found"
        items_list = "\n".join(
            [f"- {r['name']}: {r['expire_date']}" for r in items[:10]]
        )
        return f"📅 Items by expiration (soonest first):\n{items_list}"

    elif list_type == "group":
        if not group:
            return "❌ Group/category name is required for group queries"
        items = crud.get_items_by_category(db, group)
        if not items:
            return f"ℹ️ No items found in '{group}' category"
        items_list = "\n".join(
            [f"- {item_obj.name}: {item_obj.quantity} units" for item_obj in items[:10]]
        )
        return f"📦 Items in '{group}' category:\n{items_list}"

    elif list_type == "item":
        if not item:
            return "❌ Item name is required for item queries"
        item_obj = crud.get_item_by_name(db, item)
        if not item_obj:
            return f"❌ Item '{item}' not found in inventory"
        expire_info = (
            f", Expires: {item_obj.expire_date}" if item_obj.expire_date else ""
        )
        return f"📊 {item_obj.name}: {item_obj.quantity} units in stock (Category: {item_obj.category}{expire_info})"

    elif list_type == "history":
        history = crud.get_history(db, days or 7, item, group)
        target = item or group or "all items"
        if not history:
            return f"ℹ️ No history found for {target} in the last {days} days"
        history_list = "\n".join(
            [
                f"- {h['date']}: {h['action']} {h['quantity']} {h['item']}"
                for h in history[:10]
            ]
        )
        return f"📜 History for {target} (last {days} days):\n{history_list}"

    elif list_type == "summary":
        summary = crud.get_inventory_summary(db)
        total_items = summary["total_items"]
        total_quantity = summary["total_quantity"]
        categories = summary["categories"]
        categories_str = ", ".join(categories) if categories else "none"
        return f"📊 Inventory Summary:\n- Unique items: {total_items}\n- Total quantity: {total_quantity}\n- Categories ({len(categories)}): {categories_str}"

    return f"❌ Unknown list_type: {list_type}"


# ============================================================================
# Agent Creation and Execution
# ============================================================================


def get_existing_categories() -> str:
    """
    Get existing categories from database for context.

    Returns:
        Comma-separated list of categories or 'none'
    """
    try:
        db = get_db_session()
        summary = crud.get_inventory_summary(db)
        categories = summary.get("categories", [])
        return ", ".join(categories) if categories else "none"
    except RuntimeError:
        return "none"


def create_inventory_agent(config: Optional[AgentConfig] = None):
    """
    Create and configure the inventory management agent.

    Args:
        config: AgentConfig instance with settings. If None, creates from current settings.

    Returns:
        Configured LangChain agent with middleware
    """
    if config is None:
        config = AgentConfig.from_settings()
    
    existing_categories = get_existing_categories()
    system_prompt = load_prompt(
        "inventory_agent",
        existing_categories=existing_categories,
        date_format=f"{config.date_format} format",
    )

    middleware = [
        ModelCallLimitMiddleware(
            run_limit=config.model_call_run_limit,
            thread_limit=config.model_call_thread_limit,
            exit_behavior=config.model_call_exit_behavior,
        ),
        ToolCallLimitMiddleware(
            run_limit=config.tool_call_run_limit,
            thread_limit=config.tool_call_thread_limit,
            exit_behavior=config.tool_call_exit_behavior,
        ),
    ]

    agent = create_agent(
        model=config.agent_model,
        tools=[parse_intent, modify_db, query_db],
        system_prompt=system_prompt,
        middleware=middleware,
        debug=config.agent_debug,
    )

    return agent


def run_inventory_agent(user_input: str, db: Session) -> dict[str, Any]:
    """
    Run the inventory agent with user input.

    Flow:
    1. Set database session for tools
    2. Create agent with current context
    3. Invoke agent with user message
    4. Return structured response

    Args:
        user_input: User's natural language input
        db: Database session

    Returns:
        Dictionary with result, response_message, and metadata
    """
    from langchain_core.messages import HumanMessage

    set_db_session(db)

    agent = create_inventory_agent()

    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    messages = result.get("messages", [])
    response_text = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.type == "ai":
            response_text = msg.content
            break

    tools_used = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if tool_name:
                    tools_used.append(tool_name)

    return {
        "result": "success",
        "response_message": response_text,
        "tools_used": tools_used,
        "metadata": {},
    }
