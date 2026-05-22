"""
src/retrieval/retriever.py
Hybrid FAISS + BM25 retriever with cross-encoder reranking.

FIX: _load_texts_and_metadata now reads text directly from metadata.jsonl
     (text field is now stored there by embedder.py).
     No more chunk-file lookup → faster startup, no silent empty-text bug.
"""
import json
import time
import faiss
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi

from src.config import (
    EMBEDDING_MODEL, FAISS_INDEX_PATH, DATA_EMBEDDINGS,
    RETRIEVER_TOP_K, RERANKER_TOP_K, RERANKER_MODEL,
)


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    text:          str
    sport:         str
    source:        str
    metadata:      dict
    faiss_id:      int
    dense_score:   float = 0.0
    bm25_score:    float = 0.0
    rrf_score:     float = 0.0
    rerank_score:  float = 0.0

    def to_dict(self) -> dict:
        return {
            "text":         self.text,
            "sport":        self.sport,
            "source":       self.source,
            "metadata":     self.metadata,
            "faiss_id":     self.faiss_id,
            "dense_score":  round(self.dense_score,  4),
            "bm25_score":   round(self.bm25_score,   4),
            "rrf_score":    round(self.rrf_score,     6),
            "rerank_score": round(self.rerank_score,  4),
        }


@dataclass
class RetrievalResult:
    query:   str
    chunks:  list[RetrievedChunk]
    latency: dict = field(default_factory=dict)

    @property
    def texts(self) -> list[str]:
        return [c.text for c in self.chunks]

    def to_context_string(self) -> str:
        parts = []
        for i, c in enumerate(self.chunks, 1):
            parts.append(f"[{i}] ({c.sport.upper()}) {c.text}")
        return "\n\n".join(parts)

    def summary(self) -> str:
        return (
            f"Query : {self.query}\n"
            f"Chunks: {len(self.chunks)}\n"
            f"Sports: {list({c.sport for c in self.chunks})}\n"
            f"Time  : retrieve={self.latency.get('hybrid_ms',0)}ms  "
            f"rerank={self.latency.get('rerank_ms',0)}ms  "
            f"total={self.latency.get('total_ms',0)}ms"
        )


# ── Main retriever ────────────────────────────────────────────────────────────

