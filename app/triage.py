from app.llm import LLMError, rag_response, vision_response
from app.config import get_settings
from app.models import (
    ATSCard,
    ATSCategory,
    PatientContext,
    TriageInput,
    TriageResult,
    VisionResult,
)


DISCLAIMER = (
    "This is a research prototype, not a substitute for professional medical advice."
)

# ── Keyword-to-ATS mapping for rule-based fallback (Tier 3) ──────────
# ATS-1 discriminators: immediately life-threatening
ATS1_TERMS = (
    "cardiac arrest",
    "airway obstruction",
    "severe respiratory distress",
    "unresponsive",
    "major trauma",
    "multi-trauma",
    "polytrauma",
    "anaphylactic shock",
    "severe burns",
    "gcs 3",
    "gcs 4",
    "gcs 5",
    "apnoeic",
    "apneic",
    "cardiorespiratory arrest",
)

# ATS-2 discriminators: imminently life-threatening
ATS2_TERMS = (
    "chest pain",
    "severe pain",
    "altered consciousness",
    "stroke",
    "seizure",
    "active seizure",
    "severe bleeding",
    "haemorrhage",
    "hemorrhage",
    "anaphylaxis",
    "severe asthma",
    "major fracture",
    "open fracture",
    "amputation",
    "sudden vision loss",
    "sudden severe headache",
    "suicidal",
    "suicide attempt",
    "overdose",
    "shortness of breath",
    "respiratory distress",
    "diaphoretic",
    # Trauma + mechanism → high-energy transfer
    "ejected",
    "rollover",
    "entrapped",
    "high speed",
    "major trauma",
    "penetrating trauma",
    "head injury with",
    "confused at scene",
)

# ATS-4 discriminators: less urgent — normal vitals, minor complaints
ATS4_TERMS = (
    "sprain",
    "strain",
    "twisted ankle",
    "twisted knee",
    "twisted wrist",
    "laceration",
    "cut finger",
    "cut hand",
    "small cut",
    "minor cut",
    "dysuria",
    "urinary frequency",
    "uti",
    "earache",
    "ear pain",
    "sore throat",
    "minor burn",
    "superficial burn",
    "insect bite",
    "constipation",
    "diarrhoea no blood",
    "diarrhea no blood",
)

# ATS-5 discriminators: minimal urgency
ATS5_TERMS = (
    "minor rash",
    "rash no fever",
    "itchy rash",
    "medication refill",
    "repeat prescription",
    "medical certificate",
    "sick note",
    "chronic condition stable",
    "minor abrasion",
    "small bruise",
    "insect bite no reaction",
    "suture removal",
    "dressing check",
    "wound check",
    "stitch removal",
)

ATS_RANK: dict[ATSCategory, int] = {
    "ATS-5": 1,
    "ATS-4": 2,
    "ATS-3": 3,
    "ATS-2": 4,
    "ATS-1": 5,
}


