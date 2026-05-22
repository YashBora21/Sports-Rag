"""
src/llm/gemini_client.py
Gemini client with:
- per-request safety settings
- retry handling for 429 quota/rate limits
- robust response extraction
"""

import time
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from src.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)


SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

GENERATION_CONFIG = genai.types.GenerationConfig(
    temperature=LLM_TEMPERATURE,
    max_output_tokens=LLM_MAX_TOKENS,
)


class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env")

        genai.configure(api_key=GEMINI_API_KEY)

        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL
        )

        logger.info(f"Gemini client ready: {GEMINI_MODEL}")

    def generate(self, prompt: str) -> str:
        """
        Generate with automatic retry on quota/rate-limit errors.
        """
        max_retries = 4

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=GENERATION_CONFIG,
                    safety_settings=SAFETY_SETTINGS,
                )

                if (
                    response
                    and hasattr(response, "candidates")
                    and response.candidates
                ):
                    text = "".join(
                        part.text
                        for part in response.candidates[0].content.parts
                        if hasattr(part, "text")
                        and not getattr(part, "thought", False)
                    ).strip()

                    if text:
                        return text

                if hasattr(response, "text") and response.text:
                    return response.text.strip()

                logger.warning("Gemini returned empty response.")
                return "I couldn't generate a response."

            except Exception as e:
                error_msg = str(e)

                # Handle Gemini quota/rate limits
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = 25 + (attempt * 10)

                    logger.warning(
                        f"Gemini rate limit hit. "
                        f"Waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )

                    time.sleep(wait_time)
                    continue

                logger.error(
                    f"Gemini generation error: "
                    f"{type(e).__name__}: {e}"
                )
                raise

        return "Gemini quota exceeded. Please try again shortly."

    def generate_with_history(self, messages: list[dict]) -> str:
        """
        Chat-style generation with retry.
        """
        max_retries = 4

        for attempt in range(max_retries):
            try:
                chat = self.model.start_chat(history=messages[:-1])

                last = messages[-1]["parts"][0]

                response = chat.send_message(
                    last,
                    generation_config=GENERATION_CONFIG,
                    safety_settings=SAFETY_SETTINGS,
                )

                return response.text.strip()

            except Exception as e:
                error_msg = str(e)

                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = 25 + (attempt * 10)

                    logger.warning(
                        f"Gemini chat rate limit hit. "
                        f"Waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )

                    time.sleep(wait_time)
                    continue

                logger.error(f"Gemini chat error: {e}")
                raise

        return "Gemini quota exceeded. Please try again shortly."


def get_langchain_llm() -> ChatGoogleGenerativeAI:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=LLM_TEMPERATURE,
        max_output_tokens=LLM_MAX_TOKENS,
        convert_system_message_to_human=True,
    )