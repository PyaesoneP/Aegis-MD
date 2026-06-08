import base64
import concurrent.futures
import json
import re
import time
from dataclasses import dataclass
from typing import Any, get_args

from app.config import get_settings
from app.models import (
    ATSCategory,
    ComorbidityFlags,
    Confidence,
    PatientContext,
    TriageInput,
    Vitals,
    VisionResult,
)
from app.retriever import RetrievedGuideline, retrieve_relevant_guidelines

# ── Retry / timeout configuration ────────────────────────────────────
_LLM_TIMEOUT_SECONDS = 120       # per-call timeout for Ollama chat
_LLM_MAX_RETRIES = 2             # retry count (total attempts = 1 + retries)
_LLM_RETRY_BACKOFF = 1.5         # multiplier for exponential backoff


class LLMError(RuntimeError):
    """Raised when the Ollama triage model cannot produce a valid response."""


@dataclass(frozen=True)
class RagResponse:
    ats_category: ATSCategory
    rationale: str
    confidence: Confidence
    sources: list[str]


SYSTEM_PROMPT = """
You are Aegis-MD, an Emergency Department triage assistant.

Classify urgency using the Australasian Triage Scale (ATS 1-5).
Do not diagnose. Do not prescribe treatment. Do not recommend disposition.

You will receive structured ED triage data: chief complaint, vitals (HR, RR,
SpO2, Temp, BP), age, sex, pain score, onset, arrival mode, consciousness
(AVPU), mechanism (if trauma), comorbidities, pregnancy status, and allergies.

Return JSON only, with exactly these keys:
ats_category, rationale, confidence.

ats_category must be one of: ATS-1, ATS-2, ATS-3, ATS-4, ATS-5.
confidence must be one of: low, medium, high.

The rationale must be brief, safety-focused, reference specific vitals or
clinical features that drove the category decision, and cite guideline chunks
using [1], [2], etc.

ATS category definitions (Australasian Triage Scale):
- ATS-1 (Resuscitation): Immediately life-threatening — cardiac arrest,
  airway obstruction, severe respiratory distress, unresponsive, major
  multi-trauma, shock. Time target: immediate.
- ATS-2 (Emergency): Imminently life-threatening — chest pain suggestive of
  ACS, severe pain (8+/10), altered consciousness (P on AVPU), major
  fracture, stroke symptoms, anaphylaxis, severe asthma. Time target: 10 min.
- ATS-3 (Urgent): Potentially life-threatening — moderate pain (4-7/10),
  mild-moderate respiratory distress, febrile illness with comorbidities,
  minor head injury with normal consciousness, GI bleeding (stable).
  Time target: 30 min.
- ATS-4 (Semi-urgent): Less urgent — minor pain (1-3/10), minor trauma
  (sprains, small lacerations), earache, UTI symptoms, mild fever without
  comorbidities, normal vital signs, suture removal, wound check.
  Key rule: if all vitals are normal AND pain ≤ 3/10 AND ambulatory AND
  no red-flag features, classify as ATS-4. Time target: 60 min.
- ATS-5 (Non-urgent): Minimal or no urgency — minor symptoms only,
  medication refill, chronic condition review, minor rash no systemic
  symptoms, medical certificate, suture removal, wound check, dressing
  change. Key rule: if pain = 0 AND vitals normal AND no acute symptoms
  AND the reason for visit is administrative or follow-up (suture removal,
  certificate, prescription refill), classify as ATS-5.
  Time target: 120 min.

Key vitals thresholds for escalation:
- HR > 120 or HR < 50 bpm: consider ATS-2 or higher.
- RR > 30 or RR < 10 /min: consider ATS-2 or higher.
- SpO2 < 92% on room air: consider ATS-2 or higher.
- Temp > 39.0C or Temp < 35.0C: consider ATS-2 or higher with comorbidities.
- Systolic BP < 90 mmHg: consider ATS-1 or ATS-2.
- Systolic BP > 200 mmHg or Diastolic BP > 120 mmHg: consider ATS-2.

Age > 65 and comorbidities (cardiac, respiratory, DM, renal, immunocompromised,
anticoagulants) lower the threshold for escalation by one ATS level.
Pregnancy is a risk modifier — lower the threshold by one level for any
abdominal pain, bleeding, or trauma presentation.

Arrival by ambulance or stretcher is a proxy for higher acuity.
Consciousness below Alert on AVPU warrants at least ATS-2.

CRITICAL — anti-hallucination rules:
- Only cite a guideline chunk if it directly addresses a symptom or finding
  the patient actually presented with.
- Never introduce symptoms, conditions, or findings not stated in the input.
- If no retrieved guideline is directly relevant, write a concise assessment
  based on vitals, pain score, and clinical features. Explain why the
  combination maps to that ATS level. Do not simply state no guidelines matched.

When image analysis findings are present, reference them directly without
reinterpreting or inventing visual details not stated in the findings.
""".strip()

