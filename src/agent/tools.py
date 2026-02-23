"""
LangChain tool implementations for inventory management.

Each @tool function accesses the database session and language context
through the module-level state in agent.state.
"""
from typing import Optional
from datetime import date as date_type
import threading

from langchain_core.tools import tool

from ..config import settings
from ..database import crud
from ..models import (
    ParseIntentInput,
    ModifyDBInput,
    QueryDBInput,
    DetectLanguageInput,
    ResetDatabaseInput,
    BatchModifyDBInput,
    GetHelpInput,
    GetLinkCodeInput,
    LinkAccountInput,
    UnlinkAccountInput,
    GetLinkStatusInput,
)
from .prompts import load_prompt
from .state import (
    get_db_session,
    get_detected_language,
    set_detected_language,
    get_meta_session,
    get_chat_id,
    set_db_session,
)

# Lock that serialises all DB-mutating tool calls.
# LangChain may execute parallel tool calls in separate threads;
# SQLAlchemy sessions are NOT thread-safe, so we must ensure that only
# one tool touches the session at a time.
_db_lock = threading.Lock()


# ============================================================================
# Private helpers shared by modify_db and batch_modify_db
# ============================================================================


def _add_item(
    db,
    item_name: str,
    quantity: Optional[int],
    category: Optional[str],
    parsed_expire_date,
) -> str:
    """
    Add or update a single item in the inventory.

    Args:
        db: Database session
        item_name: Lowercase item name
        quantity: Quantity to add (None or 0 treated as 1 for new items)
        category: Category string (None defaults to 'general')
        parsed_expire_date: Parsed date object or None

    Returns:
        Result message describing the operation outcome
    """
    lang = get_detected_language()
    is_es = lang == "es"

    existing = crud.get_item_by_name(db, item_name)
    if existing:
        if quantity:
            updated = crud.update_item_by_name(db, item_name, quantity)
            if is_es:
                return (
                    f"✅ Se agregaron {quantity} a '{item_name}'. "
                    f"Nueva cantidad: {updated.quantity} en categoría '{updated.category}'"
                )
            return (
                f"✅ Added {quantity} to '{item_name}'. "
                f"New quantity: {updated.quantity} in category '{updated.category}'"
            )
        if is_es:
            return (
                f"ℹ️ El item '{item_name}' ya existe con cantidad "
                f"{existing.quantity} en categoría '{existing.category}'"
            )
        return (
            f"ℹ️ Item '{item_name}' already exists with quantity "
            f"{existing.quantity} in category '{existing.category}'"
        )

    final_qty = quantity or 1
    final_category = category.lower().strip() if category else "general"
    item = crud.create_item(db, item_name, final_qty, final_category, parsed_expire_date)
    if is_es:
        expire_info = f", vence: {item.expire_date}" if item.expire_date else ""
        return (
            f"✅ Nuevo item '{item_name}' creado con cantidad "
            f"{item.quantity} en categoría '{item.category}'{expire_info}"
        )
    expire_info = f", expires: {item.expire_date}" if item.expire_date else ""
    return (
        f"✅ Created new item '{item_name}' with quantity "
        f"{item.quantity} in category '{item.category}'{expire_info}"
    )


def _remove_item(db, item_name: str, quantity: Optional[int]) -> str:
    """
    Remove stock for a single item from the inventory.

    Args:
        db: Database session
        item_name: Lowercase item name
        quantity: Units to remove (None removes all stock)

    Returns:
        Result message describing the operation outcome
    """
    lang = get_detected_language()
    is_es = lang == "es"

    existing = crud.get_item_by_name(db, item_name)
    if not existing:
        if is_es:
            return f"❌ Item '{item_name}' no encontrado en el inventario"
        return f"❌ Item '{item_name}' not found in inventory"

    if quantity is None:
        old_qty = existing.quantity
        crud.set_item_quantity(db, existing.id, 0)
        if is_es:
            return f"✅ Se eliminaron todos los {old_qty} '{item_name}' del inventario"
        return f"✅ Removed all {old_qty} '{item_name}' from inventory"

    new_qty = max(0, existing.quantity - quantity)
    removed = existing.quantity - new_qty
    crud.set_item_quantity(db, existing.id, new_qty)
    if is_es:
        return f"✅ Se eliminaron {removed} '{item_name}'. Restante: {new_qty}"
    return f"✅ Removed {removed} '{item_name}'. Remaining: {new_qty}"


