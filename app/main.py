import json
import time
import uuid
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.llm import LLMError
from app.models import BlockedResponse, HealthResponse, PatientContext, TriageResponse
from app.retriever import get_guideline_collection, RetrievalError
from app.observability import (
    REQUEST_COUNT,
    SECURITY_BLOCKED,
    TRIAGE_LATENCY,
    URGENCY_DISTRIBUTION,
    log_security_event,
    metrics_payload,
)
from app.retriever import RetrievalError
from app.security import RateLimiter, detect_prompt_injection, get_client_ip
from app.triage import build_vision_placeholder, classify_text

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Aegis-MD API",
        version="0.1.0",
        description="Functional scaffold for the Aegis-MD multimodal triage backend.",
    )
    app.state.settings = settings
    app.state.rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def record_requests(request: Request, call_next):
        response = await call_next(request)
        REQUEST_COUNT.labels(
            request.method,
            request.url.path,
            str(response.status_code),
        ).inc()
        return response

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        text_model_status, text_model_detail = _check_ollama_health()
        retrieval_status, retrieval_detail = _check_retrieval_health(settings)
        return HealthResponse(
            status="ok",
            components={
                "api": {"status": "ok", "detail": "FastAPI gateway is reachable."},
                "security": {
                    "status": "ok",
                    "detail": "Regex prompt-injection filter and rate limiter enabled.",
                },
                "text_model": {
                    "status": text_model_status,
                    "detail": text_model_detail,
                },
                "retrieval": {
                    "status": retrieval_status,
                    "detail": retrieval_detail,
                },
                "vision_model": {
                    "status": "placeholder",
                    "detail": "Image validation is active; model inference is pending.",
                },
                "observability": {
                    "status": "ok",
                    "detail": "Prometheus metrics and JSONL security logging are active.",
                },
            },
        )

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(metrics_payload(), media_type="text/plain; version=0.0.4")

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard() -> str:
        return """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Aegis-MD Dashboard</title>
            <style>
              body { font-family: system-ui, sans-serif; margin: 2rem; color: #17201f; }
              main { max-width: 760px; }
              code { background: #eef6f3; padding: .2rem .35rem; border-radius: .3rem; }
              .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
              .panel { border: 1px solid #dbe7e2; border-radius: .5rem; padding: 1rem; }
            </style>
          </head>
          <body>
            <main>
              <h1>Aegis-MD Monitoring</h1>
              <p>Functional scaffold dashboard. Prometheus metrics are available at <code>/metrics</code>.</p>
              <section class="grid">
                <div class="panel"><strong>Gateway</strong><br>FastAPI online</div>
                <div class="panel"><strong>Security</strong><br>Regex filter + rate limit</div>
                <div class="panel"><strong>Models</strong><br>Placeholder routing active</div>
              </section>
            </main>
          </body>
        </html>
        """

    @app.post(
        "/api/v1/triage",
        response_model=TriageResponse,
        responses={
            400: {"model": BlockedResponse},
            429: {"model": BlockedResponse},
            503: {"description": "RAG or Ollama dependency unavailable"},
        },
    )
    async def triage(
        request: Request,
        symptoms: Annotated[str, Form()],
        patient_context: Annotated[str | None, Form()] = None,
        image: Annotated[UploadFile | None, File()] = None,
    ) -> TriageResponse:
        started = time.perf_counter()
        request_id = str(uuid.uuid4())
        client_ip = get_client_ip(request)
        settings: Settings = request.app.state.settings

        if not app.state.rate_limiter.allow(client_ip):
            SECURITY_BLOCKED.labels("rate_limit").inc()
            log_security_event(
                log_dir=settings.log_dir,
                request_id=request_id,
                reason="rate_limit",
                client_ip=client_ip,
                path=request.url.path,
            )
            return _blocked(
                status_code=429,
                error="Rate limit exceeded. Please wait before submitting another request.",
                request_id=request_id,
            )

        if len(symptoms) > settings.max_symptom_chars:
            raise HTTPException(
                status_code=422,
                detail=f"symptoms must be {settings.max_symptom_chars} characters or fewer",
            )

        injection_reason = detect_prompt_injection(symptoms)
        if injection_reason:
            SECURITY_BLOCKED.labels("prompt_injection").inc()
            log_security_event(
                log_dir=settings.log_dir,
                request_id=request_id,
                reason="prompt_injection",
                client_ip=client_ip,
                path=request.url.path,
            )
            return _blocked(
                status_code=400,
                error="Security policy violation: potentially malicious input detected.",
                request_id=request_id,
            )

        parsed_context = _parse_patient_context(patient_context)
        has_image = await _validate_image(image, settings)

        try:
            with TRIAGE_LATENCY.time():
                triage_result = await run_in_threadpool(
                    classify_text,
                    symptoms,
                    parsed_context,
                )
                vision_result = build_vision_placeholder(has_image)
        except (LLMError, RetrievalError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Text triage RAG/LLM dependency is unavailable.",
            ) from exc

        URGENCY_DISTRIBUTION.labels(triage_result.urgency).inc()
        latency_ms = int((time.perf_counter() - started) * 1000)
        return TriageResponse(
            request_id=request_id,
            triage_result=triage_result,
            vision_result=vision_result,
            latency_ms=latency_ms,
            security_passed=True,
        )

    return app


def _check_ollama_health() -> tuple[str, str]:
    try:
        from ollama import chat  # noqa: F401
    except ImportError:
        return (
            "degraded",
            "Ollama package is not installed or unavailable.",
        )

    return (
        "ok",
        "Ollama package is installed and available.",
    )


def _check_retrieval_health(settings: Settings) -> tuple[str, str]:
    try:
        get_guideline_collection(
            chroma_path=settings.chroma_path,
            collection_name=settings.chroma_collection,
        )
    except RetrievalError as exc:
        return (
            "degraded",
            f"Chroma retrieval unavailable: {exc}",
        )

    return (
        "ok",
        f"Chroma retrieval configured for collection {settings.chroma_collection}.",
    )


def _blocked(*, status_code: int, error: str, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "request_id": request_id,
            "security_passed": False,
        },
    )


def _parse_patient_context(patient_context: str | None) -> PatientContext | None:
    if not patient_context:
        return None
    try:
        payload = json.loads(patient_context)
        return PatientContext.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=422,
            detail="patient_context must be valid JSON matching {'age': int, 'sex': 'male|female'}",
        ) from exc


async def _validate_image(image: UploadFile | None, settings: Settings) -> bool:
    if image is None:
        return False
    if image.content_type not in IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail="image must be a JPEG or PNG file",
        )
    content = await image.read(settings.max_image_bytes + 1)
    if len(content) > settings.max_image_bytes:
        raise HTTPException(
            status_code=422,
            detail="image must be 5 MB or smaller",
        )
    return True


app = create_app()
