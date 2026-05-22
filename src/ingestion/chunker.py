"""
src/ingestion/chunker.py
Loads processed JSONL files → splits into chunks → saves to data/chunks/

Each chunk gets:
  - text: the passage the embedder will encode
  - chunk_id: unique ID for the FAISS index
  - metadata: sport, date, teams, source — shown to user as citations

Run:
    python -m src.ingestion.chunker
"""
import json
import uuid
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from src.config import DATA_PROCESSED, DATA_CHUNKS, CHUNK_SIZE, CHUNK_OVERLAP


def _split_text(text: str, max_chars: int = CHUNK_SIZE,
                overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Sports passages are usually 1-3 sentences (100-300 chars).
    Most won't need splitting. This handles edge cases where
    aggregated match summaries get long.
    """
    if len(text) <= max_chars:
        return [text]

    chunks, start = [], 0
    while start < len(text):
        end = start + max_chars
        # try to break at sentence boundary
        boundary = text.rfind(". ", start, end)
        if boundary != -1 and boundary > start:
            end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c.strip()]


def chunk_jsonl(input_path: Path, output_path: Path) -> int:
    """Process one JSONL file → chunked JSONL file."""
    if not input_path.exists():
        logger.warning(f"Not found: {input_path}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    with open(input_path, "r", encoding="utf-8") as fin, \
     open(output_path, "w", encoding="utf-8") as fout:

        for line in tqdm(fin, desc=input_path.stem):
            line = line.strip()
            if not line:
                continue

            doc = json.loads(line)
            text = doc.get("text", "")
            if not text:
                continue

            sub_chunks = _split_text(text)

            for i, chunk_text in enumerate(sub_chunks):
                chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "sport": doc.get("sport", "unknown"),
                    "source": doc.get("source", "kaggle"),
                    "chunk_index": i,
                    "total_chunks": len(sub_chunks),
                    "metadata": doc.get("metadata", {}),
                }

                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                total += 1

    logger.info(f"{input_path.stem}: {total:,} chunks → {output_path}")
    return total


def run_all():
    sports = ["football", "basketball", "tennis", "cricket",
              "football_live", "basketball_live", "tennis_live"]
    grand_total = 0

    for sport in sports:
        src = DATA_PROCESSED / f"{sport}.jsonl"
        dst = DATA_CHUNKS / f"{sport}_chunks.jsonl"
        n = chunk_jsonl(src, dst)
        grand_total += n

    logger.success(f"Total chunks ready for embedding: {grand_total:,}")
    return grand_total


if __name__ == "__main__":
    run_all()