# ============================================================================
# Tool Implementations
# ============================================================================


@tool(args_schema=DetectLanguageInput)
def detect_language(user_message: str) -> str:
    """
    Detect the language of the user's message (English or Spanish).

    This should be the FIRST tool called for every user message to set
    the appropriate language context for all subsequent operations.

    Uses langdetect library for accurate language detection.
    Falls back to Spanish if neither English nor Spanish is detected.

    Args:
        user_message: The user's message to analyze

    Returns:
        Language code: 'en' for English, 'es' for Spanish
    """
    from langdetect import detect_langs
    from langdetect.lang_detect_exception import LangDetectException

    try:
        detected = detect_langs(user_message)
        if not detected:
            set_detected_language("es")
            return "es"

        first_lang = detected[0].lang
        if first_lang in ("en", "es"):
            set_detected_language(first_lang)
            return first_lang

        lang_codes = [d.lang for d in detected]
        for code in ("en", "es"):
            if code in lang_codes:
                set_detected_language(code)
                return code

        set_detected_language("es")
        return "es"

    except LangDetectException:
        set_detected_language("es")
        return "es"


@tool(args_schema=ParseIntentInput)
def parse_intent(user_message: str) -> str:
    """
    Parse user's natural language message into structured intent.

    Analyzes the user message and determines whether it's a modify action
    (add/remove items) or a query action (list/check), along with parameters
    like item name, quantity, category, etc.

    Uses the appropriate language prompt based on detected language.

    Args:
        user_message: The user's natural language message

    Returns:
        JSON string with structured intent data
    """
    import json
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    lang = get_detected_language()
    system_prompt = load_prompt("intent_parser", language=lang)

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

    Use this tool after parsing intent to execute inventory modifications.

    Args:
        action: 'add' or 'remove'
        item: Item name (will be lowercased)
        quantity: Amount to add/remove (None means all for remove)
        category: Item category (optional, will be lowercased)
        expire_date: Expiration date (format from settings)

    Returns:
        Result message describing the operation outcome
    """
    from ..utils import parse_date

    with _db_lock:
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

        _dispatch = {
            "add": lambda: _add_item(db, item_name, quantity, category, parsed_expire_date),
            "remove": lambda: _remove_item(db, item_name, quantity),
        }
        handler = _dispatch.get(action)
        if handler is None:
            lang = get_detected_language()
            if lang == "es":
                return f"❌ Acción desconocida: {action}"
            return f"❌ Unknown action: {action}"
        return handler()


@tool(args_schema=QueryDBInput)
def query_db(
    list_type: str,
    item: Optional[str] = None,
    group: Optional[str] = None,
    days: Optional[int] = 7,
) -> str:
    """
    Query inventory data for listing and checking stock.

    Args:
        list_type: Query type - 'expire', 'group', 'item', 'history', or 'summary'
        item: Item name for item/history queries
        group: Category name for group/history queries
        days: Number of days for history queries

    Returns:
        Formatted query results
    """
    with _db_lock:
        db = get_db_session()
        lang = get_detected_language()
        is_es = lang == "es"

        if item:
            item = item.lower().strip()
        if group:
            group = group.lower().strip()

        if list_type == "expire":
            items = crud.get_items_by_expiration(db)
            if not items:
                return "ℹ️ No se encontraron items con fecha de vencimiento" if is_es else "ℹ️ No items with expiration dates found"
            items_list = "\n".join([f"- {r['name']}: {r['expire_date']}" for r in items[:10]])
            header = "📅 Items por vencimiento (más próximo primero):" if is_es else "📅 Items by expiration (soonest first):"
            return f"{header}\n{items_list}"

        if list_type == "group":
            if not group:
                return "❌ Se requiere nombre de grupo/categoría para consultas por grupo" if is_es else "❌ Group/category name is required for group queries"
            items = crud.get_items_by_category(db, group)
            if not items:
                return (f"ℹ️ No se encontraron items en la categoría '{group}'" if is_es
                        else f"ℹ️ No items found in '{group}' category")
            unit = "unidades" if is_es else "units"
            items_list = "\n".join(
                [f"- {i.name}: {i.quantity} {unit}" for i in items[:10]]
            )
            header = f"📦 Items en categoría '{group}':" if is_es else f"📦 Items in '{group}' category:"
            return f"{header}\n{items_list}"

        if list_type == "item":
            if not item:
                return "❌ Se requiere nombre del item para consultas por item" if is_es else "❌ Item name is required for item queries"
            item_obj = crud.get_item_by_name(db, item)
            if not item_obj:
                return (f"❌ Item '{item}' no encontrado en el inventario" if is_es
                        else f"❌ Item '{item}' not found in inventory")
            if is_es:
                expire_info = f", Vence: {item_obj.expire_date}" if item_obj.expire_date else ""
                return (
                    f"📊 {item_obj.name}: {item_obj.quantity} unidades en stock "
                    f"(Categoría: {item_obj.category}{expire_info})"
                )
            expire_info = f", Expires: {item_obj.expire_date}" if item_obj.expire_date else ""
            return (
                f"📊 {item_obj.name}: {item_obj.quantity} units in stock "
                f"(Category: {item_obj.category}{expire_info})"
            )

        if list_type == "history":
            history = crud.get_history(db, days or 7, item, group)
            target = item or group or ("todos los items" if is_es else "all items")
            if not history:
                return (f"ℹ️ No se encontró historial para {target} en los últimos {days} días" if is_es
                        else f"ℹ️ No history found for {target} in the last {days} days")
            history_list = "\n".join(
                [f"- {h['date']}: {h['action']} {h['quantity']} {h['item']}" for h in history[:10]]
            )
            header = (f"📜 Historial de {target} (últimos {days} días):" if is_es
                      else f"📜 History for {target} (last {days} days):")
            return f"{header}\n{history_list}"

        if list_type == "summary":
            summary = crud.get_inventory_summary(db)
            cats = summary["categories"]
            cats_str = ", ".join(cats) if cats else ("ninguna" if is_es else "none")
            if is_es:
                return (
                    f"📊 Resumen del Inventario:\n"
                    f"- Items únicos: {summary['total_items']}\n"
                    f"- Cantidad total: {summary['total_quantity']}\n"
                    f"- Categorías ({len(cats)}): {cats_str}"
                )
            return (
                f"📊 Inventory Summary:\n"
                f"- Unique items: {summary['total_items']}\n"
                f"- Total quantity: {summary['total_quantity']}\n"
                f"- Categories ({len(cats)}): {cats_str}"
            )

        return (f"❌ Tipo de lista desconocido: {list_type}" if is_es
                else f"❌ Unknown list_type: {list_type}")



@tool(args_schema=ResetDatabaseInput)
def reset_database(confirmation: str) -> str:
    """
    Reset the database by deleting all items. REQUIRES EXPLICIT CONFIRMATION.

    This is a DESTRUCTIVE operation that cannot be undone.
    The user MUST provide the exact word 'OK' to proceed.

    If the user has not explicitly confirmed, DO NOT call this tool.
    Instead, ask them to confirm by saying 'OK'.

    Args:
        confirmation: Must be exactly 'OK' to proceed

    Returns:
        Result message describing the operation outcome
    """
    lang = get_detected_language()

    if confirmation.upper().strip() != "OK":
        if lang == "es":
            return "⚠️ Operación cancelada. Para reiniciar la base de datos, el usuario debe confirmar explícitamente diciendo 'OK'."
        return "⚠️ Operation cancelled. To reset the database, the user must explicitly confirm by saying 'OK'."

    with _db_lock:
        db = get_db_session()
        count = crud.delete_all_items(db)

    if lang == "es":
        return f"🗑️ Base de datos reiniciada. Se eliminaron {count} items del inventario."
    return f"🗑️ Database reset complete. Deleted {count} items from inventory."


@tool(args_schema=BatchModifyDBInput)
def batch_modify_db(
    action: str,
    items: list[str],
    quantity: Optional[int] = None,
    category: Optional[str] = None,
) -> str:
    """
    Modify multiple inventory items in a single operation.

    Use this tool when the user wants to add or remove multiple items at once.

    Args:
        action: 'add' or 'remove'
        items: List of item names
        quantity: Quantity per item (default 1 for add, all for remove)
        category: Category for all items (optional)

    Returns:
        Grouped summary listing affected and not-impacted items
    """
    with _db_lock:
        db = get_db_session()
        lang = get_detected_language()

        final_category = category.lower().strip() if category else "general"

        affected: list[str] = []
        not_impacted: list[str] = []
        failed: list[str] = []

        for raw_name in items:
            item_name = raw_name.lower().strip()
            if action == "add":
                msg = _add_item(db, item_name, quantity, final_category, None)
            elif action == "remove":
                msg = _remove_item(db, item_name, quantity)
            else:
                return f"❌ Unknown action: {action}"

            if msg.startswith("❌"):
                failed.append(item_name)
            elif msg.startswith("ℹ️"):
                not_impacted.append(item_name)
            else:
                affected.append(item_name)

    return _format_batch_summary(action, affected, not_impacted, failed, lang)


def _format_batch_summary(
    action: str,
    affected: list[str],
    not_impacted: list[str],
    failed: list[str],
    lang: str,
) -> str:
    """
    Build a human-readable grouped summary for a batch operation.

    Args:
        action: 'add' or 'remove'
        affected: Item names that were successfully modified
        not_impacted: Item names that were skipped (already exist / not found)
        failed: Item names that caused errors
        lang: Language code ('en' or 'es')

    Returns:
        Formatted multi-line summary string
    """
    total = len(affected) + len(not_impacted) + len(failed)
    is_es = lang == "es"

    action_labels = {
        "add": ("Agregados", "Added"),
        "remove": ("Eliminados", "Removed"),
    }
    action_label = action_labels.get(action, (action, action))[0 if is_es else 1]

    header = (
        f"📦 Operación por lotes completada ({len(affected)}/{total}):"
        if is_es
        else f"📦 Batch operation complete ({len(affected)}/{total}):"
    )

    parts = [header]

    if affected:
        names = ", ".join(affected)
        parts.append(f"✅ {action_label}: {names}")

    if not_impacted:
        names = ", ".join(not_impacted)
        label = "Sin cambios" if is_es else "Not impacted"
        parts.append(f"ℹ️ {label}: {names}")

    if failed:
        names = ", ".join(failed)
        label = "Fallidos" if is_es else "Failed"
        parts.append(f"❌ {label}: {names}")

    return "\n".join(parts)


@tool(args_schema=GetHelpInput)
def get_help(topic: Optional[str] = None) -> str:
    """
    Provide help information about available commands and how to use the bot.

    Call this tool when the user asks for help, instructions, commands,
    or how to use the system.

    Args:
        topic: Optional specific topic to get help on

    Returns:
        Formatted help message with available commands and examples
    """
    lang = get_detected_language()

    if lang == "es":
        return """📚 **Comandos Disponibles**

