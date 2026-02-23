"""Tests for src.agent.tools — individual tool functions with a real DB.

These tests call tools via .invoke() just like the agent would,
ensuring the module-level state is set via the agent_state_with_db
/ seeded_agent_state fixtures from conftest.
"""
import pytest

from src.agent.tools import (
    detect_language,
    modify_db,
    query_db,
    batch_modify_db,
    reset_database,
    get_help,
    _add_item,
    _remove_item,
    _format_batch_summary,
)
from src.agent.state import get_detected_language, set_detected_language
from src.database import crud


# ========================================================================
# detect_language
# ========================================================================


class TestDetectLanguage:
    """Tests for the detect_language tool."""

    def test_english(self, agent_state_with_db):
        """English text detected as 'en'."""
        result = detect_language.invoke({"user_message": "Add 5 apples to fruits"})
        assert result == "en"
        assert get_detected_language() == "en"

    def test_spanish(self, agent_state_with_db):
        """Spanish text detected as 'es'."""
        result = detect_language.invoke({"user_message": "Agregar 5 manzanas a frutas"})
        assert result == "es"
        assert get_detected_language() == "es"


# ========================================================================
# modify_db  (add / remove)
# ========================================================================


class TestModifyDB:
    """Tests for the modify_db tool."""

    def test_add_new_item(self, agent_state_with_db):
        """Adding a brand-new item creates it."""
        result = modify_db.invoke({"action": "add", "item": "Eggs", "quantity": 12, "category": "dairy"})
        assert "Created new item" in result or "✅" in result

    def test_add_existing_increases_qty(self, seeded_agent_state):
        """Adding to an existing item bumps quantity."""
        result = modify_db.invoke({"action": "add", "item": "apples", "quantity": 3})
        assert "Added 3" in result

    def test_add_existing_no_qty(self, seeded_agent_state):
        """Adding with no quantity to existing shows info."""
        result = modify_db.invoke({"action": "add", "item": "apples"})
        assert "already exists" in result

    def test_remove_partial(self, seeded_agent_state):
        """Remove partial quantity."""
        result = modify_db.invoke({"action": "remove", "item": "apples", "quantity": 3})
        assert "Removed 3" in result

    def test_remove_all(self, seeded_agent_state):
        """Remove with no quantity removes all stock."""
        result = modify_db.invoke({"action": "remove", "item": "bananas"})
        assert "Removed all" in result

    def test_remove_nonexistent(self, agent_state_with_db):
        """Removing non-existent item returns error."""
        result = modify_db.invoke({"action": "remove", "item": "unicorn"})
        assert "not found" in result

    def test_unknown_action(self, agent_state_with_db):
        """Unknown action returns error string."""
        result = modify_db.invoke({"action": "fly", "item": "x"})
        assert "Unknown action" in result

    def test_add_with_expire_date(self, agent_state_with_db):
        """Adding item with expire_date parses and stores it."""
        result = modify_db.invoke({
            "action": "add", "item": "yogurt", "quantity": 2,
            "category": "dairy", "expire_date": "2026-12-31",
        })
        assert "✅" in result


# ========================================================================
# query_db
# ========================================================================


class TestQueryDB:
    """Tests for the query_db tool."""

    def test_summary(self, seeded_agent_state):
        """Summary query returns stats."""
        result = query_db.invoke({"list_type": "summary"})
        assert "Inventory Summary" in result

    def test_item_found(self, seeded_agent_state):
        """Item query for existing item returns details."""
        result = query_db.invoke({"list_type": "item", "item": "apples"})
        assert "apples" in result

    def test_item_not_found(self, seeded_agent_state):
        """Item query for missing item returns error."""
        result = query_db.invoke({"list_type": "item", "item": "unicorn"})
        assert "not found" in result

    def test_group_query(self, seeded_agent_state):
        """Group query returns items in category."""
        result = query_db.invoke({"list_type": "group", "group": "fruits"})
        assert "apples" in result

    def test_expire_query(self, seeded_agent_state):
        """Expire query returns items with dates."""
        result = query_db.invoke({"list_type": "expire"})
        assert "expiration" in result.lower() or "📅" in result

    def test_unknown_list_type(self, seeded_agent_state):
        """Unknown list_type returns error."""
        result = query_db.invoke({"list_type": "magic"})
        assert "Unknown" in result


# ========================================================================
# batch_modify_db
# ========================================================================


class TestBatchModifyDB:
    """Tests for the batch_modify_db tool."""

    def test_batch_add(self, agent_state_with_db):
        """Batch add creates multiple items."""
        result = batch_modify_db.invoke({
            "action": "add", "items": ["eggs", "rice", "pasta"], "category": "pantry",
        })
        assert "Batch operation" in result or "📦" in result



# ========================================================================
# get_help
# ========================================================================


class TestGetHelp:
    """Tests for the get_help tool."""

    def test_help_english(self, agent_state_with_db):
        """Help in English contains command examples."""
        set_detected_language("en")
        result = get_help.invoke({})
        assert "Available Commands" in result

    def test_help_spanish(self, agent_state_with_db):
        """Help in Spanish contains Spanish commands."""
        set_detected_language("es")
        result = get_help.invoke({})
        assert "Comandos Disponibles" in result


# ========================================================================
# Private helpers
# ========================================================================


class TestPrivateHelpers:
    """Tests for _add_item, _remove_item, _format_batch_summary."""

    def test_add_item_default_category(self, agent_state_with_db):
        """_add_item defaults category to 'general'."""
        result = _add_item(agent_state_with_db, "soap", 1, None, None)
        assert "general" in result

    def test_remove_item_not_found(self, agent_state_with_db):
        """_remove_item returns error for missing item."""
        result = _remove_item(agent_state_with_db, "ghost", None)
        assert "not found" in result

    def test_format_batch_summary_all_affected(self):
        """Batch summary shows all affected items."""
        result = _format_batch_summary("add", ["a", "b"], [], [], "en")
        assert "Added" in result
        assert "a, b" in result

    def test_format_batch_summary_with_failures(self):
        """Batch summary includes failed items."""
        result = _format_batch_summary("remove", [], [], ["x"], "en")
        assert "Failed" in result

    def test_format_batch_summary_spanish(self):
        """Batch summary renders in Spanish."""
        result = _format_batch_summary("add", ["a"], ["b"], [], "es")
        assert "Agregados" in result
        assert "Sin cambios" in result

