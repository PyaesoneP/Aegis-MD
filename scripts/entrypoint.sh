#!/usr/bin/env bash
set -e

# ── Graceful shutdown: forward SIGTERM to Ollama ────────────────────
cleanup() {
    echo "[entrypoint] Shutting down Ollama..."
    kill "$OLLAMA_PID" 2>/dev/null || true
    wait "$OLLAMA_PID" 2>/dev/null || true
    echo "[entrypoint] Shutdown complete."
}
trap cleanup EXIT SIGTERM SIGINT

# ── Start Ollama server in the background ───────────────────────────
echo "[entrypoint] Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# ── Wait for Ollama to be reachable ─────────────────────────────────
echo "[entrypoint] Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[entrypoint] Ollama is ready."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "[entrypoint] ERROR: Ollama failed to start within 30 seconds."
        exit 1
    fi
    sleep 1
done

# ── Verify the model is available ───────────────────────────────────
if ! ollama list | grep -q "medgemma"; then
    echo "[entrypoint] ERROR: MedGemma model not found. It should be baked into the image."
    exit 1
fi
echo "[entrypoint] MedGemma model confirmed available."

# ── Pre-warm the prompt cache with the system prompt ────────────────
echo "[entrypoint] Pre-warming prompt cache..."
curl -s http://localhost:11434/api/generate -d '{
  "model": "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:UD-Q4_K_XL",
  "prompt": "You are Aegis-MD, a research triage assistant. Classify urgency only. Do not diagnose. Do not prescribe treatment.",
  "stream": false,
  "options": {"num_predict": 1, "temperature": 0}
}' > /dev/null 2>&1 || echo "[entrypoint] Prompt cache pre-warm skipped (non-critical)"
echo "[entrypoint] Prompt cache pre-warmed."

# ── Start the FastAPI server ────────────────────────────────────────
echo "[entrypoint] Starting Aegis-MD API on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