🔹 **Agregar items** – "Añadir 5 manzanas a frutas"
🔹 **Quitar items** – "Quitar 3 bananas"
🔹 **Agregar múltiples items** – "Añadir manzanas, bananas y naranjas a frutas"
🔹 **Ver stock de un item** – "Cuánto hay de leche"
🔹 **Listar por categoría** – "Mostrar categoría frutas"
🔹 **Ver items por vencimiento** – "Mostrar items que vencen pronto"
🔹 **Ver historial** – "Historial de cambios últimos 7 días"
🔹 **Resumen del inventario** – "Dame un resumen del inventario"
🔹 **Reiniciar base de datos** – "Reiniciar base de datos" (requiere OK)

💡 **Tip:** Puedes hablar naturalmente, el bot entiende español e inglés."""

    return """📚 **Available Commands**

🔹 **Add items** – "Add 5 apples to fruits"
🔹 **Remove items** – "Remove 3 bananas"
🔹 **Add multiple items** – "Add apples, bananas, and oranges to fruits"
🔹 **Check item stock** – "How much milk do we have"
🔹 **List by category** – "Show fruits category"
🔹 **View items by expiration** – "Show items expiring soon"
🔹 **View history** – "History of changes last 7 days"
🔹 **Inventory summary** – "Give me an inventory summary"
🔹 **Reset database** – "Reset database" (requires OK)

