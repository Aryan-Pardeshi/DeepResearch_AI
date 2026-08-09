FROM python:3.11-slim

# PYTHONUNBUFFERED matters here: buffered stdout stalls SSE streaming.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    RESEARCH_DB_PATH=/app/data/research_state.db \
    LLM_CACHE_PATH=/app/data/llm_cache.db

WORKDIR /app

# curl is used by the container healthcheck
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

# Checkpointer and LLM cache live here. Mount a volume over it, or both are lost
# on every container rebuild.
RUN mkdir -p /app/data

EXPOSE 8000

# Shell form so $PORT is expanded at runtime: hosts like Hugging Face Spaces and
# Render assign the port themselves.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
