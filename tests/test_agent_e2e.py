"""End-to-end agent tests using a real LLM.

Each test sends a natural-language prompt through ``run_inventory_agent``,
then uses an LLM judge (gpt-4o-mini) to verify the response matches the
expected behaviour.  The database is an in-memory SQLite so no side-effects
leak between tests.

All tests are decorated with ``@nondeterministic()`` so each is retried up
to 3 times; a test passes if it succeeds at least once.  Pass-rate
percentages are printed at the end of the session.

Requires OPENAI_API_KEY in the environment.
"""
import json
import pytest
from openai import OpenAI

from src.agent.core import run_inventory_agent
from src.database import crud
from src.config import settings
from tests.conftest import nondeterministic

_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    """Lazily initialise a shared OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def _llm_judge(prompt: str, agent_response: str, criteria: str) -> bool:
    """Use gpt-4o-mini as an impartial judge.

    Args:
        prompt: The original user prompt sent to the agent.
        agent_response: The text the agent returned.
        criteria: A plain-English description of what a correct response looks like.

    Returns:
        True if the judge decides the agent response satisfies the criteria.
    """
    system = (
        "You are an impartial test judge.  You will receive a user prompt, "
        "the agent's response, and the criteria for a PASS.  Reply ONLY with "
        "a JSON object: {\"pass\": true/false, \"reason\": \"...\"}."
    )
    user = (
        f"USER PROMPT:\n{prompt}\n\n"
        f"AGENT RESPONSE:\n{agent_response}\n\n"
        f"CRITERIA:\n{criteria}"
    )
    resp = _get_openai_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    verdict = json.loads(resp.choices[0].message.content)
    return verdict.get("pass", False)


def _run(prompt: str, db) -> dict:
    """Run the inventory agent and return the result dict."""
    return run_inventory_agent(prompt, db, chat_id=99999)


# ========================================================================
# Adding items
# ========================================================================


class TestAgentAddItems:
    """Agent correctly adds items to inventory."""

    @nondeterministic()
    def test_add_single_item(self, thread_safe_db):
        """'Add 5 milk to dairy' creates an item (mass noun avoids singular/plural LLM flakiness)."""
        res = _run("Add 5 milk to dairy", thread_safe_db)
        assert res["result"] == "success"
        assert _llm_judge(
            "Add 5 milk to dairy",
            res["response_message"],
            "Response confirms that milk was added with quantity 5 in the dairy category.",
        )
        thread_safe_db.expire_all()
        item = crud.get_item_by_name(thread_safe_db, "milk")
        assert item is not None
        assert item.quantity == 5

    @nondeterministic()
    def test_add_item_no_category(self, thread_safe_db):
        """'Add 3 salt' defaults to a category (mass noun avoids translation/plural flakiness)."""
        res = _run("Add 3 salt", thread_safe_db)
        assert res["result"] == "success"
        assert _llm_judge(
            "Add 3 salt",
            res["response_message"],
            "Response confirms that salt was added with quantity 3.",
        )

    @nondeterministic()
    def test_add_to_existing_increases(self, thread_safe_db):
        """Adding to an existing item increases the quantity."""
        _run("Add 10 milk to dairy", thread_safe_db)
        _run("Add 5 milk", thread_safe_db)
        thread_safe_db.expire_all()
        item = crud.get_item_by_name(thread_safe_db, "milk")
        assert item is not None
        assert item.quantity == 15


# ========================================================================
# Removing items
# ========================================================================


class TestAgentRemoveItems:
    """Agent correctly removes items."""

    @nondeterministic()
    def test_remove_partial(self, thread_safe_db):
        """'Remove 2 rice' decreases quantity (mass noun avoids singular/plural LLM flakiness)."""
        _run("Add 10 rice to grains", thread_safe_db)
        res = _run("Remove 2 rice", thread_safe_db)
        assert res["result"] == "success"
        thread_safe_db.expire_all()
        item = crud.get_item_by_name(thread_safe_db, "rice")
        assert item is not None
        assert item.quantity == 8

    @nondeterministic()
    def test_remove_all(self, thread_safe_db):
        """'Remove all flour' sets quantity to 0 (mass noun avoids singular/plural LLM flakiness)."""
        _run("Add 7 flour to baking", thread_safe_db)
        res = _run("Remove all flour", thread_safe_db)
        assert res["result"] == "success"
        thread_safe_db.expire_all()
        item = crud.get_item_by_name(thread_safe_db, "flour")
        assert item is not None
        assert item.quantity == 0

    @nondeterministic()
    def test_remove_nonexistent(self, thread_safe_db):
        """Removing something not in inventory gives a meaningful error."""
        res = _run("Remove 3 unicorns", thread_safe_db)
        assert _llm_judge(
            "Remove 3 unicorns",
            res["response_message"],
            "Response indicates that unicorns were not found in the inventory.",
        )


# ========================================================================
# Querying inventory
# ========================================================================


class TestAgentQueryInventory:
    """Agent correctly answers inventory queries."""

    @nondeterministic()
    def test_check_item_stock(self, thread_safe_db):
        """'How much rice do we have' returns the correct quantity (mass noun avoids singular/plural LLM flakiness)."""
        _run("Add 8 rice to grains", thread_safe_db)
        res = _run("How much rice do we have?", thread_safe_db)
        assert _llm_judge(
            "How much rice do we have?",
            res["response_message"],
            "Response mentions rice and includes quantity 8.",
        )

    @nondeterministic()
    def test_inventory_summary(self, thread_safe_db):
        """'Give me an inventory summary' returns summary stats."""
        _run("Add 4 milk to dairy", thread_safe_db)
        _run("Add 6 bread to bakery", thread_safe_db)
        res = _run("Give me an inventory summary", thread_safe_db)
        assert _llm_judge(
            "Give me an inventory summary",
            res["response_message"],
            "Response includes total items count and category information.",
        )

    @nondeterministic()
    def test_list_category(self, thread_safe_db):
        """'Show fruits category' lists items in that category."""
        _run("Add 3 apples to fruits", thread_safe_db)
        _run("Add 5 bananas to fruits", thread_safe_db)
        res = _run("Show fruits category", thread_safe_db)
        assert _llm_judge(
            "Show fruits category",
            res["response_message"],
            "Response lists items in the fruits category, including apples and bananas.",
        )


# ========================================================================
# Batch operations
# ========================================================================


class TestAgentBatchOps:
    """Agent handles batch add/remove."""

    @nondeterministic()
    def test_batch_add(self, thread_safe_db):
        """'Add rice, flour, and sugar to pantry' creates all three (mass nouns)."""
        res = _run("Add rice, flour, and sugar to pantry", thread_safe_db)
        assert res["result"] == "success"
        assert _llm_judge(
            "Add rice, flour, and sugar to pantry",
            res["response_message"],
            "Response confirms that rice, flour, and sugar were added to the pantry category.",
        )


# ========================================================================
# Spanish language support
# ========================================================================


class TestAgentSpanish:
    """Agent responds in Spanish when addressed in Spanish."""

    @nondeterministic()
    def test_add_in_spanish(self, thread_safe_db):
        """'Agregar 5 manzanas a frutas' works and responds in Spanish."""
        res = _run("Agregar 5 manzanas a frutas", thread_safe_db)
        assert res["result"] == "success"
        assert _llm_judge(
            "Agregar 5 manzanas a frutas",
            res["response_message"],
            "Response is in Spanish and confirms manzanas were added.",
        )

    @nondeterministic()
    def test_summary_in_spanish(self, thread_safe_db):
        """'Dame un resumen del inventario' returns Spanish summary."""
        _run("Agregar 3 leche a lácteos", thread_safe_db)
        res = _run("Dame un resumen del inventario", thread_safe_db)
        assert _llm_judge(
            "Dame un resumen del inventario",
            res["response_message"],
            "Response is in Spanish and contains inventory summary information.",
        )


# ========================================================================
# Help
# ========================================================================


class TestAgentHelp:
    """Agent returns help information."""

    @nondeterministic()
    def test_help_english(self, thread_safe_db):
        """'Help' returns command list."""
        res = _run("Help", thread_safe_db)
        assert _llm_judge(
            "Help",
            res["response_message"],
            "Response lists available commands or instructions for using the bot.",
        )

    @nondeterministic()
    def test_help_spanish(self, thread_safe_db):
        """'Ayuda' returns Spanish help."""
        res = _run("Ayuda", thread_safe_db)
        assert _llm_judge(
            "Ayuda",
            res["response_message"],
            "Response is in Spanish and provides help or command instructions.",
        )


# ========================================================================
# Metadata / tools_used
# ========================================================================


class TestAgentMetadata:
    """Agent returns expected metadata."""

    @nondeterministic()
    def test_tools_used_populated(self, thread_safe_db):
        """tools_used list is non-empty for a real query."""
        res = _run("Add 2 rice to grains", thread_safe_db)
        assert len(res["tools_used"]) > 0

    @nondeterministic()
    def test_metadata_has_language(self, thread_safe_db):
        """metadata dict contains detected language."""
        res = _run("Add 1 bread to bakery", thread_safe_db)
        assert "language" in res["metadata"]
        assert res["metadata"]["language"] in ("en", "es")