💡 **Tip:** You can speak naturally, the bot understands English and Spanish."""


# ============================================================================
# Account Linking Tools
# ============================================================================


@tool(args_schema=GetLinkCodeInput)
def get_my_link_code(dummy: Optional[str] = None) -> str:
    """Return the unique link code for the current user.

    The code is permanent and can be shared with other users so they can
    link their account to this user's inventory database.

    Args:
        dummy: Unused placeholder

    Returns:
        Message containing the user's link code
    """
    from ..database import crud as _crud

    meta = get_meta_session()
    chat_id = get_chat_id()
    lang = get_detected_language()
    code = _crud.get_or_create_user_code(meta, chat_id)

    if lang == "es":
        return (
            f"🔑 Tu código de vinculación es: **{code}**\n"
            "Compartí este código con otro usuario para que pueda vincular su cuenta a tu inventario."
        )
    return (
        f"🔑 Your link code is: **{code}**\n"
        "Share this code with another user so they can link their account to your inventory."
    )


@tool(args_schema=LinkAccountInput)
def link_account(code: str) -> str:
    """Link the current user's account to another user's inventory database.

    After linking, all inventory operations will read/write the owner's
    database instead of the caller's own database.

    Args:
        code: Link code provided by the account owner

    Returns:
        Success or error message
    """
    from ..database import crud as _crud
    from ..database.models import get_session_for_user

    meta = get_meta_session()
    chat_id = get_chat_id()
    lang = get_detected_language()
    is_es = lang == "es"

    result = _crud.link_account(meta, code.strip(), chat_id)

    if not result["ok"]:
        messages = {
            "invalid_code": (
                "❌ Código inválido. Verificá el código e intentá de nuevo.",
                "❌ Invalid code. Please check the code and try again.",
            ),
            "self_link": (
                "❌ No podés vincular tu cuenta a vos mismo.",
                "❌ You cannot link your account to yourself.",
            ),
            "already_linked": (
                "❌ Tu cuenta ya está vinculada a otro usuario. Desvinculá primero con 'desvincular cuenta'.",
                "❌ Your account is already linked to another user. Unlink first with 'unlink account'.",
            ),
        }
        msg_pair = messages.get(result["msg"], ("❌ Error desconocido.", "❌ Unknown error."))
        return msg_pair[0] if is_es else msg_pair[1]

    # Swap DB session to the owner's database immediately
    owner_chat_id = result["owner_chat_id"]
    new_db = get_session_for_user(owner_chat_id)
    set_db_session(new_db)

    if is_es:
        return "✅ ¡Cuenta vinculada exitosamente! Ahora estás trabajando en el inventario compartido."
    return "✅ Account linked successfully! You are now working on the shared inventory."


@tool(args_schema=UnlinkAccountInput)
def unlink_account(dummy: Optional[str] = None) -> str:
    """Unlink the current user from a shared inventory and return to their own database.

    Args:
        dummy: Unused placeholder

    Returns:
        Success or error message
    """
    from ..database import crud as _crud
    from ..database.models import get_session_for_user

    meta = get_meta_session()
    chat_id = get_chat_id()
    lang = get_detected_language()
    is_es = lang == "es"

    result = _crud.unlink_account(meta, chat_id)

    if not result["ok"]:
        if is_es:
            return "ℹ️ Tu cuenta no está vinculada a ningún otro usuario."
        return "ℹ️ Your account is not linked to any other user."

    # Swap DB session back to caller's own database
    own_db = get_session_for_user(chat_id)
    set_db_session(own_db)

    if is_es:
        return "✅ Cuenta desvinculada. Ahora estás trabajando en tu propio inventario."
    return "✅ Account unlinked. You are now working on your own inventory."


@tool(args_schema=GetLinkStatusInput)
def get_link_status(dummy: Optional[str] = None) -> str:
    """Show the current account linking status for the user.

    Reports whether the user is linked to someone else's inventory, and
    how many users are linked to the user's own inventory.

    Args:
        dummy: Unused placeholder

    Returns:
        Formatted status message
    """
    from ..database import crud as _crud

    meta = get_meta_session()
    chat_id = get_chat_id()
    lang = get_detected_language()
    is_es = lang == "es"

    # Check if this user is linked to someone
    effective = _crud.resolve_effective_chat_id(meta, chat_id)
    linked_to_other = effective != chat_id

    # Check how many are linked to this user
    linked_users = _crud.get_linked_users(meta, chat_id)
    count = len(linked_users)

    parts: list[str] = []

    if linked_to_other:
        if is_es:
            parts.append("🔗 Tu cuenta está vinculada al inventario de otro usuario.")
        else:
            parts.append("🔗 Your account is linked to another user's inventory.")
    else:
        if is_es:
            parts.append("🔓 Tu cuenta no está vinculada a nadie. Estás usando tu propio inventario.")
        else:
            parts.append("🔓 Your account is not linked to anyone. You are using your own inventory.")

    if count:
        if is_es:
            parts.append(f"👥 {count} usuario(s) están vinculados a tu inventario.")
        else:
            parts.append(f"👥 {count} user(s) are linked to your inventory.")

    return "\n".join(parts)
