"""
Audio processing service for transcription via OpenAI Whisper.
"""
from pathlib import Path
from openai import OpenAI
from ..config import settings


client = OpenAI(api_key=settings.openai_api_key)


def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper.

    Args:
        file_path: Path to the audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)

    Returns:
        Transcribed text from the audio file

    Raises:
        FileNotFoundError: If audio file doesn't exist
        Exception: If transcription fails
    """
    audio_file_path = Path(file_path)

    with open(audio_file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", file=audio_file, response_format="text"
        )

    return transcript


async def transcribe_audio_async(file_path: str) -> str:
    """
    Async version of transcribe_audio for use in async contexts.

    Args:
        file_path: Path to the audio file

    Returns:
        Transcribed text from the audio file
    """
    return transcribe_audio(file_path)

