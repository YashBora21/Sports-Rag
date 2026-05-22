"""
src/api/schemas.py
All Pydantic request and response models for the Sports RAG API.
Keeping schemas separate from main.py makes them importable by tests.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── /query ────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question:     str            = Field(..., min_length=3, max_length=500,
                                         example="Who won the 2019 IPL final?")
    sport_filter: Optional[str]  = Field(None,
                                         example="cricket",
                                         description="football | basketball | tennis | cricket | None")
    top_k:        Optional[int]  = Field(None, ge=1, le=20,
                                         description="Number of chunks to return (default 5)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "question": "Who was the top scorer in Premier League 2021?",
                "sport_filter": "football",
                "top_k": 5,
            }
        }
    }


class SourceChunk(BaseModel):
    text:          str
    sport:         str
    source:        str
    metadata:      dict
    rerank_score:  float


class LatencyBreakdown(BaseModel):
    dense_ms:    int
    rerank_ms:   int
    llm_ms:      int
    total_ms:    int


class QueryResponse(BaseModel):
    question:    str
    answer:      str
    sources:     list[SourceChunk]
    latency_ms:  dict
    sport_filter: Optional[str] = None


# ── /health ───────────────────────────────────────────────────────────────────

class ComponentStatus(BaseModel):
    status:   str          # "ok" | "error" | "loading"
    detail:   Optional[str] = None


class HealthResponse(BaseModel):
    status:        str               # "ok" | "degraded" | "error"
    version:       str
    index_vectors: int
    components:    dict[str, ComponentStatus]
    uptime_s:      float


# ── /ingest ───────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    data_dir:   str  = Field(..., example="data/raw",
                             description="Path to folder containing raw CSV files")
    rebuild_index: bool = Field(True,
                                description="Re-embed and rebuild FAISS index after processing")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data_dir":      "data/raw",
                "rebuild_index": True,
            }
        }
    }


class IngestResponse(BaseModel):
    status:         str
    docs_processed: dict[str, int]   # sport → count
    total_chunks:   int
    index_rebuilt:  bool
    duration_s:     float
