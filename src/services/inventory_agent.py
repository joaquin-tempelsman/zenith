"""
LangGraph-based inventory management agent.
Uses a router node (LLM) to decide which tool to execute based on user input.
"""
import json
from typing import TypedDict, Annotated, Literal, Optional, List, Any
from openai import OpenAI
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from ..config import settings
from . import inventory_tools

# Initialize OpenAI client
client = OpenAI(api_key=settings.openai_api_key)

# Define tool names
TOOL_ADD_ITEM = "add_item"
TOOL_REMOVE_ITEM = "remove_item"
TOOL_GET_ITEM_STOCK = "get_item_stock"
TOOL_LIST_BY_CATEGORY = "list_by_category"
TOOL_LIST_EXPIRING = "list_expiring"
TOOL_GET_HISTORY = "get_history"
TOOL_GET_SUMMARY = "get_summary"
TOOL_CLARIFY = "clarify"


class AgentState(TypedDict):
    """State that flows through the graph."""
    user_input: str
    db: Any
    existing_categories: List[str]
    tool_name: str
    tool_args: dict
    result: dict
    response_message: str


def get_router_system_prompt(existing_categories: List[str]) -> str:
    """
    Generate the system prompt for the router with current categories.
    
    Args:
        existing_categories: List of existing category names in the database
        
    Returns:
        System prompt string for the router LLM
    """
    categories_str = ", ".join(existing_categories) if existing_categories else "none yet"
    
    return f"""You are an inventory management router. Analyze user requests and decide which tool to call.

EXISTING CATEGORIES in the inventory: [{categories_str}]

Available tools:

1. add_item - Add items to inventory
   Arguments: item_name (required), quantity (int, optional), category (str, optional), expire_date (YYYY-MM-DD, optional), notes (str, optional)
   Use when: user wants to add, put, stock items
   IMPORTANT: If no category is specified, infer it from the item name or existing categories. Only create a new category if none match.

2. remove_item - Remove items from inventory
   Arguments: item_name (required), quantity (int, optional - null means remove all)
   Use when: user wants to remove, take, use items

3. get_item_stock - Check stock of a specific item
   Arguments: item_name (required)
   Use when: user asks about stock, quantity of a specific item

4. list_by_category - List items in a category/group
   Arguments: category (required)
   Use when: user wants to see items in a category, group, or type

5. list_expiring - List items by expiration date
   Arguments: none
   Use when: user asks about expiring items, expiration dates

6. get_history - Get history of changes
   Arguments: days (int, default 7), item_name (optional), category (optional)
   Use when: user asks about history, recent changes, additions, removals

7. get_summary - Get inventory overview
   Arguments: none
   Use when: user wants a summary, overview, or statistics

8. clarify - Ask for clarification
   Arguments: message (required - the clarification question)
   Use when: the request is unclear, ambiguous, or missing critical information

RESPONSE FORMAT - Return ONLY valid JSON:
{{
  "tool": "<tool_name>",
  "args": {{<arguments>}}
}}

CATEGORY INFERENCE RULES (for add_item):
- If user specifies a category, use it (lowercase)
- If item matches an existing category context, use that category
- Common mappings: milk/cheese/yogurt→dairy, apple/banana/orange→fruits, carrot/potato→vegetables, chicken/beef→meat, bread/pasta→grains
- If uncertain but can reasonably infer, use the inferred category
- Only use "general" if truly uncategorizable

EXAMPLES:

Input: "Add 5 apples"
Existing categories: [fruits, dairy, vegetables]
Output: {{"tool": "add_item", "args": {{"item_name": "apples", "quantity": 5, "category": "fruits"}}}}

Input: "Add milk"
Existing categories: [fruits, vegetables]
Output: {{"tool": "add_item", "args": {{"item_name": "milk", "quantity": 1, "category": "dairy"}}}}

Input: "Remove 3 bananas"
Output: {{"tool": "remove_item", "args": {{"item_name": "bananas", "quantity": 3}}}}

Input: "Remove all oranges"
Output: {{"tool": "remove_item", "args": {{"item_name": "oranges", "quantity": null}}}}

Input: "What's the stock of apples?"
Output: {{"tool": "get_item_stock", "args": {{"item_name": "apples"}}}}

Input: "Show dairy items"
Output: {{"tool": "list_by_category", "args": {{"category": "dairy"}}}}

Input: "What's expiring soon?"
Output: {{"tool": "list_expiring", "args": {{}}}}

Input: "Show changes last 14 days"
Output: {{"tool": "get_history", "args": {{"days": 14}}}}

Input: "Give me a summary"
Output: {{"tool": "get_summary", "args": {{}}}}

Input: "Do the thing"
Output: {{"tool": "clarify", "args": {{"message": "I didn't understand your request. Could you please specify what action you want to perform? For example: add items, remove items, check stock, or list items."}}}}

Input: "Add something"
Output: {{"tool": "clarify", "args": {{"message": "What item would you like to add to the inventory? Please specify the item name and optionally the quantity."}}}}"""


