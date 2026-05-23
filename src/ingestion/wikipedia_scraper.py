"""
src/ingestion/wikipedia_scraper.py
────────────────────────────────────────────────────────────────────────────
Uses MediaWiki Action API (https://en.wikipedia.org/w/api.php)
instead of the REST summary API.

Key advantages over REST API:
  - Batch up to 10 pages per request  → 10x fewer HTTP calls
  - No rate limiting issues           → all pages succeed
  - exintro=1 gives full intro section (richer than REST summary)
  - explaintext=1 gives clean plain text, no HTML

Run:
    python -m src.ingestion.wikipedia_scraper
    python -m src.ingestion.wikipedia_scraper --sport football
"""
import json
import time
import argparse
import requests
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from src.config import DATA_PROCESSED

MEDIAWIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS       = {"User-Agent": "SportsRAG/1.0 (educational project; contact via GitHub)"}
BATCH_SIZE    = 10     # MediaWiki allows up to 50, we use 10 to stay safe
DELAY         = 1.0    # seconds between batch requests (polite)

# ── All pages to scrape ───────────────────────────────────────────────────────
PLAYERS = {
    "football": [
        # Players
        "Cristiano Ronaldo", "Lionel Messi", "Neymar",
        "Kylian Mbappé", "Erling Haaland", "Mohamed Salah",
        "Robert Lewandowski", "Kevin De Bruyne", "Virgil van Dijk",
        "Luka Modrić", "Karim Benzema", "Harry Kane",
        "Vinicius Junior", "Jude Bellingham", "Pedri",
        "Thierry Henry", "Zinedine Zidane", "Ronaldinho",
        "Pelé", "Diego Maradona", "Johan Cruyff",
        "Ronaldo (Brazilian footballer)",
        # Clubs
        "FC Barcelona", "Real Madrid CF", "Manchester City FC",
        "Liverpool FC", "Arsenal FC", "Chelsea FC",
        "Bayern Munich", "Paris Saint-Germain FC", "Juventus FC",
        "AC Milan", "Manchester United FC", "Tottenham Hotspur FC",
        # Tournaments
        "FIFA World Cup", "UEFA Champions League", "Premier League",
        "La Liga", "Serie A", "Bundesliga", "Ligue 1",
        "UEFA Europa League", "FIFA Club World Cup",
    ],
    "basketball": [
        # Players
        "LeBron James", "Stephen Curry", "Kevin Durant",
        "Giannis Antetokounmpo", "Nikola Jokić", "Luka Dončić",
        "Joel Embiid", "Jayson Tatum", "Anthony Davis",
        "Kawhi Leonard", "Michael Jordan", "Kobe Bryant",
        "Shaquille O'Neal", "Magic Johnson", "Larry Bird",
        "Tim Duncan", "Dirk Nowitzki", "Kareem Abdul-Jabbar",
        "Scottie Pippen", "Charles Barkley",
        # Teams & leagues
        "NBA", "Golden State Warriors", "Los Angeles Lakers",
        "Boston Celtics", "Chicago Bulls", "Miami Heat",
        "Brooklyn Nets", "Milwaukee Bucks",
    ],
    "tennis": [
        # Players
        "Novak Djokovic", "Rafael Nadal", "Roger Federer",
        "Carlos Alcaraz", "Jannik Sinner", "Daniil Medvedev",
        "Andy Murray", "Serena Williams", "Iga Świątek",
        "Naomi Osaka", "Venus Williams", "Steffi Graf",
        "Pete Sampras", "Andre Agassi", "Boris Becker",
        "John McEnroe", "Billie Jean King",
        # Tournaments
        "Wimbledon Championships", "French Open",
        "US Open (tennis)", "Australian Open",
        "ATP Tour", "WTA Tour",
    ],
    "cricket": [
        # Players
        "Virat Kohli", "Rohit Sharma", "MS Dhoni",
        "Sachin Tendulkar", "Babar Azam", "Steve Smith",
        "Pat Cummins", "Ben Stokes", "Joe Root",
        "Kane Williamson", "AB de Villiers", "Brian Lara",
        "Ricky Ponting", "Wasim Akram", "Shane Warne",
        "Muttiah Muralitharan", "Kumar Sangakkara",
        # Tournaments & formats
        "Indian Premier League", "ICC Cricket World Cup",
        "Test cricket", "One Day International",
        "Twenty20 International", "ICC World Twenty20",
        "The Ashes", "Border-Gavaskar Trophy",
    ],
}


