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

COPY requirements.txt .
RUN pip install --no-cache-dir \
    torch==2.6.0 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts
COPY data ./data

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENV=production
ENV LOG_LEVEL=INFO

EXPOSE 7860

CMD ["./start.sh"]