def router_node(state: AgentState) -> AgentState:
    """
    Router node that uses LLM to decide which tool to call.
    
    Args:
        state: Current agent state with user input
        
    Returns:
        Updated state with tool_name and tool_args set
    """
    user_input = state["user_input"]
    existing_categories = state.get("existing_categories", [])
    
    system_prompt = get_router_system_prompt(existing_categories)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0.1,
        max_tokens=300
    )
    
    response_text = response.choices[0].message.content.strip()
    
    try:
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        parsed = json.loads(response_text)
        state["tool_name"] = parsed.get("tool", TOOL_CLARIFY)
        state["tool_args"] = parsed.get("args", {})
    except json.JSONDecodeError:
        state["tool_name"] = TOOL_CLARIFY
        state["tool_args"] = {"message": "I had trouble understanding that request. Could you please rephrase?"}
    
    return state


def execute_add_item(state: AgentState) -> AgentState:
    """Execute the add_item tool."""
    db = state["db"]
    args = state["tool_args"]
    
    result = inventory_tools.add_item(
        db=db,
        item_name=args.get("item_name", ""),
        quantity=args.get("quantity"),
        category=args.get("category"),
        expire_date=args.get("expire_date"),
        notes=args.get("notes")
    )
    state["result"] = result
    state["response_message"] = format_add_response(result)
    return state


def execute_remove_item(state: AgentState) -> AgentState:
    """Execute the remove_item tool."""
    db = state["db"]
    args = state["tool_args"]
    
    result = inventory_tools.remove_item(
        db=db,
        item_name=args.get("item_name", ""),
        quantity=args.get("quantity")
    )
    state["result"] = result
    state["response_message"] = format_remove_response(result)
    return state


def execute_get_item_stock(state: AgentState) -> AgentState:
    """Execute the get_item_stock tool."""
    db = state["db"]
    args = state["tool_args"]
    
    result = inventory_tools.get_item_stock(
        db=db,
        item_name=args.get("item_name", "")
    )
    state["result"] = result
    state["response_message"] = format_stock_response(result)
    return state


def execute_list_by_category(state: AgentState) -> AgentState:
    """Execute the list_by_category tool."""
    db = state["db"]
    args = state["tool_args"]
    
    result = inventory_tools.list_items_by_category(
        db=db,
        category=args.get("category", "")
    )
    state["result"] = result
    state["response_message"] = format_category_response(result)
    return state


def execute_list_expiring(state: AgentState) -> AgentState:
    """Execute the list_expiring tool."""
    db = state["db"]
    
    result = inventory_tools.list_expiring_items(db=db)
    state["result"] = result
    state["response_message"] = format_expiring_response(result)
    return state


