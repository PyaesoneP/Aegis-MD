from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FastAPI scaffold."""

    # ── Networking ──────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173,https://pyaesonep.github.io"
    cors_allow_headers: str = "content-type,accept,authorization,x-requested-with"

    # ── Logging & observability ─────────────────────────────────────────
    log_dir: str = "logs"
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB per log file
    log_backup_count: int = 3

    # ── Rate limiting ───────────────────────────────────────────────────
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    rate_limit_burst_multiplier: float = 2.0
    rate_limit_burst_seconds: float = 5.0
    # Higher limits for lightweight endpoints.
    rate_limit_health_requests: int = 60
    rate_limit_metrics_requests: int = 60
    rate_limit_dashboard_requests: int = 30

    # ── Input validation ────────────────────────────────────────────────
    max_symptom_chars: int = 150  # chief complaint limit for ED triage
    max_allergies_chars: int = 200
    max_image_bytes: int = 5 * 1024 * 1024
    max_body_bytes: int = 10 * 1024 * 1024  # total request body limit
    max_json_depth: int = 5
    max_json_bytes: int = 10_240  # 10 KB for patient_context JSON
    max_image_megapixels: int = 100  # decompression-bomb guard
    max_aspect_ratio: int = 100

    # ── Security headers ────────────────────────────────────────────────
    enable_hsts: bool = False  # off by default for local dev

    # ── Circuit breaker ─────────────────────────────────────────────────
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_seconds: float = 30.0

    # ── Alerting ────────────────────────────────────────────────────────
    alert_threshold_per_minute: int = 20

    # ── LLM / RAG / Vision ──────────────────────────────────────────────
    model_config = SettingsConfigDict(env_prefix="Aegis_", case_sensitive=False)
    llm_model: str = "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:UD-Q4_K_XL"
    chroma_path: str = "data/chroma/chroma_db"
    chroma_collection: str = "guidelines"
    retrieval_top_k: int = 3
    vision_enabled: bool = True
    vision_system_prompt: str = (
        "You are Aegis-MD, a research triage assistant with medical image analysis capability. "
        "Analyze the provided medical image and classify risk only. "
        "Do not diagnose. Do not prescribe treatment. "
        "Return JSON only, with exactly these keys: risk, confidence, rationale. "
        "risk must be one of: High-Risk, Low-Risk, insufficient confidence. "
        "confidence must be a number between 0 and 1. "
        "The rationale must be brief, safety-focused, and describe key visual findings. "
        "If the image is not a recognizable medical image, set risk to 'insufficient confidence' and explain why."
    )

    # ── Output safety ───────────────────────────────────────────────────
    max_rationale_chars: int = 4_000
    max_disclaimer_chars: int = 500

    @property
    def allowed_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def cors_allow_header_list(self) -> list[str]:
        return [
            h.strip().lower()
            for h in self.cors_allow_headers.split(",")
            if h.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
