"""
src/tools/wiki_tool.py
Live Wikipedia fallback — fetches player bios on demand
using the MediaWiki API (no key needed, no rate limits on single queries).

Used when FAISS confidence is below threshold for bio-type questions.
"""
import time
import requests
from loguru import logger

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS       = {"User-Agent": "SportsRAG/1.0 (educational project)"}

# Sport-specific search hints to disambiguate common names
SPORT_HINTS = {
    "cricket":    ["cricketer", "cricket"],
    "football":   ["footballer", "football player", "soccer"],
    "basketball": ["basketball player", "NBA"],
    "tennis":     ["tennis player", "tennis"],
}


def _fetch_page(title: str) -> dict | None:
    """Fetch a single Wikipedia page via MediaWiki API."""
    try:
        r = requests.get(
            MEDIAWIKI_API,
            params={
                "action":      "query",
                "format":      "json",
                "titles":      title,
                "prop":        "extracts",
                "exintro":     "1",
                "explaintext": "1",
                "redirects":   "1",
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))
        if "missing" in page:
            return None
        extract = page.get("extract", "").strip()
        if not extract or len(extract) < 80:
            return None
        return page
    except Exception as e:
        logger.warning(f"Wikipedia fetch failed for '{title}': {e}")
        return None


def _search_wikipedia(query: str) -> dict | None:
    """Search Wikipedia and return the top result page."""
    try:
        r = requests.get(
            MEDIAWIKI_API,
            params={
                "action":   "opensearch",
                "format":   "json",
                "search":   query,
                "limit":    3,
                "namespace": 0,
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        results = r.json()
        titles  = results[1] if len(results) > 1 else []
        if not titles:
            return None
        # Try first 3 results, return first that has content
        for title in titles[:3]:
            page = _fetch_page(title)
            if page:
                return page
        return None
    except Exception as e:
        logger.warning(f"Wikipedia search failed for '{query}': {e}")
        return None


def search_wikipedia(query: str, sport: str | None = None) -> dict | None:
    """
    Search Wikipedia for a query, optionally with sport context.

    Returns:
        {
          "title": str,
          "text":  str,   # first 2000 chars of intro
          "source": "wikipedia",
          "url":   str,
        }
        or None if not found.
    """
    t0 = time.time()

    # Try direct page fetch first (exact name like "Steve Smith")
    page = _fetch_page(query)

    # If not found or too short, add sport hint and search
    if not page and sport and sport in SPORT_HINTS:
        for hint in SPORT_HINTS[sport]:
            page = _fetch_page(f"{query} {hint}")
            if page:
                break

    # Fall back to full-text search
    if not page:
        search_q = f"{query} {SPORT_HINTS.get(sport, [''])[0]}" if sport else query
        page = _search_wikipedia(search_q)

    if not page:
        logger.info(f"Wikipedia: no results for '{query}'")
        return None

    title   = page.get("title", query)
    extract = page.get("extract", "").strip()

    # Take first 3 paragraphs, max 2000 chars
    paragraphs = [p.strip() for p in extract.split("\n") if len(p.strip()) > 40]
    text       = " ".join(paragraphs[:3])[:2000]

    ms = round((time.time() - t0) * 1000)
    logger.info(f"Wikipedia: found '{title}' in {ms}ms")

    return {
        "title":  title,
        "text":   f"{title}: {text}",
        "source": "wikipedia",
        "url":    f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        "sport":  sport or "unknown",
    }
