# Aegis-MD

> **A containerized, research-grade multimodal triage agent with built-in adversarial safety guardrails.**  
> Built by a former clinician and cybersecurity intern to explore the intersection of medical AI, LLM security, and production MLOps.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Research%20Use-lightgrey)](./LICENSE)

---

##  Live Demo

**[Try the live demo →](coming soon)** *(replace with your Cloud Run URL)*

Upload a symptom description (and optionally a skin-lesion image) to receive an informational triage urgency suggestion with explainable sources and confidence indicators.

![Demo Screenshot](coming soon)

---

##  Overview

Aegis-MD is a **minimum viable prototype (MVP)** of a multimodal clinical triage agent. It combines:

- **Retrieval-Augmented Generation (RAG)** over open-source medical guidelines (WHO, Singapore MOH, Australian ETEK)
- **Lightweight LLM inference** via a local Ollama-hosted research model (MedGemma-1.5 by default) for RAG-enabled, safety-focused triage. The model reference is configurable via `Aegis_LLM_MODEL` and can be replaced with another Ollama-compatible model or an on-disk GGUF runtime.
- **Computer Vision** risk stratification using a fine-tuned EfficientNet-B0 for skin-lesion screening
- **Security Gateway** with prompt-injection detection, rate limiting, and anomaly logging
- **Production Observability** via Prometheus metrics and a lightweight monitoring dashboard

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
- Retrieves top-3 relevant chunks from **5 open-source medical guideline PDFs**
- Classifies urgency into 4 tiers: `Emergency`, `Urgent`, `Routine`, `Self-Care`
- Returns structured rationale, source citations, and a mandatory medical disclaimer
- **p95 latency target:** < 3,000 ms on Cloud Run (2 vCPU, 4 GB RAM)

###  Vision Risk Stratification
- Optional image upload (JPEG/PNG, max 5 MB)
- Fine-tuned **EfficientNet-B0** on HAM10000 for binary lesion risk: `High-Risk` vs. `Low-Risk`
- Confidence-gated output (> 0.70 threshold); returns "insufficient confidence" if below
- **p95 latency target:** < 500 ms

###  Security Gateway
- FastAPI middleware intercepts all inputs **before** they reach the LLM
- Regex + keyword filter blocks known prompt-injection patterns:
  - `ignore previous instructions`, `DAN mode`, `jailbreak`, Base64-encoded attacks
- Rate limiting: 10 requests/minute per IP (sliding window)
- Security events logged to JSONL + Prometheus counter `aegis_security_blocked_total`

###  Monitoring Dashboard
- `/metrics` endpoint exposes Prometheus histograms for latency, throughput, and block rates
- `/dashboard` serves a lightweight HTML view of:
  - Request volume (24h)
  - Average latency (text vs. vision)
  - Security block count
  - Urgency distribution

---

##  Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **LLM** | MedGemma / MedGemma-1.5 (4B) via Ollama (configurable via `Aegis_LLM_MODEL`) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` |
| **Vector DB** | ChromaDB (in-memory, baked into container) |
| **Vision** | PyTorch, EfficientNet-B0 (fine-tuned on HAM10000) |
| **Security** | Custom FastAPI middleware, regex filters, rate limiting |
| **Monitoring** | Prometheus client, custom HTML dashboard |
| **Deployment** | Docker, Google Cloud Run |
| **CI/CD** | GitHub Actions (pytest → build → deploy) |
| **Frontend** | React (static, hosted on GitHub Pages) |

---

##  Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker (optional, for containerized deployment)
- `git`

### 1. Clone the repository
```bash
git clone https://github.com/pyaesonep/aegis-md.git
cd aegis-md
```

### 2. Set up the Python environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Models & retrieval
This backend now uses a local Ollama-hosted model for RAG-enabled triage. The model reference is configurable via the environment variable `Aegis_LLM_MODEL` (default set in `app/config.py`). Retrieval is performed using ChromaDB; configure the storage path and collection via `Aegis_CHROMA_PATH` and `Aegis_CHROMA_COLLECTION`.

