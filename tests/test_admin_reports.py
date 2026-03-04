"""Tests for admin authentication, message logging, token tracking, and daily reports.

Covers the CRUD layer for AdminUser, MessageLog, TokenUsage models and
the daily-report generation logic.
"""
import pytest
from datetime import date, datetime, timezone, timedelta
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
def db_engine():
    """In-memory SQLite engine with per-user item schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Session:
    """Fresh session for the per-user item database."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def async_client():
    """Async HTTP client wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ---------------------------------------------------------------------------
# CRUD – Admin
# ---------------------------------------------------------------------------


class TestAdminCRUD:
    """Tests for admin CRUD operations."""

    def test_unknown_user_is_not_admin(self, meta_session):
        assert crud.is_admin(meta_session, 999) is False

    def test_grant_admin(self, meta_session):
        crud.grant_admin(meta_session, 100)
        assert crud.is_admin(meta_session, 100) is True

    def test_grant_admin_idempotent(self, meta_session):
        crud.grant_admin(meta_session, 100)
        crud.grant_admin(meta_session, 100)
        assert crud.is_admin(meta_session, 100) is True

    def test_revoke_admin(self, meta_session):
        crud.grant_admin(meta_session, 200)
        assert crud.revoke_admin(meta_session, 200) is True
        assert crud.is_admin(meta_session, 200) is False

    def test_revoke_non_admin(self, meta_session):
        assert crud.revoke_admin(meta_session, 999) is False

    def test_get_all_admins(self, meta_session):
        crud.grant_admin(meta_session, 10)
        crud.grant_admin(meta_session, 20)
        admins = crud.get_all_admins(meta_session)
        assert set(admins) == {10, 20}

    def test_get_all_admins_empty(self, meta_session):
        assert crud.get_all_admins(meta_session) == []


# ---------------------------------------------------------------------------
# CRUD – Message logging
# ---------------------------------------------------------------------------


class TestMessageLogging:
    """Tests for message logging CRUD operations."""

    def test_log_message_and_total_users(self, meta_session):
        crud.log_message(meta_session, 100)
        crud.log_message(meta_session, 200)
        crud.log_message(meta_session, 100)  # duplicate user
        assert crud.get_total_users(meta_session) == 2

    def test_get_all_user_chat_ids(self, meta_session):
        crud.log_message(meta_session, 10)
        crud.log_message(meta_session, 20)
        ids = crud.get_all_user_chat_ids(meta_session)
        assert set(ids) == {10, 20}

    def test_get_daily_active_users(self, meta_session):
        crud.log_message(meta_session, 100)
        crud.log_message(meta_session, 200)
        active = crud.get_daily_active_users(meta_session, date.today())
        assert set(active) == {100, 200}

    def test_get_daily_active_users_no_activity(self, meta_session):
        crud.log_message(meta_session, 100)
        yesterday = date.today() - timedelta(days=1)
        # The message was logged today, so yesterday should be empty
        active = crud.get_daily_active_users(meta_session, yesterday)
        assert active == []

    def test_total_users_empty(self, meta_session):
        assert crud.get_total_users(meta_session) == 0


# ---------------------------------------------------------------------------
# CRUD – Token usage
# ---------------------------------------------------------------------------


class TestTokenUsage:
    """Tests for token usage CRUD operations."""

    def test_log_and_get_daily_tokens(self, meta_session):
        crud.log_token_usage(meta_session, 100, input_tokens=50, output_tokens=30)
        crud.log_token_usage(meta_session, 200, input_tokens=100, output_tokens=70)
        result = crud.get_daily_token_usage(meta_session, date.today())
        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 100
        assert result["total_tokens"] == 250

    def test_daily_tokens_zero_on_empty_day(self, meta_session):
        result = crud.get_daily_token_usage(meta_session, date.today())
        assert result["total_tokens"] == 0

    def test_monthly_token_usage(self, meta_session):
        crud.log_token_usage(meta_session, 100, input_tokens=200, output_tokens=100)
        today = date.today()
        result = crud.get_monthly_token_usage(meta_session, today.year, today.month)
        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 100
        assert result["total_tokens"] == 300

    def test_monthly_tokens_zero_on_empty_month(self, meta_session):
        result = crud.get_monthly_token_usage(meta_session, 2020, 1)
        assert result["total_tokens"] == 0


# ---------------------------------------------------------------------------
# Daily report generation
# ---------------------------------------------------------------------------


class TestDailyReport:
    """Tests for generate_daily_report."""

    def test_report_contains_sections(self, meta_session):
        crud.log_message(meta_session, 100)
        crud.log_message(meta_session, 200)
        crud.log_token_usage(meta_session, 100, 50, 30)

        with patch(
            "src.services.daily_report.get_metadata_session",
            return_value=meta_session,
        ):
            from src.services.daily_report import generate_daily_report
            report = generate_daily_report(date.today())

        assert "Daily Report" in report
        assert "Total users" in report
        assert "Active today" in report
        assert "Token usage today" in report
        assert "Token usage this month" in report

    def test_report_empty_db(self, meta_session):
        with patch(
            "src.services.daily_report.get_metadata_session",
            return_value=meta_session,
        ):
            from src.services.daily_report import generate_daily_report
            report = generate_daily_report(date.today())

        assert "Total users" in report
        assert "0" in report


# ---------------------------------------------------------------------------
# send_daily_reports
# ---------------------------------------------------------------------------


class TestSendDailyReports:
    """Tests for send_daily_reports."""

    @pytest.mark.asyncio
    async def test_send_to_admins(self, meta_session):
        crud.grant_admin(meta_session, 10)
        crud.grant_admin(meta_session, 20)

        with (
            patch(
                "src.services.daily_report.get_metadata_session",
                return_value=meta_session,
            ),
            patch("src.services.daily_report.telegram_bot") as mock_bot,
        ):
            mock_bot.send_message_async = AsyncMock()
            from src.services.daily_report import send_daily_reports
            sent = await send_daily_reports(date.today())

        assert sent == 2
        assert mock_bot.send_message_async.await_count == 2

    @pytest.mark.asyncio
    async def test_no_admins_sends_nothing(self, meta_session):
        with (
            patch(
                "src.services.daily_report.get_metadata_session",
                return_value=meta_session,
            ),
            patch("src.services.daily_report.telegram_bot") as mock_bot,
        ):
            mock_bot.send_message_async = AsyncMock()
            from src.services.daily_report import send_daily_reports
            sent = await send_daily_reports(date.today())

        assert sent == 0
        mock_bot.send_message_async.assert_not_awaited()


# ---------------------------------------------------------------------------
# Webhook – /admin command
# ---------------------------------------------------------------------------


def _make_text_payload(chat_id: int, text: str) -> dict:
    """Build a minimal Telegram webhook payload."""
    return {"message": {"chat": {"id": chat_id}, "text": text}}


class TestAdminWebhook:
    """Integration tests for the /admin command in the webhook."""

    @pytest.mark.asyncio
    async def test_admin_auth_correct_code(self, async_client, meta_session):
        """Providing correct admin code grants admin access."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.admin_secret_code = "adminpass"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "/admin adminpass"),
            )
        assert resp.status_code == 200
        assert crud.is_admin(meta_session, 42) is True
        call_text = mock_bot.send_message_async.call_args[0][1]
        assert "Admin access granted" in call_text

    @pytest.mark.asyncio
    async def test_admin_auth_wrong_code(self, async_client, meta_session):
        """Providing wrong admin code is rejected."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.admin_secret_code = "adminpass"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "/admin wrongcode"),
            )
        assert resp.status_code == 200
        assert crud.is_admin(meta_session, 42) is False
        call_text = mock_bot.send_message_async.call_args[0][1]
        assert "Invalid admin code" in call_text

    @pytest.mark.asyncio
    async def test_admin_report_command(self, async_client, meta_session):
        """Admin can request a report with /admin report."""
        crud.grant_admin(meta_session, 42)

        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.admin_secret_code = "adminpass"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "/admin report"),
            )
        assert resp.status_code == 200
        call_text = mock_bot.send_message_async.call_args[0][1]
        assert "Daily Report" in call_text

    @pytest.mark.asyncio
    async def test_admin_report_denied_non_admin(self, async_client, meta_session):
        """Non-admin user cannot get a report."""
        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.admin_secret_code = "adminpass"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "/admin report"),
            )
        assert resp.status_code == 200
        call_text = mock_bot.send_message_async.call_args[0][1]
        assert "Admin access required" in call_text

    @pytest.mark.asyncio
    async def test_admin_status_command(self, async_client, meta_session):
        """Admin can check status with /admin status."""
        crud.grant_admin(meta_session, 42)

        with (
            patch("src.main.settings") as mock_settings,
            patch("src.main.get_metadata_session", return_value=meta_session),
            patch("src.main.telegram_bot") as mock_bot,
        ):
            mock_settings.allowed_users_only = False
            mock_settings.admin_secret_code = "adminpass"
            mock_bot.send_message_async = AsyncMock()

            resp = await async_client.post(
                "/telegram-webhook",
                json=_make_text_payload(42, "/admin status"),
            )
        assert resp.status_code == 200
        call_text = mock_bot.send_message_async.call_args[0][1]
        assert "You are an admin" in call_text
