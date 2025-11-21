"""Model initialization and configuration."""
import os
from langchain_openai import ChatOpenAI


def initialize_llm(models_to_try=None):
    """
    Initialize LLM based on MODEL_TYPE environment variable.
    
    Args:
        models_to_try: List of model names to try in order
        
    Returns:
        Tuple of (llm, chosen_model_name)
        
    Raises:
        ValueError: If no model can be initialized
    """
    model_type = os.getenv("MODEL_TYPE", "openai").lower()
    
    if model_type == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required when MODEL_TYPE=openrouter")
        
        if models_to_try is None:
            models_to_try = ["mistralai/mistral-nemo", "anthropic/claude-3-haiku"]
        
        for model_name in models_to_try:
            try:
                llm = ChatOpenAI(
                    model=model_name,
                    openai_api_key=openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0
                )
                print(f"Initialized OpenRouter model: {model_name}")
                return llm, model_name
            except Exception:
                # Model failed, try next one
                continue
        
        raise ValueError(f"Failed to initialize any available OpenRouter model. Tried: {', '.join(models_to_try)}")
    
    elif model_type == "openai":
        if models_to_try is None:
            models_to_try = ["gpt-5-mini", "gpt-5", "gpt-4", "gpt-4o"]
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required when MODEL_TYPE=openai")
        
        for model_name in models_to_try:
            try:
                llm = ChatOpenAI(
                    model=model_name,
                    openai_api_key=openai_api_key,
                    temperature=0
                )
                return llm, model_name
            except Exception:
                # Model failed, try next one
                continue
        
        raise ValueError(f"Failed to initialize any available OpenAI model. Tried: {', '.join(models_to_try)}")
    
    else:
        raise ValueError(f"Unknown MODEL_TYPE: {model_type}. Supported values: 'openrouter', 'openai'")

