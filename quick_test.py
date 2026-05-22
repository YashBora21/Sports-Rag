"""Quick test - run with: python quick_test.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

print("\n" + "="*70)
print("Testing with gemma4:31b-cloud...")
print("="*70)

# Check config
from src.config import OLLAMA_MODEL, OLLAMA_BASE_URL
print(f"\n✓ Config loaded")
print(f"  OLLAMA_BASE_URL: {OLLAMA_BASE_URL}")
print(f"  OLLAMA_MODEL: {OLLAMA_MODEL}")

# Test connection & generation
from src.llm.ollama_client import OllamaClient
try:
    client = OllamaClient()
    print(f"\n✓ Ollama client initialized")
    
    response = client.generate("What is 2+2? One sentence.")
    print(f"\n✓ Generation works!")
    print(f"  Response: {response}")
    
    print("\n" + "="*70)
    print("SUCCESS! Ready to use with RAG queries.")
    print("="*70 + "\n")
except Exception as e:
    print(f"\n✗ Error: {e}\n")
    sys.exit(1)