class SportsRetriever:

    def __init__(
        self,
        top_k_retrieval: int       = RETRIEVER_TOP_K,
        top_k_final:     int       = RERANKER_TOP_K,
        sport_filter:    str|None  = None,
        use_reranker:    bool      = True,
    ):
        self.top_k_retrieval = top_k_retrieval
        self.top_k_final     = top_k_final
        self.sport_filter    = sport_filter
        self.use_reranker    = use_reranker

        logger.info("Initialising SportsRetriever...")
        t0 = time.time()

        self._load_faiss_index()
        self._load_metadata()        # ← reads text directly from metadata.jsonl
        self._build_bm25()
        if use_reranker:
            self._load_reranker()

        elapsed = round((time.time() - t0) * 1000)
        logger.success(
            f"Retriever ready in {elapsed}ms | "
            f"{self.index.ntotal:,} vectors | "
            f"BM25 corpus: {len(self.corpus_texts):,} docs"
        )

    # ── Loaders ───────────────────────────────────────────────────────────────

    def _load_faiss_index(self):
        index_path = Path(str(FAISS_INDEX_PATH) + ".index")
        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}\n"
                "Run: python scripts/run_pipeline.py --data-dir data/raw"
            )
        self.index = faiss.read_index(str(index_path))
        logger.info(f"FAISS index loaded: {self.index.ntotal:,} vectors")

    def _load_metadata(self):
        """
        Load metadata.jsonl — text field now stored directly here.
        This is the FIX: no separate chunk-file lookup needed.
        """
        meta_path = DATA_EMBEDDINGS / "metadata.jsonl"
        if not meta_path.exists():
            raise FileNotFoundError(f"metadata.jsonl not found: {meta_path}")

        self.metadata: list[dict] = []
        missing_text = 0
        bad_lines    = 0

        with open(meta_path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue                    # skip blank lines silently
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    bad_lines += 1
                    logger.warning(f"Bad JSON at line {lineno}: {e} — skipped")
                    continue
                if not obj.get("text"):
                    missing_text += 1
                self.metadata.append(obj)

        if bad_lines:
            logger.warning(
                f"{bad_lines} corrupt lines skipped in metadata.jsonl. "
                "Run: python scripts/patch_metadata.py"
            )

        if missing_text:
            logger.warning(
                f"{missing_text:,} entries have no text field. "
                "Re-run: python scripts/run_pipeline.py --data-dir data/raw --skip-api"
            )
        else:
            logger.info(f"Metadata loaded: {len(self.metadata):,} entries (all have text)")

    def _build_bm25(self):
        logger.info("Building BM25 index...")
        t0 = time.time()
        self.corpus_texts = [m.get("text", "") for m in self.metadata]
        tokenized = [text.lower().split() for text in self.corpus_texts]
        self.bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 ready in {round((time.time()-t0)*1000)}ms")

    def _load_reranker(self):
        logger.info(f"Loading reranker: {RERANKER_MODEL}")
        self.reranker = CrossEncoder(RERANKER_MODEL, max_length=512)

    @property
    def embedder(self) -> SentenceTransformer:
        if not hasattr(self, "_embedder"):
            logger.info(f"Loading embedder: {EMBEDDING_MODEL}")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL)
        return self._embedder

    # ── Retrieval stages ──────────────────────────────────────────────────────

    def _dense_retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        q_vec = self.embedder.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        ).astype("float32")

        scores, ids = self.index.search(q_vec, top_k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            m = self.metadata[idx]
            if self.sport_filter and m.get("sport") != self.sport_filter:
                continue
            text = m.get("text", "")
            if not text:
                continue          # skip silently — don't send empty text to LLM
            results.append(RetrievedChunk(
                text        = text,
                sport       = m.get("sport", "unknown"),
                source      = m.get("source", "kaggle"),
                metadata    = m.get("metadata", {}),
                faiss_id    = int(idx),
                dense_score = float(score),
            ))
        return results

    def _bm25_retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_ids = np.argsort(scores)[::-1][:top_k * 2]

        results = []
        for idx in top_ids:
            if len(results) >= top_k:
                break
            if scores[idx] <= 0:
                continue
            m = self.metadata[idx]
            if self.sport_filter and m.get("sport") != self.sport_filter:
                continue
            text = m.get("text", "")
            if not text:
                continue
            results.append(RetrievedChunk(
                text       = text,
                sport      = m.get("sport", "unknown"),
                source     = m.get("source", "kaggle"),
                metadata   = m.get("metadata", {}),
                faiss_id   = int(idx),
                bm25_score = float(scores[idx]),
            ))
        return results

    def _rrf_merge(
        self,
        dense:  list[RetrievedChunk],
        sparse: list[RetrievedChunk],
        k:      int = 60,
    ) -> list[RetrievedChunk]:
        rrf: dict[int, float] = {}
        for rank, c in enumerate(dense):
            rrf[c.faiss_id] = rrf.get(c.faiss_id, 0) + 1 / (k + rank + 1)
        for rank, c in enumerate(sparse):
            rrf[c.faiss_id] = rrf.get(c.faiss_id, 0) + 1 / (k + rank + 1)

        seen:   set[int]             = set()
        merged: list[RetrievedChunk] = []
        for c in dense + sparse:
            if c.faiss_id not in seen:
                c.rrf_score = rrf[c.faiss_id]
                merged.append(c)
                seen.add(c.faiss_id)
        return sorted(merged, key=lambda c: c.rrf_score, reverse=True)

    def _rerank(
        self,
        query:  str,
        chunks: list[RetrievedChunk],
        top_k:  int,
    ) -> list[RetrievedChunk]:
        if not self.use_reranker or not chunks:
            return chunks[:top_k]
        pairs  = [(query, c.text) for c in chunks]
        scores = self.reranker.predict(pairs, show_progress_bar=False)
        for c, s in zip(chunks, scores):
            c.rerank_score = float(s)
        return sorted(chunks, key=lambda c: c.rerank_score, reverse=True)[:top_k]

    # ── Public API ────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query:        str,
        top_k:        int|None  = None,
        sport_filter: str|None  = None,
    ) -> RetrievalResult:
        final_k      = top_k or self.top_k_final
        orig_filter  = self.sport_filter
        if sport_filter:
            self.sport_filter = sport_filter

        timings: dict[str, int] = {}
        t_total = time.time()

        t0             = time.time()
        dense_results  = self._dense_retrieve(query, self.top_k_retrieval)
        sparse_results = self._bm25_retrieve(query,  self.top_k_retrieval)
        timings["dense_ms"] = round((time.time() - t0) * 1000)

        logger.debug(f"Dense: {len(dense_results)} | Sparse: {len(sparse_results)}")

        t1     = time.time()
        merged = self._rrf_merge(dense_results, sparse_results)
        timings["hybrid_ms"] = round((time.time() - t1) * 1000)

        t2         = time.time()
        candidates = merged[:self.top_k_retrieval]
        final      = self._rerank(query, candidates, final_k)
        timings["rerank_ms"] = round((time.time() - t2) * 1000)

        timings["total_ms"] = round((time.time() - t_total) * 1000)

        logger.info(
            f"Retrieved {len(final)} chunks | "
            f"dense={timings['dense_ms']}ms "
            f"rerank={timings['rerank_ms']}ms "
            f"total={timings['total_ms']}ms"
        )

        self.sport_filter = orig_filter
        return RetrievalResult(query=query, chunks=final, latency=timings)

    def explain(self, query: str) -> None:
        print(f"\n{'='*60}\nRETRIEVAL EXPLAIN: {query}\n{'='*60}")
        dense  = self._dense_retrieve(query, 5)
        sparse = self._bm25_retrieve(query,  5)
        print("\n── TOP 5 DENSE ──")
        for i, c in enumerate(dense, 1):
            print(f"  {i}. [{c.sport:10s}] score={c.dense_score:.4f}  {c.text[:80]}...")
        print("\n── TOP 5 BM25 ──")
        for i, c in enumerate(sparse, 1):
            print(f"  {i}. [{c.sport:10s}] score={c.bm25_score:.4f}  {c.text[:80]}...")
        merged = self._rrf_merge(dense, sparse)
        print("\n── TOP 5 AFTER RRF ──")
        for i, c in enumerate(merged[:5], 1):
            print(f"  {i}. [{c.sport:10s}] rrf={c.rrf_score:.6f}  {c.text[:80]}...")
        if self.use_reranker:
            reranked = self._rerank(query, merged[:10], 5)
            print("\n── TOP 5 AFTER RERANK ──")
            for i, c in enumerate(reranked, 1):
                print(f"  {i}. [{c.sport:10s}] rerank={c.rerank_score:.4f}  {c.text[:80]}...")
        print()


if __name__ == "__main__":
    import sys
    from rich.console import Console
    from rich.table   import Table
    from rich.panel   import Panel
    console = Console()
    query   = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Who won the 2019 IPL final?"
    console.print(Panel(f"[bold]Query:[/bold] {query}", title="Sports RAG Retriever"))
    retriever = SportsRetriever()
    result    = retriever.retrieve(query)
    console.print(f"\n[dim]{result.summary()}[/dim]\n")
    table = Table(title=f"Top {len(result.chunks)} chunks", show_lines=True)
    table.add_column("#",      width=3)
    table.add_column("Sport",  width=12)
    table.add_column("Rerank", width=8)
    table.add_column("Text",   width=80)
    for i, c in enumerate(result.chunks, 1):
        table.add_row(str(i), c.sport, f"{c.rerank_score:.3f}",
                      c.text[:120] + ("..." if len(c.text) > 120 else ""))
    console.print(table)
    console.print(Panel(result.to_context_string(), title="Context for LLM", border_style="dim"))
