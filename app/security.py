import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum

from fastapi import Request

# ---------------------------------------------------------------------------
# Character-level sanitization
# ---------------------------------------------------------------------------

# Control characters and zero-width codepoints that have no legitimate use in
# natural-language medical text.
_CONTROL_CHARS_RE = re.compile(
    "[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f"
    "\u200b-\u200f\u2028-\u202f\u2060-\u2064\u2066-\u206f"
    "\ufeff\ufff9-\ufffb]"
)

# Homoglyph / confusable character mapping ― only the most common
# substitutions that evade naive regex while remaining visually near-identical.
_HOMOGLYPH_MAP: dict[int, int | None] = {
    # Cyrillic → Latin
    0x0430: 0x0061,  # а → a
    0x0435: 0x0065,  # е → e
    0x043E: 0x006F,  # о → o
    0x0440: 0x0070,  # р → p
    0x0441: 0x0063,  # с → c
    0x0443: 0x0079,  # у → y
    0x0445: 0x0078,  # х → x
    0x0410: 0x0041,  # А → A
    0x0415: 0x0045,  # Е → E
    0x041E: 0x004F,  # О → O
    0x0420: 0x0050,  # Р → P
    0x0421: 0x0043,  # С → C
    0x0425: 0x0058,  # Х → X
    0x041C: 0x004D,  # М → M
    0x0422: 0x0054,  # Т → T
    0x041D: 0x0048,  # Н → H
    # Greek → Latin
    0x03BF: 0x006F,  # ο → o
    0x039F: 0x004F,  # Ο → O
    # Fullwidth → ASCII
    0xFF21: 0x0041,  # Ａ → A
    0xFF28: 0x0048,  # Ｈ → H
    0xFF29: 0x0049,  # Ｉ → I
    0xFF2D: 0x004D,  # Ｍ → M
    0xFF2F: 0x004F,  # Ｏ → O
    0xFF30: 0x0050,  # Ｐ → P
    0xFF33: 0x0053,  # Ｓ → S
    0xFF34: 0x0054,  # Ｔ → T
    0xFF38: 0x0058,  # Ｘ → X
    0xFF39: 0x0059,  # Ｙ → Y
    0xFF41: 0x0061,  # ａ → a
    0xFF43: 0x0063,  # ｃ → c
    0xFF45: 0x0065,  # ｅ → e
    0xFF48: 0x0068,  # ｈ → h
    0xFF49: 0x0069,  # ｉ → i
    0xFF4D: 0x006D,  # ｍ → m
    0xFF4F: 0x006F,  # ｏ → o
    0xFF50: 0x0070,  # ｐ → p
    0xFF53: 0x0073,  # ｓ → s
    0xFF54: 0x0074,  # ｔ → t
    0xFF58: 0x0078,  # ｘ → x
    0xFF59: 0x0079,  # ｙ → y
}


def _translate_homoglyphs(text: str) -> str:
    """Return *text* with known homoglyph codepoints remapped to ASCII."""
    return text.translate(_HOMOGLYPH_MAP)


def strip_control_chars(text: str) -> str:
    """Remove control characters and zero-width codepoints."""
    return _CONTROL_CHARS_RE.sub("", text)


def normalize_text(text: str) -> str:
    """NFKC-normalize, strip control chars, and remap homoglyphs.

    This is the canonical pre-processing step for all user-supplied text
    before any downstream inspection or model consumption.
    """
    text = unicodedata.normalize("NFKC", text)
    text = strip_control_chars(text)
    text = _translate_homoglyphs(text)
    return text


# ---------------------------------------------------------------------------
# Prompt-injection detection (scored heuristics)
# ---------------------------------------------------------------------------

