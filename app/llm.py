import json
from dataclasses import dataclass
from typing import Any, get_args

from app.config import get_settings
from app.models import Confidence, PatientContext, Urgency
from app.retriever import RetrievedGuideline, retrieve_relevant_guidelines


class LLMError(RuntimeError):
    """Raised when the Ollama triage model cannot produce a valid response."""


@dataclass(frozen=True)
class RagResponse:
    urgency: Urgency
    rationale: str
    confidence: Confidence
    sources: list[str]


SYSTEM_PROMPT = """
You are Aegis-MD, a research triage assistant.
Classify urgency only. Do not diagnose. Do not prescribe treatment.
Use only the retrieved guideline context and the patient symptom text.
Return JSON only, with exactly these keys:
urgency, rationale, confidence.
urgency must be one of: Emergency, Urgent, Routine, Self-Care.
confidence must be one of: low, medium, high.
The rationale must be brief, safety-focused, and cite guideline chunks using [1], [2], etc.
""".strip()

URGENCY_VALUES = set(get_args(Urgency))
CONFIDENCE_VALUES = set(get_args(Confidence))


def rag_response(
    query: str,
    patient_context: PatientContext | None = None,
    rule_urgency: Urgency | None = None,
) -> RagResponse:
    settings = get_settings()
    guidelines = retrieve_relevant_guidelines(
        query=query,
        top_k=settings.retrieval_top_k,
    )

    raw_content = _chat_with_ollama(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    query=query,
                    patient_context=patient_context,
                    rule_urgency=rule_urgency,
                    guidelines=guidelines,
                ),
            },
        ],
    )
    payload = _parse_json_payload(raw_content)

    return RagResponse(
        urgency=_normalize_urgency(payload.get("urgency")),
        rationale=_require_text(payload.get("rationale"), "rationale"),
        confidence=_normalize_confidence(payload.get("confidence")),
        sources=[guideline.citation for guideline in guidelines],
    )


def _build_user_prompt(
    *,
    query: str,
    patient_context: PatientContext | None,
    rule_urgency: Urgency | None,
    guidelines: list[RetrievedGuideline],
) -> str:
    patient_context_text = _format_patient_context(patient_context)
    rule_urgency_text = rule_urgency or "No rule-based prior"
    guideline_text = "\n\n".join(
        f"[{index}] {guideline.content}\nSource: {guideline.citation}"
        for index, guideline in enumerate(guidelines, start=1)
    )

    return (
        f"Symptoms:\n{query}\n\n"
        f"Patient context:\n{patient_context_text}\n\n"
        f"Rule-based urgency prior:\n{rule_urgency_text}\n\n"
        f"Retrieved guideline chunks:\n{guideline_text}"
    )


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
        from ollama import chat
    except ImportError as exc:
        raise LLMError("The Ollama Python package is not installed.") from exc

    # Embed images in the last message dict (ollama Python client 0.6.x API)
    if images:
        messages = [dict(m) for m in messages]  # shallow copy
        messages[-1]["images"] = images

    try:
        response = chat(
            model=model,
            messages=messages,
            format="json",
            options={"temperature": 0},
        )
    except Exception as exc:
        raise LLMError("Ollama chat request failed.") from exc

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


def _normalize_urgency(value: Any) -> Urgency:
    text = str(value or "").strip()
    normalized = text.lower().replace("_", "-")
    aliases = {
        "emergency": "Emergency",
        "urgent": "Urgent",
        "routine": "Routine",
        "self-care": "Self-Care",
        "self care": "Self-Care",
    }
    urgency = aliases.get(normalized, text)
    if urgency not in URGENCY_VALUES:
        raise LLMError("Ollama response contained an invalid urgency.")
    return urgency


def _normalize_confidence(value: Any) -> Confidence:
    confidence = str(value or "").strip().lower()
    if confidence not in CONFIDENCE_VALUES:
        raise LLMError("Ollama response contained an invalid confidence.")
    return confidence
