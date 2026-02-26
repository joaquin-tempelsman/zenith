"""Tests for src.utils — date parsing / formatting helpers."""
import pytest

from src.utils import parse_date, format_date, get_date_format_description
from src.settings import DATE_FORMAT


class TestParseDate:
    """Tests for parse_date."""

    def test_valid_date_in_configured_format(self):
        """Date matching DATE_FORMAT returns ISO string."""
        if DATE_FORMAT == "DD-MM-YYYY":
            result = parse_date("15-06-2026")
            assert result == "2026-06-15"
        else:
            result = parse_date("2026-06-15")
            assert result == "2026-06-15"

    def test_invalid_date_returns_none(self):
        """Garbage string returns None."""
        assert parse_date("not-a-date") is None

    def test_wrong_format_returns_none(self):
        """Date in wrong format returns None."""
        if DATE_FORMAT == "DD-MM-YYYY":
            assert parse_date("2026-06-15") is None
        else:
            assert parse_date("15-06-2026") is None


class TestFormatDate:
    """Tests for format_date."""

    def test_iso_to_configured_format(self):
        """ISO date is formatted into configured DATE_FORMAT."""
        result = format_date("2026-06-15")
        if DATE_FORMAT == "DD-MM-YYYY":
            assert result == "15-06-2026"
        else:
            assert result == "2026-06-15"

    def test_invalid_returns_input(self):
        """Invalid ISO string is returned unchanged."""
        assert format_date("garbage") == "garbage"


class TestGetDateFormatDescription:
    """Tests for get_date_format_description."""

    def test_returns_string(self):
        """Returns a non-empty human-readable string."""
        desc = get_date_format_description()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_contains_example(self):
        """Description includes an example date."""
        desc = get_date_format_description()
        assert "e.g." in desc