ATS_VALUES = set(get_args(ATSCategory))
CONFIDENCE_VALUES = set(get_args(Confidence))


def rag_response(
    triage_input: TriageInput,
    rule_ats: ATSCategory | None = None,
    vision_findings: str | None = None,
) -> RagResponse:
    settings = get_settings()

    # ── Tier-1 retrieval (may fail gracefully) ───────────────────────
    retrieval_query = _build_retrieval_query(triage_input)
    try:
        guidelines = retrieve_relevant_guidelines(
            query=retrieval_query,
            top_k=settings.retrieval_top_k,
        )
    except Exception:
        guidelines = []  # proceed without retrieval context

    raw_content = _chat_with_ollama(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    triage_input=triage_input,
                    rule_ats=rule_ats,
                    guidelines=guidelines,
                    vision_findings=vision_findings,
                ),
            },
        ],
    )
    payload = _parse_json_payload(raw_content)

    return RagResponse(
        ats_category=_normalize_ats_category(payload.get("ats_category")),
        rationale=_require_text(payload.get("rationale"), "rationale"),
        confidence=_normalize_confidence(payload.get("confidence")),
        sources=(
            [guideline.citation for guideline in guidelines]
            if guidelines
            else ["retrieval unavailable — LLM-only assessment"]
        ),
    )


def _build_retrieval_query(triage_input: TriageInput) -> str:
    """Build a dense query string for the retriever from structured ED fields."""
    parts = [triage_input.chief_complaint]
    if triage_input.mechanism:
        parts.append(f"mechanism: {triage_input.mechanism}")
    return " ".join(parts)


def _build_user_prompt(
    *,
    triage_input: TriageInput,
    rule_ats: ATSCategory | None,
    guidelines: list[RetrievedGuideline],
    vision_findings: str | None = None,
) -> str:
    """Format all ED triage fields as structured sections for the LLM."""
    sections: list[str] = []

    # ── Chief complaint ─────────────────────────────────────────────
    sections.append(f"Chief complaint:\n{triage_input.chief_complaint}")

    # ── Vitals (structured with reference ranges) ────────────────────
    vitals = triage_input.vitals
    vitals_lines = _format_vitals(vitals, triage_input.age)
    sections.append(f"Vitals:\n{vitals_lines}")

    # ── Vitals normality signal (suppressed for elderly + comorbidities) ──
    has_coms = any(
        getattr(triage_input.comorbidities, attr, False)
        for attr in (
            "cardiac_disease", "diabetes_mellitus", "respiratory_disease",
            "immunocompromised", "anticoagulants", "renal_disease",
        )
    )
    normality = _vitals_normality_note(
        vitals, age=triage_input.age, has_comorbidities=has_coms,
    )
    if normality:
        sections.append(normality)

    # ── Patient demographics ─────────────────────────────────────────
    sections.append(
        f"Age: {triage_input.age}  |  Sex: {triage_input.sex}  |  "
        f"Pain score: {triage_input.pain_score}/10"
    )

    # ── Contextual fields ────────────────────────────────────────────
    context_parts: list[str] = []
    if triage_input.onset:
        context_parts.append(f"Onset: {triage_input.onset}")
    if triage_input.arrival_mode:
        context_parts.append(f"Arrival mode: {triage_input.arrival_mode}")
    if triage_input.consciousness:
        context_parts.append(f"Consciousness (AVPU): {triage_input.consciousness}")
    if triage_input.mechanism:
        context_parts.append(f"Mechanism: {triage_input.mechanism}")
    if context_parts:
        sections.append("Clinical context:\n" + "\n".join(context_parts))

    # ── Risk modifiers ───────────────────────────────────────────────
    modifiers = _format_comorbidities(triage_input.comorbidities)
    if triage_input.pregnancy:
        modifiers.append(f"Pregnancy: {triage_input.pregnancy}")
    if triage_input.allergies:
        modifiers.append(f"Known allergies: {triage_input.allergies}")
    if modifiers:
        sections.append("Risk modifiers:\n" + "\n".join(modifiers))

    # ── Rule-based prior ─────────────────────────────────────────────
    sections.append(
        f"Rule-based ATS prior (from keyword matching — may be overridden): "
        f"{rule_ats or 'Not determined'}"
    )

    # ── Retrieved guidelines ─────────────────────────────────────────
    guideline_text: str
    if guidelines:
        guideline_text = "\n\n".join(
            f"[{index}] {guideline.content}\nSource: {guideline.citation}"
            for index, guideline in enumerate(guidelines, start=1)
        )
    else:
        guideline_text = (
            "No relevant guideline chunks were retrieved — "
            "assess urgency from vitals, pain score, and clinical features alone."
        )
    sections.append(
        f"Retrieved guideline chunks (only cite if directly relevant "
        f"to the stated presenting features — do not apply unrelated guidelines):\n"
        f"{guideline_text}"
    )

    prompt = "\n\n".join(sections)

    # ── Vision findings (appended verbatim, no LLM rewriting) ────────
    if vision_findings:
        prompt += (
            f"\n\nImage analysis findings (produced by a separate vision model — "
            f"reference verbatim, do not re-describe the image):\n{vision_findings}"
        )

    return prompt