class SecurityVerdict(Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


# Patterns that, if matched, trigger an immediate BLOCK.
_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Classic instruction-override attacks
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions?\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(prior|previous|above)\s+(instructions?|prompts?|messages?)\b", re.I),
    re.compile(
        r"\b(forget|delete|erase|clear)\s+(all\s+)?(the\s+)?(previous|prior|above)\s+(conversation|context|instructions?|prompts?)\b",
        re.I,
    ),
    # DAN / jailbreak variants
    re.compile(r"\b(?:dan|do\s*anything\s*now)\s*(?:mode|prompt|jailbreak)?\b", re.I),
    re.compile(r"\b(?:developer|superuser|admin|root)\s*mode\s*(?:enabled|activated|override)\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    # Prompt extraction
    re.compile(r"\b(reveal|show|display|print|echo|dump|output)\s+(?:me\s+|us\s+|your\s+)?(the\s+)?(system|developer|hidden|secret)\s+(prompt|instructions?|message)\b", re.I),
    re.compile(r"\bwhat\s+(is|are)\s+(your|the)\s+(system|initial|original|base)\s+(prompt|instructions?)\b", re.I),
    # Encoding-based evasion
    re.compile(r"\bbase64[-\s]?encoded\s+(attack|payload|instructions?)\b", re.I),
    re.compile(r"\bdecode\s+(this|the\s+following)\s+(base64|hex|binary)\b", re.I),
    # Delimiter / token-splitting attacks
    re.compile(r"[-_=]{8,}\s*(system|assistant|user)\s*:\s*", re.I),
    re.compile(r"<\|(?:system|endoftext|im_start|im_end)\|>", re.I),
    # Role-play / persona override
    re.compile(r"\byou\s+(?:are|become)\s+(?:now|no\s+longer)\b.{0,50}\b(?:evil|malicious|unethical|without\s+(?:restrictions?|rules?|limits?|ethics?))\b", re.I),
    re.compile(r"\bpretend\s+(?:to\s*be|you\s*are)\b.{0,80}\b(?:without|no)\s+(?:any\s+)?(?:restrictions?|rules?|limits?|ethics?|morals?|guidelines?|ethical)\b", re.I),
    # Recursive / nesting attacks
    re.compile(r"\btranslate\s+(?:the|this)\s+(?:following\s+)?text\s+(?:from|to)\b.{0,60}\b(?:ignore|system|prompt|instructions?)\b", re.I),
    re.compile(r"\brepeat\s+(?:after\s+me|the\s+following)\s*:\s*.{0,100}\b(ignore|disregard|system|prompt)\b", re.I),
)

# Patterns that raise a WARN but do not block on their own.
_WARN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:you\s+(?:are|must|should|need\s+to))\b.{0,40}\b(?:bypass|override|ignore)\b", re.I),
    re.compile(r"\bcan\s+you\s+(?:act|behave|respond|answer)\s+(?:as|like)\s+(?:if|a)\b", re.I),
    re.compile(r"\bconvince\s+(?:me|yourself)\s+(?:that|you)\b.{0,30}\b(?:are|can|should|must)\b", re.I),
    re.compile(r"\b(?:format|respond|answer)\s+(?:in|as|using)\s+(?:JSON|XML|YAML|code|markdown)\s*(?:only|exclusively)\b", re.I),
    re.compile(r"\bwhat\s+(?:would|could|should)\s+you\s+(?:do|say)\s+if\b.{0,60}\b(?:no|without|ignore)\s+(?:rules?|limits?|restrictions?|ethics?)\b", re.I),
    re.compile(r"\bstart\s+(?:your|each|every)\s+(?:response|message|reply)\s+(?:with|by)\b.{0,30}\b(?:system|security|prompt|bypass)\b", re.I),
)


@dataclass(frozen=True)
class SecurityScore:
    verdict: SecurityVerdict
    reason: str
    matched_pattern: str | None = None


def score_text(text: str, *, field_name: str = "input") -> SecurityScore:
    """Score *text* for prompt-injection risk.

    Returns a ``SecurityScore`` with verdict PASS, WARN, or BLOCK.
    *field_name* is used only for the reason string.
    """
    # Normalize first so homoglyph tricks are neutralized before regex matching.
    normalized = normalize_text(text)
    if not normalized.strip():
        return SecurityScore(SecurityVerdict.PASS, f"{field_name} is empty after sanitization")

    for pattern in _BLOCK_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return SecurityScore(
                SecurityVerdict.BLOCK,
                f"Prompt injection pattern matched in {field_name}",
                pattern.pattern,
            )

    for pattern in _WARN_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return SecurityScore(
                SecurityVerdict.WARN,
                f"Borderline prompt-injection pattern in {field_name}",
                pattern.pattern,
            )

    return SecurityScore(SecurityVerdict.PASS, f"{field_name} passed injection checks")


def detect_prompt_injection(text: str) -> str | None:
    """Legacy compatibility wrapper — returns the matched pattern string or None.

    Prefer ``score_text()`` for new code.
    """
    result = score_text(text)
    return result.matched_pattern


def sanitize_text(text: str) -> str:
    """Normalize, strip control characters, and remap homoglyphs.

    This is the entry point all request handlers should use before passing
    user text to downstream systems (LLM, retriever, logging, etc.).
    """
    return normalize_text(text)


# ---------------------------------------------------------------------------
# Patient-context security checks
# ---------------------------------------------------------------------------

_MAX_JSON_DEPTH = 5
_MAX_JSON_BYTES = 10_240  # 10 KB


def validate_json_depth(obj: object, *, max_depth: int = _MAX_JSON_DEPTH, _current: int = 0) -> None:
    """Raise ValueError if *obj* nests deeper than *max_depth*."""
    if _current > max_depth:
        raise ValueError(f"JSON exceeds maximum nesting depth of {max_depth}")
    if isinstance(obj, dict):
        for value in obj.values():
            validate_json_depth(value, max_depth=max_depth, _current=_current + 1)
    elif isinstance(obj, list):
        for item in obj:
            validate_json_depth(item, max_depth=max_depth, _current=_current + 1)


