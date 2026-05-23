"""
src/ingestion/chunker.py
"""

import json
import uuid
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from src.config import DATA_PROCESSED, DATA_CHUNKS, CHUNK_SIZE, CHUNK_OVERLAP


def _split_text(
    text: str,
    max_chars: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> list[str]:

    if not text:
        return []

    text = text.strip()

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + max_chars, text_len)

        if end < text_len:
            for sep in [". ", "! ", "? ", "; ", ", "]:
                boundary = text.rfind(sep, start, end)
                if boundary > start:
                    end = boundary + len(sep)
                    break

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        next_start = end - overlap

        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def chunk_jsonl(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        logger.warning(f"Not found: {input_path}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    bad_lines = 0

    with open(input_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:

        for line in tqdm(fin, desc=input_path.stem):
            line = line.strip()

            if not line:
                continue

            try:
                doc = json.loads(line)
            except Exception as e:
                bad_lines += 1
                logger.warning(f"Bad JSON in {input_path.name}: {e}")
                continue

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

                fout.write(
                    json.dumps(chunk, ensure_ascii=False) + "\n"
                )

                total += 1

    logger.info(f"{input_path.stem}: {total:,} chunks → {output_path}")

    if bad_lines:
        logger.warning(f"Skipped {bad_lines} malformed lines")

    return total


def run_all():
    sports = [
        "football",
        "basketball",
        "tennis",
        "cricket",
        "football_live",
        "basketball_live",
        "tennis_live",
        "cricket_live",
        "wikipedia",
    ]

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