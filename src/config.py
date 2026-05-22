"""
src/config.py
Single source of truth for all settings.
Every other module imports from here — never from os.getenv directly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).parent.parent
DATA_RAW        = ROOT_DIR / "data" / "raw"
DATA_PROCESSED  = ROOT_DIR / "data" / "processed"
DATA_CHUNKS     = ROOT_DIR / "data" / "chunks"
DATA_EMBEDDINGS = ROOT_DIR / "data" / "embeddings"
LOGS_DIR        = ROOT_DIR / "logs"

# create dirs if they don't exist
for d in [DATA_RAW, DATA_PROCESSED, DATA_CHUNKS, DATA_EMBEDDINGS, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM ──────────────────────────────────────────────────────────────────────
# Provider: "gemini" or "ollama"
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "ollama")  # switched to ollama

# Gemini settings (if LLM_PROVIDER == "gemini")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Ollama settings (if LLM_PROVIDER == "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "gemma4")

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM     = 384   # all-MiniLM-L6-v2 output dimension
FAISS_INDEX_PATH  = ROOT_DIR / os.getenv("FAISS_INDEX_PATH", "data/embeddings/faiss_index")
CHUNK_SIZE        = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP     = int(os.getenv("CHUNK_OVERLAP", "50"))

# ── Retrieval ─────────────────────────────────────────────────────────────────
RETRIEVER_TOP_K   = int(os.getenv("RETRIEVER_TOP_K", "20"))   # initial dense fetch
RERANKER_TOP_K    = int(os.getenv("RERANKER_TOP_K", "5"))     # after reranking
RERANKER_MODEL    = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ── SofaScore API ─────────────────────────────────────────────────────────────
RAPIDAPI_KEY      = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST     = os.getenv("RAPIDAPI_HOST", "sportapi7.p.rapidapi.com")
SOFASCORE_BASE    = "https://sportapi7.p.rapidapi.com"
API_RATE_LIMIT_S  = 1.2   # seconds between requests (free tier safe)

# ── App ───────────────────────────────────────────────────────────────────────
APP_ENV   = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_PORT  = int(os.getenv("API_PORT", "8000"))
IS_DEV    = APP_ENV == "development"
