"""
src/ingestion/sofascore_collector.py
Fetches live/recent data from SofaScore via RapidAPI.
Saves raw JSON to data/raw/api/ then converts to processed JSONL.

Usage:
    python -m src.ingestion.sofascore_collector --sport football --days 30
"""
import json
import time
import argparse
import requests
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from src.config import (
    RAPIDAPI_KEY, RAPIDAPI_HOST, SOFASCORE_BASE,
    API_RATE_LIMIT_S, DATA_RAW, DATA_PROCESSED
)


HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
}

# SofaScore sport slugs
SPORT_SLUGS = {
    "football":   "football",
    "basketball": "basketball",
    "tennis":     "tennis",
    "cricket":    "cricket",
}


class SofaScoreCollector:
    def __init__(self):
        self.raw_api_dir = DATA_RAW / "api"
        self.raw_api_dir.mkdir(parents=True, exist_ok=True)
        self._call_count = 0

    def _get(self, endpoint: str, retries: int = 3) -> dict | None:
        url = f"{SOFASCORE_BASE}{endpoint}"
        for attempt in range(retries):
            try:
                time.sleep(API_RATE_LIMIT_S)
                resp = requests.get(url, headers=HEADERS, timeout=10)
                self._call_count += 1

                if resp.status_code == 429:
                    wait = 2 ** attempt * 10
                    logger.warning(f"Rate limited. Sleeping {wait}s...")
                    time.sleep(wait)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.RequestException as e:
                logger.error(f"Request failed (attempt {attempt+1}): {e}")
                if attempt == retries - 1:
                    return None
        return None

    def fetch_scheduled_events(self, sport: str, date: str) -> list[dict]:
        slug = SPORT_SLUGS.get(sport, sport)
        data = self._get(f"/api/v1/sport/{slug}/scheduled-events/{date}")
        if not data:
            return []

        # save raw
        out = self.raw_api_dir / f"{sport}_{date}.json"
        out.write_text(json.dumps(data, indent=2))

        events = data.get("events", [])
        logger.debug(f"  {date}: {len(events)} events")
        return events

    def fetch_date_range(self, sport: str, days: int = 30) -> list[dict]:
        all_events = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            events = self.fetch_scheduled_events(sport, date)
            all_events.extend(events)

        logger.info(f"Fetched {len(all_events)} {sport} events over {days} days "
                    f"({self._call_count} API calls)")
        return all_events

    def events_to_docs(self, events: list[dict], sport: str) -> list[dict]:
        """Convert raw API events to text documents."""
        docs = []
        for ev in events:
            try:
                doc = self._event_to_doc(ev, sport)
                if doc:
                    docs.append(doc)
            except Exception as e:
                logger.warning(f"Skipped event {ev.get('id')}: {e}")
        return docs

    def _event_to_doc(self, ev: dict, sport: str) -> dict | None:
        home = ev.get("homeTeam", {}).get("name", "")
        away = ev.get("awayTeam", {}).get("name", "")
        if not home or not away:
            return None

        hs = ev.get("homeScore", {}).get("current")
        as_ = ev.get("awayScore", {}).get("current")
        tourney = ev.get("tournament", {}).get("name", "Unknown tournament")
        status = ev.get("status", {}).get("description", "")
        ts = ev.get("startTimestamp", 0)
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "unknown date"

        if hs is not None and as_ is not None:
            result = f"final score {home} {hs} - {as_} {away}"
        else:
            result = f"status: {status}"

        text = (
            f"{home} vs {away} in the {tourney} on {date_str}. "
            f"Result: {result}."
        )
        return {
            "text": text,
            "sport": sport,
            "source": "sofascore_api",
            "metadata": {
                "home_team": home,
                "away_team": away,
                "tournament": tourney,
                "date": date_str,
                "status": status,
                "event_id": str(ev.get("id", "")),
            }
        }

    def collect_and_save(self, sport: str, days: int = 30):
        logger.info(f"Collecting {days} days of {sport} from SofaScore...")
        events = self.fetch_date_range(sport, days)
        docs = self.events_to_docs(events, sport)

        # append to existing processed file
        out_path = DATA_PROCESSED / f"{sport}_live.jsonl"
        with open(out_path, "w") as f:
            for doc in docs:
                f.write(json.dumps(doc) + "\n")

        logger.success(f"Saved {len(docs)} live {sport} docs → {out_path}")
        return docs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", default="football",
                        choices=list(SPORT_SLUGS.keys()))
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    collector = SofaScoreCollector()
    collector.collect_and_save(args.sport, args.days)
