"""
Telegram message handling utilities.

Provides wrappers for extracting user text from voice and text messages,
keeping the webhook route handlers in main.py thin.
"""
import os
import tempfile
from pathlib import Path

from .telegram import telegram_bot
from .audio_processor import transcribe_audio


async def extract_voice_text(message: dict) -> str:
    """
    Download a Telegram voice message, transcribe it, and return the text.

    Handles the full lifecycle: fetch file metadata from Telegram,
    download the .ogg audio to a temporary directory, run Whisper
    transcription, and clean up the temp file.

    Args:
        message: Telegram message dict that contains a ``voice`` key

    Returns:
        Transcribed text from the voice message

    Raises:
        RuntimeError: If file info retrieval or download fails
    """
    voice = message["voice"]
    file_id = voice["file_id"]

    file_info = await telegram_bot.get_file_async(file_id)
    if not file_info.get("ok"):
        raise RuntimeError("Failed to get file info from Telegram")

    file_path = file_info["result"]["file_path"]

    temp_dir = Path(tempfile.gettempdir()) / "inventory_audio"
    temp_dir.mkdir(exist_ok=True)

    audio_file_path = temp_dir / f"{file_id}.ogg"
    download_success = await telegram_bot.download_file_async(
        file_path, str(audio_file_path)
    )
    if not download_success:
        raise RuntimeError("Failed to download audio file")

    text = transcribe_audio(str(audio_file_path))

    try:
        os.remove(audio_file_path)
    except Exception:
        pass

    return text


async def extract_message_text(message: dict) -> str | None:
    """
    Extract user text from a Telegram message (voice or text).

    Delegates to :func:`extract_voice_text` for voice messages and
    returns the plain text for text messages.  Returns ``None`` if the
    message contains neither voice nor text.

    Args:
        message: Telegram message dict from the webhook payload

    Returns:
        The user's text input, or None if the message type is unsupported
    """
    if "voice" in message:
        return await extract_voice_text(message)
    if "text" in message:
        return message["text"]
    return None

