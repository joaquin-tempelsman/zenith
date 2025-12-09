"""
AI processing service for OpenAI API interactions.
Handles speech-to-text transcription and LangGraph-based intent processing.
"""
import json
from typing import Dict, Any, Optional
from pathlib import Path
from openai import OpenAI
from ..config import settings
from .inventory_agent import run_inventory_agent

# Initialize OpenAI client
client = OpenAI(api_key=settings.openai_api_key)


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper.
    
    Args:
        file_path: Path to the audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)
        
    Returns:
        Transcribed text from the audio file
        
    Raises:
        FileNotFoundError: If audio file doesn't exist
        Exception: If transcription fails
    """
    audio_file_path = Path(file_path)
    
    with open(audio_file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    
    return transcript


async def transcribe_audio_async(file_path: str) -> str:
    """
    Async version of transcribe_audio for use in async contexts.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Transcribed text from the audio file
    """
    return transcribe_audio(file_path)


def parse_intent(text: str) -> Dict[str, Any]:
    """
    Parse user intent from text using OpenAI GPT with structured JSON output.
    
    The LLM analyzes keywords to determine action type:
    - Modify actions: add/remove items with quantity
    - Query actions: list items by various criteria
    
    Args:
        text: User input text to parse
        
    Returns:
        Dictionary with structured intent data based on action type:
        
        For modify actions (add/remove):
        {
            "action_type": "modify",
            "action": "add|remove",
            "item": "item_name",
            "quantity": int (optional, null means all stock),
            "category": "category_name" (for add),
            "expire_date": "YYYY-MM-DD" (optional),
            "notes": "additional notes" (optional)
        }
        
        For query actions (list):
        {
            "action_type": "list",
            "list_type": "item|expire|group|history",
            "item": "item_name" (for item/history),
            "group": "group_name" (for group/history),
            "days": int (for history, default 7)
        }
        
    Example:
        >>> parse_intent("Add 5 apples to fruits")
        {"action_type": "modify", "action": "add", "item": "apples", "quantity": 5, "category": "fruits"}
        
        >>> parse_intent("List items expiring soon")
        {"action_type": "list", "list_type": "expire"}
    """
    system_prompt = """You are an inventory management assistant. Parse user requests into structured JSON by analyzing keywords.

STEP 1: Determine action_type by keywords:
- If text contains: "add", "remove", "take", "put", "stock" → action_type = "modify"
- If text contains: "list", "show", "display", "what", "which", "history" → action_type = "list"

STEP 2: Build JSON based on action_type:

For action_type = "modify":
{
  "action_type": "modify",
  "action": "add" or "remove",
  "item": "item_name" (lowercase),
  "quantity": number or null (null = all stock),
  "category": "category_name" (required for add, lowercase),
  "expire_date": "YYYY-MM-DD" (optional),
  "notes": "any additional notes" (optional)
}

For action_type = "list":
{
  "action_type": "list",
  "list_type": "expire" | "group" | "item" | "history",
  "item": "item_name" (for item/history type, lowercase),
  "group": "group_name" (for group/history type, lowercase),
  "days": number (for history, default 7)
}

List type keywords:
- "expire", "expiring", "expiration" → list_type = "expire"
- "group", "category", "type" → list_type = "group"
- "item", "stock", specific item name → list_type = "item"
- "history", "additions", "extractions", "changes" → list_type = "history"

EXAMPLES:

Input: "Add 5 apples to fruits"
Output: {"action_type": "modify", "action": "add", "item": "apples", "quantity": 5, "category": "fruits"}

Input: "Add milk to dairy, expires 2025-12-15, keep refrigerated"
Output: {"action_type": "modify", "action": "add", "item": "milk", "quantity": null, "category": "dairy", "expire_date": "2025-12-15", "notes": "keep refrigerated"}

Input: "Remove 3 bananas"
Output: {"action_type": "modify", "action": "remove", "item": "bananas", "quantity": 3}

Input: "Remove all oranges"
Output: {"action_type": "modify", "action": "remove", "item": "oranges", "quantity": null}

Input: "List items expiring soon"
Output: {"action_type": "list", "list_type": "expire"}

Input: "Show fruits category"
Output: {"action_type": "list", "list_type": "group", "group": "fruits"}

