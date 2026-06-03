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


def classify_text(symptoms: str, patient_context: PatientContext | None) -> TriageResult:
    text = symptoms.lower()
    urgency = _select_urgency(text)

    if urgency == "Emergency":
        rationale = (
            "The symptom description includes red-flag language that should be treated "
            "as potentially time-sensitive in this scaffold."
        )
        confidence = "high"
    elif urgency == "Urgent":
        rationale = (
            "The symptom description includes features that may need prompt clinical "
            "review, but this scaffold does not diagnose or prescribe."
        )
        confidence = "medium"
    elif urgency == "Self-Care":
        rationale = (
            "The symptom description appears mild in this deterministic scaffold. "
            "Escalate if symptoms worsen or new red flags appear."
        )
        confidence = "low"
    else:
        rationale = (
            "No emergency red flags were detected by the scaffold rules. A routine "
            "clinical review may still be appropriate depending on context."
        )
        confidence = "medium"

    if patient_context and patient_context.age is not None and patient_context.age >= 65:
        rationale += " Age over 65 was noted as a factor for lower threshold review."

    return TriageResult(
        urgency=urgency,
        rationale=rationale,
        confidence=confidence,
        sources=["Aegis-MD scaffold triage rules"],
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

