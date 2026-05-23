#!/usr/bin/env python
"""Quick script to rebuild the vectorstore with cricket format data."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from loguru import logger
from src.ingestion.data_processor import run_all as process_all
from src.ingestion.chunker import run_all as chunk_all
from src.embeddings.embedder import run as embed_all
from src.config import DATA_RAW

logger.info("=" * 70)
logger.info("REBUILDING VECTORSTORE WITH CRICKET FORMAT DATA")
logger.info("=" * 70)

# Step 1: Process all data including new cricket formats
logger.info("\n[STEP 1/3] Processing data (including ODI/Test/T20 cricket)...")
stats = process_all(DATA_RAW)
logger.info(f"✓ Done: {sum(stats.values()):,} documents total")
for sport, count in stats.items():
    logger.info(f"    {sport}: {count:,}")

# Step 2: Chunk
logger.info("\n[STEP 2/3] Chunking documents...")
total_chunks = chunk_all()
logger.info(f"✓ Done: {total_chunks:,} chunks")

# Step 3: Embed and build FAISS index
logger.info("\n[STEP 3/3] Building embeddings + FAISS index...")
embed_all()
logger.info("✓ Embeddings complete")

logger.success("\n" + "=" * 70)
logger.success("REBUILD COMPLETE - Ready to query with cricket format data!")
logger.success("=" * 70)