Input: "What's the stock of apples"
Output: {"action_type": "list", "list_type": "item", "item": "apples"}

Input: "History of apple changes last 7 days"
Output: {"action_type": "list", "list_type": "history", "item": "apples", "days": 7}

Input: "Show dairy additions last 14 days"
Output: {"action_type": "list", "list_type": "history", "group": "dairy", "days": 14}

Return ONLY the JSON object, no other text."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=200
    )
    
    response_text = response.choices[0].message.content.strip()
    
    # Parse JSON response
    try:
        intent_data = json.loads(response_text)
        
        # Validate required fields based on action_type
        if "action_type" not in intent_data:
            return {"action_type": "unknown", "error": "No action_type specified"}
        
        action_type = intent_data.get("action_type", "").lower()
        intent_data["action_type"] = action_type
        
        if action_type == "modify":
            if "action" not in intent_data:
                return {"action_type": "unknown", "error": "No action specified for modify"}
            intent_data["action"] = intent_data["action"].lower()
            
            # Normalize item and category to lowercase
            if "item" in intent_data:
                intent_data["item"] = intent_data["item"].lower()
            if "category" in intent_data:
                intent_data["category"] = intent_data["category"].lower()
        
        elif action_type == "list":
            if "list_type" not in intent_data:
                return {"action_type": "unknown", "error": "No list_type specified"}
            intent_data["list_type"] = intent_data["list_type"].lower()
            
            # Normalize item and group to lowercase
            if "item" in intent_data:
                intent_data["item"] = intent_data["item"].lower()
            if "group" in intent_data:
                intent_data["group"] = intent_data["group"].lower()
            
            # Set default days for history
            if intent_data["list_type"] == "history" and "days" not in intent_data:
                intent_data["days"] = 7
        
        return intent_data
        
    except json.JSONDecodeError as e:
        return {
            "action_type": "unknown",
            "error": f"Failed to parse JSON: {str(e)}",
            "raw_response": response_text
        }


async def parse_intent_async(text: str) -> Dict[str, Any]:
    """
    Async version of parse_intent for use in async contexts.
    
    Args:
        text: User input text to parse
        
    Returns:
        Dictionary with structured intent data
    """
    return parse_intent(text)


def route_action(intent: Dict[str, Any], db) -> Any:
    """
    Route the parsed intent to the appropriate action handler.
    
    This function analyzes the intent and decides which database operations to perform.
    
    Args:
        intent: Parsed intent dictionary from parse_intent
        db: Database session
        
    Returns:
        Result from the executed action (varies by action type)
    """
    from ..database import crud
    
    action_type = intent.get("action_type")
    
    if action_type == "modify":
        return handle_modify_action(intent, db)
    elif action_type == "list":
        return handle_list_action(intent, db)
    else:
        return None


def handle_modify_action(intent: Dict[str, Any], db) -> Any:
    """
    Handle modify actions (add/remove items).
    
    Args:
        intent: Parsed intent with action_type="modify"
        db: Database session
        
    Returns:
        Modified item object or None
    """
    from ..database import crud
    
    action = intent.get("action")
    item_name = intent.get("item")
    quantity = intent.get("quantity")
    category = intent.get("category")
    expire_date_str = intent.get("expire_date")
    
    # Parse expire_date if provided
    expire_date = None
    if expire_date_str:
        try:
            from datetime import date
            expire_date = date.fromisoformat(expire_date_str)
        except ValueError:
            pass
    
    if action == "add":
        existing_item = crud.get_item_by_name(db, item_name)
        if existing_item:
            # If quantity is None, don't update (just return existing)
            if quantity is None:
                return existing_item
            return crud.update_item_by_name(db, item_name, quantity)
        else:
            # Create new item (use quantity 1 if None)
            return crud.create_item(
                db, 
                item_name, 
                quantity if quantity is not None else 1, 
                category or "general", 
                expire_date
            )
    
    elif action == "remove":
        existing_item = crud.get_item_by_name(db, item_name)
        if not existing_item:
            return None
        
        # If quantity is None, remove all (set to 0)
        if quantity is None:
            return crud.set_item_quantity(db, existing_item.id, 0)
        else:
            result = crud.update_item_by_name(db, item_name, -quantity)
            if result and result.quantity < 0:
                result.quantity = 0
                db.commit()
                db.refresh(result)
            return result
    
    return None


