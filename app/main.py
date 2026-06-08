import asyncio
import json
import time
import uuid
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import Settings, get_settings
from app.llm import LLMError
from app.models import BlockedResponse, HealthResponse, PatientContext, TriageResponse
from app.observability import (
    CIRCUIT_BREAKER_STATE,
    REQUEST_COUNT,
    SECURITY_BLOCKED,
    SECURITY_WARNED,
    TRIAGE_LATENCY,
    URGENCY_DISTRIBUTION,
    log_request_audit,
    log_security_event,
    metrics_payload,
    record_blocked_event,
)
from app.retriever import RetrievalError
from app.security import (
    CircuitBreaker,
    RateLimiter,
    SecurityVerdict,
    check_patient_context,
    get_client_ip,
    sanitize_text,
    score_text,
    validate_image_bytes,
)
from app.triage import classify_text, classify_vision, merge_triage_results

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security headers on every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("X-XSS-Protection", "0")  # deprecated but signals intent

        settings: Settings = request.app.state.settings
        if settings.enable_hsts:
            headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


# ---------------------------------------------------------------------------
# Max body size middleware (ASGI-level guard)
# ---------------------------------------------------------------------------

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds a configured maximum."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings: Settings = request.app.state.settings
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > settings.max_body_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": f"Request body exceeds {settings.max_body_bytes // (1024 * 1024)} MB limit",
                    "request_id": str(uuid.uuid4()),
                    "security_passed": False,
                },
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Aegis-MD API",
        version="0.1.0",
        description="Functional scaffold for the Aegis-MD multimodal triage backend.",
    )
    app.state.settings = settings

    # ── Rate limiters (per-endpoint) ─────────────────────────────────
    app.state.rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        burst_multiplier=settings.rate_limit_burst_multiplier,
        burst_seconds=settings.rate_limit_burst_seconds,
    )
    # Lightweight endpoints get their own (higher) limits.
    app.state.health_limiter = RateLimiter(
        max_requests=settings.rate_limit_health_requests,
        window_seconds=settings.rate_limit_window_seconds,
        burst_multiplier=1.0,
    )
    app.state.metrics_limiter = RateLimiter(
        max_requests=settings.rate_limit_metrics_requests,
        window_seconds=settings.rate_limit_window_seconds,
        burst_multiplier=1.0,
    )
    app.state.dashboard_limiter = RateLimiter(
        max_requests=settings.rate_limit_dashboard_requests,
        window_seconds=settings.rate_limit_window_seconds,
        burst_multiplier=1.0,
    )

    # ── Circuit breaker ──────────────────────────────────────────────
    app.state.circuit_breaker = CircuitBreaker(
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_seconds=settings.circuit_breaker_recovery_seconds,
    )

    # ── Middleware stack (order matters: outer → inner) ──────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=settings.cors_allow_header_list,
    )
    app.add_middleware(MaxBodySizeMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Request counting ─────────────────────────────────────────────
    @app.middleware("http")
    async def record_requests(request: Request, call_next):
        response = await call_next(request)
        REQUEST_COUNT.labels(
            request.method,
            request.url.path,
            str(response.status_code),
        ).inc()
        return response

    # ── Health ───────────────────────────────────────────────────────
    @app.get("/health", response_model=HealthResponse)
    async def health(
        request: Request,
        readiness: Annotated[bool | None, Query()] = None,
    ) -> HealthResponse:
        client_ip = get_client_ip(request)
        if not request.app.state.health_limiter.allow(client_ip):
            return JSONResponse(status_code=429, content={"error": "Too many requests"})

        text_model_status, text_model_detail = _check_ollama_health()
        retrieval_status, retrieval_detail = _check_retrieval_health(settings)

        # ── Readiness probe: return 503 until all critical deps are ok ──
        if readiness:
            critical_ok = text_model_status == "ok"
            if not critical_ok:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "text_model": text_model_status,
                        "detail": text_model_detail,
                    },
                )

        return HealthResponse(
            status="ok",
            components={
                "api": {"status": "ok", "detail": "FastAPI gateway is reachable."},
                "security": {
                    "status": "ok",
                    "detail": "Scored prompt-injection heuristics, burst-aware rate limiter, circuit breaker, and security headers active.",
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
                    "status": text_model_status if settings.vision_enabled else "placeholder",
                    "detail": (
                        "MedGemma multimodal model — same instance as text model."
                        if settings.vision_enabled
                        else "Vision inference is disabled (vision_enabled=False)."
                    ),
                },
                "observability": {
                    "status": "ok",
                    "detail": "Prometheus metrics, JSONL security logging with rotation, and request audit trail are active.",
                },
            },
        )

    # ── Metrics ──────────────────────────────────────────────────────
    @app.get("/metrics")
    async def metrics(request: Request) -> Response:
        client_ip = get_client_ip(request)
        if not request.app.state.metrics_limiter.allow(client_ip):
            return JSONResponse(status_code=429, content={"error": "Too many requests"})
        return Response(metrics_payload(), media_type="text/plain; version=0.0.4")

    # ── Dashboard ────────────────────────────────────────────────────
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request) -> str:
        client_ip = get_client_ip(request)
        if not request.app.state.dashboard_limiter.allow(client_ip):
            return JSONResponse(status_code=429, content={"error": "Too many requests"})
        return _DASHBOARD_HTML

    # ── Triage (main endpoint) ───────────────────────────────────────
    @app.post(
        "/api/v1/triage",
        response_model=TriageResponse,
        responses={
            400: {"model": BlockedResponse},
            413: {"description": "Request body too large"},
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
        settings_local: Settings = request.app.state.settings
        limiter: RateLimiter = request.app.state.rate_limiter
        breaker: CircuitBreaker = request.app.state.circuit_breaker

        # ── 1. Rate limiting ─────────────────────────────────────────
        if not limiter.allow(client_ip):
            SECURITY_BLOCKED.labels("rate_limit").inc()
            log_security_event(
                log_dir=settings_local.log_dir,
                request_id=request_id,
                reason="rate_limit",
                client_ip=client_ip,
                path=request.url.path,
                max_bytes=settings_local.log_max_bytes,
                backup_count=settings_local.log_backup_count,
            )
            return _blocked(
                status_code=429,
                error="Rate limit exceeded. Please wait before submitting another request.",
                request_id=request_id,
            )
        rate_info = limiter.info(client_ip)

        # ── 2. Symptom length ────────────────────────────────────────
        if len(symptoms) > settings_local.max_symptom_chars:
            raise HTTPException(
                status_code=422,
                detail=f"symptoms must be {settings_local.max_symptom_chars} characters or fewer",
            )

        # ── 3. Sanitize & score symptoms ─────────────────────────────
        clean_symptoms = sanitize_text(symptoms)
        symptom_score = score_text(symptoms, field_name="symptoms")
        if symptom_score.verdict == SecurityVerdict.BLOCK:
            SECURITY_BLOCKED.labels("prompt_injection").inc()
            log_security_event(
                log_dir=settings_local.log_dir,
                request_id=request_id,
                reason=f"prompt_injection:{symptom_score.reason}",
                client_ip=client_ip,
                path=request.url.path,
                max_bytes=settings_local.log_max_bytes,
                backup_count=settings_local.log_backup_count,
            )
            return _blocked(
                status_code=400,
                error="Security policy violation: potentially malicious input detected.",
                request_id=request_id,
            )
        if symptom_score.verdict == SecurityVerdict.WARN:
            SECURITY_WARNED.labels("prompt_injection").inc()
            log_security_event(
                log_dir=settings_local.log_dir,
                request_id=request_id,
                reason=f"prompt_injection_warn:{symptom_score.reason}",
                client_ip=client_ip,
                path=request.url.path,
                max_bytes=settings_local.log_max_bytes,
                backup_count=settings_local.log_backup_count,
            )

        # ── 4. Validate & sanitize patient_context ───────────────────
        if patient_context is not None:
            ctx_score = check_patient_context(patient_context)
            if ctx_score.verdict == SecurityVerdict.BLOCK:
                SECURITY_BLOCKED.labels("prompt_injection").inc()
                log_security_event(
                    log_dir=settings_local.log_dir,
                    request_id=request_id,
                    reason=f"prompt_injection:patient_context:{ctx_score.reason}",
                    client_ip=client_ip,
                    path=request.url.path,
                    max_bytes=settings_local.log_max_bytes,
                    backup_count=settings_local.log_backup_count,
                )
                return _blocked(
                    status_code=400,
                    error="Security policy violation: potentially malicious input in patient_context.",
                    request_id=request_id,
                )
            if ctx_score.verdict == SecurityVerdict.WARN:
                SECURITY_WARNED.labels("prompt_injection").inc()
                log_security_event(
                    log_dir=settings_local.log_dir,
                    request_id=request_id,
                    reason=f"prompt_injection_warn:patient_context:{ctx_score.reason}",
                    client_ip=client_ip,
                    path=request.url.path,
                    max_bytes=settings_local.log_max_bytes,
                    backup_count=settings_local.log_backup_count,
                )

        parsed_context = _parse_patient_context(patient_context)
        image_bytes = await _validate_image(image, settings_local)

        # ── 5. Circuit breaker check ─────────────────────────────────
        if not breaker.allow_request():
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable — downstream dependencies are failing.",
            )

        # ── 6. Run triage (parallel vision + text when image present) ──
        final_verdict = symptom_score.verdict.value
        try:
            with TRIAGE_LATENCY.time():
                if image_bytes:
                    # Fire vision and text concurrently.
                    vision_task = run_in_threadpool(
                        classify_vision, image_bytes, parsed_context
                    )
                    text_task = run_in_threadpool(
                        classify_text,
                        clean_symptoms,
                        parsed_context,
                        vision_result=None,  # text LLM runs without vision context
                    )
                    vision_result, triage_result = await asyncio.gather(
                        vision_task, text_task
                    )
                    # Merge urgency levels programmatically (no LLM — zero hallucination).
                    if vision_result is not None:
                        triage_result = merge_triage_results(
                            triage_result, vision_result
                        )
                else:
                    vision_result = None
                    triage_result = await run_in_threadpool(
                        classify_text,
                        clean_symptoms,
                        parsed_context,
                        vision_result=None,
                    )
            breaker.record_success()
        except LLMError as exc:
            breaker.record_failure()
            CIRCUIT_BREAKER_STATE.labels("failure").inc()
            raise HTTPException(
                status_code=503,
                detail="Text triage RAG/LLM dependency is unavailable.",
            ) from exc

        URGENCY_DISTRIBUTION.labels(triage_result.urgency).inc()
        latency_ms = int((time.perf_counter() - started) * 1000)

        # ── 7. Output safety ─────────────────────────────────────────
        safe_rationale = _truncate_if_needed(
            triage_result.rationale, settings_local.max_rationale_chars
        )
        safe_disclaimer = _truncate_if_needed(
            triage_result.disclaimer, settings_local.max_disclaimer_chars
        )
        triage_result.rationale = safe_rationale
        triage_result.disclaimer = safe_disclaimer

        # ── 8. Audit log ─────────────────────────────────────────────
        log_request_audit(
            log_dir=settings_local.log_dir,
            request_id=request_id,
            client_ip=client_ip,
            path=request.url.path,
            latency_ms=latency_ms,
            status_code=200,
            urgency=triage_result.urgency,
            security_verdict=final_verdict,
            has_image=image_bytes is not None,
            max_bytes=settings_local.log_max_bytes,
            backup_count=settings_local.log_backup_count,
        )

        # ── 9. Response with rate-limit headers ──────────────────────
        response = TriageResponse(
            request_id=request_id,
            triage_result=triage_result,
            vision_result=vision_result,
            latency_ms=latency_ms,
            security_passed=True,
        )
        return JSONResponse(
            status_code=200,
            content=response.model_dump(),
            headers={
                "X-RateLimit-Limit": str(rate_info.limit),
                "X-RateLimit-Remaining": str(rate_info.remaining),
                "X-RateLimit-Reset": str(int(rate_info.reset_at)),
            },
        )

    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DASHBOARD_HTML = """
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
        <div class="panel"><strong>Security</strong><br>Scored heuristics + burst rate limit + circuit breaker</div>
        <div class="panel"><strong>Models</strong><br>Placeholder routing active</div>
      </section>
    </main>
  </body>
</html>
"""


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
    from app.retriever import get_guideline_collection
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


async def _validate_image(image: UploadFile | None, settings: Settings) -> bytes | None:
    if image is None:
        return None
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

    # Magic-byte validation.
    magic_check = validate_image_bytes(content)
    if magic_check.verdict == SecurityVerdict.BLOCK:
        raise HTTPException(
            status_code=422,
            detail=magic_check.reason,
        )

    return content


def _truncate_if_needed(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 30] + "… [truncated for safety]"


app = create_app()
