"""
scripts/enrich_data.py
────────────────────────────────────────────────────────────────────────────
Adds two missing data sources then rebuilds the FAISS index:
  1. Wikipedia player bios    (~90 pages, ~5 min)
  2. SofaScore live data      (~90 days, needs RAPIDAPI_KEY in .env)
  3. Re-chunks all new data
  4. Rebuilds FAISS index     (~25 min)

Usage:
    # Full enrichment (Wikipedia + SofaScore + rebuild)
    python scripts/enrich_data.py

    # Wikipedia only (no API key needed)
    python scripts/enrich_data.py --skip-api

    # Quick test — just Wikipedia, no re-embedding
    python scripts/enrich_data.py --skip-api --skip-embed
"""
import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import DATA_PROCESSED, DATA_CHUNKS, RAPIDAPI_KEY


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-api",   action="store_true",
                        help="Skip SofaScore API collection")
    parser.add_argument("--skip-embed", action="store_true",
                        help="Skip re-embedding (just collect data)")
    parser.add_argument("--sport",      nargs="+",
                        choices=["football","basketball","tennis","cricket"],
                        default=["football","basketball","tennis","cricket"])
    args = parser.parse_args()

    logger.info("="*55)
    logger.info("  SPORTS RAG — DATA ENRICHMENT")
    logger.info("="*55)

    # ── Step 1: Wikipedia scrape ───────────────────────────────────────────
    logger.info("\n[STEP 1] Scraping Wikipedia player bios...")
    from src.ingestion.wikipedia_scraper import run as wiki_run
    wiki_stats = wiki_run(args.sport)
    total_wiki = sum(wiki_stats.values())
    logger.success(f"Wikipedia: {total_wiki} player/team bios collected")

    # ── Step 2: SofaScore API ─────────────────────────────────────────────
    if not args.skip_api:
        if not RAPIDAPI_KEY or RAPIDAPI_KEY == "your-rapidapi-key-here":
            logger.warning("RAPIDAPI_KEY not set — skipping SofaScore collection")
            logger.warning("Add your key to .env: RAPIDAPI_KEY=your-key-here")
        else:
            logger.info("\n[STEP 2] Collecting SofaScore live data (last 30 days)...")
            from src.ingestion.sofascore_collector import SofaScoreCollector
            collector = SofaScoreCollector()
            for sport in args.sport:
                try:
                    docs = collector.collect_and_save(sport, days=30)
                    logger.success(f"  {sport}: {len(docs)} live events")
                except Exception as e:
                    logger.warning(f"  {sport} failed: {e}")
    else:
        logger.info("\n[STEP 2] Skipping SofaScore API (--skip-api)")

    # ── Step 3: Chunk new data ────────────────────────────────────────────
    logger.info("\n[STEP 3] Chunking new data...")
    from src.ingestion.chunker import chunk_jsonl

    new_files = [
        (DATA_PROCESSED / "wikipedia.jsonl",
         DATA_CHUNKS    / "wikipedia_chunks.jsonl"),
    ]
    # also chunk any live files
    for sport in args.sport:
        live_src = DATA_PROCESSED / f"{sport}_live.jsonl"
        live_dst = DATA_CHUNKS    / f"{sport}_live_chunks.jsonl"
        if live_src.exists():
            new_files.append((live_src, live_dst))

    total_new_chunks = 0
    for src, dst in new_files:
        n = chunk_jsonl(src, dst)
        total_new_chunks += n
        logger.info(f"  {src.name}: {n} chunks")

    logger.success(f"New chunks: {total_new_chunks}")

    # ── Step 4: Rebuild FAISS index ───────────────────────────────────────
    if not args.skip_embed:
        logger.info("\n[STEP 4] Rebuilding embeddings + FAISS index...")
        logger.info("  This takes ~25 min on CPU — get a coffee ☕")
        from src.embeddings.embedder import run as embed_run
        embed_run()

        # Rebuild metadata from scratch
        logger.info("  Rebuilding metadata.jsonl...")
        from scripts.rebuild_metadata import rebuild
        rebuild()

        logger.success("Index rebuilt. Restart the API server:")
        logger.success("  uvicorn src.api.main:app --reload --port 8000")
    else:
        logger.info("\n[STEP 4] Skipping re-embedding (--skip-embed)")
        logger.info("  Run manually when ready:")
        logger.info("  python scripts/run_pipeline.py --data-dir data/raw --skip-api")

    logger.info("\n" + "="*55)
    logger.success("ENRICHMENT COMPLETE")
    logger.info(f"  Wikipedia bios : {total_wiki}")
    logger.info(f"  New chunks     : {total_new_chunks}")
    logger.info("="*55)


if __name__ == "__main__":
    main()
