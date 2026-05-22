"""
scripts/run_pipeline.py
One-shot script: raw data → processed → chunks → FAISS index.

Usage:
    python scripts/run_pipeline.py --data-dir path/to/your/kaggle/data
    python scripts/run_pipeline.py --data-dir data/raw --skip-api
"""
import sys
import argparse
from pathlib import Path
from loguru import logger

# make sure src/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.data_processor import run_all as process_all
from src.ingestion.chunker import run_all as chunk_all
from src.embeddings.embedder import run as embed_all


def main():
    parser = argparse.ArgumentParser(description="Run full sports RAG pipeline")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Path to folder containing Kaggle CSVs")
    parser.add_argument("--skip-api", action="store_true",
                        help="Skip SofaScore API collection")
    parser.add_argument("--skip-embed", action="store_true",
                        help="Skip embedding step (re-use existing index)")
    args = parser.parse_args()

    logger.info("=" * 55)
    logger.info("  SPORTS RAG — FULL PIPELINE")
    logger.info("=" * 55)

    # Step 1: Process Kaggle CSVs
    logger.info("\n[STEP 1/3] Processing Kaggle data...")
    stats = process_all(args.data_dir)
    logger.info(f"  Done: {sum(stats.values()):,} documents")

    # Step 2: Collect from SofaScore API (optional)
    if not args.skip_api:
        logger.info("\n[STEP 1b] Collecting live data from SofaScore API...")
        try:
            from src.ingestion.sofascore_collector import SofaScoreCollector
            collector = SofaScoreCollector()
            for sport in ["football", "tennis"]:
                collector.collect_and_save(sport, days=30)
        except Exception as e:
            logger.warning(f"API collection failed (check RAPIDAPI_KEY): {e}")
            logger.warning("Continuing without live data...")

    # Step 3: Chunk
    logger.info("\n[STEP 2/3] Chunking documents...")
    total_chunks = chunk_all()
    logger.info(f"  Done: {total_chunks:,} chunks")

    # Step 4: Embed
    if not args.skip_embed:
        logger.info("\n[STEP 3/3] Building embeddings + FAISS index...")
        embed_all()

    logger.success("\nPipeline complete. Ready to query.")
    logger.info("Next: python -m src.api.main   (start the API)")
    logger.info("  or: streamlit run src/frontend/app.py")


if __name__ == "__main__":
    main()
