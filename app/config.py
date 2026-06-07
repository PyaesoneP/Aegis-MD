from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FastAPI scaffold."""

    allowed_origins: str = "http://localhost:5173,https://pyaesonep.github.io"
    log_dir: str = "logs"
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    max_symptom_chars: int = 2_000
    max_image_bytes: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(env_prefix="Aegis_", case_sensitive=False)

    llm_model: str = "hf.co/unsloth/medgemma-1.5-4b-it-GGUF:BF16"
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

    @property
    def allowed_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
