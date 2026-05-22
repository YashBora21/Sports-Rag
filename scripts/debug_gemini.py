"""
scripts/debug_gemini.py
Isolates whether Gemini is receiving context and responding correctly.
Run this while the server is stopped.

Usage:
    python scripts/debug_gemini.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from src.config import GEMINI_API_KEY, GEMINI_MODEL

genai.configure(api_key=GEMINI_API_KEY)

MOCK_CONTEXT = """[1] (CRICKET) IPL 2019: Mumbai Indians beat Chennai Super Kings by 1 run at Rajiv Gandhi International Cricket Stadium, Hyderabad. Toss won by Mumbai Indians who chose to bat. Player of the match: Jasprit Bumrah.
[2] (CRICKET) IPL 2019: Royal Challengers Bangalore beat Kings XI Punjab by 8 wickets at IS Bindra Stadium, Mohali. Toss won by Royal Challengers Bangalore who chose to field. Player of the match: AB de Villiers."""

QUESTION = "Who won the 2019 IPL final?"

print(f"\n{'='*60}")
print(f"Model: {GEMINI_MODEL}")
print(f"API key: {GEMINI_API_KEY[:8]}...")
print(f"{'='*60}")

# ── Test 1: Raw generate with no safety settings ──────────────────────────────
print("\n[Test 1] Raw generate (no safety settings)...")
try:
    model    = genai.GenerativeModel(model_name=GEMINI_MODEL)
    prompt   = f"Context:\n{MOCK_CONTEXT}\n\nQuestion: {QUESTION}\nAnswer:"
    response = model.generate_content(prompt)

    print(f"  response type      : {type(response)}")
    print(f"  candidates count   : {len(response.candidates)}")
    print(f"  finish_reason      : {response.candidates[0].finish_reason}")
    print(f"  response.text      : {response.text[:200]}")
    print("  ✓ Test 1 PASSED")
except Exception as e:
    print(f"  ✗ Test 1 FAILED: {type(e).__name__}: {e}")

# ── Test 2: With safety settings (old format) ─────────────────────────────────
print("\n[Test 2] With safety settings (old dict format)...")
try:
    SAFETY = [
        {"category": "HARM_CATEGORY_HARASSMENT",       "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH",      "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT","threshold": "BLOCK_NONE"},
    ]
    model    = genai.GenerativeModel(
        model_name      = GEMINI_MODEL,
        safety_settings = SAFETY,
    )
    response = model.generate_content(prompt)
    print(f"  response.text: {response.text[:200]}")
    print("  ✓ Test 2 PASSED")
except Exception as e:
    print(f"  ✗ Test 2 FAILED: {type(e).__name__}: {e}")

# ── Test 3: generation_config with thinking disabled ─────────────────────────
print("\n[Test 3] With thinking_config disabled (gemini-2.5-flash specific)...")
try:
    model = genai.GenerativeModel(model_name=GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature        = 0.0,
            max_output_tokens  = 1024,
        ),
    )
    print(f"  finish_reason : {response.candidates[0].finish_reason}")
    print(f"  response.text : {response.text[:200]}")
    print("  ✓ Test 3 PASSED")
except Exception as e:
    print(f"  ✗ Test 3 FAILED: {type(e).__name__}: {e}")

# ── Test 4: Check what response object actually contains ──────────────────────
print("\n[Test 4] Full response inspection...")
try:
    model    = genai.GenerativeModel(model_name=GEMINI_MODEL)
    response = model.generate_content(prompt)
    cand     = response.candidates[0]
    print(f"  finish_reason  : {cand.finish_reason}")
    print(f"  safety_ratings : {cand.safety_ratings}")
    print(f"  parts count    : {len(cand.content.parts)}")
    for i, part in enumerate(cand.content.parts):
        print(f"  part[{i}] type : {type(part)}")
        if hasattr(part, 'text'):
            print(f"  part[{i}] text : {part.text[:100]}")
        if hasattr(part, 'thought'):
            print(f"  part[{i}] thought: {part.thought}")
except Exception as e:
    print(f"  ✗ Test 4 FAILED: {type(e).__name__}: {e}")

print(f"\n{'='*60}")
print("Share the output above — it shows exactly where Gemini fails.")
print(f"{'='*60}\n")