def execute_get_history(state: AgentState) -> AgentState:
    """Execute the get_history tool."""
    db = state["db"]
    args = state["tool_args"]
    
    result = inventory_tools.get_item_history(
        db=db,
        days=args.get("days", 7),
        item_name=args.get("item_name"),
        category=args.get("category")
    )
    state["result"] = result
    state["response_message"] = format_history_response(result)
    return state


def execute_get_summary(state: AgentState) -> AgentState:
    """Execute the get_summary tool."""
    db = state["db"]
    
    result = inventory_tools.get_inventory_summary(db=db)
    state["result"] = result
    state["response_message"] = format_summary_response(result)
    return state


def execute_clarify(state: AgentState) -> AgentState:
    """Execute the clarify tool."""
    args = state["tool_args"]
    
    result = inventory_tools.request_clarification(
        message=args.get("message", "Could you please clarify your request?")
    )
    state["result"] = result
    state["response_message"] = f"❓ {result['message']}"
    return state


def route_to_tool(state: AgentState) -> str:
    """
    Conditional edge function to route to the appropriate tool node.
    
    Args:
        state: Current agent state with tool_name set
        
    Returns:
        Name of the tool node to route to
    """
    tool_name = state.get("tool_name", TOOL_CLARIFY)
    
    tool_mapping = {
        TOOL_ADD_ITEM: "add_item_node",
        TOOL_REMOVE_ITEM: "remove_item_node",
        TOOL_GET_ITEM_STOCK: "get_item_stock_node",
        TOOL_LIST_BY_CATEGORY: "list_by_category_node",
        TOOL_LIST_EXPIRING: "list_expiring_node",
        TOOL_GET_HISTORY: "get_history_node",
        TOOL_GET_SUMMARY: "get_summary_node",
        TOOL_CLARIFY: "clarify_node"
    }
    
    return tool_mapping.get(tool_name, "clarify_node")


# Response formatting functions

def format_add_response(result: dict) -> str:
    """Format response for add_item operation."""
    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Unknown error')}"
    
    action = result.get("action")
    item = result.get("item", "item")
    
    if action == "created":
        return f"✅ Created new item '{item}' with quantity {result.get('quantity')} in category '{result.get('category')}'."
    elif action == "updated":
        return f"✅ Added {result.get('quantity_added')} to '{item}'. New quantity: {result.get('new_quantity')}"
    elif action == "exists":
        return f"ℹ️ Item '{item}' already exists with quantity {result.get('current_quantity')} in category '{result.get('category')}'."
    
    return "✅ Item added successfully."


def format_remove_response(result: dict) -> str:
    """Format response for remove_item operation."""
    if not result.get("success"):
        return f"❌ {result.get('error', 'Item not found')}"
    
    item = result.get("item", "item")
    action = result.get("action")
    
    if action == "removed_all":
        return f"✅ Removed all {result.get('quantity_removed')} '{item}' from inventory."
    else:
        return f"✅ Removed {result.get('quantity_removed')} '{item}'. Remaining: {result.get('remaining_quantity')}"


def format_stock_response(result: dict) -> str:
    """Format response for get_item_stock operation."""
    if not result.get("success"):
        return f"❌ {result.get('error', 'Item not found')}"
    
    item = result.get("item")
    quantity = result.get("quantity")
    category = result.get("category")
    expire_date = result.get("expire_date")
    
    expire_info = f", Expires: {expire_date}" if expire_date else ""
    return f"📊 {item}: {quantity} units in stock (Category: {category}{expire_info})"


def format_category_response(result: dict) -> str:
    """Format response for list_by_category operation."""
    category = result.get("category", "unknown")
    items = result.get("items", [])
    
    if not items:
        return f"ℹ️ No items found in '{category}' category."
    
    items_list = "\n".join([f"- {item['name']}: {item['quantity']} units" for item in items[:10]])
    return f"📦 Items in '{category}' category:\n{items_list}"


