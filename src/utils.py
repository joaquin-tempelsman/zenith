"""
Utility functions for date parsing and formatting.

Centralises date helpers that were previously in settings.py,
keeping settings.py focused on configuration constants only.
"""
from datetime import datetime

from .settings import DATE_FORMAT, DATE_FORMAT_PYTHON


def parse_date(date_string: str) -> str | None:
    """
    Parse a date string according to the configured DATE_FORMAT.

    Args:
        date_string: Date string to parse

    Returns:
        ISO format date string (YYYY-MM-DD) for database storage, or None if invalid
    """
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
    return "DD-MM-YYYY (e.g., 21-12-2025)"

