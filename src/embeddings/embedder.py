"""
src/embeddings/embedder.py
Reads chunks → encodes with SentenceTransformers → builds FAISS index.

FIXES:
- UTF-8 enforced for Windows compatibility
- metadata.jsonl includes chunk text
- Unicode-safe JSON writing
- safer FAISS IVF config

Run:
    python -m src.embeddings.embedder

Output:
    data/embeddings/faiss_index.index
    data/embeddings/metadata.jsonl
"""

import json
import faiss
import numpy as np
from pathlib import Path
from loguru import logger
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

from src.config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    DATA_CHUNKS,
    DATA_EMBEDDINGS,
    FAISS_INDEX_PATH
)

BATCH_SIZE = 256


def load_all_chunks(chunks_dir: Path) -> tuple[list[str], list[dict]]:
    """
    Load all chunk text and metadata from JSONL chunk files.
    UTF-8 enforced for Windows compatibility.
    """
    texts = []
    metas = []

    for path in sorted(chunks_dir.glob("*_chunks.jsonl")):
        logger.info(f"Loading chunks from {path.name}")

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if not line:
                    continue

                obj = json.loads(line)

                text = obj.get("text", "")
                if not text:
                    continue

                texts.append(text)

                metas.append({
                    "chunk_id": obj["chunk_id"],
                    "text": text,   # store actual chunk text
                    "sport": obj.get("sport", "unknown"),
                    "source": obj.get("source", "kaggle"),
                    "metadata": obj.get("metadata", {}),
                })

    logger.info(f"Loaded {len(texts):,} chunks from {chunks_dir}")
    return texts, metas


def build_index(
    texts: list[str],
    model: SentenceTransformer
) -> faiss.Index:
    """
    Encode text chunks and build FAISS vector index.
    Uses cosine similarity via normalized embeddings.
    """
    all_embeddings = []

    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="Encoding"):
        batch = texts[i:i + BATCH_SIZE]

        embs = model.encode(
            batch,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        all_embeddings.append(embs)

    matrix = np.vstack(all_embeddings).astype("float32")

    logger.info(f"Embedding matrix shape: {matrix.shape}")

    # Small dataset → flat index
    if len(texts) < 50_000:
        index = faiss.IndexFlatIP(EMBEDDING_DIM)

    # Large dataset → IVF for faster search
    else:
        quantizer = faiss.IndexFlatIP(EMBEDDING_DIM)

        nlist = min(256, max(1, len(texts) // 39))

        index = faiss.IndexIVFFlat(
            quantizer,
            EMBEDDING_DIM,
            nlist,
            faiss.METRIC_INNER_PRODUCT
        )

        logger.info("Training FAISS IVF index...")
        index.train(matrix)

    index.add(matrix)

    logger.info(f"FAISS index built with {index.ntotal:,} vectors")

    return index


def save_index(index: faiss.Index, metadata: list[dict]):
    """
    Save FAISS index + metadata mapping.
    UTF-8 enforced.
    """
    DATA_EMBEDDINGS.mkdir(parents=True, exist_ok=True)

    index_path = Path(str(FAISS_INDEX_PATH) + ".index")
    meta_path = DATA_EMBEDDINGS / "metadata.jsonl"

    faiss.write_index(index, str(index_path))

    with open(meta_path, "w", encoding="utf-8") as f:
        for i, m in enumerate(metadata):
            f.write(
                json.dumps(
                    {"faiss_id": i, **m},
                    ensure_ascii=False
                ) + "\n"
            )

    logger.success(f"Saved index → {index_path}")
    logger.success(
        f"Saved metadata → {meta_path} ({len(metadata):,} entries)"
    )


def run():
    """
    Main embedding pipeline.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    texts, metas = load_all_chunks(DATA_CHUNKS)

    if not texts:
        logger.error("No chunks found. Run data_processor and chunker first.")
        return

    index = build_index(texts, model)

    save_index(index, metas)

    logger.success("Embedding pipeline complete.")


if __name__ == "__main__":
    run()