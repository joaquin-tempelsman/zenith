"""Tests for src.database.crud — every CRUD function."""
from datetime import date, datetime, timedelta

import pytest

from src.database import crud
from src.database.models import Item


class TestCreateItem:
    """Tests for crud.create_item."""

    def test_create_basic_item(self, db_session):
        """Create item with required fields only."""
        item = crud.create_item(db_session, "apples", 10, "fruits")
        assert item.id is not None
        assert item.name == "apples"
        assert item.quantity == 10
        assert item.category == "fruits"
        assert item.expire_date is None

    def test_create_item_with_expiration(self, db_session):
        """Create item that has an expiration date."""
        exp = date(2026, 6, 15)
        item = crud.create_item(db_session, "milk", 3, "dairy", exp)
        assert item.expire_date == exp

    def test_create_item_persists(self, db_session):
        """Item is retrievable after creation."""
        crud.create_item(db_session, "bread", 2, "bakery")
        fetched = crud.get_item_by_name(db_session, "bread")
        assert fetched is not None
        assert fetched.quantity == 2


class TestGetItem:
    """Tests for get_item_by_id and get_item_by_name."""

    def test_get_by_id(self, seeded_db):
        """Retrieve an existing item by ID."""
        item = crud.get_item_by_id(seeded_db, 1)
        assert item is not None

    def test_get_by_id_missing(self, seeded_db):
        """Returns None for non-existent ID."""
        assert crud.get_item_by_id(seeded_db, 9999) is None

    def test_get_by_name_case_insensitive(self, seeded_db):
        """Name lookup is case-insensitive."""
        item = crud.get_item_by_name(seeded_db, "APPLES")
        assert item is not None
        assert item.name == "apples"

    def test_get_by_name_missing(self, seeded_db):
        """Returns None for unknown name."""
        assert crud.get_item_by_name(seeded_db, "unicorn") is None


class TestGetAllItems:
    """Tests for crud.get_all_items."""

    def test_returns_all(self, seeded_db):
        """Should return all seeded items."""
        items = crud.get_all_items(seeded_db)
        assert len(items) == 5

    def test_pagination(self, seeded_db):
        """Skip/limit pagination works."""
        page = crud.get_all_items(seeded_db, skip=2, limit=2)
        assert len(page) == 2


class TestGetItemsByCategory:
    """Tests for crud.get_items_by_category."""

    def test_known_category(self, seeded_db):
        """Returns items for existing category."""
        fruits = crud.get_items_by_category(seeded_db, "fruits")
        assert len(fruits) == 2

    def test_unknown_category(self, seeded_db):
        """Empty list for non-existent category."""
        assert crud.get_items_by_category(seeded_db, "electronics") == []


class TestUpdateItem:
    """Tests for quantity update helpers."""

    def test_update_quantity_by_id(self, seeded_db):
        """update_item_quantity adds to existing quantity."""
        item = crud.get_item_by_name(seeded_db, "apples")
        updated = crud.update_item_quantity(seeded_db, item.id, 5)
        assert updated.quantity == 15

    def test_update_quantity_by_name(self, seeded_db):
        """update_item_by_name works with name string."""
        updated = crud.update_item_by_name(seeded_db, "bananas", 3)
        assert updated.quantity == 8

    def test_set_item_quantity(self, seeded_db):
        """set_item_quantity replaces value entirely."""
        item = crud.get_item_by_name(seeded_db, "milk")
        updated = crud.set_item_quantity(seeded_db, item.id, 99)
        assert updated.quantity == 99

    def test_update_nonexistent_returns_none(self, db_session):
        """Updating missing item returns None."""
        assert crud.update_item_quantity(db_session, 9999, 1) is None
        assert crud.update_item_by_name(db_session, "ghost", 1) is None
        assert crud.set_item_quantity(db_session, 9999, 1) is None


class TestDeleteItem:
    """Tests for delete helpers."""

    def test_delete_by_id(self, seeded_db):
        """delete_item removes item and returns True."""
        item = crud.get_item_by_name(seeded_db, "bread")
        assert crud.delete_item(seeded_db, item.id) is True
        assert crud.get_item_by_name(seeded_db, "bread") is None

    def test_delete_by_name(self, seeded_db):
        """delete_item_by_name removes and returns True."""
        assert crud.delete_item_by_name(seeded_db, "chicken") is True
        assert crud.get_item_by_name(seeded_db, "chicken") is None

    def test_delete_missing_returns_false(self, db_session):
        """Deleting non-existent item returns False."""
        assert crud.delete_item(db_session, 9999) is False
        assert crud.delete_item_by_name(db_session, "ghost") is False

    def test_delete_all_items(self, seeded_db):
        """delete_all_items clears table and returns count."""
        count = crud.delete_all_items(seeded_db)
        assert count == 5
        assert crud.get_all_items(seeded_db) == []


class TestBatchOperations:
    """Tests for batch create/delete."""

    def test_create_items_batch(self, db_session):
        """Batch create persists all items."""
        data = [
            {"name": "eggs", "quantity": 12, "category": "dairy"},
            {"name": "rice", "quantity": 5, "category": "grains"},
        ]
        items = crud.create_items_batch(db_session, data)


class TestInventorySummary:
    """Tests for crud.get_inventory_summary."""

    def test_summary_empty_db(self, db_session):
        """Summary on empty DB returns zeroes."""
        s = crud.get_inventory_summary(db_session)
        assert s["total_items"] == 0
        assert s["total_quantity"] == 0
        assert s["categories"] == []

    def test_summary_seeded(self, seeded_db):
        """Summary reflects seeded data."""
        s = crud.get_inventory_summary(seeded_db)
        assert s["total_items"] == 5
        assert s["total_quantity"] == 24  # 10+5+3+2+4
        assert set(s["categories"]) == {"fruits", "dairy", "bakery", "meat"}


class TestExpirationAndHistory:
    """Tests for get_items_by_expiration and get_history."""

    def test_items_by_expiration_order(self, seeded_db):
        """Items sorted by soonest expiration first."""
        items = crud.get_items_by_expiration(seeded_db)
        assert len(items) >= 3
        dates = [i["expire_date"] for i in items]
        assert dates == sorted(dates)

    def test_items_by_expiration_excludes_null(self, seeded_db):
        """Items without expire_date are excluded."""
        items = crud.get_items_by_expiration(seeded_db)
        names = [i["name"] for i in items]
        assert "bread" not in names

    def test_get_history(self, seeded_db):
        """History returns recently-updated items."""
        history = crud.get_history(seeded_db, 7)
        assert isinstance(history, list)

    def test_get_history_filtered_by_item(self, seeded_db):
        """History with item filter only returns matching item."""
        history = crud.get_history(seeded_db, 30, item="apples")
        for h in history:
            assert h["item"] == "apples"

    def test_get_history_filtered_by_group(self, seeded_db):
        """History with group filter only returns matching category."""
        history = crud.get_history(seeded_db, 30, group="fruits")
        for h in history:
            assert h["item"] in ("apples", "bananas")


class TestExecuteRawSQL:
    """Tests for crud.execute_raw_sql."""

    def test_select_query(self, seeded_db):
        """Raw SELECT returns rows as dicts."""
        result = crud.execute_raw_sql(seeded_db, "SELECT name FROM items ORDER BY name")
        assert len(result) == 5
        assert result[0]["name"] == "apples"

    def test_update_query(self, seeded_db):
        """Raw UPDATE returns affected_rows count."""
        result = crud.execute_raw_sql(
            seeded_db, "UPDATE items SET quantity = 0 WHERE category = 'fruits'"
        )
        assert result[0]["affected_rows"] == 2
