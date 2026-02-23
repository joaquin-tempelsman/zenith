"""
Agent creation and execution logic for inventory management.

Provides create_inventory_agent and run_inventory_agent as the main
entry points for the LangChain-based agent system.
"""
from typing import Optional, Any
from sqlalchemy.orm import Session

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware

from ..models import AgentConfig
from ..database import crud
from .prompts import Language, load_prompt
from .state import (
    set_db_session,
    set_chat_id,
    get_detected_language,
)
from .tools import (
    detect_language,
    parse_intent,
    modify_db,
    query_db,
    batch_modify_db,
    reset_database,
    get_help,
)


def get_existing_categories() -> str:
    """
    Get existing categories from database for agent context.

    Returns:
        Comma-separated list of category names, or 'none' if unavailable
    """
    from .state import get_db_session
    try:
        db = get_db_session()
        summary = crud.get_inventory_summary(db)
        categories = summary.get("categories", [])
        return ", ".join(categories) if categories else "none"
    except RuntimeError:
        return "none"


def create_inventory_agent(config: Optional[AgentConfig] = None, language: Language = "en"):
    """
    Create and configure the inventory management LangChain agent.

    Builds the agent with middleware limits and a language-appropriate
    system prompt that includes existing inventory categories.

    Args:
        config: AgentConfig with middleware and model settings.
                If None, creates one from current settings.py values.
        language: Language code for the system prompt ('en' or 'es')

    Returns:
        Configured LangChain agent ready for invocation
    """
    if config is None:
        config = AgentConfig.from_settings()

    existing_categories = get_existing_categories()
    system_prompt = load_prompt(
        "inventory_agent",
        language=language,
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

    return create_agent(
        model=config.agent_model,
        tools=[detect_language, parse_intent, modify_db, query_db, batch_modify_db, reset_database, get_help],
        system_prompt=system_prompt,
        middleware=middleware,
        debug=config.agent_debug,
    )


def run_inventory_agent(user_input: str, db: Session, chat_id: int) -> dict[str, Any]:
    """
    Run the inventory agent for a single user request.

    Flow:
    1. Store database session and chat_id in module-level state for tools
    2. Pre-detect language to pick the right system prompt
    3. Create agent with language-specific context
    4. Invoke agent with a RunnableConfig that sets LangSmith thread metadata
    5. Extract and return the last AI message

    The ``RunnableConfig`` passed to ``agent.invoke`` carries:
    - ``configurable["thread_id"]``: used by LangGraph checkpointers to
      separate per-user memory threads.
    - ``metadata["chat_id"]`` and ``metadata["session_id"]``: surfaced in
      LangSmith so every trace is tagged with the originating Telegram user
      and grouped into that user's thread view.
    - ``tags``: convenience tag ``user:<chat_id>`` for quick filtering.

    Args:
        user_input: User's natural language input (text or transcribed audio)
        db: SQLAlchemy database session for the current request
        chat_id: Telegram chat/user ID; used for LangSmith thread isolation

    Returns:
        Dictionary with keys:
            result (str): 'success' on completion
            response_message (str): Agent's final reply text
            tools_used (list[str]): Names of tools called during execution
            metadata (dict): Extra info including detected language and chat_id
    """
    from langchain_core.messages import HumanMessage
    from langchain_core.runnables import RunnableConfig

    set_db_session(db)
    set_chat_id(chat_id)

    # Pre-detect language so the system prompt is in the right language
    detect_language.invoke({"user_message": user_input})
    language = get_detected_language()

    agent = create_inventory_agent(language=language)

    run_config = RunnableConfig(
        configurable={"thread_id": str(chat_id)},
        metadata={"chat_id": str(chat_id), "session_id": str(chat_id)},
        tags=[f"user:{chat_id}"],
    )
    result = agent.invoke({"messages": [HumanMessage(content=user_input)]}, run_config)

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
        "metadata": {"language": language, "chat_id": chat_id},
    }

