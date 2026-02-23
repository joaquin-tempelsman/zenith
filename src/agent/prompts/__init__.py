"""Prompts module for loading system prompts."""
from pathlib import Path
from typing import Literal


Language = Literal["en", "es"]

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(prompt_name: str, language: Language = "en", **kwargs) -> str:
    """
    Load a prompt from the prompts directory with language support.

    Falls back to Spanish (_spa) if the requested language file does not exist.

    Args:
        prompt_name: Name of the prompt file (without language suffix and .txt extension)
        language: Language code ('en' for English, 'es' for Spanish)
        **kwargs: Variables to format into the prompt template

    Returns:
        The prompt string with variables substituted
    """
    lang_suffix = "_eng" if language == "en" else "_spa"
    prompt_path = _PROMPTS_DIR / f"{prompt_name}{lang_suffix}.txt"

    if not prompt_path.exists():
        prompt_path = _PROMPTS_DIR / f"{prompt_name}_spa.txt"

    with open(prompt_path, "r") as f:
        prompt_template = f.read()

    if kwargs:
        return prompt_template.format(**kwargs)
    return prompt_template

