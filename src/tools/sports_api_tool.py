"""
src/tools/sports_api_tool.py
Live sports data via SofaScore RapidAPI.
Used when query contains live/today/current keywords.

Requires RAPIDAPI_KEY in .env
"""
import time
import requests
from datetime import datetime
from loguru import logger
from src.config import RAPIDAPI_KEY, RAPIDAPI_HOST, SOFASCORE_BASE

HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
}

SPORT_SLUGS = {
    "football":   "football",
    "basketball": "basketball",
    "tennis":     "tennis",
    "cricket":    "cricket",
    "all":        "football",  # default
}


def _get(endpoint: str) -> dict | None:
    try:
        r = requests.get(
            f"{SOFASCORE_BASE}{endpoint}",
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"SofaScore API error: {e}")
        return None


def get_live_matches(sport: str = "football") -> list[dict]:
    """Get today's scheduled matches."""
    slug = SPORT_SLUGS.get(sport, "football")
    date = datetime.now().strftime("%Y-%m-%d")
    data = _get(f"/api/v1/sport/{slug}/scheduled-events/{date}")
    if not data:
        return []
    events = data.get("events", [])
    results = []
    for ev in events[:10]:   # top 10 events
        home   = ev.get("homeTeam", {}).get("name", "")
        away   = ev.get("awayTeam", {}).get("name", "")
        hs     = ev.get("homeScore", {}).get("current")
        as_    = ev.get("awayScore", {}).get("current")
        status = ev.get("status", {}).get("description", "")
        tourney= ev.get("tournament", {}).get("name", "")

        score  = f"{hs}-{as_}" if hs is not None and as_ is not None else "TBD"
        text   = (
            f"{home} vs {away} | {tourney} | "
            f"Score: {score} | Status: {status} | Date: {date}"
        )
        results.append({
            "text":   text,
            "sport":  sport,
            "source": "sofascore_live",
            "home":   home,
            "away":   away,
            "score":  score,
            "status": status,
        })
    logger.info(f"SofaScore: {len(results)} live events for {sport}")
    return results


def format_live_context(matches: list[dict]) -> str:
    """Format live match list as context string for LLM."""
    if not matches:
        return "No live matches found for today."
    lines = [f"[LIVE] {m['text']}" for m in matches]
    return "\n".join(lines)
