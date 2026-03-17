"""
LLM Factory — Central routing for all LLM calls.
Routes requests to OpenAI, HuggingFace, or Gemini based on config/providers.py.
"""

import os
from config.providers import LLM_PROVIDER, get_llm_settings
from src.core.tools.openai_tools import call_openai
from src.core.tools.huggingface_tools import call_huggingface
from src.core.tools.gemini_tools import call_gemini

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    The main entry point for all agent nodes to get an LLM result.
    """
    settings = get_llm_settings()
    provider = LLM_PROVIDER

    # MOCK MODE check
    if os.getenv("USE_MOCKS") == "true":
        # Pass to HF tools which handles mocking for now
        from src.core.tools.huggingface_tools import call_huggingface
        return call_huggingface(system_prompt, user_prompt)

    try:
        if provider == "openai":
            return call_openai(
                system_prompt, 
                user_prompt, 
                model=settings.get("model", "gpt-4o-mini"),
                max_tokens=settings.get("max_tokens", 1024)
            )
        elif provider == "huggingface":
            return call_huggingface(
                system_prompt, 
                user_prompt, 
                model=settings.get("model")
            )
        elif provider == "gemini":
            return call_gemini(
                system_prompt, 
                user_prompt, 
                model=settings.get("model")
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
    except Exception as e:
        print(f"[LLM Factory] Error using {provider}: {e}")
        # Fallback logic could go here
        raise e