def _format_vitals(vitals: Vitals, age: int) -> str:
    """Format vitals with age-appropriate normal reference ranges."""
    lines: list[str] = []

    def _fmt(name: str, value: int | float | None, unit: str, norm: str) -> str:
        if value is not None:
            return f"  {name}: {value} {unit}  (normal: {norm})"
        return f"  {name}: not recorded  (normal: {norm})"

    lines.append(_fmt("HR", vitals.hr, "bpm", "60-100 bpm"))
    lines.append(_fmt("RR", vitals.rr, "/min", "12-20 /min"))
    lines.append(_fmt("SpO2", vitals.spo2, "%", ">=95%"))
    lines.append(_fmt("Temp", vitals.temp, "C", "36.1-37.2C"))
    lines.append(_fmt("Systolic BP", vitals.bp_systolic, "mmHg", "100-140 mmHg"))
    lines.append(_fmt("Diastolic BP", vitals.bp_diastolic, "mmHg", "60-90 mmHg"))

    if age < 18:
        lines.append("  Note: patient is pediatric — age-adjusted vitals ranges apply.")

    return "\n".join(lines)


def _vitals_normality_note(
    vitals: Vitals,
    age: int = 0,
    has_comorbidities: bool = False,
) -> str | None:
    """Return a note if ALL recorded vitals are within normal adult ranges.

    Suppressed when age ≥ 65 with comorbidities — normal vitals in an
    elderly anticoagulated patient with head injury do not mean low acuity.
    """
    # ── Safety carve-out: elderly + risk modifiers ──────────────────
    if age >= 65 and has_comorbidities:
        return None

    recorded: list[bool] = []
    normal: int = 0

    def _check(value: int | float | None, lo: float, hi: float) -> bool:
        if value is None:
            return True
        nonlocal normal
        normal += 1
        return lo <= value <= hi

    hr_ok = _check(vitals.hr, 60, 100)
    rr_ok = _check(vitals.rr, 12, 20)
    spo2_ok = _check(vitals.spo2, 95, 100)
    temp_ok = _check(vitals.temp, 36.1, 37.2)
    sys_ok = _check(vitals.bp_systolic, 100, 140)
    dia_ok = _check(vitals.bp_diastolic, 60, 90)

    recorded.append(hr_ok)
    recorded.append(rr_ok)
    recorded.append(spo2_ok)
    recorded.append(temp_ok)
    recorded.append(sys_ok)
    recorded.append(dia_ok)

    if all(recorded) and normal >= 3:
        return (
            "VITALS NORMALITY: All recorded vital signs are within normal "
            "adult ranges. Combined with a minor chief complaint and no "
            "red-flag features, this strongly supports ATS-4 (Semi-urgent) "
            "or ATS-5 (Non-urgent) rather than ATS-3. Do NOT default to "
            "ATS-3 when vitals are normal and the presentation is minor."
        )

    return None


def _format_comorbidities(coms: ComorbidityFlags) -> list[str]:
    """Return list of active comorbidity flags for the prompt."""
    active: list[str] = []
    mapping = [
        ("cardiac_disease", "Cardiac disease"),
        ("diabetes_mellitus", "Diabetes mellitus"),
        ("respiratory_disease", "Respiratory disease"),
        ("immunocompromised", "Immunocompromised"),
        ("anticoagulants", "Anticoagulants"),
        ("renal_disease", "Renal disease"),
    ]
    for attr, label in mapping:
        if getattr(coms, attr, False):
            active.append(f"  - {label}")
    return active


def _format_patient_context(patient_context: PatientContext | None) -> str:
    if patient_context is None:
        return "Not provided"

    values: list[str] = []
    if patient_context.age is not None:
        values.append(f"age={patient_context.age}")
    if patient_context.sex is not None:
        values.append(f"sex={patient_context.sex}")
    return ", ".join(values) if values else "Not provided"


