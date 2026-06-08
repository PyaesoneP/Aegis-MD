# Aegis-MD

> **A containerized, research-grade multimodal triage agent with built-in adversarial safety guardrails.**  
> Built by a former clinician and cybersecurity intern to explore the intersection of medical AI, LLM security, and production MLOps.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Research%20Use-lightgrey)](./LICENSE)

---

##  Live Demo

**[Try the live demo →](https://pyaesonep.github.io/Aegis-MD/)**

Upload a symptom description (and optionally a skin-lesion image) to receive an informational triage urgency suggestion with explainable sources and confidence indicators. The backend runs on Cloud Run (CPU-only by default); cold-start requests take 2-3 minutes, warm requests ~30s. The frontend client has a 10-minute timeout to accommodate this.

![Aegis-MD Demo](./assets/Aegis-MD.gif)

*The demo above was recorded locally with an RTX 5070 Ti Mobile (12 GB VRAM) — triage completes in ~5s. The live Cloud Run deployment is CPU-only and takes 2-3 minutes on cold start.*

> **Why is it slow?** This is a student portfolio project running on a **$0 budget**. The LLM (MedGemma 4B) runs on Cloud Run's CPU-only tier because GPU instances require a paid quota increase. Locally on an RTX 5070 Ti Mobile (12 GB VRAM) the pipeline completes in ~5s (text-only) or ~8-10s (with vision running in parallel). With a cloud-hosted inference API it would be sub-second. The latency is a **cost constraint, not an architectural limitation** — the RAG pipeline, security gateway, and multimodal fusion are designed for production throughput.

To debug connectivity issues, open the browser DevTools console and run:
```js
import('/assets/index.js').then(m => m.diagnose().then(console.log))
```

---

##  Overview

Aegis-MD is a **minimum viable prototype (MVP)** of a multimodal clinical triage agent. It combines:

- **Retrieval-Augmented Generation (RAG)** over open-source medical guidelines (WHO, Singapore MOH, Australian ETEK). The current corpus is limited to 5 documents — a production system would index orders of magnitude more sources across specialties.
- **Lightweight LLM inference** via a local Ollama-hosted research model (MedGemma-1.5 by default) for RAG-enabled, safety-focused triage. The model reference is configurable via `Aegis_LLM_MODEL` and can be replaced with another Ollama-compatible model or an on-disk GGUF runtime.
- **Computer Vision** risk stratification using the same Ollama-hosted multimodal model (MedGemma), running in parallel with text triage for lower latency; urgency levels are merged programmatically and findings are appended verbatim — the text LLM never sees vision output, eliminating hallucination risk
- **Security Gateway** with prompt-injection detection, rate limiting, and anomaly logging
- **Production Observability** via Prometheus metrics and a lightweight monitoring dashboard

**Privacy-first by design.** All inference runs locally — the LLM and vision model execute on-device via Ollama with no data ever leaving the machine. No patient symptoms, images, or triage results are sent to external APIs, stored beyond the request lifecycle, or used for training. This is a deliberate architectural choice: medical triage data is sensitive by nature, and local inference eliminates the trust, compliance, and latency burdens of cloud-hosted models.

This project is explicitly **not a diagnostic tool**. It is a research prototype designed to demonstrate:
- Safe medical AI scoping (triage-only, no diagnosis)
- LLM security hardening (prompt injection defense)
- End-to-end MLOps (Docker, CI/CD, Cloud Run, monitoring)
- Multimodal system design (text + vision fusion)

---

##  Architecture

![Aegis-MD Architecture](./assets/architecture.png)

---

##  Key Features

###  Text Triage (RAG + SLM)
- Accepts natural-language symptom descriptions (max 2,000 characters)
- Retrieves top-3 relevant chunks from **5 open-source medical guideline PDFs** (WHO, Singapore MOH, Australian ETEK). The guideline corpus is intentionally small for this MVP — a production system would index hundreds of peer-reviewed sources across multiple languages and specialties.
- Classifies urgency into 4 tiers: `Emergency`, `Urgent`, `Routine`, `Self-Care`
- Returns structured rationale, source citations, and a mandatory medical disclaimer
- **Latency:** ~2-3 min cold start on Cloud Run CPU-only (4 vCPU); ~5s on RTX 5070 Ti Mobile (12 GB VRAM). Vision+text requests run both models in parallel, keeping total latency close to the slower of the two calls. The CPU latency reflects a **student budget constraint** — the architecture is designed for GPU-accelerated inference and would be significantly faster on provisioned hardware.

###  Vision Risk Stratification
- Optional image upload (JPEG/PNG, max 5 MB)
- **MedGemma multimodal model** (same Ollama instance as text triage) for image analysis
- Classifies risk into three tiers: `High-Risk`, `Low-Risk`, `insufficient confidence`
- Confidence scored as a float (0.0–1.0) with structured rationale
- Vision and text triage run **in parallel** via `asyncio.gather`; urgency levels are merged programmatically and findings are structured into labelled sections with no LLM rewriting — zero hallucination risk from cross-model contamination
- Configurable via `Aegis_VISION_ENABLED` (default: `true`); graceful fallback when disabled (text triage still returns independently)
- **Latency:** ~8-10s on RTX 5070 Ti Mobile (parallel vision + text); ~50-60s on Cloud Run CPU-only

###  Security Gateway
- **Defense-in-depth** pipeline intercepts all inputs **before** they reach the LLM
- **Scored heuristics** (PASS / WARN / BLOCK): borderline cases are logged for observability without blocking legitimate use; severe attacks return 400
- **16+ injection patterns** across 7 attack families: instruction override, DAN/jailbreak, prompt extraction, encoding evasion, delimiter attacks, role-play override, recursive/nesting attacks
- **Unicode defense**: NFKC normalization + homoglyph remapping (Cyrillic, Greek, Fullwidth → ASCII) neutralizes character-level evasion
- **Control-character stripping**: null bytes, zero-width chars, and Unicode control blocks removed before pattern matching
- **Per-field inspection**: both `symptoms` and `patient_context` are checked recursively for injection patterns; JSON depth and size limits enforced
- **Image validation**: magic-byte verification (JPEG FF D8 FF / PNG 89 50 4E 47) in addition to Content-Type and size checks
- **Burst-aware rate limiting**: sliding window with configurable burst allowance (2× sustained for 5 s); per-endpoint limits (triage, health, metrics, dashboard)
- **Circuit breaker**: automatic fail-open when downstream LLM/ChromaDB error rate exceeds threshold; auto-recovery after cooldown
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-Permitted-Cross-Domain-Policies`, configurable HSTS
- **Output safety**: response fields truncated to configurable max lengths to prevent unbounded LLM output
- Security events logged with rotation (JSONL) + Prometheus counters `aegis_security_blocked_total` and `aegis_security_warned_total`

###  Monitoring Dashboard
- `/metrics` endpoint exposes Prometheus histograms and counters for latency, throughput, block/warn rates, circuit breaker state, and urgency distribution
- `/dashboard` serves a lightweight HTML view of:
  - Request volume (24h)
  - Average latency (text vs. vision)
  - Security block + warn counts
  - Urgency distribution
- **Structured audit logging**: every triage request is logged with request ID, client hash, latency, urgency, security verdict, and image presence (rotating JSONL, 10 MB/file, 3 backups)

---

##  Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **LLM** | MedGemma-1.5 (4B, Q4_K_XL quantized, 3.4 GB) via Ollama (configurable via `Aegis_LLM_MODEL`). Note: The default in `app/config.py` is `hf.co/unsloth/medgemma-1.5-4b-it-GGUF:UD-Q4_K_XL`. |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector DB** | ChromaDB (persistent on disk, initialized via `data/chroma/chunk.py`) |
| **Vision** | Ollama multimodal (same model as LLM), base64 image encoding |
| **Security** | Scored heuristics (pass/warn/block), 16+ injection patterns, Unicode defense, burst-aware rate limiting, circuit breaker, security headers |
| **Monitoring** | Prometheus client, custom HTML dashboard |
| **Deployment** | Docker, Google Cloud Run |
| **CI/CD** | GitHub Actions (pytest only for backend; frontend deploys to GitHub Pages) |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite, Vitest + Testing Library (GitHub Pages) |

---

##  Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker (optional, for containerized deployment)
- `git`

### 1. Clone the repository
```bash
git clone https://github.com/PyaesoneP/Aegis-MD.git
cd Aegis-MD
```

### 2. Set up the Python environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Models & retrieval
This backend now uses a local Ollama-hosted model for RAG-enabled triage. The model reference is configurable via the environment variable `Aegis_LLM_MODEL` (default set in `app/config.py`). Retrieval is performed using ChromaDB; configure the storage path and collection via `Aegis_CHROMA_PATH` and `Aegis_CHROMA_COLLECTION`.

If you plan to run RAG and vision locally with Ollama:

```bash
# Install and run Ollama (see https://ollama.com/docs)
# Pull the multimodal model (model ref must match Aegis_LLM_MODEL)
ollama pull hf.co/unsloth/medgemma-1.5-4b-it-GGUF:UD-Q4_K_XL

# Start Ollama daemon (platform-specific)
ollama serve

# Verify model is available
ollama list
```

To disable vision while keeping text triage active:
```bash
export Aegis_VISION_ENABLED=false
```

If you prefer to run a local GGUF model directly with another runtime, place model files under `./models/` and update `Aegis_LLM_MODEL` accordingly.

Guideline PDFs remain under `./data/guidelines/` and are chunked/embedded by running the `data/chroma/chunk.py` script. This script must be executed once to prepare the ChromaDB collection.

### 4. Run the FastAPI server locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.

Backend environment variables:

| Variable | Default | Description |
|---|---|---|
| `Aegis_ALLOWED_ORIGINS` | `http://localhost:5173,https://pyaesonep.github.io` | Comma-separated CORS allowlist |
| `Aegis_LOG_DIR` | `logs` | Directory for security JSONL events |
| `Aegis_RATE_LIMIT_REQUESTS` | `10` | Requests allowed per client window (triage endpoint) |
| `Aegis_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length |
| `Aegis_RATE_LIMIT_BURST_MULTIPLIER` | `2.0` | Burst allowance multiplier (× sustained) |
| `Aegis_RATE_LIMIT_BURST_SECONDS` | `5.0` | Burst window duration |
| `Aegis_RATE_LIMIT_HEALTH_REQUESTS` | `60` | Rate limit for `/health` endpoint |
| `Aegis_RATE_LIMIT_METRICS_REQUESTS` | `60` | Rate limit for `/metrics` endpoint |
| `Aegis_RATE_LIMIT_DASHBOARD_REQUESTS` | `30` | Rate limit for `/dashboard` endpoint |
| `Aegis_CORS_ALLOW_HEADERS` | `content-type,accept,authorization,x-requested-with` | Allowed CORS request headers |
| `Aegis_ENABLE_HSTS` | `false` | Enable Strict-Transport-Security header |
| `Aegis_MAX_BODY_BYTES` | `10485760` | Maximum request body size (10 MB) |
| `Aegis_MAX_JSON_DEPTH` | `5` | Max nesting depth for patient_context JSON |
| `Aegis_MAX_JSON_BYTES` | `10240` | Max raw size for patient_context JSON (10 KB) |
| `Aegis_MAX_IMAGE_MEGAPIXELS` | `100` | Max image resolution (decompression-bomb guard) |
| `Aegis_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Consecutive downstream failures to open circuit |
| `Aegis_CIRCUIT_BREAKER_RECOVERY_SECONDS` | `30.0` | Cooldown before half-open probe |
| `Aegis_LLM_MODEL` | `hf.co/unsloth/medgemma-1.5-4b-it-GGUF:UD-Q4_K_XL` | Ollama model reference (Q4 quantized, 3.4 GB) |
| `Aegis_CHROMA_PATH` | `data/chroma/chroma_db` | Filesystem path for ChromaDB persistence |
| `Aegis_CHROMA_COLLECTION` | `guidelines` | Chroma collection name for guideline chunks |
| `Aegis_RETRIEVAL_TOP_K` | `3` | Number of guideline chunks to retrieve per query |
| `Aegis_VISION_ENABLED` | `true` | Enable/disable multimodal vision inference |
| `Aegis_MAX_RATIONALE_CHARS` | `4000` | Max characters for triage rationale output |
| `Aegis_MAX_DISCLAIMER_CHARS` | `500` | Max characters for medical disclaimer output |
| `Aegis_LOG_MAX_BYTES` | `10485760` | Max bytes per security log file (10 MB) |
| `Aegis_LOG_BACKUP_COUNT` | `3` | Number of rotated log backups to keep |

### 5. Test the API
```bash
curl -X POST "http://localhost:8000/api/v1/triage" \
  -H "Content-Type: multipart/form-data" \
  -F "symptoms=I have chest pain radiating to my left arm and I feel nauseous." \
  -F "patient_context={\"age\": 45, \"sex\": \"male\"}"
```

### 6. Run tests
```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

### 7. Run the React frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend dev server will be available at `http://localhost:5173/Aegis-MD/`.
Local API calls are configured through `frontend/.env.development`. Note: This file is not committed to the repository and needs to be created manually based on `frontend/.env.development.example` if it exists, or by creating a new file with the specified content.

```bash
VITE_API_BASE_URL=http://localhost:8000
```

To verify the static GitHub Pages build:

```bash
npm run build
npm run preview
```

The production build output is written to `frontend/dist`.

### 8. Configure GitHub Pages
The frontend workflow in `.github/workflows/frontend-pages.yml` builds the React app and deploys `frontend/dist` to GitHub Pages.

1. In GitHub, enable Pages with **Source: GitHub Actions**.
2. Add a repository variable named `VITE_API_BASE_URL` with your Cloud Run URL, for example `https://your-cloud-run-url.a.run.app`.
3. Push to `main` or run **Deploy Frontend to GitHub Pages** manually from the Actions tab.

The deployed frontend is configured for `https://pyaesonep.github.io/Aegis-MD/` and connects to the Cloud Run backend at the URL set in the `VITE_API_BASE_URL` repository variable. For local production builds, copy `frontend/.env.production.example` to `frontend/.env.production` and set your backend URL there.

---

##  Docker Deployment

### Prerequisites for building
Copy the Ollama model into the build context before running `docker build`:
```bash
# Copy the Q4 model from Ollama's system directory
sudo cp -r /usr/share/ollama/.ollama/models/* ollama_models/
# Ensure blobs/ and manifests/ are present
ls ollama_models/
```

### Build and run locally
```bash
docker build -t asia-southeast1-docker.pkg.dev/aegis-md/aegismd/backend:v4 .
docker run -p 8000:8000 asia-southeast1-docker.pkg.dev/aegis-md/aegismd/backend:v4
```

Cloud Run uses the container `PORT` environment variable automatically; the Docker image starts `uvicorn app.main:app` on that port via `scripts/entrypoint.sh`.

> **Note:** The image is ~7 GB (includes Ollama + CUDA runtime + Q4 model). CPU-only inference yields ~25-30s warm latency (text-only) or ~50-60s (with vision). For lower latency, attach a GPU (`--gpu 1 --gpu-type nvidia-l4`).

### Deploy to Google Cloud Run (CPU-only)
```bash
# Authenticate
gcloud auth login
gcloud config set project aegis-md

# Build, tag, and push
docker build -t asia-southeast1-docker.pkg.dev/aegis-md/aegismd/backend:v4 .
docker push asia-southeast1-docker.pkg.dev/aegis-md/aegismd/backend:v4

# Deploy
# Omit --gpu and --gpu-type for CPU-only; add them for L4 GPU
# (Cloud Run GPU requires allowlist — contact GCP support)
gcloud run deploy backend-489834841444 \
  --image asia-southeast1-docker.pkg.dev/aegis-md/aegismd/backend:v4 \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --port 8000 \
  --set-env-vars "Aegis_ALLOWED_ORIGINS=https://pyaesonep.github.io,Aegis_RETRIEVAL_TOP_K=1"
```

---

##  API Reference

### `POST /api/v1/triage`
Submit a triage request.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `symptoms` | string | Yes | Symptom description (max 2,000 chars) |
| `patient_context` | JSON string | No | `{"age": int, "sex": "male\|female"}` |
| `image` | file | No | JPEG/PNG image, max 5 MB |

**Success Response (200):**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "triage_result": {
    "urgency": "Emergency",
    "rationale": "Chest pain with radiation to the left arm in a patient over 40 is a high-risk presentation for acute coronary syndrome.",
    "confidence": "high",
    "sources": ["Australian ETEK Ch. 4", "MOH Hypertension CPG"],
    "disclaimer": "This is a research prototype, not a substitute for professional medical advice."
  },
  "vision_result": {
    "risk": "High-Risk",
    "confidence": 0.95,
    "rationale": "The image shows a significant open wound on the scalp with visible bleeding and surrounding inflammation. This suggests potential trauma or injury requiring urgent medical attention."
  },
  "latency_ms": 30000,
  "security_passed": true
}
```

**Blocked Response (400 — prompt injection / invalid input):**
```json
{
  "error": "Security policy violation: potentially malicious input detected.",
  "request_id": "...",
  "security_passed": false
}
```

**Rate-Limited Response (429):**
```json
{
  "error": "Rate limit exceeded. Please wait before submitting another request.",
  "request_id": "...",
  "security_passed": false
}
```

**Body Too Large (413):**
```json
{
  "error": "Request body exceeds 10 MB limit",
  "request_id": "...",
  "security_passed": false
}
```

**Service Unavailable — Circuit Open (503):**
```json
{
  "detail": "Service temporarily unavailable — downstream dependencies are failing."
}
```

### `GET /health`
Health check with per-component status (api, security, text_model, retrieval, vision_model, observability).  Each component reports `ok`, `degraded`, or `placeholder`.

### `GET /metrics`
Prometheus metrics endpoint.

### `GET /dashboard`
Lightweight HTML monitoring dashboard.

---

##  Evaluation

**Note:** The evaluation suite described in previous versions of this README has not yet been implemented or performed. The project currently includes unit tests for the backend and frontend, but comprehensive evaluation metrics for triage accuracy, vision confidence, and security gateway performance are pending.

---

##  Safety, Ethics & Limitations

**This is a research prototype. It is not a medical device and must not be used for real patient care.**

- **No diagnosis:** The system classifies triage urgency only. It never names diseases, prescribes medications, or recommends dosages.
- **No PII storage:** User inputs and images are processed in-memory only. No data is persisted beyond the request lifecycle.
- **Mandatory disclaimer:** Every response includes a clear statement that this is not a substitute for professional medical advice.
- **Guardrails:** The LLM is constrained to 4 urgency tiers via structured prompting. The security gateway blocks known jailbreak attempts.
- **Known limitations:**
  - The LLM can hallucinate. The RAG layer grounds it in guideline text, and the system prompt includes explicit anti-hallucination rules (only cite guidelines directly relevant to stated symptoms; never introduce unstated conditions). Vision findings are appended verbatim — the text LLM never sees them, eliminating cross-model hallucination.
  - The vision model uses the same Ollama instance as the text triage model. Its output is constrained to specific risk labels (`High-Risk`, `Low-Risk`, `insufficient confidence`) and a 0-1 float confidence score. While it processes general medical images, its performance may vary depending on the image type and quality.
  - The security filter uses scored regex heuristics with Unicode defense — effective against common attacks but novel ML-based jailbreaks may still bypass it.
  - English language only in the MVP.

If you discover a safety issue or bypass, please open a GitHub issue or email me directly.

---

##  Guideline Sources

Triage logic is grounded in the following publicly available clinical guidelines:

1. **Australian Emergency Triage Education Kit (ETEK), 2nd Edition** — Australian Commission on Safety and Quality in Health Care
2. **WHO Pocket Book of Hospital Care for Children, 2nd Edition** — World Health Organization
3. **MOH Clinical Practice Guidelines: Hypertension (2017)** — Ministry of Health, Singapore
4. **MOH Clinical Practice Guidelines: Diabetes Mellitus (2014)** — Ministry of Health, Singapore
5. **NHLBI Guidelines for the Diagnosis and Management of Asthma (EPR-3)** — U.S. National Institutes of Health

These documents are used under their respective public-domain / non-commercial educational licenses. Full citations are included in the `/data/guidelines/` directory.

---

##  Roadmap

- [x] MVP: Text triage with RAG + SLM
- [x] MVP: Vision risk stratification (skin lesion)
- [x] MVP: Prompt-injection security gateway
- [x] MVP: Prometheus monitoring + dashboard
- [ ] Post-MVP: Adversarial image detection (FGSM demo + rejection)
- [x] Post-MVP: Scored heuristics security gateway (16+ patterns, Unicode defense, burst rate limiting, circuit breaker, security headers)
- [ ] Post-MVP: ML-based intent classification guard (further upgrade from scored regex heuristics)
- [ ] Post-MVP: Edge deployment (ONNX Runtime + Raspberry Pi)
- [ ] Post-MVP: Multilingual support (Burmese / Chinese)
- [ ] Post-MVP: Synthetic patient vignette expansion (500 cases)

---

##  Contributing

This is a personal portfolio project. I am not accepting external code contributions at this time, but I welcome:
- Bug reports and safety disclosures via GitHub Issues
- Feedback on the architecture or evaluation methodology
- Suggestions for additional open-source guideline PDFs

---

##  License

This project is released for **non-commercial research and educational use only**.

- Code: MIT License (see [LICENSE](./LICENSE))
- Model weights (Gemma): Subject to [Gemma Terms of Use](https://ai.google.dev/gemma/terms)
- Guideline PDFs: Copyright respective authors (WHO, MOH Singapore, etc.), used under fair use for research
- HAM10000 dataset: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

**Do not deploy this in a clinical setting.**

---

##  Author

**Pyae Sone**  
BEng Computer Science & Design @ SUTD | Former MBBS | Cybersecurity & Red Teaming Intern @ LTA Singapore  

-  [Portfolio](https://github.com/pyaesonep)
-  [LinkedIn](https://linkedin.com/in/pyaesonep)
-  pyaesone.perfect2014@gmail.com

---

> *"I spent five years in medical school and then did red teaming at LTA. I built Aegis-MD because I believe the biggest bottleneck in medical AI is not accuracy, it is trust. This prototype is my answer to that question."*
