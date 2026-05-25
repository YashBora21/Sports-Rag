"""
src/rag/rag_chain.py
Smart RAG chain — now with accurate source tracking for eval.

source_used values (precise):
  "wikipedia"           — wiki fetch succeeded, answer from Wikipedia
  "faiss_bio_fallback"  — bio intent but wiki failed, used FAISS
  "faiss_wiki_boost"    — history intent, weak FAISS, wiki boosted context
  "faiss"               — history intent, FAISS only
  "sofascore_api"       — live intent, RapidAPI data
  "sofascore_unavailable" — live intent but no API key
"""
import time
from loguru import logger

from src.retrieval.retriever import SportsRetriever, RetrievalResult
from src.llm.llm_client      import get_llm_client
from src.rag.query_router    import QueryRouter, QueryIntent
from src.tools.wiki_tool     import search_wikipedia, test_connectivity
from src.config              import RAPIDAPI_KEY

FAISS_CONFIDENCE_THRESHOLD = -5.0

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
Using the biography below, answer the question clearly.
Focus on career highlights, achievements, and key facts.

BIOGRAPHY:
{context}

QUESTION: {question}
ANSWER:"""

LIVE_PROMPT = """\
You are a live sports reporter.
Using the current match data below, answer the question.
Always mention the date and competition.

LIVE DATA:
{context}

QUESTION: {question}
ANSWER:"""


class SportsRAGChain:

    def __init__(self, sport_filter: str | None = None):
        logger.info(f"Loading RAG chain (LLM: from .env)...")
        self.retriever     = SportsRetriever(sport_filter=sport_filter)
        self.llm           = get_llm_client()
        self.router        = QueryRouter()
        self._rapidapi_ok  = bool(RAPIDAPI_KEY and
                                  RAPIDAPI_KEY != "your-rapidapi-key-here")
        # Check Wikipedia at startup
        self._wiki_ok      = test_connectivity()
        logger.success(
            f"RAG chain ready. "
            f"Wikipedia: {'✓' if self._wiki_ok else '✗'} | "
            f"SofaScore: {'✓' if self._rapidapi_ok else '✗'}"
        )

    def _wiki_fetch(self, question: str, sport: str | None) -> dict | None:
        if not self._wiki_ok:
            logger.warning("Skipping Wikipedia — connectivity check failed at startup")
            return None
        return search_wikipedia(question, sport)

    def _live_fetch(self, sport: str | None) -> str:
        if not self._rapidapi_ok:
            return "Live data unavailable (RAPIDAPI_KEY not configured)."
        try:
            from src.tools.sports_api_tool import get_live_matches, format_live_context
            matches = get_live_matches(sport or "football")
            return format_live_context(matches)
        except Exception as e:
            logger.warning(f"Live data fetch failed: {e}")
            return "Live data temporarily unavailable."

    def _is_weak(self, retrieval: RetrievalResult) -> bool:
        if not retrieval.chunks:
            return True
        return retrieval.chunks[0].rerank_score < FAISS_CONFIDENCE_THRESHOLD

    def query(
        self,
        question:     str,
        sport_filter: str | None = None,
        top_k:        int | None = None,
    ) -> dict:
        t_total = time.time()
        timings = {}

        intent: QueryIntent = self.router.route(question)
        sport   = sport_filter or intent.sport
        context = ""
        sources = []
        source_used = "faiss"   # default — overridden below

        # ── BIO intent ────────────────────────────────────────────────────────
        if intent.intent == "bio":
            t0   = time.time()
            wiki = self._wiki_fetch(intent.rewritten, sport)
            timings["wiki_ms"] = round((time.time() - t0) * 1000)

            if wiki:
                # Wikipedia succeeded
                context     = wiki["text"]
                source_used = "wikipedia"
                sources     = [{
                    "text":         wiki["text"],
                    "sport":        sport or "unknown",
                    "source":       "wikipedia",
                    "metadata":     {
                        "title":    wiki["title"],
                        "url":      wiki["url"],
                        "tried":    wiki.get("tried", []),
                    },
                    "rerank_score": 1.0,
                }]
                prompt = BIO_PROMPT.format(context=context, question=question)
                logger.info(f"BIO: Wikipedia ✓ '{wiki['title']}'")

            else:
                # Wikipedia failed → FAISS fallback
                logger.warning(
                    f"BIO: Wikipedia failed for '{question}' "
                    f"(wiki_ok={self._wiki_ok}) → FAISS fallback"
                )
                retrieval   = self.retriever.retrieve(
                    query=intent.rewritten, top_k=top_k, sport_filter=sport
                )
                context     = retrieval.to_context_string()
                source_used = "faiss_bio_fallback"
                sources     = [c.to_dict() for c in retrieval.chunks]
                timings.update(retrieval.latency)
                prompt = BIO_PROMPT.format(context=context, question=question)

        # ── LIVE intent ───────────────────────────────────────────────────────
        elif intent.intent == "live":
            t0      = time.time()
            context = self._live_fetch(sport)
            timings["live_api_ms"] = round((time.time() - t0) * 1000)
            source_used = "sofascore_api" if self._rapidapi_ok else "sofascore_unavailable"
            sources     = [{
                "text":         context,
                "sport":        sport or "football",
                "source":       source_used,
                "metadata":     {},
                "rerank_score": 1.0,
            }]
            prompt = LIVE_PROMPT.format(context=context, question=question)

        # ── HISTORY intent (default) ──────────────────────────────────────────
        else:
            retrieval = self.retriever.retrieve(
                query=intent.rewritten, top_k=top_k, sport_filter=sport
            )
            timings.update(retrieval.latency)
            context     = retrieval.to_context_string()
            source_used = "faiss"
            sources     = [c.to_dict() for c in retrieval.chunks]

            # Weak FAISS → boost with Wikipedia
            if self._is_weak(retrieval):
                top_score = retrieval.chunks[0].rerank_score if retrieval.chunks else "N/A"
                logger.info(f"HISTORY: weak FAISS (score={top_score}) → Wikipedia boost")
                t0   = time.time()
                wiki = self._wiki_fetch(question, sport)
                timings["wiki_ms"] = round((time.time() - t0) * 1000)
                if wiki:
                    context     = wiki["text"] + "\n\n" + context
                    source_used = "faiss_wiki_boost"
                    sources.insert(0, {
                        "text":         wiki["text"],
                        "sport":        sport or "unknown",
                        "source":       "wikipedia",
                        "metadata":     {"title": wiki["title"], "url": wiki["url"]},
                        "rerank_score": 0.9,
                    })

            prompt = HISTORY_PROMPT.format(context=context, question=question)

        # ── LLM generation ────────────────────────────────────────────────────
        t_llm = time.time()
        try:
            answer = self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            answer = f"Error generating answer: {str(e)}"
        llm_ms   = round((time.time() - t_llm) * 1000)
        total_ms = round((time.time() - t_total) * 1000)

        timings["llm_ms"]   = llm_ms
        timings["total_ms"] = total_ms

        logger.info(
            f"RAG {total_ms}ms | intent={intent.intent} "
            f"sport={sport} source={source_used} llm={llm_ms}ms"
        )

        return {
            "question":    question,
            "answer":      answer,
            "context":     context,
            "sources":     sources,
            "intent":      intent.intent,
            "sport":       sport,
            "source_used": source_used,      # precise tracking
            "wiki_ok":     self._wiki_ok,    # diagnostic
            "latency_ms":  timings,
        }
