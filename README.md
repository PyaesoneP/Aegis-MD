# Aegis-MD

> **An ED Triage Console — containerized, research-grade, with built-in adversarial safety guardrails.**<br>
> Built by a former clinician and cybersecurity intern to explore the intersection of medical AI, LLM security, and production MLOps.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](./)
[![Tests](https://img.shields.io/badge/tests-332%20backend%20%7C%2056%20frontend-blue)](./)
[![License](https://img.shields.io/badge/License-Research%20Use-lightgrey)](./LICENSE)

---

##  Live Demo

**[Try the live demo →](https://pyaesonep.github.io/Aegis-MD/)**

Upload a symptom description (and optionally a skin-lesion image) to receive an informational triage urgency suggestion with explainable sources and confidence indicators. The backend runs on Cloud Run (CPU-only by default); cold-start requests take 2-3 minutes, warm requests ~30s. The frontend client has a 10-minute timeout to accommodate this.

![Aegis-MD Demo](./assets/Aegis-MD.gif)

*The demo above was recorded locally with an RTX 5070 Ti Mobile (12 GB VRAM) — triage completes in ~2–3s. The live Cloud Run deployment is CPU-only and takes 2-3 minutes on cold start.*

> **Why is it slow?** This is a student portfolio project running on a **$0 budget**. The LLM (MedGemma 4B) runs on Cloud Run's CPU-only tier because GPU instances require a paid quota increase. Locally on an RTX 5070 Ti Mobile (12 GB VRAM) the pipeline completes in ~2–3s (text-only) or ~8-10s (with vision running in parallel). With a cloud-hosted inference API it would be sub-second. The latency is a **cost constraint, not an architectural limitation** — the RAG pipeline, security gateway, and multimodal fusion are designed for production throughput.

To debug connectivity issues, open the browser DevTools console and run:
```js
import('/assets/index.js').then(m => m.diagnose().then(console.log))
```

---

##  Overview

Aegis-MD is an **ED Triage Console** — a multimodal clinical triage agent designed for the Emergency Department. It combines:

- **Structured ED triage intake** capturing what a triage nurse collects in 2–5 minutes: chief complaint (150 char), vital signs (HR, RR, SpO₂, Temp, BP), pain score (0–10), onset, arrival mode, consciousness (AVPU), mechanism, and risk modifiers (comorbidities, pregnancy, allergies). Optional image upload for wounds/rashes.
- **ATS 1–5 classification** using the Australasian Triage Scale, with time-to-treatment targets (ATS-1 = immediate, ATS-2 = 10 min, ATS-3 = 30 min, ATS-4 = 60 min, ATS-5 = 120 min) and colour-coded triage cards.
- **Retrieval-Augmented Generation (RAG)** over open-source medical guidelines (WHO, Singapore MOH, Australian ETEK). The current corpus is limited to 5 documents — a production system would index orders of magnitude more sources across specialties.
- **Lightweight LLM inference** via a local Ollama-hosted research model (MedGemma-1.5 4B by default) for RAG-enabled, safety-focused triage. The model reference is configurable via `Aegis_LLM_MODEL`.
- **Computer Vision** risk stratification using the same Ollama-hosted multimodal model, running in parallel with text triage; urgency levels are merged programmatically and findings are appended verbatim — zero hallucination risk from cross-model contamination
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

###  ED Triage (RAG + SLM)
- **Structured intake** designed for speed: chief complaint (150 char limit), individual vital sign fields with unit labels and soft validation, 0–10 pain score button strip, quick-select contextual fields (onset, arrival mode, AVPU consciousness, trauma mechanism), and single-tap comorbidity checkboxes (cardiac, DM, respiratory, immunocompromised, anticoagulants, renal). Pregnancy status conditionally shown for female patients.
- **ATS 1–5 classification** using the Australasian Triage Scale with time-to-treatment targets. The LLM prompt includes ATS definitions, vitals thresholds for escalation (HR > 120, SpO₂ < 92%, systolic < 90 mmHg, etc.), and risk-modifier escalation rules (age > 65, pregnancy, anticoagulants).
- **Three-tier fallback**: Tier 1 — full RAG (retrieval + LLM); Tier 2 — LLM-only (when retrieval unavailable); Tier 3 — rule-based keyword matching (when LLM is down). The rule layer uses ATS-1, ATS-2, ATS-4, and ATS-5 keyword discriminators with ATS-3 as the default for undifferentiated presentations.
- **Vitals normality signal**: when all recorded vitals are within normal adult ranges, a strong prompt signal pushes the LLM toward ATS-4 or ATS-5 — counteracting the model's ATS-3 anchoring bias. Suppressed for elderly patients (≥65) with comorbidities to prevent inappropriate down-triage.
- Retrieves top-3 relevant chunks from **5 open-source medical guideline PDFs** (WHO, Singapore MOH, Australian ETEK).
- Returns structured rationale, source citations, ATS triage card (category + label + time target + colour), and a mandatory medical disclaimer.
- **Latency:** ~25–37s on CPU (Docker, 4 vCPU); ~2–3s on RTX 5070 Ti Mobile (12 GB VRAM). The CPU latency reflects a **student budget constraint** — the architecture is designed for GPU-accelerated inference.

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
curl -X POST http://localhost:8000/api/v1/triage \
  -F "chief_complaint=65M central chest pain radiating to jaw, onset 40 min ago, diaphoretic" \
  -F "age=65" \
  -F "sex=male" \
  -F "pain_score=8" \
  -F 'vitals={"hr":110,"rr":22,"spo2":94,"temp":37.1,"bp_systolic":160,"bp_diastolic":95}' \
  -F "arrival_mode=Ambulance" \
  -F "consciousness=Alert" \
  -F "onset=<1 hour"
```

### 6. Run tests
```bash
# Backend: 332 tests, 94% coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend: 56 tests across 11 component files
cd frontend && npx vitest --run
```

See the [Test Suite](#-test-suite) section below for a detailed breakdown.

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

##  Test Suite

The project has a comprehensive layered test suite: **332 backend tests** (94% coverage) and **56 frontend tests** across 11 component files.

### Backend Tests (`tests/`)

| Module | Tests | Coverage | Description |
|--------|-------|----------|-------------|
| `test_security.py` | 88 | 99% | Text sanitization (NFKC, homoglyphs, control chars), 16+ BLOCK/WARN injection patterns, JSON depth/size limits, image magic-byte validation, burst-aware rate limiter, circuit breaker lifecycle, client IP extraction |
| `test_api.py` | 47 | 87% | Health, metrics, dashboard endpoints; triage contract validation; prompt injection blocking (parametrized across 14 attack strings + homoglyph/unicode variants); rate limiting; security headers; CORS; audit logging; output truncation |
| `test_triage.py` | 59 | 93% | `_select_ats` keyword matching (all 5 ATS levels, priority ordering), `_highest_ats` comparisons, `merge_triage_results` (vision+text fusion), `_rule_based_result` fallback, `classify_vision` degradation paths, escalation notes (age/anticoagulant/pregnancy), vitals normality note edge cases |
| `test_llm.py` | 46 | 93% | Message extraction, JSON parsing, ATS/confidence/vision normalizers, `_build_user_prompt` (all sections), `_format_vitals`, `_format_comorbidities`, `rag_response` pipeline (mocked Ollama + retrieval) |
| `test_retriever.py` | 5 | 94% | Guideline object construction, empty results error, ChromaDB import failure |
| `test_observability.py` | 20 | 98% | Prometheus metrics registration/increment/payload, client ID hashing, JSONL logging + rotation, alert threshold |
| `test_config.py` | 26 | 100% | Default settings, env var overrides (`Aegis_` prefix), list parsing, type coercion |
| **Eval** | | | |
| `test_triage_accuracy.py` | 30 | — | 15 synthetic cases × 2 scenarios (LLM agrees + LLM downgrades) — verifies ATS agreement and safety escalation |
| `test_safety_evaluation.py` | 13 | — | Safe degradation (Tier 3 fallback), non-medical input handling, hallucination resistance, injection blocking, confidence bounds |

**Total backend: 332 tests, 94% line coverage**

```bash
# Full suite with coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Security only
pytest tests/test_security.py -v

# Eval only
pytest tests/eval/ -v
```

### Frontend Tests (`frontend/src/`)

| File | Tests | Description |
|------|-------|-------------|
| `TriageForm.test.tsx` | 15 | Field rendering, validation errors, form submission, loading state, clear, sex toggle, pregnancy conditional, comorbidities |
| `ResponsePreview.test.tsx` | 11 | Loading skeletons, ATS card, rationale, sources, disclaimer, null/loading states, vision result rendering |
| `Shell.test.tsx` | 2 | Form submission + response display (existing) |
| `UrgencyBadge.test.tsx` | 7 | All 5 ATS categories with correct labels and time targets |
| `SkeletonCard.test.tsx` | 4 | Label rendering, shimmer line count, custom className |
| `TriageHeader.test.tsx` | 3 | Title, API URL display, smoke test |
| `PageIntro.test.tsx` | 3 | Heading element, onComplete callback |
| `CursorGlow.test.tsx` | 1 | Smoke test (renders null in jsdom without fine pointer) |
| `NoiseOverlay.test.tsx` | 2 | CSS class presence, smoke test |
| `useMagnetic.test.ts` | 3 | Hook return shape, motion value methods |
| `api.test.ts` | 7 | `ApiError` class, `submitTriage` POST/error paths, `diagnose()` connectivity checks |

**Total frontend: 56 tests across 11 files**

```bash
cd frontend
npm install
npx vitest --run
```

### Evaluation Framework (`scripts/` + `tests/eval/`)

The evaluation framework uses 17 synthetic ED triage cases (`scripts/synthetic_triage_cases.py`) covering all ATS categories as ground truth:

- **`tests/eval/test_triage_accuracy.py`** — 30 parametrized tests: runs each case through `classify_text` with mocked LLM responses, verifying ATS agreement and that the safety escalation layer prevents under-triage
- **`tests/eval/test_safety_evaluation.py`** — 13 tests: Tier 3 degradation, non-medical input, hallucination resistance, injection blocking at security layer
- **`scripts/run_triage_batch.py`** — CLI runner for live evaluation against a running container:
  ```bash
  # Single run
  python scripts/run_triage_batch.py --url http://localhost:8000

  # With JSON export and per-ATS breakdown
  python scripts/run_triage_batch.py --url http://localhost:8000 --output-json results.json

  # Consistency measurement across 3 repeat runs
  python scripts/run_triage_batch.py --url http://localhost:8000 --repeat 3 --output-json results.json
  ```
  Supports `--output-json`, `--repeat N`, per-category pass-rate bars, and aggregate statistics (mean ± stdev).

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
Submit an ED triage assessment.

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|---|---|---|---|
| `chief_complaint` | string | **Yes** | Terse clinical chief complaint (max 150 chars) |
| `age` | int | **Yes** | Patient age (0–130) |
| `sex` | string | **Yes** | `male` or `female` |
| `pain_score` | int | **Yes** | Pain score 0–10 |
| `vitals` | JSON string | No | `{"hr": int, "rr": int, "spo2": int, "temp": float, "bp_systolic": int, "bp_diastolic": int}` |
| `onset` | string | No | `<1 hour`, `1-6 hours`, `6-24 hours`, `>24 hours` |
| `arrival_mode` | string | No | `Ambulatory`, `Wheelchair`, `Stretcher`, `Ambulance` |
| `consciousness` | string | No | `Alert`, `Verbal`, `Pain`, `Unresponsive` (AVPU scale) |
| `mechanism` | string | No | `Fall`, `MVA`, `Assault`, `Penetrating`, `Other` (trauma) |
| `comorbidities` | JSON string | No | `{"cardiac_disease": bool, ...}` — 6 flags |
| `pregnancy` | string | No | `Yes`, `No`, `Unknown` (female patients) |
| `allergies` | string | No | Known allergies, brief (max 200 chars) |
| `image` | file | No | JPEG/PNG image, max 5 MB |

**Success Response (200):**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "triage_result": {
    "ats_category": "ATS-2",
    "ats_card": {
      "category": "ATS-2",
      "label": "Emergency",
      "time_target_min": 10,
      "color": "#ea580c"
    },
    "rationale": "The patient presents with chest pain suggestive of acute coronary syndrome given the central location, radiation to jaw, diaphoresis, and associated tachycardia (HR 110 bpm). Age over 65 was noted as a factor for lower threshold review.",
    "confidence": "high",
    "sources": ["emergency_triage_education_kit_-_second_edition.pdf p.220"],
    "disclaimer": "This is a research prototype, not a substitute for professional medical advice."
  },
  "vision_result": null,
  "latency_ms": 24714,
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

The triage system was evaluated against 17 synthetic ED cases spanning all five ATS categories — from cardiac arrest (ATS-1) to medical certificate requests (ATS-5). Each case includes chief complaint, vitals, age, sex, pain score, and contextual fields (onset, arrival mode, consciousness, mechanism, comorbidities, pregnancy). Tests were run on two hardware configurations:

| Platform | Hardware | Accuracy | Avg Latency | Warm Latency |
|----------|----------|----------|-------------|--------------|
| **GPU** | RTX 5070 Ti Mobile (12 GB VRAM) | **16/17 (94.1%)** | 3.2s | 2.1–2.5s |
| **CPU** | 4 vCPU (Docker) | 15/17 (88.2%) | 36.8s | 24–42s |

> **Note:** The renal colic case (ATS-3) matched on GPU but not on CPU — the same MedGemma 4B Q4 model produced different triage results across hardware, likely due to floating-point precision differences in quantized inference. This is a known characteristic of quantized LLMs.

### Results Summary (GPU)

```
Results: 16 passed, 1 failed, 17 total  (94.1%)
Average latency: 3.2s (GPU, RTX 5070 Ti Mobile)
```

| Category | Passed | Rate | Notes |
|----------|--------|------|-------|
| ATS-1 (Resuscitation) | 2/2 | 100% | Cardiac arrest and anaphylactic shock — both immediately life-threatening cases correctly identified |
| ATS-2 (Emergency) | 5/5 | 100% | ACS, stroke, severe asthma, pregnant abdominal pain, MVA major trauma — all correct |
| ATS-3 (Urgent) | 2/4 | 50% | Two mismatches; see analysis below |
| ATS-4 (Semi-urgent) | 3/3 | 100% | Ankle sprain, UTI, small laceration — keyword matching + vitals normality signal correct |
| ATS-5 (Non-urgent) | 3/3 | 100% | Suture removal, minor rash, medical certificate — all correctly classified |

### Per-Case Results

| # | Case | Expected | Got | GPU | CPU | Match |
|---|------|----------|-----|-----|-----|-------|
| 1 | Cardiac arrest | ATS-1 | ATS-1 | 11.4s | 27.2s | ✓ |
| 2 | Anaphylactic shock | ATS-1 | ATS-1 | 2.1s | 27.2s | ✓ |
| 3 | ACS typical | ATS-2 | ATS-2 | 2.1s | 24.3s | ✓ |
| 4 | Stroke symptoms | ATS-2 | ATS-2 | 2.2s | 31.8s | ✓ |
| 5 | Severe asthma | ATS-2 | ATS-2 | 2.5s | 23.6s | ✓ |
| 6 | Pregnant abdominal pain | ATS-2 | ATS-2 | 1.7s | 31.3s | ✓ |
| 7 | Febrile elderly | ATS-3 | ATS-3 | 3.1s | 42.0s | ✓ |
| 8 | Renal colic | ATS-3 | ATS-3 ★ | 3.2s | 36.1s | ✓ |
| 9 | Head injury + warfarin | ATS-3 | ATS-4 | 3.1s | 40.4s | ✗ |
| 10 | Ankle sprain | ATS-4 | ATS-4 | 2.1s | 30.6s | ✓ |
| 11 | UTI symptoms | ATS-4 | ATS-4 | 2.3s | 32.1s | ✓ |
| 12 | Small laceration | ATS-4 | ATS-4 | 2.2s | 33.6s | ✓ |
| 13 | Suture removal | ATS-5 | ATS-5 | 2.3s | 42.2s | ✓ |
| 14 | Minor rash | ATS-5 | ATS-5 | 2.3s | 32.9s | ✓ |
| 15 | Medical certificate | ATS-5 | ATS-5 | 2.4s | 34.0s | ✓ |
| 16 | MVA major trauma | ATS-2 | ATS-2 | 3.1s | 22.9s | ✓ |
| 17 | Fall elderly | ATS-3 | ATS-3 | 3.1s | 40.4s | ✓ |

> ★ Case 8 (renal colic) matched on GPU but was misclassified as ATS-2 on CPU — see hardware note above. |

### Error Analysis

One case consistently fails across both CPU and GPU:

| Case | Expected | Got | Direction | Root Cause |
|------|----------|-----|-----------|------------|
| Head injury + warfarin (case 9) | ATS-3 | ATS-4 | **Unsafe** (under-triage) | "laceration" keyword in ATS-4 list matches. The rule layer only inspects chief complaint text — it doesn't incorporate structured fields (age 80, anticoagulants, head injury mechanism). The anticoagulant escalation note was appended to the rationale but did not elevate the category. **Fix pending:** wire structured risk modifiers into the rule-based tier |

The renal colic case (case 8) matched correctly on GPU (ATS-3) but was over-triaged on CPU (ATS-2). This is attributable to floating-point precision differences in Q4 quantized inference rather than a systemic triage logic issue.

### Key Design Decisions

- **Over-triage is safe; under-triage is dangerous.** The single remaining failure is an under-triage of an 80-year-old anticoagulated patient with head injury — this is the highest-priority fix.
- **Rule layer guards the LLM.** Keyword-based ATS-1, ATS-2, ATS-4, and ATS-5 discriminators provide a safety floor. The LLM can escalate but cannot override a definitive ATS-5 keyword match.
- **Vitals normality signal** successfully broke the LLM's ATS-3 anchoring bias for low-acuity cases. All 6 ATS-4 and ATS-5 cases were correctly classified.
- **GPU vs CPU divergence observed.** The same Q4-quantized model produced different triage outputs on GPU vs CPU for the renal colic case — a known characteristic of quantized LLM inference that warrants consistency testing across hardware targets.

### Running the Evaluation

```bash
# GPU (local Ollama + FastAPI)
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
python scripts/run_triage_batch.py --url http://localhost:8000

# CPU (Docker)
docker build -t aegis-md:eval .
docker run -d --rm -p 8000:8000 --name aegis-eval aegis-md:eval
# Wait ~30s for Ollama warmup, then:
python scripts/run_triage_batch.py --url http://localhost:8000 --output-json results.json

# With repeat runs for consistency measurement
python scripts/run_triage_batch.py --repeat 3 --output-json results.json

# List individual test cases
python scripts/synthetic_triage_cases.py --table
python scripts/synthetic_triage_cases.py --curl

# Clean up
docker stop aegis-eval
```

---

##  Safety, Ethics & Limitations

**This is a research prototype. It is not a medical device and must not be used for real patient care.**

- **No diagnosis:** The system classifies triage urgency only. It never names diseases, prescribes medications, or recommends dosages.
- **No PII storage:** User inputs and images are processed in-memory only. No data is persisted beyond the request lifecycle.
- **Mandatory disclaimer:** Every response includes a clear statement that this is not a substitute for professional medical advice.
- **Guardrails:** The LLM is constrained to ATS 1-5 via structured prompting with explicit vitals thresholds, risk-modifier escalation rules, and anti-hallucination directives. The rule-based keyword layer provides a safety floor for ATS-1, ATS-2, and ATS-5 classifications.
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
- [x] Post-MVP: Scored heuristics security gateway (16+ patterns, Unicode defense, burst rate limiting, circuit breaker, security headers)
- [x] Post-MVP: Comprehensive evaluation suite (332 backend tests, 94% coverage; 56 frontend tests; Docker + GPU evaluation at 94.1% accuracy)
- [ ] Post-MVP: Adversarial image detection (FGSM demo + rejection)
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