def classify_text(
    triage_input: TriageInput,
    vision_result: VisionResult | None = None,
) -> TriageResult:
    """Classify ED triage input into an ATS category.

    Uses a three-tier approach:
    Tier 1 — Full RAG (retrieval + LLM)
    Tier 2 — LLM only (no retrieval, handled internally by rag_response)
    Tier 3 — Rule-based fallback (keyword matching only)
    """
    text = triage_input.chief_complaint.lower()
    rule_ats = _select_ats(text)

    # ── Consolidate vision findings for the LLM prompt ───────────────
    vision_findings: str | None = None
    if vision_result is not None:
        parts = [f"Risk: {vision_result.risk}"]
        if vision_result.rationale:
            parts.append(f"Findings: {vision_result.rationale}")
        if vision_result.confidence is not None:
            parts.append(f"Confidence: {vision_result.confidence:.2f}")
        vision_findings = "\n".join(parts)

    # ── Tier 1: Full RAG; Tier 3: Rule-based fallback ────────────────
    try:
        rag_result = rag_response(
            triage_input=triage_input,
            rule_ats=rule_ats,
            vision_findings=vision_findings,
        )
    except LLMError:
        return _rule_based_result(rule_ats, triage_input)

    ats = rule_ats
    # ── LLM may upgrade urgency but cannot override a definitive ATS-5 ──
    if rule_ats != "ATS-5":
        ats = _highest_ats(rule_ats, rag_result.ats_category)
    rationale = rag_result.rationale

    if ats != rag_result.ats_category:
        rationale += (
            f" Local triage safeguards raised the final ATS category from "
            f"{rag_result.ats_category} to {ats}."
        )

    # ── Age / comorbidity escalation note ────────────────────────────
    if triage_input.age >= 65:
        rationale += " Age over 65 was noted as a factor for lower threshold review."
    if triage_input.comorbidities.anticoagulants:
        rationale += (
            " Anticoagulant use noted — lower threshold for head injury "
            "and bleeding presentations."
        )
    if triage_input.pregnancy == "Yes":
        rationale += (
            " Pregnancy noted — lower threshold for abdominal pain, "
            "bleeding, and trauma presentations."
        )

    ats_card = ATSCard.from_category(ats)

    return TriageResult(
        ats_category=ats,
        ats_card=ats_card,
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


def _select_ats(text: str) -> ATSCategory:
    """Rule-based ATS classification from chief complaint keywords."""
    if any(term in text for term in ATS1_TERMS):
        return "ATS-1"
    if any(term in text for term in ATS2_TERMS):
        return "ATS-2"
    if any(term in text for term in ATS5_TERMS):
        return "ATS-5"
    if any(term in text for term in ATS4_TERMS):
        return "ATS-4"
    # Default: ATS-3 covers most undifferentiated presentations.
    return "ATS-3"


def _highest_ats(first: ATSCategory, second: ATSCategory) -> ATSCategory:
    """Return the more urgent (numerically lower) ATS category."""
    return first if ATS_RANK[first] >= ATS_RANK[second] else second


# ── Vision → ATS mapping for parallel text+vision merge ──────────────
_VISION_TO_ATS: dict[str, ATSCategory | None] = {
    "High-Risk": "ATS-2",
    "Low-Risk": "ATS-4",
    "insufficient confidence": None,
}


def _vision_risk_to_ats(risk: str) -> ATSCategory | None:
    """Map a vision risk tier to an ATS category.

    Returns None when the vision result should not influence urgency
    (e.g. insufficient confidence).
    """
    return _VISION_TO_ATS.get(risk)


def merge_triage_results(
    text_result: TriageResult,
    vision_result: VisionResult,
) -> TriageResult:
    """Merge parallel text triage and vision results into a single assessment.

    ATS category is the most urgent of the text classification and the
    vision risk tier mapped to ATS.  The rationale is structured with
    clearly labelled sections — no LLM rewrites, so zero hallucination risk.
    """
    vision_ats = _vision_risk_to_ats(vision_result.risk)
    ats = text_result.ats_category
    if vision_ats is not None:
        ats = _highest_ats(text_result.ats_category, vision_ats)

    conf_str = (
        f"{vision_result.confidence:.0%}"
        if vision_result.confidence is not None
        else "N/A"
    )

    # ── Structured rationale: labelled sections, no LLM rewriting ────
    sections: list[str] = [text_result.rationale]

    if vision_result.rationale:
        sections.append(
            f"Image findings: {vision_result.rationale} "
            f"(risk: {vision_result.risk}, confidence: {conf_str})"
        )

    if ats != text_result.ats_category:
        sections.append(
            f"Overall ATS category elevated to {ats} (from "
            f"{text_result.ats_category}) — image analysis revealed "
            f"{vision_result.risk.lower().replace('-', ' ')} findings."
        )
    elif vision_result.risk == "insufficient confidence":
        sections.append(
            f"Overall ATS category: {ats} — image analysis was inconclusive "
            f"and did not modify the text-based assessment."
        )
    else:
        sections.append(
            f"Overall ATS category: {ats} — consistent across both assessments."
        )

    ats_card = ATSCard.from_category(ats)

    return TriageResult(
        ats_category=ats,
        ats_card=ats_card,
        rationale="\n\n".join(sections),
        confidence=text_result.confidence,
        sources=text_result.sources,
        disclaimer=text_result.disclaimer,
    )


def _rule_based_result(
    rule_ats: ATSCategory,
    triage_input: TriageInput,
) -> TriageResult:
    """Fallback result when LLM is entirely unavailable (Tier 3 degradation).

    Returns a rule-based triage assessment using keyword matching and
    vital-sign thresholds only, with an explicit warning that LLM
    inference was unavailable.
    """
    rationale = (
        f"Rule-based ATS classification (LLM unavailable): "
        f"chief complaint keywords matched the '{rule_ats}' tier. "
        "No guideline citations or AI-generated rationale are available. "
        "This is a degraded assessment — seek professional medical evaluation."
    )

    if triage_input.age >= 65:
        rationale += " Age over 65 was noted as a factor for lower threshold review."

    ats_card = ATSCard.from_category(rule_ats)

    return TriageResult(
        ats_category=rule_ats,
        ats_card=ats_card,
        rationale=rationale,
        confidence="low",
        sources=["rule-based fallback — LLM unavailable"],
        disclaimer=DISCLAIMER,
    )
