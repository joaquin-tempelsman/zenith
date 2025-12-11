"""Prompts module for loading system prompts."""
from pathlib import Path


def load_prompt(prompt_name: str, **kwargs) -> str:
    """
    Load a prompt from the prompts directory.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        **kwargs: Variables to format into the prompt template
        
    Returns:
        The prompt string with variables substituted
    """
    prompts_dir = Path(__file__).parent
    prompt_path = prompts_dir / f"{prompt_name}.txt"
    
    with open(prompt_path, "r") as f:
        prompt_template = f.read()
    
    if kwargs:
        return prompt_template.format(**kwargs)
    return prompt_template
