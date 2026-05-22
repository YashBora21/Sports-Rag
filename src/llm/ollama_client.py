"""
src/llm/ollama_client.py
Ollama client for local Gemma4 or other models.
Uses requests to call Ollama API at http://localhost:11434
"""

import requests
from loguru import logger

from src.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)


class OllamaClient:
    def __init__(self):
        if not OLLAMA_BASE_URL:
            raise ValueError("OLLAMA_BASE_URL not set in .env")
        if not OLLAMA_MODEL:
            raise ValueError("OLLAMA_MODEL not set in .env")

        self.base_url = OLLAMA_BASE_URL.rstrip("/")
        self.model = OLLAMA_MODEL
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS

        # Test connection
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info(f"✓ Ollama connected at {self.base_url}")
            else:
                logger.warning(f"⚠ Ollama returned {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Cannot connect to Ollama at {self.base_url}: {e}")
            raise

        logger.info(f"Ollama client ready: {self.model}")

    def generate(self, prompt: str) -> str:
        """
        Generate response using Ollama API.
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Ollama API error {response.status_code}: {error_msg}")
                raise Exception(f"Ollama error: {error_msg}")

            data = response.json()
            text = data.get("response", "").strip()

            if not text:
                logger.warning("Ollama returned empty response.")
                return "I couldn't generate a response."

            return text

        except requests.exceptions.Timeout:
            logger.error("Ollama request timeout (60s). Model taking too long.")
            return "Response generation timed out. Try a simpler question."
        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is it running? Try: ollama serve"
            )
            raise
        except Exception as e:
            logger.error(f"Ollama generation error: {type(e).__name__}: {e}")
            raise

    def generate_with_history(self, messages: list[dict]) -> str:
        """
        Chat-style generation using Ollama /api/chat endpoint.
        Messages format: [{"role": "user"/"assistant", "content": "..."}, ...]
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            }

            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60,
            )

            if response.status_code != 200:
                error_msg = response.text
                logger.error(f"Ollama API error {response.status_code}: {error_msg}")
                raise Exception(f"Ollama error: {error_msg}")

            data = response.json()
            text = data.get("message", {}).get("content", "").strip()

            if not text:
                logger.warning("Ollama returned empty response.")
                return "I couldn't generate a response."

            return text

        except requests.exceptions.Timeout:
            logger.error("Ollama request timeout (60s).")
            return "Response generation timed out."
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}.")
            raise
        except Exception as e:
            logger.error(f"Ollama chat error: {type(e).__name__}: {e}")
            raise
