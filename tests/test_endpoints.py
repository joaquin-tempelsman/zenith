"""Tests for FastAPI endpoints in src.main.

All external dependencies (Telegram API, OpenAI, per-user DB) are mocked so
tests run without network access or side-effects.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from httpx import AsyncClient, ASGITransport

from src.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def async_client():
    """Async HTTP client wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client):
        """Health endpoint returns 200 with expected fields."""
        resp = await async_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["version"] == "1.0.0"
        assert "timestamp" in body
        assert "telegram_configured" in body
        assert "openai_configured" in body


# ---------------------------------------------------------------------------
# GET /inventory
# ---------------------------------------------------------------------------


class TestInventoryEndpoint:
    """Tests for the inventory listing endpoint."""

    @pytest.mark.asyncio
    async def test_inventory_returns_items(self, async_client, seeded_db):
        """GET /inventory returns seeded items."""
        with patch("src.main.get_session_for_user", return_value=seeded_db):
            resp = await async_client.get("/inventory", params={"chat_id": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 5
        assert len(body["items"]) == 5

    @pytest.mark.asyncio
    async def test_inventory_empty(self, async_client, db_session):
        """GET /inventory on empty DB returns zero items."""
        with patch("src.main.get_session_for_user", return_value=db_session):
            resp = await async_client.get("/inventory", params={"chat_id": 1})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ---------------------------------------------------------------------------
# GET /inventory/summary
# ---------------------------------------------------------------------------


class TestInventorySummaryEndpoint:
    """Tests for the inventory summary endpoint."""

    @pytest.mark.asyncio
    async def test_summary_returns_stats(self, async_client, seeded_db):
        """GET /inventory/summary returns summary dict."""
        with patch("src.main.get_session_for_user", return_value=seeded_db):
            resp = await async_client.get("/inventory/summary", params={"chat_id": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_items"] == 5
        assert body["total_quantity"] == 24


# ---------------------------------------------------------------------------
# POST /agent/process
# ---------------------------------------------------------------------------


class TestAgentProcessEndpoint:
    """Tests for the agent process endpoint."""

    @pytest.mark.asyncio
    async def test_agent_process_success(self, async_client, db_session):
        """POST /agent/process returns agent result."""
        mock_result = {
            "result": "success",
            "response_message": "Added 5 apples",
            "tools_used": ["modify_db"],
            "metadata": {"language": "en", "chat_id": 1},
        }
        with (
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.run_inventory_agent", return_value=mock_result),
        ):
            resp = await async_client.post(
                "/agent/process",
                params={"user_input": "Add 5 apples", "chat_id": 1},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["response"] == "Added 5 apples"

    @pytest.mark.asyncio
    async def test_agent_process_error(self, async_client, db_session):
        """POST /agent/process handles exceptions gracefully."""
        with (
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.run_inventory_agent", side_effect=RuntimeError("boom")),
        ):
            resp = await async_client.post(
                "/agent/process",
                params={"user_input": "crash", "chat_id": 1},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "error"


# ---------------------------------------------------------------------------
# POST /agent/voice
# ---------------------------------------------------------------------------


class TestAgentVoiceEndpoint:
    """Tests for the agent voice endpoint."""

    @pytest.mark.asyncio
    async def test_voice_success(self, async_client, db_session):
        """POST /agent/voice returns transcription and agent result."""
        mock_result = {
            "result": "success",
            "response_message": "Added milk",
            "tools_used": ["modify_db"],
            "metadata": {"language": "en"},
        }
        with (
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.extract_voice_text", new_callable=AsyncMock, return_value="Add milk"),
            patch("src.main.run_inventory_agent", return_value=mock_result),
        ):
            resp = await async_client.post(
                "/agent/voice",
                json={
                    "message": {
                        "chat": {"id": 1},
                        "voice": {"file_id": "abc123", "duration": 3},
                    }
                },
            )
        body = resp.json()
        assert body["status"] == "success"
        assert body["transcribed_text"] == "Add milk"

    @pytest.mark.asyncio
    async def test_voice_no_voice_in_payload(self, async_client):
        """POST /agent/voice rejects payload without voice."""
        resp = await async_client.post(
            "/agent/voice",
            json={"message": {"chat": {"id": 1}, "text": "hello"}},
        )
        body = resp.json()
        assert body["status"] == "error"
        assert "No voice message" in body["error"]

    @pytest.mark.asyncio
    async def test_voice_no_message_in_payload(self, async_client):
        """POST /agent/voice rejects payload without message."""
        resp = await async_client.post("/agent/voice", json={"update_id": 123})
        body = resp.json()
        assert body["status"] == "error"


# ---------------------------------------------------------------------------
# GET /agent/health
# ---------------------------------------------------------------------------


class TestAgentHealthEndpoint:
    """Tests for the agent health endpoint."""

    @pytest.mark.asyncio
    async def test_agent_health_success(self, async_client):
        """GET /agent/health returns healthy when agent can be created."""
        with patch("src.agent.create_inventory_agent"):
            resp = await async_client.get("/agent/health")
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["agent_type"] == "LangChain 1.0"
        assert "timestamp" in body

    @pytest.mark.asyncio
    async def test_agent_health_error(self, async_client):
        """GET /agent/health returns error when agent creation fails."""
        with patch(
            "src.agent.create_inventory_agent", side_effect=RuntimeError("no key")
        ):
            resp = await async_client.get("/agent/health")
        body = resp.json()
        assert body["status"] == "error"


# ---------------------------------------------------------------------------
# GET /webhook-info
# ---------------------------------------------------------------------------


class TestWebhookInfoEndpoint:
    """Tests for the webhook info endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_info_success(self, async_client):
        """GET /webhook-info returns webhook data."""
        mock_info = {"ok": True, "result": {"url": "https://example.com/hook"}}
        with patch.object(
            __import__("src.main", fromlist=["telegram_bot"]).telegram_bot,
            "get_webhook_info",
            return_value=mock_info,
        ):
            resp = await async_client.get("/webhook-info")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_webhook_info_error(self, async_client):
        """GET /webhook-info returns 500 on failure."""
        with patch(
            "src.main.telegram_bot"
        ) as mock_bot:
            mock_bot.get_webhook_info.side_effect = RuntimeError("fail")
            resp = await async_client.get("/webhook-info")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /set-webhook
# ---------------------------------------------------------------------------


class TestSetWebhookEndpoint:
    """Tests for the set-webhook endpoint."""

    @pytest.mark.asyncio
    async def test_set_webhook_success(self, async_client):
        """POST /set-webhook sets webhook and returns result."""
        mock_result = {"ok": True, "description": "Webhook was set"}
        with patch("src.main.telegram_bot") as mock_bot:
            mock_bot.set_webhook.return_value = mock_result
            resp = await async_client.post(
                "/set-webhook", params={"webhook_url": "https://example.com/hook"}
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_set_webhook_error(self, async_client):
        """POST /set-webhook returns 500 on failure."""
        with patch("src.main.telegram_bot") as mock_bot:
            mock_bot.set_webhook.side_effect = RuntimeError("fail")
            resp = await async_client.post(
                "/set-webhook", params={"webhook_url": "https://example.com/hook"}
            )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /telegram-webhook
# ---------------------------------------------------------------------------


class TestTelegramWebhookEndpoint:
    """Tests for the Telegram webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_no_message(self, async_client):
        """Payload without 'message' returns ok."""
        resp = await async_client.post(
            "/telegram-webhook", json={"update_id": 123}
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_webhook_text_message(self, async_client, db_session):
        """Text message is processed through agent and response sent."""
        mock_result = {
            "result": "success",
            "response_message": "Done!",
            "tools_used": [],
            "metadata": {},
        }
        with (
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.run_inventory_agent", return_value=mock_result),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_bot.send_message_async = AsyncMock()
            resp = await async_client.post(
                "/telegram-webhook",
                json={
                    "message": {
                        "chat": {"id": 42},
                        "text": "Add 5 apples",
                    }
                },
            )
        assert resp.status_code == 200
        mock_bot.send_message_async.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_webhook_no_text_or_voice(self, async_client, db_session):
        """Message with neither text nor voice sends error reply."""
        with (
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_bot.send_message_async = AsyncMock()
            resp = await async_client.post(
                "/telegram-webhook",
                json={
                    "message": {
                        "chat": {"id": 42},
                        "photo": [{"file_id": "abc"}],
                    }
                },
            )
        assert resp.status_code == 200
