"""
scripts/rebuild_metadata.py
──────────────────────────────────────────────────────────────────────────────
Rebuilds metadata.jsonl from scratch using chunk files + existing FAISS index.

Use this when metadata.jsonl is corrupt (0 entries, bad JSON).
Does NOT re-run embeddings — reuses the existing faiss_index.index.
Takes ~30 seconds.

Usage:
    python scripts/rebuild_metadata.py
"""
import sys
import json
import faiss
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import DATA_CHUNKS, DATA_EMBEDDINGS, FAISS_INDEX_PATH


def rebuild():
    index_path = Path(str(FAISS_INDEX_PATH) + ".index")
    meta_path  = DATA_EMBEDDINGS / "metadata.jsonl"

    # ── Verify FAISS index exists ─────────────────────────────────────────
    if not index_path.exists():
        logger.error(f"FAISS index not found: {index_path}")
        logger.error("You need to re-run the full pipeline:")
        logger.error("  python scripts/run_pipeline.py --data-dir data/raw")
        sys.exit(1)

    index = faiss.read_index(str(index_path))
    total_vectors = index.ntotal
    logger.info(f"FAISS index loaded: {total_vectors:,} vectors")

    # ── Load all chunks in the SAME ORDER as embedder ────────────────────
    # embedder.py uses sorted(chunks_dir.glob("*_chunks.jsonl"))
    # We must match that exact order so faiss_id → chunk maps correctly
    logger.info("Loading chunks in embedding order...")
    chunks = []
    for path in sorted(DATA_CHUNKS.glob("*_chunks.jsonl")):
        count = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    text = obj.get("text", "")
                    if not text:
                        continue
                    chunks.append({
                        "chunk_id": obj["chunk_id"],
                        "text":     text,
                        "sport":    obj.get("sport", "unknown"),
                        "source":   obj.get("source", "kaggle"),
                        "metadata": obj.get("metadata", {}),
                    })
                    count += 1
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Skipped bad chunk line in {path.name}: {e}")
        logger.info(f"  {path.name}: {count:,} chunks")

    total_chunks = len(chunks)
    logger.info(f"Total chunks loaded: {total_chunks:,}")

    # ── Sanity check ─────────────────────────────────────────────────────
    if total_chunks != total_vectors:
        logger.warning(
            f"Chunk count ({total_chunks:,}) != FAISS vectors ({total_vectors:,}). "
            "Index may be out of sync. Proceeding with min of both."
        )
        # use whichever is smaller to avoid index-out-of-bounds
        total_chunks = min(total_chunks, total_vectors)
        chunks = chunks[:total_chunks]

    # ── Back up corrupt file ──────────────────────────────────────────────
    if meta_path.exists():
        backup = meta_path.with_suffix(".jsonl.corrupt_bak")
        shutil.copy(meta_path, backup)
        logger.info(f"Corrupt file backed up → {backup}")

    # ── Write clean metadata.jsonl ────────────────────────────────────────
    logger.info("Writing clean metadata.jsonl...")
    DATA_EMBEDDINGS.mkdir(parents=True, exist_ok=True)

    written = 0
    with open(meta_path, "w", encoding="utf-8") as f:
        for faiss_id, chunk in enumerate(chunks):
            record = {"faiss_id": faiss_id, **chunk}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    logger.success(f"metadata.jsonl rebuilt: {written:,} entries → {meta_path}")

    # ── Verify ────────────────────────────────────────────────────────────
    logger.info("Verifying output...")
    verified = 0
    bad      = 0
    with open(meta_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("text") and obj.get("sport"):
                    verified += 1
                else:
                    bad += 1
            except json.JSONDecodeError:
                bad += 1

    if bad > 0:
        logger.error(f"{bad} bad entries after rebuild — something is wrong")
        sys.exit(1)

    logger.success(f"Verification passed: {verified:,} valid entries, 0 bad")

    # Print sample
    logger.info("Sample entries:")
    with open(meta_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            obj = json.loads(line.strip())
            logger.info(
                f"  [{obj['faiss_id']}] sport={obj['sport']}  "
                f"text='{obj['text'][:70]}...'"
            )

    logger.success(
        "\nDone! Now start the API:\n"
        "  uvicorn src.api.main:app --reload --port 8000"
    )


if __name__ == "__main__":
    rebuild()
