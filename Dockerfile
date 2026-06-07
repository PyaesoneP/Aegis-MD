# ── Base: CUDA runtime for L4 GPU support on Cloud Run ──────────────
# Ubuntu 24.04 ships Python 3.12 natively — no PPA needed.
FROM nvidia/cuda:12.6.3-base-ubuntu24.04

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    OLLAMA_MODELS=/app/ollama_models

# ── Install Python 3.12 + system deps ───────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3-pip \
    curl \
    zstd \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && rm -rf /var/lib/apt/lists/*

# ── Install Ollama ──────────────────────────────────────────────────
RUN curl -fsSL https://ollama.com/install.sh | sh

# ── Copy pre-downloaded Ollama model from local filesystem ──────────
# Before building, copy your local Ollama model into the build context:
#   mkdir -p ollama_models && cp -r ~/.ollama/models/* ollama_models/
# The ollama_models/ directory is gitignored (too large for git).
COPY ollama_models /app/ollama_models
# Make model readable by any user (host files carry the host UID, not aegis).
RUN chmod -R a+rX /app/ollama_models

WORKDIR /app

# ── Python dependencies ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# ── Application code ────────────────────────────────────────────────
COPY app ./app
COPY main.py .
COPY data/chroma/chroma_db ./data/chroma/chroma_db

# ── Pre-cached ChromaDB embedding model (avoids runtime download) ───
# Copied to /tmp first; moved to /home/aegis after user creation below.
COPY .cache/chroma /tmp/chroma_cache

# ── Startup script ──────────────────────────────────────────────────
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p logs && \
    adduser --disabled-password --gecos "" aegis && \
    mkdir -p /home/aegis/.cache && \
    mv /tmp/chroma_cache /home/aegis/.cache/chroma && \
    chown -R aegis:aegis /app/logs /entrypoint.sh && \
    chown -R aegis:aegis /app/app /app/main.py /app/data && \
    chown -R aegis:aegis /home/aegis/.cache

USER aegis

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
