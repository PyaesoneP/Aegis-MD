from typing import Literal

from pydantic import BaseModel, Field


Urgency = Literal["Emergency", "Urgent", "Routine", "Self-Care"]
Confidence = Literal["low", "medium", "high"]
VisionRisk = Literal["High-Risk", "Low-Risk", "insufficient confidence"]


class PatientContext(BaseModel):
    age: int | None = Field(default=None, ge=0, le=130)
    sex: Literal["male", "female"] | None = None


class TriageResult(BaseModel):
    urgency: Urgency
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