def format_expiring_response(result: dict) -> str:
    """Format response for list_expiring operation."""
    items = result.get("items", [])
    
    if not items:
        return "ℹ️ No items with expiration dates found."
    
    items_list = "\n".join([f"- {item['name']}: {item['expire_date']}" for item in items[:10]])
    return f"📅 Items by expiration (soonest first):\n{items_list}"


def format_history_response(result: dict) -> str:
    """Format response for get_history operation."""
    history = result.get("history", [])
    days = result.get("days", 7)
    item_filter = result.get("filter_item")
    category_filter = result.get("filter_category")
    
    target = item_filter or category_filter or "all items"
    
    if not history:
        return f"ℹ️ No history found for {target} in the last {days} days."
    
    history_list = "\n".join([
        f"- {h['date']}: {h['action']} {h['quantity']} {h['item']}"
        for h in history[:10]
    ])
    return f"📜 History for {target} (last {days} days):\n{history_list}"


def format_summary_response(result: dict) -> str:
    """Format response for get_summary operation."""
    total_items = result.get("total_unique_items", 0)
    total_quantity = result.get("total_quantity", 0)
    categories = result.get("categories", [])
    
    categories_str = ", ".join(categories) if categories else "none"
    return f"📊 Inventory Summary:\n- Unique items: {total_items}\n- Total quantity: {total_quantity}\n- Categories ({len(categories)}): {categories_str}"


def build_inventory_graph() -> StateGraph:
    """
    Build and compile the LangGraph for inventory management.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("add_item_node", execute_add_item)
    workflow.add_node("remove_item_node", execute_remove_item)
    workflow.add_node("get_item_stock_node", execute_get_item_stock)
    workflow.add_node("list_by_category_node", execute_list_by_category)
    workflow.add_node("list_expiring_node", execute_list_expiring)
    workflow.add_node("get_history_node", execute_get_history)
    workflow.add_node("get_summary_node", execute_get_summary)
    workflow.add_node("clarify_node", execute_clarify)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add conditional edges from router to tool nodes
    workflow.add_conditional_edges(
        "router",
        route_to_tool,
        {
            "add_item_node": "add_item_node",
            "remove_item_node": "remove_item_node",
            "get_item_stock_node": "get_item_stock_node",
            "list_by_category_node": "list_by_category_node",
            "list_expiring_node": "list_expiring_node",
            "get_history_node": "get_history_node",
            "get_summary_node": "get_summary_node",
            "clarify_node": "clarify_node"
        }
    )
    
    # All tool nodes end the graph
    workflow.add_edge("add_item_node", END)
    workflow.add_edge("remove_item_node", END)
    workflow.add_edge("get_item_stock_node", END)
    workflow.add_edge("list_by_category_node", END)
    workflow.add_edge("list_expiring_node", END)
    workflow.add_edge("get_history_node", END)
    workflow.add_edge("get_summary_node", END)
    workflow.add_edge("clarify_node", END)
    
    return workflow.compile()


# Cached compiled graph
_compiled_graph = None


def get_inventory_graph():
    """
    Get the compiled inventory graph (cached).
    
    Returns:
        Compiled StateGraph
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_inventory_graph()
    return _compiled_graph


def run_inventory_agent(user_input: str, db: Session) -> dict:
    """
    Run the inventory agent with user input.
    
    Args:
        user_input: The user's text input
        db: Database session
        
    Returns:
        Dictionary with result and response_message
    """
    # Get existing categories for context
    existing_categories = inventory_tools.get_all_categories(db)
    
    # Initialize state
    initial_state: AgentState = {
        "user_input": user_input,
        "db": db,
        "existing_categories": existing_categories,
        "tool_name": "",
        "tool_args": {},
        "result": {},
        "response_message": ""
    }
    
    # Run the graph
    graph = get_inventory_graph()
    final_state = graph.invoke(initial_state)
    
    return {
        "result": final_state.get("result", {}),
        "response_message": final_state.get("response_message", ""),
        "tool_used": final_state.get("tool_name", ""),
        "tool_args": final_state.get("tool_args", {})
    }
