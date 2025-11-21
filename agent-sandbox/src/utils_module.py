"""Utility functions for file operations and path resolution."""
import os
import json
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


def get_prompts_directory():
    """
    Get prompts directory path.
    
    Returns:
        Path to prompts directory
    """
    env_prompts_dir = os.getenv("PROMPTS_DIR")
    if env_prompts_dir:
        return env_prompts_dir
    
    candidate_paths = [
        "/app/prompts",
        str(Path(__file__).parent.parent / "prompts")
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    
    # Default fallback
    return str(Path(__file__).parent.parent / "prompts")


def find_prompt_file_path(prompt_name, prompts_dir=None):
    """
    Find a prompt file path, handling .txt extension automatically.
    
    Args:
        prompt_name: Name of the prompt file (with or without .txt)
        prompts_dir: Directory to search in (defaults to prompts directory)
        
    Returns:
        Path to prompt file if found
        
    Raises:
        FileNotFoundError: If prompt file not found
    """
    if prompts_dir is None:
        prompts_dir = get_prompts_directory()
    
    # Normalize prompt name - remove .txt if present, we'll add it back
    if prompt_name.endswith('.txt'):
        prompt_name = prompt_name[:-4]
    
    # Try multiple paths with .txt extension
    candidate_paths = [
        os.path.join(prompts_dir, f"{prompt_name}.txt"),
        os.path.join("/app/prompts", f"{prompt_name}.txt"),
        str(Path(__file__).parent.parent / "prompts" / f"{prompt_name}.txt"),
        # Also try without .txt in case it's already in the name
        os.path.join(prompts_dir, prompt_name),
        os.path.join("/app/prompts", prompt_name),
        str(Path(__file__).parent.parent / "prompts" / prompt_name)
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    
    raise FileNotFoundError(
        f"Prompt file '{prompt_name}' not found. "
        f"Tried paths: {', '.join(candidate_paths)}"
    )


def load_prompts_from_config(prompt_type="initial"):
    """
    Load and concatenate prompts based on config.json settings.
    
    Args:
        prompt_type: Type of prompt to load ("system", "initial", or "review")
        
    Returns:
        Concatenated prompt content as string
        
    Raises:
        FileNotFoundError: If prompt files not found
    """
    config = load_config()
    prompts_config = config.get("prompts", {})
    
    # Get the specific prompt type config
    type_config = prompts_config.get(prompt_type, {})
    
    if not type_config or "files" not in type_config:
        # Fallback to old behavior based on prompt type
        if prompt_type == "system":
            prompt_file = get_system_prompt_file()
        elif prompt_type == "review":
            prompt_file = get_review_prompt_file()
        else:  # initial
            prompt_file = find_prompt_file()
        return read_file_content(prompt_file)
    
    prompt_files = type_config.get("files", [])
    separator = type_config.get("separator", "\n\n")
    
    if not prompt_files:
        # Fallback to old behavior if no files specified
        if prompt_type == "system":
            prompt_file = get_system_prompt_file()
        elif prompt_type == "review":
            prompt_file = get_review_prompt_file()
        else:  # initial
            prompt_file = find_prompt_file()
        return read_file_content(prompt_file)
    
    prompt_contents = []
    for prompt_name in prompt_files:
        prompt_path = find_prompt_file_path(prompt_name)
        prompt_contents.append(read_file_content(prompt_path))
    
    return separator.join(prompt_contents)


def get_system_prompt_file():
    """
    Get system prompt file path.
    
    Returns:
        Path to system prompt file
    """
    env_file = os.getenv("SYSTEM_PROMPT_FILE")
    if env_file:
        return env_file
    
    # Try to get from config
    try:
        config = load_config()
        prompts_config = config.get("prompts", {})
        system_config = prompts_config.get("system", {})
        system_files = system_config.get("files", [])
        if system_files:
            return find_prompt_file_path(system_files[0])
    except Exception:
        pass
    
    # Default fallback
    return str(Path(__file__).parent.parent / "prompts" / "system_prompt.txt")


def get_review_prompt_file():
    """
    Get review prompt file path.
    
    Returns:
        Path to review prompt file
    """
    env_file = os.getenv("REVIEW_PROMPT_FILE")
    if env_file:
        return env_file
    
    # Try to get from config
    try:
        config = load_config()
        prompts_config = config.get("prompts", {})
        review_config = prompts_config.get("review", {})
        review_files = review_config.get("files", [])
        if review_files:
            return find_prompt_file_path(review_files[0])
    except Exception:
        pass
    
    # Default fallback
    return str(Path(__file__).parent.parent / "prompts" / "review_prompt.txt")


def get_config_file():
    """
    Get config file path.
    
    Returns:
        Path to config file
    """
    return os.getenv(
        "CONFIG_FILE",
        str(Path(__file__).parent.parent / "config.json")
    )


def load_config():
    """
    Load configuration from JSON file.
    
    Returns:
        Dictionary containing configuration
    """
    config_file = get_config_file()
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)

