"""
scripts/patch_metadata.py
──────────────────────────────────────────────────────────────────────────────
ONE-TIME FIX: adds the 'text' field to your existing metadata.jsonl
by joining it with the chunk files.

This means you do NOT need to re-run the full 23-minute embedding pipeline.
Run this once, then restart the API server.

Usage:
    python scripts/patch_metadata.py
"""
import sys
import json
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import DATA_EMBEDDINGS, DATA_CHUNKS


def patch():
    meta_path = DATA_EMBEDDINGS / "metadata.jsonl"
    backup    = DATA_EMBEDDINGS / "metadata.jsonl.bak"

    if not meta_path.exists():
        logger.error(f"metadata.jsonl not found: {meta_path}")
        sys.exit(1)

    # Step 1: Build chunk_id → text map from all chunk files
    logger.info("Step 1/3: Loading chunk texts...")
    id_to_text: dict[str, str] = {}
    for path in sorted(DATA_CHUNKS.glob("*_chunks.jsonl")):
        count = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj  = json.loads(line)
                cid  = obj.get("chunk_id", "")
                text = obj.get("text", "")
                if cid and text:
                    id_to_text[cid] = text
                    count += 1
        logger.info(f"  {path.name}: {count:,} texts loaded")

    logger.info(f"Total chunk texts loaded: {len(id_to_text):,}")

    # Step 2: Back up original metadata
    logger.info("Step 2/3: Backing up original metadata.jsonl...")
    shutil.copy(meta_path, backup)
    logger.info(f"  Backup saved → {backup}")

    # Step 3: Rewrite metadata with text field
    logger.info("Step 3/3: Patching metadata.jsonl...")
    patched   = 0
    missing   = 0
    out_lines = []

    with open(meta_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj      = json.loads(line)
            chunk_id = obj.get("chunk_id", "")
            text     = id_to_text.get(chunk_id, "")

            if text:
                obj["text"] = text
                patched += 1
            else:
                missing += 1

            out_lines.append(json.dumps(obj, ensure_ascii=False))

    # Write patched file
    with open(meta_path, "w", encoding="utf-8") as f:
        for line in out_lines:
            f.write(line + "\n")

    logger.success(
        f"Patch complete: {patched:,} entries updated, "
        f"{missing} missing text (expected: 0)"
    )

    if missing > 0:
        logger.warning(
            f"{missing} entries still have no text. "
            "This means chunk files don't match metadata. "
            "Run the full pipeline: python scripts/run_pipeline.py --data-dir data/raw"
        )
    else:
        logger.success(
            "All entries patched successfully!\n"
            "Now restart your API server:\n"
            "  Stop it with Ctrl+C, then:\n"
            "  uvicorn src.api.main:app --reload --port 8000"
        )

    # Verify sample
    logger.info("Verifying patch (first 3 entries)...")
    with open(meta_path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            obj = json.loads(line)
            has_text = bool(obj.get("text"))
            logger.info(
                f"  faiss_id={obj['faiss_id']} sport={obj.get('sport')} "
                f"has_text={has_text} "
                f"text_preview='{obj.get('text','')[:60]}...'"
            )


if __name__ == "__main__":
    patch()
