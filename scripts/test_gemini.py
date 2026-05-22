"""
scripts/test_gemini.py
Quick sanity check — run this FIRST before anything else.
Verifies your Gemini API key works and the model responds.

Run:
    python scripts/test_gemini.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.config import GEMINI_API_KEY, GEMINI_MODEL

def test_gemini():
    print(f"\n{'='*50}")
    print(f"  Testing Gemini: {GEMINI_MODEL}")
    print(f"{'='*50}")

    # 1. Check key exists
    if not GEMINI_API_KEY or GEMINI_API_KEY == "AIza-your-gemini-key-here":
        print("\n❌  GEMINI_API_KEY not set in .env")
        print("    Get your key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    print(f"\n✅  API key found: {GEMINI_API_KEY[:8]}...{GEMINI_API_KEY[-4:]}")

    # 2. Test raw generation
    print("\n[Test 1] Direct generation...")
    try:
        from src.llm.gemini_client import GeminiClient
        client = GeminiClient()
        answer = client.generate(
            "In one sentence: who won the 2022 FIFA World Cup?"
        )
        print(f"✅  Response: {answer}")
    except Exception as e:
        print(f"❌  Direct generation failed: {e}")
        sys.exit(1)

    # 3. Test LangChain wrapper
    print("\n[Test 2] LangChain wrapper...")
    try:
        from src.llm.gemini_client import get_langchain_llm
        from langchain_core.messages import HumanMessage
        llm = get_langchain_llm()
        resp = llm.invoke([HumanMessage(content="Name 3 football leagues in one line.")])
        print(f"✅  LangChain response: {resp.content}")
    except Exception as e:
        print(f"❌  LangChain wrapper failed: {e}")
        sys.exit(1)

    # 4. Test Sports RAG prompt
    print("\n[Test 3] Sports RAG prompt with mock context...")
    try:
        mock_context = (
            "[1] (FOOTBALL) Arsenal beat Chelsea 2-1 in the Premier League "
            "on 2024-04-20. Saka scored twice."
        )
        prompt = f"""You are a sports analyst. Answer using ONLY the context.
CONTEXT:
{mock_context}

QUESTION: Who scored for Arsenal?
ANSWER:"""
        answer = client.generate(prompt)
        print(f"✅  RAG prompt response: {answer}")
    except Exception as e:
        print(f"❌  RAG prompt failed: {e}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print("  All tests passed. Gemini is ready!")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    test_gemini()
