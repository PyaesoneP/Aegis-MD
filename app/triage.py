from app.llm import rag_response
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


def classify_text(symptoms: str, patient_context: PatientContext | None) -> TriageResult:
    text = symptoms.lower()
    rule_urgency = _select_urgency(text)
    rag_result = rag_response(
        symptoms,
        patient_context=patient_context,
        rule_urgency=rule_urgency,
    )
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


def build_vision_placeholder(has_image: bool) -> VisionResult | None:
    if not has_image:
        return None
    return VisionResult(
        risk="insufficient confidence",
        confidence=None,
        rationale="Vision model inference is not wired in this functional scaffold.",
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
