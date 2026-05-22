"""
src/api/main.py
Sports RAG — FastAPI backend

Fixes applied:
  1. ThreadPoolExecutor with max_workers=1 — prevents concurrent FAISS/BM25
     access which caused 500 errors on rapid sequential queries
  2. Per-request semaphore limits to 3 concurrent queries max
  3. json import added for startup error handling
  4. Support for both Gemini API and Ollama LLM providers
"""
import json
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.config import API_PORT, APP_ENV, IS_DEV
from src.api.schemas import (
    QueryRequest, QueryResponse, SourceChunk,
    HealthResponse, ComponentStatus,
    IngestRequest, IngestResponse,
)


# ── App state ─────────────────────────────────────────────────────────────────

class AppState:
    rag_chain    = None
    start_time   = None
    index_ready  = False
    ingest_lock  = None      # set in lifespan (needs running loop)
    # Single-worker executor — FAISS + BM25 are not thread-safe
    executor     = ThreadPoolExecutor(max_workers=1)
    # Semaphore: max 3 queries queued at once (prevents request pile-up)
    query_sem    = None      # set in lifespan

state = AppState()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.start_time  = time.time()
    state.ingest_lock = asyncio.Lock()
    state.query_sem   = asyncio.Semaphore(3)

    logger.info("Starting Sports RAG API...")
    try:
        from src.rag.rag_chain import SportsRAGChain
        logger.info("Loading RAG chain (FAISS + BM25 + reranker + Gemini)...")
        state.rag_chain   = SportsRAGChain()
        state.index_ready = True
        logger.success("API ready.")
    except FileNotFoundError as e:
        logger.error(f"Index not found: {e}")
        logger.error("Run: python scripts/run_pipeline.py --data-dir data/raw")
    except json.JSONDecodeError as e:
        logger.error(f"metadata.jsonl corrupt: {e}")
        logger.error("Fix: python scripts/rebuild_metadata.py")
    except Exception as e:
        import traceback
        logger.error(f"Startup error: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())

    yield

    state.executor.shutdown(wait=False)
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Sports RAG API",
    description = "Production RAG system for sports Q&A",
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs"  if IS_DEV else None,
    redoc_url   = "/redoc" if IS_DEV else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0       = time.time()
    response = await call_next(request)
    ms       = round((time.time() - t0) * 1000)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)")
    return response


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    uptime     = round(time.time() - (state.start_time or time.time()), 1)
    components = {}

    if state.rag_chain is not None:
        components["rag_chain"] = ComponentStatus(status="ok")
    else:
        components["rag_chain"] = ComponentStatus(
            status="error",
            detail="RAG chain not loaded. Run the pipeline first."
        )

    index_vectors = 0
    try:
        if state.rag_chain and state.rag_chain.retriever.index:
            index_vectors = state.rag_chain.retriever.index.ntotal
            components["faiss_index"] = ComponentStatus(
                status="ok", detail=f"{index_vectors:,} vectors"
            )
    except Exception as e:
        components["faiss_index"] = ComponentStatus(status="error", detail=str(e))

    try:
        if state.rag_chain and state.rag_chain.llm:
            components["gemini_llm"] = ComponentStatus(status="ok")
    except Exception as e:
        components["gemini_llm"] = ComponentStatus(status="error", detail=str(e))

    all_ok  = all(c.status == "ok" for c in components.values())
    overall = "ok" if all_ok else ("degraded" if state.rag_chain else "error")

    return HealthResponse(
        status=overall, version="1.0.0",
        index_vectors=index_vectors,
        components=components, uptime_s=uptime,
    )


# ── POST /query ───────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query(req: QueryRequest):
    """
    Full RAG pipeline: hybrid retrieval → rerank → Gemini 2.5 Flash.
    Queries are serialised through a single-worker executor to prevent
    concurrent FAISS/BM25 access (which caused 500 errors).
    """
    if not state.index_ready or state.rag_chain is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not ready. Check /health.",
        )
    if state.ingest_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ingestion in progress. Retry shortly.",
        )

    # Queue the query — semaphore prevents pile-up beyond 3
    async with state.query_sem:
        try:
            loop   = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                state.executor,          # ← single-worker, serialises FAISS calls
                lambda: state.rag_chain.query(
                    question     = req.question,
                    sport_filter = req.sport_filter,
                    top_k        = req.top_k,
                )
            )
        except Exception as e:
            logger.error(f"Query failed: {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query processing failed: {str(e)}",
            )

    sources = [
        SourceChunk(
            text         = s["text"],
            sport        = s["sport"],
            source       = s["source"],
            metadata     = s["metadata"],
            rerank_score = s.get("rerank_score", 0.0),
        )
        for s in result["sources"]
    ]

    return QueryResponse(
        question=result["question"], answer=result["answer"],
        sources=sources, latency_ms=result["latency_ms"],
        sport_filter=req.sport_filter,
    )


# ── POST /ingest ──────────────────────────────────────────────────────────────

@app.post("/ingest", response_model=IngestResponse, tags=["Admin"])
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    if state.ingest_lock.locked():
        raise HTTPException(status_code=409, detail="Ingestion already in progress.")

    data_dir = Path(req.data_dir)
    if not data_dir.exists():
        raise HTTPException(status_code=400, detail=f"data_dir not found: {data_dir}")

    t0 = time.time()
    async with state.ingest_lock:
        state.index_ready = False
        try:
            loop = asyncio.get_event_loop()
            from src.ingestion.data_processor import run_all as process_all
            stats = await loop.run_in_executor(
                state.executor, lambda: process_all(data_dir)
            )
            from src.ingestion.chunker import run_all as chunk_all
            total_chunks = await loop.run_in_executor(state.executor, chunk_all)

            index_rebuilt = False
            if req.rebuild_index:
                from src.embeddings.embedder import run as embed_all
                await loop.run_in_executor(state.executor, embed_all)
                from src.rag.rag_chain import SportsRAGChain
                state.rag_chain = SportsRAGChain()
                index_rebuilt   = True
        except Exception as e:
            logger.error(f"Ingest failed: {e}")
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
        finally:
            state.index_ready = True

    return IngestResponse(
        status="ok", docs_processed=stats,
        total_chunks=total_chunks, index_rebuilt=index_rebuilt,
        duration_s=round(time.time() - t0, 2),
    )


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Sports RAG API", "version": "1.0.0",
            "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=API_PORT,
                reload=IS_DEV, workers=1)
