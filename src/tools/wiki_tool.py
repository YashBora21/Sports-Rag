"""
src/tools/wiki_tool.py
Live Wikipedia fallback using MediaWiki Action API.

FIXES:
  1. Better error logging — shows exactly WHY fetch failed
  2. Multiple fallback strategies per query
  3. Returns diagnostic info so eval can track what happened
  4. Timeout increased to 15s for slow connections
"""
import time
import requests
from loguru import logger

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS       = {"User-Agent": "SportsRAG/1.0 (educational project; github.com/YashBora21)"}

SPORT_HINTS = {
    "cricket":    ["cricketer", "cricket player"],
    "football":   ["footballer", "soccer player"],
    "basketball": ["basketball player", "NBA player"],
    "tennis":     ["tennis player"],
}

# Track fetch attempts for diagnostics
_fetch_log: list[dict] = []


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
            headers = HEADERS,
            timeout = 15,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))

        if "missing" in page:
            logger.debug(f"Wikipedia: '{title}' page missing")
            return None

        extract = page.get("extract", "").strip()
        if not extract or len(extract) < 80:
            logger.debug(f"Wikipedia: '{title}' extract too short ({len(extract)} chars)")
            return None

        return page

    except requests.Timeout:
        logger.warning(f"Wikipedia timeout for '{title}' (>15s)")
        return None
    except requests.ConnectionError as e:
        logger.warning(f"Wikipedia connection failed for '{title}': {e}")
        return None
    except Exception as e:
        logger.warning(f"Wikipedia fetch failed for '{title}': {type(e).__name__}: {e}")
        return None


def _opensearch(query: str) -> list[str]:
    """Get top 3 Wikipedia title suggestions for a query."""
    try:
        r = requests.get(
            MEDIAWIKI_API,
            params={
                "action":    "opensearch",
                "format":    "json",
                "search":    query,
                "limit":     3,
                "namespace": 0,
            },
            headers = HEADERS,
            timeout = 10,
        )
        r.raise_for_status()
        results = r.json()
        return results[1] if len(results) > 1 else []
    except Exception as e:
        logger.warning(f"Wikipedia opensearch failed for '{query}': {e}")
        return []


def search_wikipedia(query: str, sport: str | None = None) -> dict | None:
    """
    Search Wikipedia with multiple fallback strategies.
    Returns document dict or None.

    Strategy order:
      1. Direct title fetch (exact name)
      2. Direct fetch with sport disambiguation hint
      3. OpenSearch → fetch first result
    """
    t0       = time.time()
    tried    = []
    page     = None

    # Strategy 1 — exact title
    tried.append(query)
    page = _fetch_page(query)

    # Strategy 2 — with sport hint
    if not page and sport and sport in SPORT_HINTS:
        for hint in SPORT_HINTS[sport]:
            title = f"{query} {hint}"
            tried.append(title)
            page = _fetch_page(title)
            if page:
                break

    # Strategy 3 — opensearch
    if not page:
        search_q = f"{query} {SPORT_HINTS.get(sport,[''])[0]}" if sport else query
        suggestions = _opensearch(search_q)
        for title in suggestions:
            if title not in tried:
                tried.append(title)
                page = _fetch_page(title)
                if page:
                    break

    ms = round((time.time() - t0) * 1000)

    # Log diagnostic for eval tracking
    _fetch_log.append({
        "query":   query,
        "sport":   sport,
        "tried":   tried,
        "success": page is not None,
        "ms":      ms,
    })

    if not page:
        logger.info(
            f"Wikipedia: no result for '{query}' "
            f"(tried {len(tried)} variants in {ms}ms)"
        )
        return None

    title   = page.get("title", query)
    extract = page.get("extract", "").strip()
    paras   = [p.strip() for p in extract.split("\n") if len(p.strip()) > 40]
    text    = " ".join(paras[:3])[:2000]

    logger.info(f"Wikipedia: ✓ '{title}' ({ms}ms, tried {len(tried)} variants)")

    return {
        "title":  title,
        "text":   f"{title}: {text}",
        "source": "wikipedia",
        "url":    f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        "sport":  sport or "unknown",
        "tried":  tried,
    }


def get_fetch_log() -> list[dict]:
    """Return diagnostic log of all Wikipedia fetch attempts."""
    return _fetch_log.copy()


def test_connectivity() -> bool:
    """Quick connectivity check — call at startup."""
    try:
        r = requests.get(
            MEDIAWIKI_API,
            params={"action": "query", "format": "json",
                    "titles": "Cricket", "prop": "info"},
            headers=HEADERS, timeout=8,
        )
        ok = r.status_code == 200
        logger.info(f"Wikipedia connectivity: {'✓ OK' if ok else '✗ FAILED'}")
        return ok
    except Exception as e:
        logger.warning(f"Wikipedia connectivity check failed: {e}")
        return False
