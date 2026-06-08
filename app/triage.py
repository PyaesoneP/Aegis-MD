from app.llm import LLMError, rag_response, vision_response
from app.config import get_settings
from app.models import PatientContext, TriageResult, Urgency, VisionResult


DISCLAIMER = (
    "This is a research prototype, not a substitute for professional medical advice."
)

EMERGENCY_TERMS = (
    "chest pain",
    "shortness of breath",
    "severe bleeding",
    "stroke",
    "unconscious",
    "seizure",
    "suicidal",
    "anaphylaxis",
)

URGENT_TERMS = (
    "fever",
    "infection",
    "worsening",
    "severe pain",
    "persistent vomiting",
    "dehydration",
    "new rash",
)

SELF_CARE_TERMS = (
    "mild cough",
    "runny nose",
    "minor headache",
    "small bruise",
    "sore throat",
)

URGENCY_RANK: dict[Urgency, int] = {
    "Self-Care": 0,
    "Routine": 1,
    "Urgent": 2,
    "Emergency": 3,
}


def classify_text(
    symptoms: str,
    patient_context: PatientContext | None = None,
    vision_result: VisionResult | None = None,
) -> TriageResult:
    text = symptoms.lower()
    rule_urgency = _select_urgency(text)

    vision_findings: str | None = None
    if vision_result is not None:
        parts = [f"Risk: {vision_result.risk}"]
        if vision_result.rationale:
            parts.append(f"Findings: {vision_result.rationale}")
        if vision_result.confidence is not None:
            parts.append(f"Confidence: {vision_result.confidence:.2f}")
        vision_findings = "\n".join(parts)

    # ── Tier 1: Full RAG (retrieval + LLM); Tier 2: LLM-only (no retrieval);
    #     Tier 3: Rule-based fallback (no LLM at all) ─────────────────
    try:
        rag_result = rag_response(
            symptoms,
            patient_context=patient_context,
            rule_urgency=rule_urgency,
            vision_findings=vision_findings,
        )
    except LLMError:
        return _rule_based_result(rule_urgency, patient_context)

    urgency = _highest_urgency(rule_urgency, rag_result.urgency)
    rationale = rag_result.rationale

    if urgency != rag_result.urgency:
        rationale += (
            f" Local triage safeguards raised the final urgency from "
            f"{rag_result.urgency} to {urgency}."
        )

    if patient_context and patient_context.age is not None and patient_context.age >= 65:
        rationale += " Age over 65 was noted as a factor for lower threshold review."

    return TriageResult(
        urgency=urgency,
        rationale=rationale,
        confidence=rag_result.confidence,
        sources=rag_result.sources,
        disclaimer=DISCLAIMER,
    )


def classify_vision(
    image_bytes: bytes,
    patient_context: PatientContext | None = None,
) -> VisionResult | None:
    """Run MedGemma multimodal analysis on the uploaded image.

    Returns None when no image is provided.  Degrades gracefully when
    vision is disabled or inference fails so the triage endpoint remains
    available.
    """
    settings = get_settings()
    if not image_bytes:
        return None
    if not settings.vision_enabled:
        return VisionResult(
            risk="insufficient confidence",
            confidence=None,
            rationale="Vision model is not yet deployed — placeholder mode active.",
        )
    try:
        return vision_response(image_bytes, patient_context=patient_context)
    except LLMError:
        return VisionResult(
            risk="insufficient confidence",
            confidence=None,
            rationale="Vision model inference failed — check model compatibility.",
        )


def _select_urgency(text: str) -> Urgency:
    if any(term in text for term in EMERGENCY_TERMS):
        return "Emergency"
    if any(term in text for term in URGENT_TERMS):
        return "Urgent"
    if any(term in text for term in SELF_CARE_TERMS):
        return "Self-Care"
    return "Routine"


def _highest_urgency(first: Urgency, second: Urgency) -> Urgency:
    return first if URGENCY_RANK[first] >= URGENCY_RANK[second] else second


# ── Vision → Urgency mapping for parallel text+vision merge ──────────
_VISION_TO_URGENCY: dict[str, Urgency | None] = {
    "High-Risk": "Emergency",
    "Low-Risk": "Routine",
    "insufficient confidence": None,  # don't affect text urgency
}


def _vision_risk_to_urgency(risk: str) -> Urgency | None:
    """Map a vision risk tier to a text triage urgency level.

    Returns None when the vision result should not influence urgency
    (e.g. insufficient confidence).
    """
    return _VISION_TO_URGENCY.get(risk)


def merge_triage_results(
    text_result: TriageResult,
    vision_result: VisionResult,
) -> TriageResult:
    """Merge parallel text triage and vision results into a single assessment.

    Urgency is the maximum of the text classification and the vision risk
    tier mapped to urgency.  The rationale is structured with clearly
    labelled sections — no LLM rewrites, so zero hallucination risk.
    """
    vision_urgency = _vision_risk_to_urgency(vision_result.risk)
    urgency = text_result.urgency
    if vision_urgency is not None:
        urgency = _highest_urgency(text_result.urgency, vision_urgency)

    conf_str = (
        f"{vision_result.confidence:.0%}"
        if vision_result.confidence is not None
        else "N/A"
    )

    # ── Structured rationale: labelled sections, no LLM rewriting ────
    sections: list[str] = []

    # Text-based assessment (LLM + RAG)
    sections.append(text_result.rationale)

    # Image findings (vision model, verbatim)
    if vision_result.rationale:
        sections.append(
            f"Image findings: {vision_result.rationale} "
            f"(risk: {vision_result.risk}, confidence: {conf_str})"
        )

    # Combined urgency summary
    if urgency != text_result.urgency:
        sections.append(
            f"Overall urgency elevated to {urgency} (from "
            f"{text_result.urgency}) — image analysis revealed "
            f"{vision_result.risk.lower().replace('-', ' ')} findings."
        )
    elif vision_result.risk == "insufficient confidence":
        sections.append(
            f"Overall urgency: {urgency} — image analysis was inconclusive "
            f"and did not modify the text-based assessment."
        )
    else:
        sections.append(
            f"Overall urgency: {urgency} — consistent across both assessments."
        )

    rationale = "\n\n".join(sections)

    return TriageResult(
        urgency=urgency,
        rationale=rationale,
        confidence=text_result.confidence,
        sources=text_result.sources,
        disclaimer=text_result.disclaimer,
    )


def _rule_based_result(
    rule_urgency: Urgency,
    patient_context: PatientContext | None = None,
) -> TriageResult:
    """Fallback result when LLM is entirely unavailable (Tier 3 degradation).

    Returns a rule-based triage assessment using keyword matching only,
    with an explicit warning that LLM inference was unavailable.
    """
    rationale = (
        f"Rule-based urgency classification (LLM unavailable): "
        f"symptoms matched the '{rule_urgency}' keyword tier. "
        "No guideline citations or AI-generated rationale are available. "
        "This is a degraded assessment — seek professional medical evaluation."
    )
    if patient_context and patient_context.age is not None and patient_context.age >= 65:
        rationale += " Age over 65 was noted as a factor for lower threshold review."

    return TriageResult(
        urgency=rule_urgency,
        rationale=rationale,
        confidence="low",
        sources=["rule-based fallback — LLM unavailable"],
        disclaimer=DISCLAIMER,
    )
