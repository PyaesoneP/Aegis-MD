from typing import Literal

from pydantic import BaseModel, Field


# ── ATS Triage Categories (Australasian Triage Scale) ─────────────────
ATSCategory = Literal["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"]

ATS_LABELS: dict[ATSCategory, str] = {
    "ATS-1": "Resuscitation",
    "ATS-2": "Emergency",
    "ATS-3": "Urgent",
    "ATS-4": "Semi-urgent",
    "ATS-5": "Non-urgent",
}

ATS_TIMES: dict[ATSCategory, int] = {
    "ATS-1": 0,
    "ATS-2": 10,
    "ATS-3": 30,
    "ATS-4": 60,
    "ATS-5": 120,
}

ATS_COLORS: dict[ATSCategory, str] = {
    "ATS-1": "#dc2626",
    "ATS-2": "#ea580c",
    "ATS-3": "#d97706",
    "ATS-4": "#059669",
    "ATS-5": "#2563eb",
}

Confidence = Literal["low", "medium", "high"]
VisionRisk = Literal["High-Risk", "Low-Risk", "insufficient confidence"]


# ── ED Triage Enums ───────────────────────────────────────────────────
Onset = Literal["<1 hour", "1-6 hours", "6-24 hours", ">24 hours"]
ArrivalMode = Literal["Ambulatory", "Wheelchair", "Stretcher", "Ambulance"]
AVPU = Literal["Alert", "Verbal", "Pain", "Unresponsive"]
Mechanism = Literal["Fall", "MVA", "Assault", "Penetrating", "Other"]
PregnancyStatus = Literal["Yes", "No", "Unknown"]


# ── Data Models ────────────────────────────────────────────────────────

class Vitals(BaseModel):
    """Individual vital signs with soft validation ranges.

    Fields are optional at the model level — required validation happens
    at the form/endpoint layer.  Ranges are deliberately wide to avoid
    rejecting critical values that are clinically possible.
    """
    hr: int | None = Field(default=None, ge=0, le=300, description="Heart rate (bpm)")
    rr: int | None = Field(default=None, ge=0, le=80, description="Respiratory rate (/min)")
    spo2: int | None = Field(default=None, ge=0, le=100, description="Oxygen saturation (%)")
    temp: float | None = Field(default=None, ge=28.0, le=45.0, description="Temperature (°C)")
    bp_systolic: int | None = Field(default=None, ge=0, le=300, description="Systolic BP (mmHg)")
    bp_diastolic: int | None = Field(default=None, ge=0, le=200, description="Diastolic BP (mmHg)")


class ComorbidityFlags(BaseModel):
    """Key comorbidities that directly modify urgency classification.

    These are flags, not a full PMH — limited to conditions that change
    triage decision thresholds.
    """
    cardiac_disease: bool = False
    diabetes_mellitus: bool = False
    respiratory_disease: bool = False
    immunocompromised: bool = False
    anticoagulants: bool = False
    renal_disease: bool = False


class TriageInput(BaseModel):
    """Complete ED triage intake — what a nurse collects in 2–5 minutes."""
    chief_complaint: str = Field(
        default=..., min_length=1, max_length=150,
        description="Terse clinical chief complaint (e.g. '65M, central chest pain radiating to jaw, onset 40 min ago, diaphoretic')",
    )
    vitals: Vitals = Field(default_factory=Vitals)
    age: int = Field(default=..., ge=0, le=130)
    sex: Literal["male", "female"]
    pain_score: int = Field(default=..., ge=0, le=10)

    # Contextual quick-selects
    onset: Onset | None = None
    arrival_mode: ArrivalMode | None = None
    consciousness: AVPU | None = None
    mechanism: Mechanism | None = None  # conditionally shown for trauma

    # Risk modifiers
    comorbidities: ComorbidityFlags = Field(default_factory=ComorbidityFlags)
    pregnancy: PregnancyStatus | None = None  # shown for female patients

    # Optional
    allergies: str | None = Field(default=None, max_length=200)


# ── Legacy compatibility (kept for existing vision/security code) ──────

class PatientContext(BaseModel):
    """Minimal patient context for existing code paths (vision, security)."""
    age: int | None = Field(default=None, ge=0, le=130)
    sex: Literal["male", "female"] | None = None


# ── Response Models ────────────────────────────────────────────────────

class ATSCard(BaseModel):
    """ATS triage card — everything a nurse needs to act."""
    category: ATSCategory
    label: str
    time_target_min: int
    color: str

    @classmethod
    def from_category(cls, category: ATSCategory) -> "ATSCard":
        return cls(
            category=category,
            label=ATS_LABELS[category],
            time_target_min=ATS_TIMES[category],
            color=ATS_COLORS[category],
        )


class TriageResult(BaseModel):
    ats_category: ATSCategory
    ats_card: ATSCard
    rationale: str
    confidence: Confidence
    sources: list[str]
    disclaimer: str


class VisionResult(BaseModel):
    risk: VisionRisk
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = None


class TriageResponse(BaseModel):
    request_id: str
    triage_result: TriageResult
    vision_result: VisionResult | None
    latency_ms: int
    security_passed: Literal[True]


class BlockedResponse(BaseModel):
    error: str
    request_id: str
    security_passed: Literal[False]


class ComponentStatus(BaseModel):
    status: Literal["ok", "degraded", "placeholder"]
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    components: dict[str, ComponentStatus]

