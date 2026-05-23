"""
src/rag/rag_chain.py
──────────────────────────────────────────────────────────────────────────────
Smart RAG chain with intent routing:

  BIO    → Wikipedia live fetch → LLM
  LIVE   → SofaScore API       → LLM
  HISTORY→ FAISS + BM25        → rerank → LLM

  Fallback: if FAISS confidence < threshold → Wikipedia
"""
import time
from loguru import logger

from src.retrieval.retriever import SportsRetriever, RetrievalResult
from src.llm.llm_client      import get_llm_client
from src.rag.query_router    import QueryRouter, QueryIntent
from src.tools.wiki_tool     import search_wikipedia
from src.config              import RAPIDAPI_KEY


# ── Confidence threshold — below this we try Wikipedia fallback ───────────────
FAISS_CONFIDENCE_THRESHOLD = -5.0   # rerank score below this = weak retrieval


# ── Prompt templates ──────────────────────────────────────────────────────────

HISTORY_PROMPT = """\
You are a sports analyst with access to a database of match results, \
player statistics, and tournament records.

Answer the question using the context below.
- Use context as primary source, even if not a perfect match.
- Never invent scores, names, or statistics.
- State which sport/competition the info is from.
- Be concise (3-5 sentences).
- If context is insufficient, say so clearly.

CONTEXT:
{context}

QUESTION: {question}
ANSWER:"""

BIO_PROMPT = """\
You are a sports knowledge assistant.
Using the biography information below, answer the question clearly and concisely.
Focus on career highlights, achievements, and key facts.

BIOGRAPHY:
{context}

QUESTION: {question}
ANSWER:"""

LIVE_PROMPT = """\
You are a live sports reporter.
Using the current match data below, answer the question.
Always mention the date and competition name.

LIVE DATA:
{context}

QUESTION: {question}
ANSWER:"""

NO_DATA_PROMPT = """\
You are a sports analyst assistant.
The retrieval system could not find specific data for this question.
Based on your general sports knowledge, provide a helpful answer but
clearly state that this is from general knowledge, not the sports database.

QUESTION: {question}
ANSWER:"""


