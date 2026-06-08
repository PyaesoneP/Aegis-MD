"""Tests for app.config — default settings, env-var overrides, and property parsing."""

from app.config import Settings


class TestDefaultSettings:
    def test_default_allowed_origins(self):
        s = Settings()
        origins = s.allowed_origin_list
        assert "http://localhost:5173" in origins
        assert "https://pyaesonep.github.io" in origins

    def test_cors_allow_header_list_parsed(self):
        s = Settings()
        headers = s.cors_allow_header_list
        assert "content-type" in headers
        assert "accept" in headers

    def test_max_symptom_chars_default(self):
        s = Settings()
        assert s.max_symptom_chars == 150

    def test_max_image_bytes_default(self):
        s = Settings()
        assert s.max_image_bytes == 5 * 1024 * 1024

    def test_max_body_bytes_default(self):
        s = Settings()
        assert s.max_body_bytes == 10 * 1024 * 1024

    def test_rate_limit_defaults(self):
        s = Settings()
        assert s.rate_limit_requests == 10
        assert s.rate_limit_window_seconds == 60
        assert s.rate_limit_burst_multiplier == 2.0

    def test_rate_limit_health_defaults(self):
        s = Settings()
        assert s.rate_limit_health_requests == 60

    def test_circuit_breaker_defaults(self):
        s = Settings()
        assert s.circuit_breaker_failure_threshold == 5
        assert s.circuit_breaker_recovery_seconds == 30.0

    def test_vision_enabled_default(self):
        s = Settings()
        assert s.vision_enabled is True

    def test_llm_model_default(self):
        s = Settings()
        assert "medgemma" in s.llm_model.lower()

    def test_chroma_defaults(self):
        s = Settings()
        assert s.chroma_path == "data/chroma/chroma_db"
        assert s.chroma_collection == "guidelines"
        assert s.retrieval_top_k == 3

    def test_enable_hsts_default(self):
        s = Settings()
        assert s.enable_hsts is False

    def test_max_json_depth_default(self):
        s = Settings()
        assert s.max_json_depth == 5

    def test_max_json_bytes_default(self):
        s = Settings()
        assert s.max_json_bytes == 10_240

    def test_output_safety_defaults(self):
        s = Settings()
        assert s.max_rationale_chars == 4_000
        assert s.max_disclaimer_chars == 500


class TestEnvironmentOverrides:
    def test_env_var_overrides_allowed_origins(self, monkeypatch):
        monkeypatch.setenv("Aegis_ALLOWED_ORIGINS", "http://example.com,http://test.com")
        s = Settings()
        origins = s.allowed_origin_list
        assert origins == ["http://example.com", "http://test.com"]

    def test_env_var_overrides_rate_limit(self, monkeypatch):
        monkeypatch.setenv("Aegis_RATE_LIMIT_REQUESTS", "30")
        s = Settings()
        assert s.rate_limit_requests == 30

    def test_env_var_overrides_vision_enabled(self, monkeypatch):
        monkeypatch.setenv("Aegis_VISION_ENABLED", "false")
        s = Settings()
        assert s.vision_enabled is False

    def test_env_var_overrides_vision_enabled_true(self, monkeypatch):
        monkeypatch.setenv("Aegis_VISION_ENABLED", "true")
        s = Settings()
        assert s.vision_enabled is True

    def test_env_var_overrides_llm_model(self, monkeypatch):
        monkeypatch.setenv("Aegis_LLM_MODEL", "llama3:8b")
        s = Settings()
        assert s.llm_model == "llama3:8b"

    def test_env_var_overrides_chroma_path(self, monkeypatch):
        monkeypatch.setenv("Aegis_CHROMA_PATH", "/custom/chroma/path")
        s = Settings()
        assert s.chroma_path == "/custom/chroma/path"

    def test_env_var_overrides_enable_hsts(self, monkeypatch):
        monkeypatch.setenv("Aegis_ENABLE_HSTS", "true")
        s = Settings()
        assert s.enable_hsts is True


class TestPropertyParsing:
    def test_allowed_origin_list_single(self, monkeypatch):
        monkeypatch.setenv("Aegis_ALLOWED_ORIGINS", "http://single-origin.com")
        s = Settings()
        assert s.allowed_origin_list == ["http://single-origin.com"]

    def test_allowed_origin_list_empty_string(self, monkeypatch):
        monkeypatch.setenv("Aegis_ALLOWED_ORIGINS", "")
        s = Settings()
        assert s.allowed_origin_list == []

    def test_allowed_origin_list_strips_whitespace(self, monkeypatch):
        monkeypatch.setenv("Aegis_ALLOWED_ORIGINS", "  http://a.com , http://b.com  ")
        s = Settings()
        assert s.allowed_origin_list == ["http://a.com", "http://b.com"]

    def test_cors_allow_header_list_lowercased(self, monkeypatch):
        monkeypatch.setenv("Aegis_CORS_ALLOW_HEADERS", "Content-Type,Authorization")
        s = Settings()
        assert "content-type" in s.cors_allow_header_list
        assert "authorization" in s.cors_allow_header_list
