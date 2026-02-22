"""
Compatibility shim for services.agent.

All implementation has been moved to:
  - src/agent/tools.py   (@tool functions)
  - src/agent/core.py    (create_inventory_agent, run_inventory_agent)
  - src/agent/state.py   (session/language state)
  - src/agent/prompts/   (prompt loading)
"""
from ..agent.core import create_inventory_agent, run_inventory_agent
from ..agent.state import (
    set_db_session,
    get_db_session,
    set_detected_language,
    get_detected_language,
    set_chat_id,
    get_chat_id,
)
from ..agent.tools import (
    detect_language,
    parse_intent,
    modify_db,
    query_db,
    batch_modify_db,
    reset_database,
    get_help,
)

__all__ = [
    "create_inventory_agent",
    "run_inventory_agent",
    "set_db_session",
    "get_db_session",
    "set_detected_language",
    "get_detected_language",
    "set_chat_id",
    "get_chat_id",
    "detect_language",
    "parse_intent",
    "modify_db",
    "query_db",
    "batch_modify_db",
    "reset_database",
    "get_help",
]
