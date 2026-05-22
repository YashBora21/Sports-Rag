#!/usr/bin/env python
"""
Test Ollama integration
Run: python scripts/test_ollama.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

logger.info("=" * 70)
logger.info("Testing Ollama Integration")
logger.info("=" * 70)

# Test 1: Config loads
logger.info("\n[1/4] Checking config...")
try:
    from src.config import LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL
    logger.info(f"  LLM_PROVIDER: {LLM_PROVIDER}")
    logger.info(f"  OLLAMA_BASE_URL: {OLLAMA_BASE_URL}")
    logger.info(f"  OLLAMA_MODEL: {OLLAMA_MODEL}")
    assert LLM_PROVIDER == "ollama", f"Expected LLM_PROVIDER='ollama', got '{LLM_PROVIDER}'"
    logger.success("✓ Config looks good")
except Exception as e:
    logger.error(f"✗ Config error: {e}")
    sys.exit(1)

# Test 2: Ollama client imports
logger.info("\n[2/4] Checking Ollama client import...")
try:
    from src.llm.ollama_client import OllamaClient
    logger.success("✓ OllamaClient imported")
except Exception as e:
    logger.error(f"✗ Import error: {e}")
    sys.exit(1)

# Test 3: Ollama connection
logger.info("\n[3/4] Testing Ollama connection...")
try:
    client = OllamaClient()
    logger.success("✓ Ollama client connected")
except Exception as e:
    logger.error(f"✗ Ollama not available at {OLLAMA_BASE_URL}")
    logger.error(f"   Error: {e}")
    logger.error("   Make sure Ollama is running: ollama serve")
    sys.exit(1)

# Test 4: Simple generation
logger.info("\n[4/4] Testing generation...")
try:
    prompt = "What is 2 + 2? Answer in one sentence."
    logger.info(f"  Prompt: {prompt}")
    response = client.generate(prompt)
    logger.info(f"  Response: {response}")
    logger.success("✓ Generation works!")
except Exception as e:
    logger.error(f"✗ Generation error: {e}")
    sys.exit(1)

logger.info("\n" + "=" * 70)
logger.success("All tests passed! Ollama is ready for RAG queries.")
logger.info("=" * 70)
