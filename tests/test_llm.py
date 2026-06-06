from types import SimpleNamespace

import pytest

from app.llm import (
    LLMError,
    _extract_message_content,
    _normalize_confidence,
    _normalize_urgency,
    _parse_json_payload,
)


def test_extract_message_content_from_dict_response():
    assert _extract_message_content({"message": {"content": "hello"}}) == "hello"


def test_extract_message_content_from_object_response():
    response = SimpleNamespace(message={"content": "world"})
    assert _extract_message_content(response) == "world"

    response = SimpleNamespace(message=SimpleNamespace(content="ok"))
    assert _extract_message_content(response) == "ok"


def test_parse_json_payload_can_parse_wrapped_json():
    raw = 'prefix {"urgency":"Routine","rationale":"safe","confidence":"low"} suffix'
    payload = _parse_json_payload(raw)

    assert payload["urgency"] == "Routine"
    assert payload["confidence"] == "low"


def test_parse_json_payload_fails_for_invalid_json():
    with pytest.raises(LLMError):
        _parse_json_payload("not json")


def test_normalize_urgency_accepts_aliases_and_case():
    assert _normalize_urgency("self care") == "Self-Care"
    assert _normalize_urgency("EMERGENCY") == "Emergency"


def test_normalize_urgency_rejects_invalid_value():
    with pytest.raises(LLMError):
        _normalize_urgency("critical")


def test_normalize_confidence_accepts_values():
    assert _normalize_confidence("high") == "high"
    assert _normalize_confidence("MEDIUM") == "medium"


def test_normalize_confidence_rejects_invalid_value():
    with pytest.raises(LLMError):
        _normalize_confidence("certain")
