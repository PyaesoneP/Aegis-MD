import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from fastapi import Request


PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions\b", re.I),
    re.compile(r"\bdan\s+mode\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\breveal\s+(the\s+)?(system|developer)\s+prompt\b", re.I),
    re.compile(r"\bbase64[-\s]?encoded\s+(attack|payload|instructions?)\b", re.I),
)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def detect_prompt_injection(text: str) -> str | None:
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


@dataclass
class RateLimiter:
    max_requests: int
    window_seconds: int
    buckets: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        bucket = self.buckets[client_id]
        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(now)
        return True

    def clear(self) -> None:
        self.buckets.clear()

