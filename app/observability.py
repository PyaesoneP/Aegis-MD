import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

REGISTRY = CollectorRegistry()

REQUEST_COUNT = Counter(
    "aegis_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "path", "status"],
    registry=REGISTRY,
)

TRIAGE_LATENCY = Histogram(
    "aegis_triage_latency_seconds",
    "Latency for triage requests.",
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10),
    registry=REGISTRY,
)

SECURITY_BLOCKED = Counter(
    "aegis_security_blocked_total",
    "Total requests blocked by security controls.",
    ["reason"],
    registry=REGISTRY,
)

SECURITY_WARNED = Counter(
    "aegis_security_warned_total",
    "Total requests that triggered a security warning (not blocked).",
    ["reason"],
    registry=REGISTRY,
)

URGENCY_DISTRIBUTION = Counter(
    "aegis_urgency_total",
    "Total triage responses by urgency.",
    ["urgency"],
    registry=REGISTRY,
)

CIRCUIT_BREAKER_STATE = Counter(
    "aegis_circuit_breaker_total",
    "Circuit breaker state transitions.",
    ["state"],
    registry=REGISTRY,
)


def metrics_payload() -> bytes:
    return generate_latest(REGISTRY)


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def hashed_client_id(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Security event logging (JSONL with rotation)
# ---------------------------------------------------------------------------

_security_logger: logging.Logger | None = None


def _get_security_logger(log_dir: str, max_bytes: int, backup_count: int) -> logging.Logger:
    global _security_logger
    if _security_logger is not None:
        return _security_logger

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("aegis.security")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # don't duplicate to root logger

    handler = RotatingFileHandler(
        filename=str(Path(log_dir) / "security_events.jsonl"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    _security_logger = logger
    return logger


def _reset_security_logger() -> None:
    """Reset the cached security logger (useful for tests)."""
    global _security_logger
    if _security_logger is not None:
        for handler in _security_logger.handlers[:]:
            handler.close()
            _security_logger.removeHandler(handler)
    _security_logger = None


def log_security_event(
    *,
    log_dir: str,
    request_id: str,
    reason: str,
    client_ip: str,
    path: str,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    logger = _get_security_logger(log_dir, max_bytes, backup_count)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "reason": reason,
        "client_hash": hashed_client_id(client_ip),
        "path": path,
    }
    logger.info(json.dumps(event, separators=(",", ":")))


def log_request_audit(
    *,
    log_dir: str,
    request_id: str,
    client_ip: str,
    path: str,
    latency_ms: int,
    status_code: int,
    urgency: str | None = None,
    security_verdict: str = "pass",
    has_image: bool = False,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 3,
) -> None:
    """Log a structured audit record for every triage request."""
    logger = _get_security_logger(log_dir, max_bytes, backup_count)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": "request_audit",
        "request_id": request_id,
        "client_hash": hashed_client_id(client_ip),
        "path": path,
        "latency_ms": latency_ms,
        "status_code": status_code,
        "security_verdict": security_verdict,
        "urgency": urgency,
        "has_image": has_image,
    }
    logger.info(json.dumps(event, separators=(",", ":")))


# ---------------------------------------------------------------------------
# Alert threshold tracking (simple in-memory counter)
# ---------------------------------------------------------------------------

_alert_bucket: list[float] = []


def record_blocked_event() -> bool:
    """Record a blocked event. Returns True if the alert threshold is exceeded."""
    now = datetime.now(UTC).timestamp()
    _alert_bucket.append(now)
    # Prune entries older than 60 seconds.
    cutoff = now - 60
    while _alert_bucket and _alert_bucket[0] < cutoff:
        _alert_bucket.pop(0)
    return len(_alert_bucket) >= int(os.getenv("Aegis_ALERT_THRESHOLD_PER_MINUTE", "20"))


__all__ = [
    "REGISTRY",
    "REQUEST_COUNT",
    "TRIAGE_LATENCY",
    "SECURITY_BLOCKED",
    "SECURITY_WARNED",
    "URGENCY_DISTRIBUTION",
    "CIRCUIT_BREAKER_STATE",
    "metrics_payload",
    "hashed_client_id",
    "log_security_event",
    "log_request_audit",
    "record_blocked_event",
]

