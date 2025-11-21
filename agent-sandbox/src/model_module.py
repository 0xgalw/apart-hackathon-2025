"""Model initialization and configuration."""
import os
from langchain_openai import ChatOpenAI


def initialize_llm(models_to_try=None):
    """
    Initialize LLM by trying models in order.
    
    Args:
        models_to_try: List of model names to try in order
        
    Returns:
        Tuple of (llm, chosen_model_name)
        
    Raises:
        ValueError: If no model can be initialized
    """
    if models_to_try is None:
        models_to_try = ["gpt-5", "gpt-4", "gpt-4o"]
        # models_to_try = ["gpt-4", "gpt-4o"]
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    for model_name in models_to_try:
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=openai_api_key,
            temperature=0
        )
        return llm, model_name
    
    raise ValueError(f"Failed to initialize any available model. Tried: {', '.join(models_to_try)}")

