"""
src/rag/query_router.py
──────────────────────────────────────────────────────────────────────────────
Intent router — classifies every query before retrieval.

Three intents:
  BIO    → "who is", "tell me about", "biography", player names
           → use Wikipedia live fallback
  LIVE   → "today", "live", "now", "current score", "latest"
           → use SofaScore API
  HISTORY→ everything else — match results, stats, records
           → use FAISS (default)

Also detects sport context from keywords.
"""
import re
from dataclasses import dataclass
from loguru import logger


@dataclass
class QueryIntent:
    intent:      str          # "bio" | "live" | "history"
    sport:       str | None   # "football" | "basketball" | "tennis" | "cricket" | None
    confidence:  float        # 0.0 – 1.0
    rewritten:   str          # query rewritten for better retrieval


# ── Keyword patterns ──────────────────────────────────────────────────────────

BIO_PATTERNS = [
    r"\bwho is\b", r"\bwho was\b", r"\btell me about\b",
    r"\bbiography\b", r"\bcareer of\b", r"\bprofile\b",
    r"\babout\b.{1,20}\b(player|cricketer|footballer|athlete)\b",
    r"\bbackground\b", r"\bpersonal\b",
]

LIVE_PATTERNS = [
    r"\blive\b", r"\btoday\b", r"\bright now\b", r"\bcurrent(ly)?\b",
    r"\blatest\b", r"\bnow\b", r"\bthis (week|month|season)\b",
    r"\bongoing\b", r"\bscore.*today\b", r"\btoday.*score\b",
    r"\bfixture\b", r"\bschedule\b", r"\bstanding(s)?\b",
    r"\bleaderboard\b",
]

SPORT_KEYWORDS = {
    "football":   [r"\bfootball\b", r"\bsoccer\b", r"\bpremier league\b",
                   r"\bla liga\b", r"\bchampions league\b", r"\bfa cup\b",
                   r"\bfifa\b", r"\bbundesliga\b", r"\bserie a\b",
                   r"\bmessi\b", r"\bronaldo\b", r"\bneymar\b",
                   r"\bmbapp[eé]\b", r"\bhaaland\b", r"\bsalah\b"],
    "cricket":    [r"\bcricket\b", r"\bipl\b", r"\btest match\b",
                   r"\bodi\b", r"\bt20\b", r"\bbatsman\b", r"\bbowler\b",
                   r"\bwicket\b", r"\binning\b", r"\bkohli\b",
                   r"\bdhoni\b", r"\bsmith\b.{0,10}\bcricket\b",
                   r"\bsteve smith\b", r"\bsachin\b", r"\bponting\b"],
    "basketball": [r"\bbasketball\b", r"\bnba\b", r"\bpoints?\b.{0,10}\brebound\b",
                   r"\blakers\b", r"\bceltics\b", r"\bwarriours\b",
                   r"\blebron\b", r"\bcurry\b", r"\bjordan\b",
                   r"\bkobe\b", r"\bdurant\b"],
    "tennis":     [r"\btennis\b", r"\bwimbledon\b", r"\bfrench open\b",
                   r"\bus open\b", r"\baustralian open\b", r"\batp\b",
                   r"\bwta\b", r"\bdjokovic\b", r"\bnadal\b",
                   r"\bfederer\b", r"\balcaraz\b", r"\bsinner\b"],
}


def detect_sport(query: str) -> str | None:
    q = query.lower()
    scores = {sport: 0 for sport in SPORT_KEYWORDS}
    for sport, patterns in SPORT_KEYWORDS.items():
        for pat in patterns:
            if re.search(pat, q):
                scores[sport] += 1
    best = max(scores, key=lambda s: scores[s])
    return best if scores[best] > 0 else None


def rewrite_query(query: str, intent: str, sport: str | None) -> str:
    """
    Rewrite vague queries to improve retrieval quality.
    "who is steve smith" → "Steve Smith cricketer biography career"
    "live arsenal score" → "Arsenal match today score"
    """
    q = query.strip()

    if intent == "bio":
        # Strip "who is / tell me about" prefix
        cleaned = re.sub(
            r"^(who is|who was|tell me about|what is|biography of|profile of)\s+",
            "", q, flags=re.IGNORECASE
        ).strip()
        sport_hint = sport or "sports"
        return f"{cleaned} {sport_hint} biography career statistics"

    if intent == "live":
        return f"{q} today live score result"

    # history — just return cleaned query
    return q


class QueryRouter:
    """
    Classifies user queries into bio / live / history
    and detects sport context.
    """

    def route(self, question: str) -> QueryIntent:
        q     = question.lower().strip()
        sport = detect_sport(question)

        # Check LIVE intent first (highest priority for "today/live" keywords)
        live_score = sum(1 for p in LIVE_PATTERNS if re.search(p, q))
        if live_score >= 1:
            rewritten = rewrite_query(question, "live", sport)
            logger.info(f"Router: LIVE | sport={sport} | '{rewritten}'")
            return QueryIntent("live", sport, min(live_score * 0.4, 1.0), rewritten)

        # Check BIO intent
        bio_score = sum(1 for p in BIO_PATTERNS if re.search(p, q))
        if bio_score >= 1:
            rewritten = rewrite_query(question, "bio", sport)
            logger.info(f"Router: BIO  | sport={sport} | '{rewritten}'")
            return QueryIntent("bio", sport, min(bio_score * 0.5, 1.0), rewritten)

        # Default: HISTORY (FAISS retrieval)
        rewritten = rewrite_query(question, "history", sport)
        logger.info(f"Router: HIST | sport={sport} | '{rewritten}'")
        return QueryIntent("history", sport, 0.7, rewritten)