class SportsRAGChain:

    def __init__(self, sport_filter: str | None = None):
        logger.info(f"Loading RAG chain (LLM: from .env)...")
        self.retriever    = SportsRetriever(sport_filter=sport_filter)
        self.llm          = get_llm_client()
        self.router       = QueryRouter()
        self._rapidapi_ok = bool(RAPIDAPI_KEY and
                                 RAPIDAPI_KEY != "your-rapidapi-key-here")
        logger.success("RAG chain ready.")

    # ── Context builders ──────────────────────────────────────────────────────

    def _faiss_context(self, retrieval: RetrievalResult) -> str:
        return retrieval.to_context_string()

    def _wiki_context(self, question: str, sport: str | None) -> dict | None:
        return search_wikipedia(question, sport)

    def _live_context(self, sport: str | None) -> str:
        if not self._rapidapi_ok:
            return "Live data unavailable (RAPIDAPI_KEY not configured)."
        try:
            from src.tools.sports_api_tool import get_live_matches, format_live_context
            matches = get_live_matches(sport or "football")
            return format_live_context(matches)
        except Exception as e:
            logger.warning(f"Live data fetch failed: {e}")
            return "Live data temporarily unavailable."

    def _is_weak_retrieval(self, retrieval: RetrievalResult) -> bool:
        """True if top rerank score is below threshold = weak FAISS result."""
        if not retrieval.chunks:
            return True
        top_score = retrieval.chunks[0].rerank_score
        return top_score < FAISS_CONFIDENCE_THRESHOLD

    # ── Main query method ─────────────────────────────────────────────────────

    def query(
        self,
        question:     str,
        sport_filter: str | None = None,
        top_k:        int | None = None,
    ) -> dict:
        t_total = time.time()
        timings = {}

        # ── Step 1: Route the query ───────────────────────────────────────────
        intent: QueryIntent = self.router.route(question)
        sport = sport_filter or intent.sport

        # ── Step 2: Retrieve based on intent ─────────────────────────────────

        source_used = "faiss"
        context     = ""
        sources     = []
        retrieval   = None

        # BIO intent → try Wikipedia first
        if intent.intent == "bio":
            t0       = time.time()
            wiki     = self._wiki_context(intent.rewritten, sport)
            timings["wiki_ms"] = round((time.time() - t0) * 1000)

            if wiki:
                context     = wiki["text"]
                source_used = "wikipedia"
                sources     = [{
                    "text":         wiki["text"],
                    "sport":        sport or "unknown",
                    "source":       "wikipedia",
                    "metadata":     {"title": wiki["title"], "url": wiki["url"]},
                    "rerank_score": 1.0,
                }]
                prompt = BIO_PROMPT.format(context=context, question=question)
            else:
                # Wikipedia failed → fallback to FAISS
                logger.info("Wikipedia returned nothing → falling back to FAISS")
                retrieval = self.retriever.retrieve(
                    query=intent.rewritten, top_k=top_k, sport_filter=sport
                )
                context     = self._faiss_context(retrieval)
                source_used = "faiss_bio_fallback"
                sources     = [c.to_dict() for c in retrieval.chunks]
                timings.update(retrieval.latency)
                prompt = BIO_PROMPT.format(context=context, question=question)

        # LIVE intent → SofaScore API
        elif intent.intent == "live":
            t0       = time.time()
            context  = self._live_context(sport)
            timings["live_api_ms"] = round((time.time() - t0) * 1000)
            source_used = "sofascore_api"
            sources     = [{"text": context, "sport": sport or "football",
                             "source": "sofascore_live", "metadata": {},
                             "rerank_score": 1.0}]
            prompt = LIVE_PROMPT.format(context=context, question=question)

        # HISTORY intent → FAISS (default)
        else:
            t0        = time.time()
            retrieval = self.retriever.retrieve(
                query=intent.rewritten, top_k=top_k, sport_filter=sport
            )
            timings.update(retrieval.latency)
            context     = self._faiss_context(retrieval)
            source_used = "faiss"
            sources     = [c.to_dict() for c in retrieval.chunks]

            # Weak FAISS → try Wikipedia fallback
            if self._is_weak_retrieval(retrieval):
                logger.info(
                    f"Weak FAISS confidence "
                    f"(top score={retrieval.chunks[0].rerank_score if retrieval.chunks else 'N/A'}) "
                    f"→ trying Wikipedia fallback"
                )
                wiki = self._wiki_context(question, sport)
                if wiki:
                    context     = wiki["text"] + "\n\n" + context
                    source_used = "faiss+wikipedia"
                    sources.insert(0, {
                        "text":         wiki["text"],
                        "sport":        sport or "unknown",
                        "source":       "wikipedia",
                        "metadata":     {"title": wiki["title"], "url": wiki["url"]},
                        "rerank_score": 0.9,
                    })

            prompt = HISTORY_PROMPT.format(context=context, question=question)

        # ── Step 3: Generate answer ───────────────────────────────────────────
        t_llm  = time.time()
        try:
            answer = self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Sorry, I encountered an error generating the answer. Please try again."
        llm_ms = round((time.time() - t_llm) * 1000)

        total_ms = round((time.time() - t_total) * 1000)
        timings["llm_ms"]   = llm_ms
        timings["total_ms"] = total_ms

        logger.info(
            f"RAG done {total_ms}ms | "
            f"intent={intent.intent} sport={sport} "
            f"source={source_used} llm={llm_ms}ms"
        )

        return {
            "question":    question,
            "answer":      answer,
            "context":     context,
            "sources":     sources,
            "intent":      intent.intent,
            "sport":       sport,
            "source_used": source_used,
            "latency_ms":  timings,
        }
