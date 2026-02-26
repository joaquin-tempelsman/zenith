"""
Agent configuration model.

Centralizes all agent settings from settings.py in a single Pydantic model
for easy passing between modules and validation.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field

from ..settings import (
    DATE_FORMAT_PYTHON,
    DATE_FORMAT,
    AGENT_DEBUG,
    AGENT_MODEL,
    MODEL_CALL_RUN_LIMIT,
    MODEL_CALL_THREAD_LIMIT,
    MODEL_CALL_EXIT_BEHAVIOR,
    TOOL_CALL_RUN_LIMIT,
    TOOL_CALL_THREAD_LIMIT,
    TOOL_CALL_EXIT_BEHAVIOR,
)


class AgentConfig(BaseModel):
    """
    Centralized configuration for the inventory agent.

    Captures all agent settings from settings.py in a single Pydantic model
    for easy passing between modules and validation.

    Attributes:
        date_format: Current date format (YYYY-MM-DD or DD-MM-YYYY)
        date_format_python: Python strftime format string
        agent_debug: Enable debug mode for verbose output
        agent_model: OpenAI model identifier
        model_call_run_limit: Max LLM calls per invocation
        model_call_thread_limit: Max LLM calls per thread
        model_call_exit_behavior: Behavior when model call limit reached
        tool_call_run_limit: Max tool calls per invocation
        tool_call_thread_limit: Max tool calls per thread
        tool_call_exit_behavior: Behavior when tool call limit reached
    """

    date_format: Literal["YYYY-MM-DD", "DD-MM-YYYY"] = Field(
        default=DATE_FORMAT, description="Date format for parsing and display"
    )
    date_format_python: str = Field(
        default=DATE_FORMAT_PYTHON, description="Python strftime format string"
    )
    agent_debug: bool = Field(
        default=AGENT_DEBUG, description="Enable debug mode for verbose output"
    )
    agent_model: str = Field(
        default=AGENT_MODEL, description="OpenAI model to use"
    )
    model_call_run_limit: Optional[int] = Field(
        default=MODEL_CALL_RUN_LIMIT, description="Max LLM calls per invocation"
    )
    model_call_thread_limit: Optional[int] = Field(
        default=MODEL_CALL_THREAD_LIMIT, description="Max LLM calls per thread"
    )
    model_call_exit_behavior: Literal["continue", "error", "end"] = Field(
        default=MODEL_CALL_EXIT_BEHAVIOR,
        description="Behavior when model call limit reached",
    )
    tool_call_run_limit: Optional[int] = Field(
        default=TOOL_CALL_RUN_LIMIT, description="Max tool calls per invocation"
    )
    tool_call_thread_limit: Optional[int] = Field(
        default=TOOL_CALL_THREAD_LIMIT, description="Max tool calls per thread"
    )
    tool_call_exit_behavior: Literal["continue", "error", "end"] = Field(
        default=TOOL_CALL_EXIT_BEHAVIOR,
        description="Behavior when tool call limit reached",
    )

    @classmethod
    def from_settings(cls) -> "AgentConfig":
        """
        Create AgentConfig instance from current settings.py values.

        Returns:
            AgentConfig instance with all current settings
        """
        return cls(
            date_format=DATE_FORMAT,
            date_format_python=DATE_FORMAT_PYTHON,
            agent_debug=AGENT_DEBUG,
            agent_model=AGENT_MODEL,
            model_call_run_limit=MODEL_CALL_RUN_LIMIT,
            model_call_thread_limit=MODEL_CALL_THREAD_LIMIT,
            model_call_exit_behavior=MODEL_CALL_EXIT_BEHAVIOR,
            tool_call_run_limit=TOOL_CALL_RUN_LIMIT,
            tool_call_thread_limit=TOOL_CALL_THREAD_LIMIT,
            tool_call_exit_behavior=TOOL_CALL_EXIT_BEHAVIOR,
        )

