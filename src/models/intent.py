"""
Intent models for inventory operations.

Defines Pydantic schemas for parsed user intents (modify/list),
response validation, and date format helpers.
"""
from typing import Optional, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from ..settings import DATE_FORMAT_PYTHON
from ..utils import get_date_format_description


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

    Validates and represents requests to modify inventory items,
    including adding new items, updating quantities, or removing items.

    Attributes:
        action_type: Must be 'modify'
        action: 'add' or 'remove'
        item: Item name in lowercase
        quantity: Quantity to add/remove (None means all stock)
        category: Category for the item (optional)
        expire_date: Expiration date (format configured in settings)
        notes: Additional notes about the item
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


class ListIntentRequest(BaseModel):
    """
    Schema for inventory list/query intent.

    Validates and represents requests to query/list inventory items
    based on various criteria (expiration, category, specific item, history).

    Attributes:
        action_type: Must be 'list'
        list_type: Type of list query to perform
        item: Item name for item/history queries
        group: Group/category name for group/history queries
        days: Number of days for history queries
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
        360, description="Number of days for history queries", ge=1
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

    Attributes:
        action_type: Type of action (modify, list, or unknown)
        action: Action for modify type
        list_type: Query type for list type
        item: Item name
        quantity: Quantity
        category: Category/group
        group: Alias for category in list queries
        expire_date: Expiration date YYYY-MM-DD
        days: Days for history queries
        notes: Additional notes
        error: Error message if parsing failed
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

    Attributes:
        is_valid: Whether validation passed
        model_type: Type of validated model (modify/list)
        data: Parsed and validated data
        errors: Validation errors if any
        raw_response: Raw response that was validated
    """

    is_valid: bool = Field(..., description="Whether validation passed")
    model_type: Optional[str] = Field(
        None, description="Type of validated model (modify/list)"
    )
    data: Optional[Union[ModifyIntentRequest, ListIntentRequest]] = Field(
        None, description="Parsed and validated data"
    )
    errors: Optional[list] = Field(None, description="Validation errors if any")
    raw_response: Optional[str] = Field(
        None, description="Raw response that was validated"
    )


def validate_intent_response(response_data: Union[dict, str]) -> ResponseValidationResult:
    """
    Validate an intent response against the appropriate Pydantic model.

    Routes to either ModifyIntentRequest or ListIntentRequest based
    on the action_type field.

    Args:
        response_data: Raw response data (dict or JSON string) from LLM

    Returns:
        ResponseValidationResult with validation status and parsed data
    """
    import json

    if isinstance(response_data, str):
        try:
            response_dict = json.loads(response_data)
            raw_response = response_data
        except json.JSONDecodeError as e:
            return ResponseValidationResult(
                is_valid=False,
                errors=[f"JSON parse error: {str(e)}"],
                raw_response=response_data,
            )
    else:
        response_dict = response_data
        raw_response = json.dumps(response_data)

    action_type = response_dict.get("action_type", "").lower()
    model_map = {"modify": ModifyIntentRequest, "list": ListIntentRequest}
    model_cls = model_map.get(action_type)

    if not model_cls:
        return ResponseValidationResult(
            is_valid=False,
            errors=[f"Unknown action_type: {action_type}"],
            raw_response=raw_response,
        )

    try:
        validated_data = model_cls(**response_dict)
        return ResponseValidationResult(
            is_valid=True,
            model_type=action_type,
            data=validated_data,
            raw_response=raw_response,
        )
    except Exception as e:
        error_messages = (
            [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            if hasattr(e, "errors")
            else [str(e)]
        )
        return ResponseValidationResult(
            is_valid=False,
            model_type=action_type if action_type in model_map else None,
            errors=error_messages,
            raw_response=raw_response,
        )

