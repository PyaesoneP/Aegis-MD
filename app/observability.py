import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest


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

URGENCY_DISTRIBUTION = Counter(
    "aegis_urgency_total",
    "Total triage responses by urgency.",
    ["urgency"],
    registry=REGISTRY,
)


def metrics_payload() -> bytes:
    return generate_latest(REGISTRY)


def hashed_client_id(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:16]


def log_security_event(
    *,
    log_dir: str,
    request_id: str,
    reason: str,
    client_ip: str,
    path: str,
) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "reason": reason,
        "client_hash": hashed_client_id(client_ip),
        "path": path,
    }
    with Path(log_dir, "security_events.jsonl").open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(event, separators=(",", ":")) + "\n")

