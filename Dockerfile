# ── Sports RAG Dockerfile ─────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Yash Bora"
LABEL description="Sports RAG"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies
COPY requirements.txt .

# CPU torch
RUN pip install --no-cache-dir \
    torch==2.4.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

# App
COPY src ./src
COPY scripts ./scripts

# Runtime dirs
RUN mkdir -p \
    data/raw \
    data/processed \
    data/chunks \
    data/embeddings \
    data/eval \
    logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENV=production
ENV LOG_LEVEL=INFO

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]