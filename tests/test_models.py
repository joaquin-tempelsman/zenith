"""Tests for src.models — Pydantic schemas and validation helpers."""
import json

import pytest

from src.models import (
    AgentConfig,
    ModifyIntentRequest,
    ListIntentRequest,
    ParsedIntent,
    ResponseValidationResult,
    validate_date_format,
    validate_intent_response,
    ParseIntentInput,
    ModifyDBInput,
    QueryDBInput,
    DetectLanguageInput,
    ResetDatabaseInput,
    BatchModifyDBInput,
    GetHelpInput,
)


# ========================================================================
# AgentConfig
# ========================================================================


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_from_settings(self):
        """from_settings returns a valid config object."""
        cfg = AgentConfig.from_settings()
        assert cfg.agent_model is not None
        assert cfg.date_format in ("YYYY-MM-DD", "DD-MM-YYYY")

    def test_defaults_match_settings(self):
        """Default values propagate from settings module."""
        cfg = AgentConfig()
        assert isinstance(cfg.agent_debug, bool)
        assert cfg.model_call_exit_behavior in ("continue", "error", "end")


# ========================================================================
# ModifyIntentRequest
# ========================================================================


class TestModifyIntentRequest:
    """Tests for ModifyIntentRequest schema."""

    def test_valid_add(self):
        """Basic add intent passes validation."""
        req = ModifyIntentRequest(action_type="modify", action="add", item="Apples", quantity=5, category="Fruits")
        assert req.item == "apples"
        assert req.category == "fruits"

    def test_valid_remove(self):
        """Remove intent with no quantity (remove all)."""
        req = ModifyIntentRequest(action_type="modify", action="remove", item="milk")
        assert req.quantity is None

    def test_quantity_must_be_positive(self):
        """Quantity <= 0 raises ValidationError."""
        with pytest.raises(Exception):
            ModifyIntentRequest(action_type="modify", action="add", item="x", quantity=-1)

    def test_expire_date_validated(self):
        """expire_date must match configured format."""
        req = ModifyIntentRequest(
            action_type="modify", action="add", item="milk", expire_date="15-03-2026"
        )
        assert req.expire_date == "2026-03-15"

    def test_invalid_expire_date_raises(self):
        """Malformed expire_date raises ValidationError."""
        with pytest.raises(Exception):
            ModifyIntentRequest(
                action_type="modify", action="add", item="milk", expire_date="not-a-date"
            )


# ========================================================================
# ListIntentRequest
# ========================================================================


class TestListIntentRequest:
    """Tests for ListIntentRequest schema."""

    def test_summary_no_extra_fields(self):
        """Summary type needs no item/group."""
        req = ListIntentRequest(action_type="list", list_type="summary")
        assert req.list_type == "summary"

    def test_group_requires_group_field(self):
        """list_type='group' without group raises."""
        with pytest.raises(Exception):
            ListIntentRequest(action_type="list", list_type="group")

    def test_item_type(self):
        """Item query lowercases the name."""
        req = ListIntentRequest(action_type="list", list_type="item", item="MILK")
        assert req.item == "milk"

    def test_expire_type(self):
        """Expire type is valid."""
        req = ListIntentRequest(action_type="list", list_type="expire")
        assert req.list_type == "expire"


# ========================================================================
# validate_intent_response
# ========================================================================


class TestValidateIntentResponse:
    """Tests for validate_intent_response helper."""

    def test_valid_modify_dict(self):
        """Dict with action_type='modify' validates OK."""
        data = {"action_type": "modify", "action": "add", "item": "rice", "quantity": 2, "category": "grains"}
        result = validate_intent_response(data)
        assert result.is_valid
        assert result.model_type == "modify"

    def test_valid_list_json_string(self):
        """JSON string input validates correctly."""
        data = json.dumps({"action_type": "list", "list_type": "summary"})
        result = validate_intent_response(data)
        assert result.is_valid

    def test_invalid_json_string(self):
        """Malformed JSON returns is_valid=False."""
        result = validate_intent_response("{bad json")
        assert not result.is_valid

    def test_unknown_action_type(self):
        """Unknown action_type is invalid."""
        result = validate_intent_response({"action_type": "fly"})
        assert not result.is_valid


# ========================================================================
# Tool schemas
# ========================================================================


class TestToolSchemas:
    """Tests for Pydantic tool input schemas."""

    def test_parse_intent_input(self):
        """ParseIntentInput accepts user_message."""
        s = ParseIntentInput(user_message="add 5 apples")
        assert s.user_message == "add 5 apples"

    def test_modify_db_input_quantity_positive(self):
        """ModifyDBInput rejects quantity <= 0."""
        with pytest.raises(Exception):
            ModifyDBInput(action="add", item="x", quantity=0)

    def test_query_db_input_defaults(self):
        """QueryDBInput has default days=7."""
        q = QueryDBInput(list_type="summary")
        assert q.days == 7

    def test_detect_language_input(self):
        """DetectLanguageInput requires user_message."""
        s = DetectLanguageInput(user_message="hola")
        assert s.user_message == "hola"

    def test_reset_database_input(self):
        """ResetDatabaseInput requires confirmation."""
        s = ResetDatabaseInput(confirmation="OK")
        assert s.confirmation == "OK"

    def test_batch_modify_db_input(self):
        """BatchModifyDBInput accepts item list."""
        s = BatchModifyDBInput(action="add", items=["a", "b"])
        assert len(s.items) == 2

    def test_get_help_input_optional_topic(self):
        """GetHelpInput topic is optional."""
        s = GetHelpInput()
        assert s.topic is None


# ========================================================================
# validate_date_format
# ========================================================================


class TestValidateDateFormat:
    """Tests for validate_date_format helper."""

    def test_configured_format(self):
        """Accepts date in configured DD-MM-YYYY format."""
        result = validate_date_format("15-03-2026")
        assert result == "2026-03-15"

    def test_iso_format_fallback(self):
        """Accepts ISO YYYY-MM-DD as fallback."""
        result = validate_date_format("2026-03-15")
        assert result == "2026-03-15"

    def test_invalid_raises(self):
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            validate_date_format("nope")