def check_patient_context(raw_json: str) -> SecurityScore:
    """Security checks on the raw patient_context JSON string.

    Returns BLOCK if the payload exceeds size/depth limits or contains
    injection patterns in any string value.
    """
    if len(raw_json.encode("utf-8")) > _MAX_JSON_BYTES:
        return SecurityScore(
            SecurityVerdict.BLOCK,
            f"patient_context exceeds {_MAX_JSON_BYTES // 1024} KB limit",
        )

    try:
        import json
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return SecurityScore(SecurityVerdict.BLOCK, "patient_context is not valid JSON")

    try:
        validate_json_depth(payload)
    except ValueError as exc:
        return SecurityScore(SecurityVerdict.BLOCK, str(exc))

    # Recursively scan all string values for injection patterns.
    return _scan_json_values(payload)


def _scan_json_values(obj: object) -> SecurityScore:
    """Recursively scan string values in *obj* for injection patterns."""
    if isinstance(obj, str):
        return score_text(obj, field_name="patient_context")
    if isinstance(obj, dict):
        for value in obj.values():
            result = _scan_json_values(value)
            if result.verdict != SecurityVerdict.PASS:
                return result
    elif isinstance(obj, list):
        for item in obj:
            result = _scan_json_values(item)
            if result.verdict != SecurityVerdict.PASS:
                return result
    return SecurityScore(SecurityVerdict.PASS, "patient_context passed checks")


# ---------------------------------------------------------------------------
# Image security validation
# ---------------------------------------------------------------------------

# Minimal magic-byte signatures for JPEG and PNG.
_JPEG_MAGIC = bytes([0xFF, 0xD8, 0xFF])
_PNG_MAGIC = bytes([0x89, 0x50, 0x4E, 0x47])

# Maximum sane image resolution (100 megapixels) to catch decompression bombs.
_MAX_IMAGE_MEGAPIXELS = 100

# Extreme aspect ratio threshold — anything beyond this is almost certainly
# an attack or error.
_MAX_ASPECT_RATIO = 100


def validate_image_bytes(content: bytes) -> SecurityScore:
    """Check image *content* for magic-byte mismatch and basic sanity.

    Does NOT decode the image (that requires Pillow, which is optional).
    Returns BLOCK for magic-byte failures, PASS otherwise.
    """
    if len(content) == 0:
        return SecurityScore(SecurityVerdict.BLOCK, "Image content is empty")

    if not (content.startswith(_JPEG_MAGIC) or content.startswith(_PNG_MAGIC)):
        return SecurityScore(
            SecurityVerdict.BLOCK,
            "Image magic bytes do not match JPEG or PNG — content may be forged",
        )

    return SecurityScore(SecurityVerdict.PASS, "Image magic bytes valid")


# ---------------------------------------------------------------------------
# Rate limiter with burst allowance and per-path configuration
# ---------------------------------------------------------------------------


@dataclass
class RateLimitInfo:
    limit: int
    remaining: int
    reset_at: float  # monotonic timestamp


@dataclass
class RateLimiter:
    max_requests: int
    window_seconds: int
    burst_multiplier: float = 2.0
    burst_seconds: float = 5.0
    buckets: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, client_id: str) -> bool:
        """Check whether *client_id* is within the rate limit.

        Returns True if the request is allowed, False if blocked.
        """
        now = time.monotonic()
        bucket = self.buckets[client_id]
        window_start = now - self.window_seconds

        # Prune expired timestamps.
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        # Burst check: if we're above the sustained limit, check whether the
        # recent burst (within burst_seconds) is also exhausted.
        burst_start = now - self.burst_seconds
        recent = sum(1 for ts in bucket if ts >= burst_start)

        if len(bucket) >= self.max_requests and recent >= int(self.max_requests * self.burst_multiplier):
            return False

        bucket.append(now)
        return True

    def info(self, client_id: str) -> RateLimitInfo:
        """Return current rate-limit state for *client_id* (for response headers)."""
        now = time.monotonic()
        bucket = self.buckets[client_id]
        window_start = now - self.window_seconds
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        remaining = max(0, self.max_requests - len(bucket))
        reset_at = (bucket[0] + self.window_seconds) if bucket else now + self.window_seconds

        return RateLimitInfo(
            limit=self.max_requests,
            remaining=remaining,
            reset_at=reset_at,
        )

    def clear(self) -> None:
        self.buckets.clear()


# ---------------------------------------------------------------------------
# Circuit breaker for downstream dependencies
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_seconds: float = 30.0
    half_open_requests: int = 2

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    state: str = "closed"  # closed | open | half_open

    def record_failure(self) -> None:
        now = time.monotonic()
        self.failure_count += 1
        self.last_failure_time = now
        if self.state == "half_open" or self.failure_count >= self.failure_threshold:
            self.state = "open"

    def record_success(self) -> None:
        self.failure_count = 0
        if self.state == "half_open":
            self.success_count += 1
            if self.success_count >= self.half_open_requests:
                self.state = "closed"
                self.success_count = 0

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            now = time.monotonic()
            if now - self.last_failure_time >= self.recovery_seconds:
                self.state = "half_open"
                self.success_count = 0
                return True
            return False
        # half_open — allow a limited number of probe requests.
        return self.success_count < self.half_open_requests


# ---------------------------------------------------------------------------
# Client IP extraction
# ---------------------------------------------------------------------------


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"