def handle_list_action(intent: Dict[str, Any], db) -> Any:
    """
    Handle list/query actions.
    
    Args:
        intent: Parsed intent with action_type="list"
        db: Database session
        
    Returns:
        List of items or item object based on list_type
    """
    from ..database import crud
    
    list_type = intent.get("list_type")
    
    if list_type == "expire":
        return crud.get_items_by_expiration(db)
    
    elif list_type == "group":
        group = intent.get("group")
        items = crud.get_items_by_category(db, group)
        return [item.to_dict() for item in items]
    
    elif list_type == "item":
        item_name = intent.get("item")
        return crud.get_item_by_name(db, item_name)
    
    elif list_type == "history":
        days = intent.get("days", 7)
        item = intent.get("item")
        group = intent.get("group")
        return crud.get_history(db, days, item, group)
    
    return None


def generate_response_message(intent: Dict[str, Any], result: Any) -> str:
    """
    Generate a user-friendly response message based on the action result.
    
    Args:
        intent: Parsed intent dictionary
        result: Result from database operation
        
    Returns:
        Human-readable response message
    """
    action_type = intent.get("action_type", "unknown")
    
    if action_type == "modify":
        action = intent.get("action", "unknown")
        item = intent.get("item", "item")
        quantity = intent.get("quantity")
        
        if action == "add":
            if result:
                qty_msg = f"{quantity}" if quantity else "items"
                return f"✅ Added {qty_msg} {item} to inventory. Current quantity: {result.quantity}"
            return f"✅ Created new item: {item}"
        
        elif action == "remove":
            if result:
                qty_msg = f"{quantity}" if quantity else "all"
                return f"✅ Removed {qty_msg} {item}. Remaining quantity: {result.quantity}"
            return f"❌ Item '{item}' not found in inventory"
    
    elif action_type == "list":
        list_type = intent.get("list_type", "unknown")
        
        if list_type == "expire":
            if result and len(result) > 0:
                items_list = "\n".join([f"- {r['name']}: {r['expire_date']}" for r in result[:10]])
                return f"📅 Items by expiration (recent to older):\n{items_list}"
            return "ℹ️ No items with expiration dates found"
        
        elif list_type == "group":
            group = intent.get("group", "unknown")
            if result and len(result) > 0:
                items_list = "\n".join([f"- {r['name']}: {r['quantity']} units" for r in result[:10]])
                return f"📦 Items in '{group}' group:\n{items_list}"
            return f"ℹ️ No items found in '{group}' group"
        
        elif list_type == "item":
            item = intent.get("item", "unknown")
            if result:
                expire_info = f", Expires: {result.expire_date}" if result.expire_date else ""
                return f"📊 {item}: {result.quantity} units in stock (Category: {result.category}{expire_info})"
            return f"❌ Item '{item}' not found in inventory"
        
        elif list_type == "history":
            days = intent.get("days", 7)
            item = intent.get("item")
            group = intent.get("group")
            target = item if item else group if group else "all items"
            
            if result and len(result) > 0:
                history_list = "\n".join([
                    f"- {r['date']}: {r['action']} {r['quantity']} {r['item']}"
                    for r in result[:10]
                ])
                return f"📜 History for {target} (last {days} days):\n{history_list}"
            return f"ℹ️ No history found for {target} in last {days} days"
    
    return "❌ I couldn't understand that request. Please try again."


def process_user_input(user_input: str, db) -> Dict[str, Any]:
    """
    Process user input using the LangGraph-based inventory agent.
    
    This is the main entry point for processing natural language
    inventory commands. It uses a router LLM to decide which tool
    to execute based on the user's intent.
    
    Args:
        user_input: Natural language text from the user
        db: Database session
        
    Returns:
        Dictionary containing:
        - result: Raw result from the tool execution
        - response_message: Human-readable response message
        - tool_used: Name of the tool that was executed
        - tool_args: Arguments passed to the tool
    """
    return run_inventory_agent(user_input, db)


async def process_user_input_async(user_input: str, db) -> Dict[str, Any]:
    """
    Async version of process_user_input.
    
    Args:
        user_input: Natural language text from the user
        db: Database session
        
    Returns:
        Dictionary with result and response_message
    """
    return process_user_input(user_input, db)
