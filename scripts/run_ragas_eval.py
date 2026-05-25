# -*- coding: utf-8 -*-
"""
RAGAS evaluation using local Ollama judge + local embeddings
"""

import json
import requests
from pathlib import Path
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings

BASE_URL = "http://localhost:8000"
QUESTIONS_FILE = Path("data/eval/questions.json")
OUTPUT_FILE = Path("data/eval/ragas_results.json")


def collect_eval_data():
    questions = json.loads(
        QUESTIONS_FILE.read_text(encoding="utf-8")
    )

    rows = []

    for q in questions:
        question = q["question"]
        ground_truth = q["ground_truth"]

        print(f"Evaluating: {question}")

        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"question": question},
                timeout=180,
            )

            if response.status_code != 200:
                print(f"Skipping {question}")
                continue

            data = response.json()

            contexts = [
                chunk.get("text", "")
                for chunk in data.get("sources", [])
                if chunk.get("text")
            ]

            rows.append({
                "question": question,
                "answer": data.get("answer", ""),
                "contexts": contexts,
                "ground_truth": ground_truth,
            })

        except Exception as e:
            print(e)

    return rows


def main():
    rows = collect_eval_data()

    dataset = Dataset.from_list(rows)

    evaluator_llm = ChatOllama(
        model="gemma4:31b-cloud",
        temperature=0,
    )

    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        batch_size=1,
        raise_exceptions=False
    )

    print(result)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    result.to_pandas().to_json(
        OUTPUT_FILE,
        orient="records",
        indent=2,
    )

    print(f"Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()