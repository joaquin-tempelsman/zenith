"""Tests for access control: secret-code gating and user authorization.

Covers the CRUD layer (AuthorizedUser model) and the webhook gating
logic in the Telegram webhook endpoint.
"""
import pytest
from unittest.mock import patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from src.database.models import MetadataBase, Base
from src.database import crud
from src.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def meta_engine():
    """In-memory SQLite engine with metadata schema initialised."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MetadataBase.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def meta_session(meta_engine) -> Session:
    """Fresh session for the shared metadata database."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=meta_engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def async_client():
    """Async HTTP client wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# CRUD – is_user_authorized
# ---------------------------------------------------------------------------


class TestIsUserAuthorized:
    """Tests for crud.is_user_authorized."""

    def test_unknown_user_is_not_authorized(self, meta_session):
        """A user with no record is not authorized."""
        assert crud.is_user_authorized(meta_session, 999) is False

    def test_authorized_user_returns_true(self, meta_session):
        """After authorization, the check returns True."""
        crud.authorize_user(meta_session, 123)
        assert crud.is_user_authorized(meta_session, 123) is True

    def test_user_with_attempts_only_is_not_authorized(self, meta_session):
        """A user who has only failed attempts is not authorized."""
        crud.increment_failed_attempts(meta_session, 456)
        assert crud.is_user_authorized(meta_session, 456) is False


# ---------------------------------------------------------------------------
# CRUD – authorize_user
# ---------------------------------------------------------------------------


class TestAuthorizeUser:
    """Tests for crud.authorize_user."""

    def test_authorize_new_user(self, meta_session):
        """Creates record and marks user authorized."""
        crud.authorize_user(meta_session, 100)
        assert crud.is_user_authorized(meta_session, 100) is True

    def test_authorize_existing_user_with_attempts(self, meta_session):
        """User who had failed attempts can still be authorized."""
        crud.increment_failed_attempts(meta_session, 200)
        crud.increment_failed_attempts(meta_session, 200)
        crud.authorize_user(meta_session, 200)
        assert crud.is_user_authorized(meta_session, 200) is True


# ---------------------------------------------------------------------------
# CRUD – failed attempts & blocking
# ---------------------------------------------------------------------------


class TestFailedAttemptsAndBlocking:
    """Tests for increment_failed_attempts, get_failed_attempts, is_user_blocked."""

    def test_initial_attempts_is_zero(self, meta_session):
        """Unknown user has zero failed attempts."""
        assert crud.get_failed_attempts(meta_session, 999) == 0

    def test_increment_creates_record(self, meta_session):
        """First increment creates the row with attempts=1."""
        result = crud.increment_failed_attempts(meta_session, 300)
        assert result == 1

    def test_increments_accumulate(self, meta_session):
        """Repeated increments accumulate."""
        crud.increment_failed_attempts(meta_session, 400)
        crud.increment_failed_attempts(meta_session, 400)
        assert crud.get_failed_attempts(meta_session, 400) == 2

    def test_not_blocked_under_limit(self, meta_session):
        """User with fewer than MAX_ACCESS_ATTEMPTS is not blocked."""
        crud.increment_failed_attempts(meta_session, 500)
        crud.increment_failed_attempts(meta_session, 500)
        assert crud.is_user_blocked(meta_session, 500) is False

    def test_blocked_at_limit(self, meta_session):
        """User reaching MAX_ACCESS_ATTEMPTS is blocked."""
        for _ in range(crud.MAX_ACCESS_ATTEMPTS):
            crud.increment_failed_attempts(meta_session, 600)
        assert crud.is_user_blocked(meta_session, 600) is True

    def test_authorized_user_is_never_blocked(self, meta_session):
        """An authorized user is not blocked even with many prior attempts."""
        for _ in range(5):
            crud.increment_failed_attempts(meta_session, 700)
        crud.authorize_user(meta_session, 700)
        assert crud.is_user_blocked(meta_session, 700) is False


# ---------------------------------------------------------------------------
# Webhook integration – access control gate
# ---------------------------------------------------------------------------

def _make_text_payload(chat_id: int, text: str) -> dict:
    """Build a minimal Telegram webhook payload."""
    return {"message": {"chat": {"id": chat_id}, "text": text}}


class TestWebhookAccessControl:
    """Integration tests for the access-control gate in _process_telegram_webhook."""

    @pytest.mark.asyncio
    async def test_access_disabled_allows_all(self, async_client, db_session):
        """When allowed_users_only is False, messages reach the agent."""
        mock_result = {
            "result": "success",
            "response_message": "Done!",
            "tools_used": [],
            "metadata": {},
        }
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.run_inventory_agent", return_value=mock_result),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.telegram_bot_token = "fake"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "Add 5 apples"),
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_correct_code_grants_access(self, async_client, meta_session):
        """Providing the correct secret code authorizes the user."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = True
            mock_settings.secret_code = "testcode"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "testcode"),
            )
        assert resp.status_code == 200
        mock_bot.send_message_async.assert_awaited_once()
        call_args = mock_bot.send_message_async.call_args
        assert "Access granted" in call_args[0][1]

        # Verify user is now stored as authorized
        assert crud.is_user_authorized(meta_session, 42) is True

    @pytest.mark.asyncio
    async def test_wrong_code_prompts_and_increments(self, async_client, meta_session):
        """Wrong text prompts the user and increments failed attempts."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = True
            mock_settings.secret_code = "testcode"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(55, "wrongcode"),
            )
        assert resp.status_code == 200
        mock_bot.send_message_async.assert_awaited_once()
        call_args = mock_bot.send_message_async.call_args
        assert "código de ingreso" in call_args[0][1]

        assert crud.get_failed_attempts(meta_session, 55) == 1

    @pytest.mark.asyncio
    async def test_blocked_user_gets_no_response(self, async_client, meta_session):
        """After MAX_ACCESS_ATTEMPTS wrong codes, the user is silently ignored."""
        # Pre-fill attempts to the limit
        for _ in range(crud.MAX_ACCESS_ATTEMPTS):
            crud.increment_failed_attempts(meta_session, 77)

        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = True
            mock_settings.secret_code = "testcode"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(77, "still wrong"),
            )
        assert resp.status_code == 200
        mock_bot.send_message_async.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_authorized_user_bypasses_gate(self, async_client, meta_session, db_session):
        """An already-authorized user goes straight to the agent."""
        crud.authorize_user(meta_session, 88)

        mock_result = {
            "result": "success",
            "response_message": "Done!",
            "tools_used": [],
            "metadata": {},
        }
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.get_session_for_user", return_value=db_session),
            patch("src.main.run_inventory_agent", return_value=mock_result),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = True
            mock_settings.secret_code = "testcode"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(88, "Add 5 apples"),
            )
        assert resp.status_code == 200
        mock_bot.send_message_async.assert_awaited_once()
        call_args = mock_bot.send_message_async.call_args
        assert "Done!" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_prompt_sent_up_to_max_times(self, async_client, meta_session):
        """The prompt message is sent exactly MAX_ACCESS_ATTEMPTS times, then silence."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = True
            mock_settings.secret_code = "testcode"
            mock_bot.send_message_async = AsyncMock()

            # Send MAX_ACCESS_ATTEMPTS wrong messages — each should get a prompt
            for i in range(crud.MAX_ACCESS_ATTEMPTS):
                resp = await async_client.post(
                    "/telegram-webhook",
                    json=_make_text_payload(99, f"wrong-{i}"),
                )
                assert resp.status_code == 200

            assert mock_bot.send_message_async.await_count == crud.MAX_ACCESS_ATTEMPTS

            # One more message — should be silently ignored
            mock_bot.send_message_async.reset_mock()
            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(99, "wrong again"),
            )
            assert resp.status_code == 200
            mock_bot.send_message_async.assert_not_awaited()