If you plan to run RAG locally with Ollama:

```bash
# Install and run Ollama (see https://ollama.com/docs)
# Example: pull a model into your Ollama instance (model ref must match Aegis_LLM_MODEL)
ollama pull hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16

# Start Ollama daemon (platform-specific)
ollama serve
```

If you prefer to run a local GGUF model directly with another runtime, place model files under `./models/` and update `Aegis_LLM_MODEL` accordingly.

Guideline PDFs remain under `./data/guidelines/` and are chunked/embedded when you first run the app (or via your ingestion script).

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
| `Aegis_RATE_LIMIT_REQUESTS` | `10` | Requests allowed per client window |
| `Aegis_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length |
| `Aegis_LLM_MODEL` | `hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16` | Ollama model reference used for RAG triage |
| `Aegis_CHROMA_PATH` | `data/chroma/chroma_db` | Filesystem path for ChromaDB persistence |
| `Aegis_CHROMA_COLLECTION` | `guidelines` | Chroma collection name for guideline chunks |
| `Aegis_RETRIEVAL_TOP_K` | `3` | Number of guideline chunks to retrieve per query |

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
Local API calls are configured through `frontend/.env.development`:

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

The deployed frontend is configured for `https://pyaesonep.github.io/Aegis-MD/`.

---

##  Docker Deployment

### Build and run locally
```bash
docker build -t aegis-md:latest .
docker run -p 8000:8000 aegis-md:latest
```

Cloud Run uses the container `PORT` environment variable automatically; the Docker image starts `uvicorn app.main:app` on that port.

### Deploy to Google Cloud Run
```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/aegis-md

# Deploy (min instances = 1 to avoid cold-start during demo week)
gcloud run deploy aegis-md \
  --image gcr.io/YOUR_PROJECT_ID/aegis-md \
  --platform managed \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 5 \
  --memory 4Gi \
  --cpu 2
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
  "vision_result": null,
  "latency_ms": 1240,
  "security_passed": true
}
```

**Blocked Response (400):**
```json
{
  "error": "Security policy violation: potentially malicious input detected.",
  "request_id": "...",
  "security_passed": false
}
```

### `GET /health`
Health check. Returns component status.

### `GET /metrics`
Prometheus metrics endpoint.

### `GET /dashboard`
Lightweight HTML monitoring dashboard.

---

##  Evaluation

| Test | Dataset | Pass Threshold |
|---|---|---|
| Text triage accuracy | 50 hand-crafted synthetic vignettes | ≥ 70% exact-match urgency |
| Vision confidence gate | 20 HAM10000 test images | ≥ 80% high-risk flagged with confidence > 0.70 |
| Security gateway | 20 known prompt-injection strings | ≥ 90% blocked |
| Rate limiting | 15 rapid requests from same IP | Requests 11–15 return `429` |
| Latency | `locust` load test (10 users, 5 min) | p95 text < 3,000 ms; p95 vision < 500 ms |

Run evaluation suite:
```bash
python -m evaluation.run_all
```

---

##  Safety, Ethics & Limitations

**This is a research prototype. It is not a medical device and must not be used for real patient care.**

- **No diagnosis:** The system classifies triage urgency only. It never names diseases, prescribes medications, or recommends dosages.
- **No PII storage:** User inputs and images are processed in-memory only. No data is persisted beyond the request lifecycle.
- **Mandatory disclaimer:** Every response includes a clear statement that this is not a substitute for professional medical advice.
- **Guardrails:** The LLM is constrained to 4 urgency tiers via structured prompting. The security gateway blocks known jailbreak attempts.
- **Known limitations:**
  - The SLM (Gemma-2B) can hallucinate. The RAG layer grounds it in guideline text, but errors are possible.
  - The vision model is trained on dermoscopic images and may not generalize to smartphone photos.
  - The security filter is regex-based and will not catch all novel prompt-injection strategies.
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
- [ ] Post-MVP: ML-based intent classification guard (upgrade from regex)
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
