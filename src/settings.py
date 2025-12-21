"""
Application settings and configuration for the inventory agent.
All configurable values are centralized here for easy customization.
"""
from typing import Literal


# =============================================================================
# DATE FORMAT CONFIGURATION
# =============================================================================

# Date format used throughout the application for parsing and displaying dates
# Possible values:
#   - "YYYY-MM-DD": ISO 8601 format (e.g., "2025-12-21") - recommended for APIs
#   - "DD-MM-YYYY": European format (e.g., "21-12-2025")
DATE_FORMAT: Literal["YYYY-MM-DD", "DD-MM-YYYY"] = "YYYY-MM-DD"

# Python strftime/strptime format strings corresponding to DATE_FORMAT
# These are derived from DATE_FORMAT - do not modify directly
DATE_FORMAT_PYTHON = "%Y-%m-%d" if DATE_FORMAT == "YYYY-MM-DD" else "%d-%m-%Y"


# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

# Enable debug mode for verbose agent output
# Possible values:
#   - True: Print debug information during agent execution
#   - False: Silent execution (production mode)
AGENT_DEBUG: bool = True

# OpenAI model to use for the agent
# Possible values:
#   - "gpt-4o-mini": Faster, cheaper, good for most tasks
#   - "gpt-4o": More capable, better reasoning
#   - "gpt-4-turbo": High capability with vision support
AGENT_MODEL: str = "openai:gpt-4o-mini"


# =============================================================================
# MODEL CALL LIMIT MIDDLEWARE CONFIGURATION
# =============================================================================
# Limits the number of LLM calls to prevent infinite loops or excessive costs

# Maximum model calls per single invocation (one user message → response cycle)
# Resets with each new user message
# Possible values: Any positive integer, or None for no limit
# Recommended: 5-10 for typical agents
MODEL_CALL_RUN_LIMIT: int | None = 5

# Maximum model calls across all runs in a thread (conversation)
# Requires a checkpointer to maintain state
# Possible values: Any positive integer, or None for no limit
# Recommended: 50-100 for long conversations
MODEL_CALL_THREAD_LIMIT: int | None = 20

# Behavior when model call limit is reached
# Possible values:
#   - "continue": Block exceeded calls with error messages, agent continues
#   - "error": Raise exception immediately
#   - "end": Stop execution with message
MODEL_CALL_EXIT_BEHAVIOR: Literal["continue", "error", "end"] = "end"


# =============================================================================
# TOOL CALL LIMIT MIDDLEWARE CONFIGURATION
# =============================================================================
# Limits the number of tool calls to prevent excessive API usage

# Maximum tool calls per single invocation (one user message → response cycle)
# Resets with each new user message
# Possible values: Any positive integer, or None for no limit
# Recommended: 10-20 for typical agents
TOOL_CALL_RUN_LIMIT: int | None = 10

# Maximum tool calls across all runs in a thread (conversation)
# Requires a checkpointer to maintain state
# Possible values: Any positive integer, or None for no limit
# Recommended: 100-200 for long conversations
TOOL_CALL_THREAD_LIMIT: int | None = 50

# Behavior when tool call limit is reached
# Possible values:
#   - "continue": Block exceeded calls with error messages, agent continues
#   - "error": Raise exception immediately
#   - "end": Stop execution with message (single-tool scenarios only)
TOOL_CALL_EXIT_BEHAVIOR: Literal["continue", "error", "end"] = "continue"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def parse_date(date_string: str) -> str | None:
    """
    Parse a date string according to the configured DATE_FORMAT.

    Args:
        date_string: Date string to parse

    Returns:
        ISO format date string (YYYY-MM-DD) for database storage, or None if invalid
    """
    from datetime import datetime

    try:
        parsed = datetime.strptime(date_string, DATE_FORMAT_PYTHON)
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        return None


def format_date(iso_date: str) -> str:
    """
    Format an ISO date string according to the configured DATE_FORMAT.

    Args:
        iso_date: ISO format date string (YYYY-MM-DD)

    Returns:
        Formatted date string according to DATE_FORMAT
    """
    from datetime import datetime

    try:
        parsed = datetime.strptime(iso_date, "%Y-%m-%d")
        return parsed.strftime(DATE_FORMAT_PYTHON)
    except ValueError:
        return iso_date


def get_date_format_description() -> str:
    """
    Get human-readable description of the current date format.

    Returns:
        Description string for prompts and error messages
    """
    if DATE_FORMAT == "YYYY-MM-DD":
        return "YYYY-MM-DD (e.g., 2025-12-21)"
    else:
        return "DD-MM-YYYY (e.g., 21-12-2025)"
