"""
scripts/quick_fix_index.py
──────────────────────────────────────────────────────────────────────────────
Targeted fix — does NOT re-run the full 25-min embedding pipeline.

What this does:
  1. Re-chunks basketball (was 0 due to Unicode crash)
  2. Chunks wikipedia (was 0, never chunked)
  3. Embeds ONLY the new chunks (basketball + wikipedia ~1,400 docs)
  4. Merges new vectors into existing FAISS index
  5. Rebuilds metadata.jsonl correctly

Run:
    python scripts/quick_fix_index.py
Takes ~3 minutes instead of 25.
"""
import sys
import json
import uuid
import faiss
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sentence_transformers import SentenceTransformer
from src.config import (
    DATA_PROCESSED, DATA_CHUNKS, DATA_EMBEDDINGS,
    FAISS_INDEX_PATH, EMBEDDING_MODEL, EMBEDDING_DIM
)
from src.ingestion.chunker import chunk_jsonl


def rechunk_missing():
    """Re-chunk basketball and wikipedia which had 0 chunks."""
    fixed = {}

    # Basketball
    src = DATA_PROCESSED / "basketball.jsonl"
    dst = DATA_CHUNKS    / "basketball_chunks.jsonl"
    if src.exists():
        logger.info("Re-chunking basketball...")
        n = chunk_jsonl(src, dst)
        fixed["basketball"] = n
        logger.info(f"  basketball: {n:,} chunks")

    # Wikipedia
    src = DATA_PROCESSED / "wikipedia.jsonl"
    dst = DATA_CHUNKS    / "wikipedia_chunks.jsonl"
    if src.exists():
        logger.info("Chunking wikipedia...")
        n = chunk_jsonl(src, dst)
        fixed["wikipedia"] = n
        logger.info(f"  wikipedia: {n:,} chunks")
    else:
        logger.warning("wikipedia.jsonl not found — run enrich_data.py first")

    return fixed


def load_new_chunks(sport_names: list[str]) -> tuple[list[str], list[dict]]:
    """Load text + metadata for the newly chunked files."""
    texts, metas = [], []
    for name in sport_names:
        path = DATA_CHUNKS / f"{name}_chunks.jsonl"
        if not path.exists():
            logger.warning(f"Not found: {path}")
            continue
        count = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj  = json.loads(line)
                    text = obj.get("text", "")
                    if not text:
                        continue
                    texts.append(text)
                    metas.append({
                        "chunk_id": obj["chunk_id"],
                        "text":     text,
                        "sport":    obj.get("sport", name),
                        "source":   obj.get("source", "kaggle"),
                        "metadata": obj.get("metadata", {}),
                    })
                    count += 1
                except Exception as e:
                    logger.warning(f"Bad line in {name}: {e}")
        logger.info(f"  {name}: {count:,} new chunks loaded")
    return texts, metas


def embed_and_merge(new_texts: list[str], new_metas: list[dict]):
    """Embed new chunks and add them to the existing FAISS index."""
    if not new_texts:
        logger.error("No new texts to embed")
        return

    # Load existing index
    index_path = Path(str(FAISS_INDEX_PATH) + ".index")
    logger.info(f"Loading existing FAISS index ({index_path})...")
    index = faiss.read_index(str(index_path))
    existing_count = index.ntotal
    logger.info(f"  Existing vectors: {existing_count:,}")

    # Load existing metadata
    meta_path = DATA_EMBEDDINGS / "metadata.jsonl"
    existing_metas = []
    with open(meta_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                existing_metas.append(json.loads(line))
            except:
                pass
    logger.info(f"  Existing metadata: {len(existing_metas):,} entries")

    # Embed new chunks
    logger.info(f"Embedding {len(new_texts):,} new chunks...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    BATCH = 256
    all_embs = []
    for i in range(0, len(new_texts), BATCH):
        batch = new_texts[i:i+BATCH]
        embs  = model.encode(batch, normalize_embeddings=True,
                             show_progress_bar=False)
        all_embs.append(embs)
        logger.info(f"  Encoded {min(i+BATCH, len(new_texts))}/{len(new_texts)}")

    matrix = np.vstack(all_embs).astype("float32")
    logger.info(f"  Embedding matrix: {matrix.shape}")

    # Add to existing index
    index.add(matrix)
    logger.success(f"Index now has {index.ntotal:,} vectors "
                   f"(+{index.ntotal - existing_count:,} new)")

    # Save updated index
    faiss.write_index(index, str(index_path))
    logger.success(f"Saved updated index → {index_path}")

    # Rebuild metadata — existing + new (with correct faiss_ids)
    logger.info("Rebuilding metadata.jsonl...")
    all_metas = existing_metas.copy()
    start_id  = existing_count
    for i, m in enumerate(new_metas):
        all_metas.append({"faiss_id": start_id + i, **m})

    with open(meta_path, "w", encoding="utf-8") as f:
        for m in all_metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    logger.success(f"metadata.jsonl rebuilt: {len(all_metas):,} entries")

    # Verify sample of new entries
    logger.info("Sample new entries:")
    for m in all_metas[-3:]:
        logger.info(f"  [{m['faiss_id']}] sport={m.get('sport')}  "
                    f"text='{m.get('text','')[:70]}...'")


def main():
    logger.info("="*55)
    logger.info("  SPORTS RAG — QUICK INDEX FIX")
    logger.info("="*55)

    # Step 1: Re-chunk missing files
    logger.info("\n[Step 1] Re-chunking missing files...")
    fixed = rechunk_missing()
    if not fixed:
        logger.error("Nothing to fix — check data/processed/ has the JSONL files")
        sys.exit(1)

    # Step 2: Load new chunks
    logger.info("\n[Step 2] Loading new chunks...")
    new_texts, new_metas = load_new_chunks(list(fixed.keys()))
    logger.info(f"Total new chunks to embed: {len(new_texts):,}")

    if not new_texts:
        logger.error("No chunks loaded. Exiting.")
        sys.exit(1)

    # Step 3: Embed and merge into existing index
    logger.info("\n[Step 3] Embedding + merging into FAISS index...")
    embed_and_merge(new_texts, new_metas)

    logger.info("\n" + "="*55)
    logger.success("DONE — index updated with basketball + wikipedia data")
    logger.info("Restart the API:")
    logger.info("  uvicorn src.api.main:app --reload --port 8000")
    logger.info("Then ask: 'who is Ronaldo?' — should now get a bio answer")
    logger.info("="*55)


if __name__ == "__main__":
    main()
