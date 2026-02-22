"""
Pydantic input schemas for agent tools.

Each schema defines the expected inputs for a corresponding @tool function
in the agent tools module.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ParseIntentInput(BaseModel):
    """Input schema for the parse_intent tool.

    Attributes:
        user_message: The user's natural language message to parse into structured intent
    """

    user_message: str = Field(
        ...,
        description="The user's natural language message to parse into structured intent",
    )


class ModifyDBInput(BaseModel):
    """Input schema for the modify_db tool - modifies inventory items.

    Attributes:
        action: Action to perform ('add' or 'remove')
        item: Item name (lowercase)
        quantity: Quantity to add/remove (must be positive; None means all stock for remove)
        category: Category for the item (optional, lowercase)
        expire_date: Expiration date in YYYY-MM-DD format
    """

    action: str = Field(
        ..., description="Action to perform: 'add' or 'remove'"
    )
    item: str = Field(..., description="Item name (lowercase)")
    quantity: Optional[int] = Field(
        None, description="Quantity to add/remove (must be positive). None means all stock for remove.",
        gt=0,
    )
    category: Optional[str] = Field(
        None, description="Category for the item (optional, lowercase)"
    )
    expire_date: Optional[str] = Field(
        None, description="Expiration date in YYYY-MM-DD format"
    )


class QueryDBInput(BaseModel):
    """Input schema for the query_db tool - queries inventory data.

    Attributes:
        list_type: Type of query ('expire', 'group', 'item', 'history', or 'summary')
        item: Item name for item/history queries (lowercase)
        group: Category/group name for group/history queries (lowercase)
        days: Number of days for history queries
    """

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


class DetectLanguageInput(BaseModel):
    """Input schema for the detect_language tool.

    Attributes:
        user_message: The user's message to detect language from
    """

    user_message: str = Field(
        ...,
        description="The user's message to detect language from",
    )


class ResetDatabaseInput(BaseModel):
    """Input schema for the reset_database tool.

    Attributes:
        confirmation: Must be exactly 'OK' to proceed with database reset
    """

    confirmation: str = Field(
        ...,
        description="Must be exactly 'OK' to proceed with database reset",
    )


class BatchModifyDBInput(BaseModel):
    """Input schema for batch_modify_db tool - modifies multiple items at once.

    Attributes:
        action: Action to perform ('add' or 'remove')
        items: List of item names (lowercase)
        quantity: Quantity per item (must be positive; None means 1 for add, all stock for remove)
        category: Category for all items (optional, lowercase)
    """

    action: str = Field(
        ..., description="Action to perform: 'add' or 'remove'"
    )
    items: list[str] = Field(
        ..., description="List of item names (lowercase)"
    )
    quantity: Optional[int] = Field(
        None, description="Quantity per item (must be positive). None means 1 for add, all stock for remove.",
        gt=0,
    )
    category: Optional[str] = Field(
        None, description="Category for all items (optional, lowercase)"
    )


class GetHelpInput(BaseModel):
    """Input schema for the get_help tool.

    Attributes:
        topic: Specific topic to get help on (optional)
    """

    topic: Optional[str] = Field(
        None, description="Specific topic to get help on (optional)"
    )

