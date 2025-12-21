"""
Pydantic models for API responses and structured data validation.
Provides type-safe request/response validation using Pydantic v2 BaseModel.
"""
from typing import Optional, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from .settings import (
    DATE_FORMAT_PYTHON,
    get_date_format_description,
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
        default=MODEL_CALL_EXIT_BEHAVIOR, description="Behavior when model call limit reached"
    )
    tool_call_run_limit: Optional[int] = Field(
        default=TOOL_CALL_RUN_LIMIT, description="Max tool calls per invocation"
    )
    tool_call_thread_limit: Optional[int] = Field(
        default=TOOL_CALL_THREAD_LIMIT, description="Max tool calls per thread"
    )
    tool_call_exit_behavior: Literal["continue", "error", "end"] = Field(
        default=TOOL_CALL_EXIT_BEHAVIOR, description="Behavior when tool call limit reached"
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


def validate_date_format(date_str: str) -> str:
    """
    Validate date string against configured format.

    Args:
        date_str: Date string to validate

    Returns:
        ISO format date string for storage

    Raises:
        ValueError: If date format is invalid
    """
    try:
        parsed = datetime.strptime(date_str, DATE_FORMAT_PYTHON)
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            raise ValueError(
                f"Invalid date format: {date_str}. Use {get_date_format_description()}"
            )


class ModifyIntentRequest(BaseModel):
    """
    Schema for inventory modification intent (add/remove items).

    This model validates and represents requests to modify inventory items,
    including adding new items, updating quantities, or removing items entirely.
    """

    action_type: Literal["modify"] = Field(
        ..., description="Must be 'modify' for this schema"
    )
    action: Literal["add", "remove"] = Field(
        ..., description="Action to perform: add or remove"
    )
    item: str = Field(..., description="Item name in lowercase", min_length=1)
    quantity: Optional[int] = Field(
        None, description="Quantity to add/remove. None means all stock"
    )
    category: Optional[str] = Field(
        None, description="Category for the item (optional)", min_length=1
    )
    expire_date: Optional[str] = Field(
        None, description="Expiration date (format configured in settings)"
    )
    notes: Optional[str] = Field(None, description="Additional notes about the item")

    @field_validator("item", mode="before")
    @classmethod
    def item_lowercase(cls, v):
        """Ensure item name is lowercase."""
        return v.lower() if isinstance(v, str) else v

    @field_validator("category", mode="before")
    @classmethod
    def category_lowercase(cls, v):
        """Ensure category is lowercase."""
        return v.lower() if isinstance(v, str) else v

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v):
        """Ensure quantity is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("expire_date")
    @classmethod
    def validate_expire_date_field(cls, v):
        """Validate expire_date format based on settings."""
        if v is None:
            return v
        return validate_date_format(v)
        return v


class ListIntentRequest(BaseModel):
    """
    Schema for inventory list/query intent.

    This model validates and represents requests to query/list inventory items
    based on various criteria (expiration, category, specific item, history).
    """

    action_type: Literal["list"] = Field(
        ..., description="Must be 'list' for this schema"
    )
    list_type: Literal["expire", "group", "item", "history", "summary"] = Field(
        ..., description="Type of list query to perform"
    )
    item: Optional[str] = Field(
        None, description="Item name in lowercase (for item/history type)"
    )
    group: Optional[str] = Field(
        None, description="Group/category name in lowercase (for group/history type)"
    )
    days: Optional[int] = Field(
        7, description="Number of days for history queries", ge=1
    )

    @field_validator("item", mode="before")
    @classmethod
    def item_lowercase(cls, v):
        """Ensure item name is lowercase."""
        return v.lower() if isinstance(v, str) else v

    @field_validator("group", mode="before")
    @classmethod
    def group_lowercase(cls, v):
        """Ensure group name is lowercase."""
        return v.lower() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_required_fields(self):
        """Validate required fields based on list_type."""
        if self.list_type in ["item", "history"] and not self.item and not self.group:
            raise ValueError(
                f"Either 'item' or 'group' is required for list_type '{self.list_type}'"
            )

        if self.list_type == "group" and not self.group:
            raise ValueError("'group' is required for list_type 'group'")

        return self


class ParsedIntent(BaseModel):
    """
    Union type for parsed intent from user input.
    Discriminates between modify and list actions based on action_type.
    """

    action_type: Literal["modify", "list", "unknown"] = Field(
        ..., description="Type of action: modify, list, or unknown"
    )
    action: Optional[Literal["add", "remove"]] = Field(
        None, description="Action for modify type"
    )
    list_type: Optional[Literal["expire", "group", "item", "history", "summary"]] = (
        Field(None, description="Query type for list type")
    )
    item: Optional[str] = Field(None, description="Item name")
    quantity: Optional[int] = Field(None, description="Quantity")
    category: Optional[str] = Field(None, description="Category/group")
    group: Optional[str] = Field(None, description="Alias for category in list queries")
    expire_date: Optional[str] = Field(None, description="Expiration date YYYY-MM-DD")
    days: Optional[int] = Field(7, description="Days for history queries")
    notes: Optional[str] = Field(None, description="Additional notes")
    error: Optional[str] = Field(None, description="Error message if parsing failed")


class ResponseValidationResult(BaseModel):
    """
    Result of validating a response against the structured models.
    
    Provides detailed information about validation success/failure,
    including parsed data and any validation errors encountered.
    """
    is_valid: bool = Field(..., description="Whether validation passed")
    model_type: Optional[str] = Field(None, description="Type of validated model (modify/list)")
    data: Optional[Union[ModifyIntentRequest, ListIntentRequest]] = Field(
        None, description="Parsed and validated data"
    )
    errors: Optional[list] = Field(None, description="Validation errors if any")
    raw_response: Optional[str] = Field(None, description="Raw response that was validated")


def validate_intent_response(response_data: Union[dict, str]) -> ResponseValidationResult:
    """
    Validate an intent response against the appropriate Pydantic model.
    
    This function attempts to parse and validate the response data,
    routing to either ModifyIntentRequest or ListIntentRequest based
    on the action_type field.
    
    Args:
        response_data: Raw response data (dict or JSON string) from LLM
        
    Returns:
        ResponseValidationResult with validation status and parsed data
        
    Example:
        >>> result = validate_intent_response('{"action_type": "add", "action": "add", ...}')
        >>> if result.is_valid:
        ...     intent = result.data
    """
    import json
    
    # Convert string to dict if needed
    if isinstance(response_data, str):
        try:
            response_dict = json.loads(response_data)
            raw_response = response_data
        except json.JSONDecodeError as e:
            return ResponseValidationResult(
                is_valid=False,
                model_type=None,
                data=None,
                errors=[f"JSON parse error: {str(e)}"],
                raw_response=response_data
            )
    else:
        response_dict = response_data
        raw_response = json.dumps(response_data)
    
    # Determine action type and validate
    action_type = response_dict.get("action_type", "").lower()
    
    try:
        if action_type == "modify":
            validated_data = ModifyIntentRequest(**response_dict)
            return ResponseValidationResult(
                is_valid=True,
                model_type="modify",
                data=validated_data,
                errors=None,
                raw_response=raw_response
            )
        
        elif action_type == "list":
            validated_data = ListIntentRequest(**response_dict)
            return ResponseValidationResult(
                is_valid=True,
                model_type="list",
                data=validated_data,
                errors=None,
                raw_response=raw_response
            )
        
        else:
            return ResponseValidationResult(
                is_valid=False,
                model_type=None,
                data=None,
                errors=[f"Unknown action_type: {action_type}"],
                raw_response=raw_response
            )
    
    except Exception as e:
        # Capture validation errors from Pydantic
        error_messages = []
        if hasattr(e, "errors"):
            error_messages = [
                f"{err['loc']}: {err['msg']}" for err in e.errors()
            ]
        else:
            error_messages = [str(e)]
        
        return ResponseValidationResult(
            is_valid=False,
            model_type=action_type if action_type in ["modify", "list"] else None,
            data=None,
            errors=error_messages,
            raw_response=raw_response
        )
