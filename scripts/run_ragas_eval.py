# -*- coding: utf-8 -*-
"""
RAGAS evaluation for Sports RAG
Uses:
- Gemini (LLM judge)
- HuggingFace embeddings (local, stable)
Metrics:
- faithfulness
- answer_relevancy
- context_precision
- context_recall
"""

import json
import os
import requests
from pathlib import Path

from dotenv import load_dotenv
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings

# ---------------------------------------------------
# Config
# ---------------------------------------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_URL = "http://localhost:8000"
QUESTIONS_FILE = Path("data/eval/questions.json")
OUTPUT_FILE = Path("data/eval/ragas_results.json")


# ---------------------------------------------------
# Collect eval data from RAG API
# ---------------------------------------------------
def collect_eval_data() -> list[dict]:
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"Questions file not found: {QUESTIONS_FILE}")

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    rows = []

    for q in questions:
        question = q["question"]
        ground_truth = q["ground_truth"]

        print(f"\n Querying: {question}")

        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"question": question},
                timeout=180,
            )

            if response.status_code != 200:
                print(f"  ⚠️  API returned {response.status_code} — skipping")
                continue

            data = response.json()

            contexts = [
                chunk.get("text", "")
                for chunk in data.get("sources", [])
                if chunk.get("text", "").strip()
            ]

            if not contexts:
                print(f"  ⚠️  No contexts returned — skipping")
                continue

            answer = data.get("answer", "").strip()
            if not answer:
                print(f"  ⚠️  Empty answer returned — skipping")
                continue

            rows.append({
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth,
            })

            print(f"  ✅ Collected | answer_len={len(answer)} | contexts={len(contexts)}")

        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout for: {question}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Cannot connect to {BASE_URL} — is your RAG server running?")
            break
        except Exception as e:
            print(f"  ❌ Unexpected error: {type(e).__name__}: {e}")

    return rows


# ---------------------------------------------------
# Main
# ---------------------------------------------------
def main():
    # Validate API key
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not found in .env file")

    # Step 1: Collect data
    print("\n========== Collecting RAG Responses ==========")
    rows = collect_eval_data()

    if not rows:
        print("\n❌ No valid rows collected. Exiting.")
        return

    print(f"\n✅ Total rows ready for evaluation: {len(rows)}")

    # Step 2: Build dataset
    dataset = Dataset.from_list(rows)

    # Step 3: Setup Gemini LLM judge
    evaluator_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        generation_config={"temperature": 0.0},
    )

    # Step 4: Setup HuggingFace embeddings (local)
    print("\n Loading HuggingFace embeddings model...")
    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    # Step 5: Run RAGAS evaluation
    print("\n========== Running RAGAS Evaluation ==========")
    result = evaluate(
        dataset=dataset,
        metrics=[
            Faithfulness(),
            AnswerRelevancy(),
            ContextPrecision(),
            ContextRecall(),
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        raise_exceptions=False,
    )

    # Step 6: Print results
    print("\n========== RAGAS Scores ==========")
    print(result)

    # Step 7: Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result.to_pandas().to_json(
        OUTPUT_FILE,
        orient="records",
        indent=2,
    )

    print(f"\n✅ Results saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()