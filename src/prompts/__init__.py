"""Prompts module for loading system prompts."""
from pathlib import Path
from typing import Literal


Language = Literal["en", "es"]


def load_prompt(prompt_name: str, language: Language = "en", **kwargs) -> str:
    """
    Load a prompt from the prompts directory with language support.
    
    Args:
        prompt_name: Name of the prompt file (without language suffix and .txt extension)
        language: Language code ('en' for English, 'es' for Spanish)
        **kwargs: Variables to format into the prompt template
        
    Returns:
        The prompt string with variables substituted
    """
    prompts_dir = Path(__file__).parent
    lang_suffix = "_eng" if language == "en" else "_spa"
    prompt_path = prompts_dir / f"{prompt_name}{lang_suffix}.txt"
    
    # Fallback to non-suffixed file if language-specific doesn't exist
    if not prompt_path.exists():
        prompt_path = prompts_dir / f"{prompt_name}.txt"
    
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
    
    if kwargs:
        return prompt_template.format(**kwargs)
    return prompt_template
