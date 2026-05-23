"""
src/llm/llm_client.py
Unified LLM loader
"""

from src.config import LLM_PROVIDER

if LLM_PROVIDER == "gemini":
    from src.llm.gemini_client import GeminiClient

    def get_llm_client():
        return GeminiClient()

elif LLM_PROVIDER == "ollama":
    from src.llm.ollama_client import OllamaClient

    def get_llm_client():
        return OllamaClient()

else:
    raise ValueError(
        f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}"
    )