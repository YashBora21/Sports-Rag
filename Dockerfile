# ── Sports RAG Dockerfile ─────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Yash Bora"
LABEL description="Sports RAG"

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY start.sh . 

RUN chmod +x start.sh
# ── App code ──
COPY src ./src
COPY scripts ./scripts
COPY data ./data
# ── Torch first (separate cached layer — only re-downloads if version changes) ──
RUN pip install --no-cache-dir \
    torch==2.6.0 \
    --index-url https://download.pytorch.org/whl/cpu

# ── Rest of dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App code ──
COPY src ./src
COPY scripts ./scripts

# ── Runtime dirs ──
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

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["./start.sh"]