def _chat_with_ollama(
    model: str,
    messages: list[dict[str, str]],
    images: list[str] | None = None,
) -> str:
    try:
        from ollama import chat as ollama_chat
    except ImportError as exc:
        raise LLMError("The Ollama Python package is not installed.") from exc

    # Embed images in the last message dict (ollama Python client 0.6.x API)
    if images:
        messages = [dict(m) for m in messages]  # shallow copy
        messages[-1]["images"] = images

    last_exc: Exception | None = None
    for attempt in range(_LLM_MAX_RETRIES + 1):
        try:
            return _call_ollama_with_timeout(
                ollama_chat, model, messages, images
            )
        except LLMError:
            raise  # non-transient — propagate immediately
        except Exception as exc:
            last_exc = exc
            if attempt < _LLM_MAX_RETRIES:
                delay = _LLM_RETRY_BACKOFF ** attempt
                time.sleep(delay)
                continue

    raise LLMError(
        f"Ollama chat request failed after {_LLM_MAX_RETRIES + 1} attempts."
    ) from last_exc


def _call_ollama_with_timeout(
    ollama_chat,
    model: str,
    messages: list[dict[str, str]],
    images: list[str] | None,
) -> str:
    """Execute the blocking ollama.chat() call with a timeout guard."""

    def _do_chat():
        return ollama_chat(
            model=model,
            messages=messages,
            format="json",
            options={"temperature": 0, "num_predict": 256},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do_chat)
        try:
            response = future.result(timeout=_LLM_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise LLMError(
                f"Ollama chat request timed out after {_LLM_TIMEOUT_SECONDS}s."
            )

    content = _extract_message_content(response)
    if not content:
        raise LLMError("Ollama returned an empty response.")
    return content


def _extract_message_content(response: Any) -> str:
    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", ""))

    message = getattr(response, "message", None)
    if isinstance(message, dict):
        return str(message.get("content", ""))
    if message is not None and hasattr(message, "content"):
        return str(message.content)

    return ""


def _parse_json_payload(raw_content: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError:
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start == -1 or end == -1 or start >= end:
            raise LLMError("Ollama response was not valid JSON.")
        try:
            payload = json.loads(raw_content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("Ollama response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise LLMError("Ollama response JSON must be an object.")
    return payload


def _require_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise LLMError(f"Ollama response missing required field '{field_name}'.")
    return text


def _normalize_ats_category(value: Any) -> ATSCategory:
    text = str(value or "").strip().upper()
    # Accept both "ATS-1" and "1" formats.
    match = re.search(r"(?:ATS[\s-]*)?([1-5])", text)
    if match:
        category = f"ATS-{match.group(1)}"
        if category in ATS_VALUES:
            return category
    raise LLMError(
        f"Ollama response contained an invalid ATS category: '{text}'. "
        f"Expected one of ATS-1 through ATS-5."
    )


def _normalize_confidence(value: Any) -> Confidence:
    confidence = str(value or "").strip().lower()
    if confidence not in CONFIDENCE_VALUES:
        raise LLMError("Ollama response contained an invalid confidence.")
    return confidence


def vision_response(
    image_bytes: bytes,
    patient_context: PatientContext | None = None,
) -> VisionResult:
    """Run MedGemma multimodal inference on a medical image.

    Encodes the image as base64, sends it alongside a text prompt to the
    same Ollama model used for text triage, and parses the JSON response.
    """
    settings = get_settings()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    patient_context_text = _format_patient_context(patient_context)

    user_prompt = (
        f"Analyze the attached medical image.\n\n"
        f"Patient context: {patient_context_text}"
    )

    raw_content = _chat_with_ollama(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": settings.vision_system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        images=[image_b64],
    )
    payload = _parse_json_payload(raw_content)

    risk = _normalize_vision_risk(payload.get("risk"))
    confidence = _normalize_vision_confidence(payload.get("confidence"))
    rationale = _require_text(payload.get("rationale"), "rationale")

    return VisionResult(risk=risk, confidence=confidence, rationale=rationale)


def _normalize_vision_risk(value: Any) -> str:
    text = str(value or "").strip()
    normalized = text.lower().replace("_", "-")
    aliases = {
        "high-risk": "High-Risk",
        "high risk": "High-Risk",
        "low-risk": "Low-Risk",
        "low risk": "Low-Risk",
        "insufficient confidence": "insufficient confidence",
        "insufficient": "insufficient confidence",
        "uncertain": "insufficient confidence",
    }
    risk = aliases.get(normalized, text)
    if risk not in {"High-Risk", "Low-Risk", "insufficient confidence"}:
        raise LLMError("Ollama response contained an invalid vision risk.")
    return risk


def _normalize_vision_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        raise LLMError("Ollama response contained an invalid vision confidence.")
    if not (0 <= confidence <= 1):
        raise LLMError("Vision confidence must be between 0 and 1.")
    return confidence