# ── MediaWiki batch fetcher ───────────────────────────────────────────────────

def fetch_batch(titles: list[str]) -> dict[str, dict]:
    """
    Fetch up to 10 Wikipedia pages in a single API call.
    Returns dict of { normalized_title: page_data }
    """
    params = {
        "action":         "query",
        "format":         "json",
        "titles":         "|".join(titles),
        "prop":           "extracts|description",
        "exintro":        "1",        # intro section only
        "explaintext":    "1",        # plain text, no HTML
        "exsectionformat":"plain",
        "redirects":      "1",        # follow redirects
    }
    try:
        r = requests.get(
            MEDIAWIKI_API, params=params,
            headers=HEADERS, timeout=15,
        )
        r.raise_for_status()
        data  = r.json()
        pages = data.get("query", {}).get("pages", {})

        # Build normalized title → page map
        result = {}
        for page in pages.values():
            if "missing" in page:
                continue
            title   = page.get("title", "")
            extract = page.get("extract", "").strip()
            if extract and len(extract) > 80:
                result[title] = page
        return result

    except Exception as e:
        logger.warning(f"Batch fetch failed: {e}")
        return {}


def page_to_doc(page: dict, sport: str) -> dict | None:
    """Convert a MediaWiki page dict to a RAG document."""
    title   = page.get("title", "")
    extract = page.get("extract", "").strip()
    desc    = page.get("description", "")

    if not extract or len(extract) < 80:
        return None

    # Take first 3 paragraphs, max 1200 chars for good chunk size
    paragraphs = [p.strip() for p in extract.split("\n") if len(p.strip()) > 40]
    text       = " ".join(paragraphs[:3])[:1200]

    return {
        "text":   f"{title}: {text}",
        "sport":  sport,
        "source": "wikipedia",
        "metadata": {
            "title":       title,
            "description": desc,
            "sport":       sport,
            "wiki_url":    f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        }
    }


def scrape_sport(sport: str, titles: list[str]) -> list[dict]:
    """Scrape all pages for one sport using batch requests."""
    docs = []

    # Split into batches of BATCH_SIZE
    batches = [titles[i:i+BATCH_SIZE] for i in range(0, len(titles), BATCH_SIZE)]

    for batch in tqdm(batches, desc=f"Wikipedia/{sport}"):
        pages = fetch_batch(batch)
        for title, page in pages.items():
            doc = page_to_doc(page, sport)
            if doc:
                docs.append(doc)
        time.sleep(DELAY)   # polite delay between batches

    logger.info(f"  {sport}: {len(docs)}/{len(titles)} pages scraped")
    return docs


def run(sports: list[str] | None = None) -> dict[str, int]:
    sports   = sports or list(PLAYERS.keys())
    stats    = {}
    all_docs = []

    for sport in sports:
        if sport not in PLAYERS:
            logger.warning(f"Unknown sport: {sport}")
            continue
        titles = PLAYERS[sport]
        docs   = scrape_sport(sport, titles)
        all_docs.extend(docs)
        stats[sport] = len(docs)

    # Save to processed/
    out_path = DATA_PROCESSED / "wikipedia.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for doc in all_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    total = sum(stats.values())
    logger.success(f"Wikipedia done: {total} docs → {out_path}")
    for s, n in stats.items():
        logger.info(f"  {s:12s}: {n} docs")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", nargs="+",
                        choices=list(PLAYERS.keys()),
                        help="Scrape specific sports only")
    args = parser.parse_args()
    run(args.sport)
