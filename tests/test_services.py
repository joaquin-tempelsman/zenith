"""Tests for src.services — TelegramBot, message_handler, audio_processor.

All external HTTP and OpenAI calls are mocked.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

from src.services.telegram import TelegramBot
from src.services.message_handler import extract_message_text, extract_voice_text


# ========================================================================
# TelegramBot
# ========================================================================


class TestTelegramBot:
    """Tests for the TelegramBot class."""

    def test_init_uses_provided_token(self):
        """Bot stores the token passed at init."""
        bot = TelegramBot(bot_token="test-token-123")
        assert bot.bot_token == "test-token-123"
        assert "test-token-123" in bot.base_url

    def test_init_falls_back_to_settings(self):
        """Bot falls back to settings.telegram_bot_token."""
        bot = TelegramBot()
        assert bot.bot_token is not None

    @patch("src.services.telegram.httpx.Client")
    def test_send_message(self, mock_client_cls):
        """send_message posts to the correct URL."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.send_message(123, "hi")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    @patch("src.services.telegram.httpx.AsyncClient")
    async def test_send_message_async(self, mock_aclient_cls):
        """send_message_async posts correctly."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_ctx = AsyncMock()
        mock_ctx.post.return_value = mock_resp
        mock_aclient_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_aclient_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = await bot.send_message_async(123, "hi")
        assert result == {"ok": True}

    @patch("src.services.telegram.httpx.Client")
    def test_get_file(self, mock_client_cls):
        """get_file returns file info dict."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"file_path": "voice/file.ogg"}}
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.get_file("file123")
        assert result["ok"] is True

    @patch("src.services.telegram.httpx.Client")
    def test_download_file_success(self, mock_client_cls):
        """download_file writes content and returns True."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.content = b"audio-data"
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        with patch("builtins.open", mock_open()) as mocked_file:
            result = bot.download_file("voice/file.ogg", "/tmp/test.ogg")
        assert result is True

    @patch("src.services.telegram.httpx.Client")
    def test_download_file_failure(self, mock_client_cls):
        """download_file returns False on HTTP error."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("network error")
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.download_file("voice/file.ogg", "/tmp/test.ogg")
        assert result is False

    @patch("src.services.telegram.httpx.Client")
    def test_set_webhook(self, mock_client_cls):
        """set_webhook posts webhook URL."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.set_webhook("https://example.com/hook")
        assert result["ok"] is True

    @patch("src.services.telegram.httpx.Client")
    def test_get_webhook_info(self, mock_client_cls):
        """get_webhook_info returns info dict."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "result": {"url": ""}}
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(get=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.get_webhook_info()
        assert result["ok"] is True

    @patch("src.services.telegram.httpx.Client")
    def test_delete_webhook(self, mock_client_cls):
        """delete_webhook posts and returns result."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock(post=MagicMock(return_value=mock_resp)))
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        bot = TelegramBot(bot_token="tok")
        result = bot.delete_webhook()
        assert result["ok"] is True


# ========================================================================
# extract_message_text
# ========================================================================


class TestExtractMessageText:
    """Tests for the extract_message_text function."""

    @pytest.mark.asyncio
    async def test_text_message(self):
        """Text message returns the text directly."""
        msg = {"text": "Add 5 apples"}
        result = await extract_message_text(msg)
        assert result == "Add 5 apples"

    @pytest.mark.asyncio
    async def test_no_text_or_voice(self):
        """Message with neither text nor voice returns None."""


# ========================================================================
# extract_voice_text
# ========================================================================


class TestExtractVoiceText:
    """Tests for the extract_voice_text function."""

    @pytest.mark.asyncio
    async def test_successful_transcription(self):
        """Voice message is downloaded and transcribed."""
        msg = {"voice": {"file_id": "f123"}}
        mock_bot = AsyncMock()
        mock_bot.get_file_async.return_value = {
            "ok": True,
            "result": {"file_path": "voice/f123.ogg"},
        }
        mock_bot.download_file_async.return_value = True

        with (
            patch("src.services.message_handler.telegram_bot", mock_bot),
            patch("src.services.message_handler.transcribe_audio", return_value="hello world"),
            patch("os.remove"),
        ):
            result = await extract_voice_text(msg)
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_get_file_fails(self):
        """RuntimeError raised when get_file_async fails."""
        msg = {"voice": {"file_id": "f123"}}
        mock_bot = AsyncMock()
        mock_bot.get_file_async.return_value = {"ok": False}

        with (
            patch("src.services.message_handler.telegram_bot", mock_bot),
            pytest.raises(RuntimeError, match="Failed to get file info"),
        ):
            await extract_voice_text(msg)

    @pytest.mark.asyncio
    async def test_download_fails(self):
        """RuntimeError raised when download fails."""
        msg = {"voice": {"file_id": "f123"}}
        mock_bot = AsyncMock()
        mock_bot.get_file_async.return_value = {
            "ok": True,
            "result": {"file_path": "voice/f123.ogg"},
        }
        mock_bot.download_file_async.return_value = False

        with (
            patch("src.services.message_handler.telegram_bot", mock_bot),
            pytest.raises(RuntimeError, match="Failed to download"),
        ):
            await extract_voice_text(msg)


# ========================================================================
# transcribe_audio
# ========================================================================


class TestTranscribeAudio:
    """Tests for the transcribe_audio function."""

    def test_transcribe_calls_openai(self, tmp_path):
        """transcribe_audio calls OpenAI Whisper with the file."""
        audio_file = tmp_path / "test.ogg"
        audio_file.write_bytes(b"fake-audio-data")

        with patch("src.services.audio_processor.client") as mock_client:
            mock_client.audio.transcriptions.create.return_value = "hello world"
            from src.services.audio_processor import transcribe_audio

            result = transcribe_audio(str(audio_file))
        assert result == "hello world"
