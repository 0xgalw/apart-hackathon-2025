"""Utility functions for file operations and path resolution."""
import os
from pathlib import Path


def read_file_content(file_path):
    """
    Read content from a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def find_prompt_file():
    """
    Find prompt file by checking multiple candidate paths.
    
    Returns:
        Path to prompt file
        
    Raises:
        FileNotFoundError: If no prompt file found
    """
    env_prompt_file = os.getenv("PROMPT_FILE")
    candidate_paths = []
    
    if env_prompt_file:
        candidate_paths.append(env_prompt_file)
    
    candidate_paths.append("/app/prompts/prompt.txt")
    candidate_paths.append(str(Path(__file__).parent.parent / "prompts" / "prompt.txt"))
    
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError(f"Prompt file not found. Tried paths: {', '.join(candidate_paths)}")


def get_system_prompt_file():
    """
    Get system prompt file path.
    
    Returns:
        Path to system prompt file
    """
    return os.getenv(
        "SYSTEM_PROMPT_FILE",
        str(Path(__file__).parent.parent / "prompts" / "system_prompt.txt")
    )

