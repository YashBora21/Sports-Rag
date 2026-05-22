"""
src/rag/rag_chain.py
Complete RAG pipeline: retriever → prompt → LLM (Gemini or Ollama) → answer.

Supports both Gemini API and Ollama (local Gemma4 or other models).
Provider set via LLM_PROVIDER in .env
"""
import time
from loguru import logger

from src.config import LLM_PROVIDER
from src.retrieval.retriever import SportsRetriever


# Dynamically load the appropriate LLM client
if LLM_PROVIDER == "gemini":
    from src.llm.gemini_client import GeminiClient
    LLMClient = GeminiClient
elif LLM_PROVIDER == "ollama":
    from src.llm.ollama_client import OllamaClient
    LLMClient = OllamaClient
else:
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}. Use 'gemini' or 'ollama'")


SPORTS_RAG_PROMPT = """\
You are a knowledgeable sports analyst assistant with access to a database \
of match results, player statistics, and tournament records.

Answer the user's question using the context passages below.

Rules:
- Use the context as your primary source. Answer based on what the context \
contains, even if it does not perfectly match every word in the question.
- If the context has related information (e.g. season results, team records) \
use it to give the best possible answer and mention what the data shows.
- Only say "I don't have enough data" if the context contains absolutely \
nothing relevant to the question.
- Never invent scores, player names, or statistics not in the context.
- Always state which sport/competition the information is from.
- Keep answers to 3-5 sentences unless asked for more detail.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


class SportsRAGChain:

    def __init__(self, sport_filter: str | None = None):
        logger.info(f"Loading RAG chain (LLM: {LLM_PROVIDER})...")
        self.retriever = SportsRetriever(sport_filter=sport_filter)
        self.llm       = LLMClient()
        logger.success("RAG chain ready.")

    def query(
        self,
        question:     str,
        sport_filter: str | None = None,
        top_k:        int | None = None,
    ) -> dict:
        t_total = time.time()

        retrieval = self.retriever.retrieve(
            query=question, top_k=top_k, sport_filter=sport_filter,
        )

        context = retrieval.to_context_string()
        prompt  = SPORTS_RAG_PROMPT.format(context=context, question=question)

        t_llm  = time.time()
        answer = self.llm.generate(prompt)
        llm_ms = round((time.time() - t_llm) * 1000)

        total_ms = round((time.time() - t_total) * 1000)
        logger.info(
            f"RAG done in {total_ms}ms | "
            f"retrieve={retrieval.latency.get('total_ms', 0)}ms llm={llm_ms}ms"
        )

        return {
            "question":   question,
            "answer":     answer,
            "context":    context,
            "sources":    [c.to_dict() for c in retrieval.chunks],
            "latency_ms": {**retrieval.latency, "llm_ms": llm_ms, "total_ms": total_ms},
        }
