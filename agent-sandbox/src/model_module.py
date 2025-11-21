"""Model initialization and configuration."""
import os
from langchain_openai import ChatOpenAI
from utils_module import load_config


def initialize_llm(models_to_try=None):
    """
    Initialize LLM based on model_type from config.json.
    
    Args:
        models_to_try: List of model names to try in order
        
    Returns:
        Tuple of (llm, chosen_model_name)
        
    Raises:
        ValueError: If no model can be initialized
    """
    config = load_config()
    model_type = config.get("model_type", "openai").lower()
    
    if model_type == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required when model_type=openrouter")
        
        if models_to_try is None:
            openrouter_config = config.get("openrouter", {})
            chosen_model = openrouter_config.get("chosen_model")
            models = openrouter_config.get("models", [])
            
            # If chosen_model is specified, try it first, then fall back to models list
            if chosen_model:
                models_to_try = [chosen_model] + [m for m in models if m != chosen_model]
            else:
                models_to_try = models
        
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
            openai_config = config.get("openai", {})
            chosen_model = openai_config.get("chosen_model")
            models = openai_config.get("models", [])
            
            # If chosen_model is specified, try it first, then fall back to models list
            if chosen_model:
                models_to_try = [chosen_model] + [m for m in models if m != chosen_model]
            else:
                models_to_try = models
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required when model_type=openai")
        
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

