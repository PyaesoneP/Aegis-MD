from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.llm import (
    LLMError,
    _extract_message_content,
    _normalize_ats_category,
    _normalize_confidence,
    _normalize_vision_confidence,
    _normalize_vision_risk,
    _parse_json_payload,
    vision_response,
)
from app.models import VisionResult


def test_extract_message_content_from_dict_response():
    assert _extract_message_content({"message": {"content": "hello"}}) == "hello"


def test_extract_message_content_from_object_response():
    response = SimpleNamespace(message={"content": "world"})
    assert _extract_message_content(response) == "world"

    response = SimpleNamespace(message=SimpleNamespace(content="ok"))
    assert _extract_message_content(response) == "ok"


def test_parse_json_payload_can_parse_wrapped_json():
    raw = 'prefix {"ats_category":"ATS-3","rationale":"safe","confidence":"low"} suffix'
    payload = _parse_json_payload(raw)

    assert payload["ats_category"] == "ATS-3"
    assert payload["confidence"] == "low"


def test_parse_json_payload_fails_for_invalid_json():
    with pytest.raises(LLMError):
        _parse_json_payload("not json")


def test_normalize_ats_category_accepts_formats():
    assert _normalize_ats_category("ATS-1") == "ATS-1"
    assert _normalize_ats_category("ATS-3") == "ATS-3"
    assert _normalize_ats_category("1") == "ATS-1"
    assert _normalize_ats_category("  ats-2  ") == "ATS-2"


def test_normalize_ats_category_rejects_invalid_value():
    with pytest.raises(LLMError):
        _normalize_ats_category("critical")
    with pytest.raises(LLMError):
        _normalize_ats_category("ATS-6")


def test_normalize_confidence_accepts_values():
    assert _normalize_confidence("high") == "high"
    assert _normalize_confidence("MEDIUM") == "medium"


def test_normalize_confidence_rejects_invalid_value():
    with pytest.raises(LLMError):
        _normalize_confidence("certain")


# ---------------------------------------------------------------------------
# Vision risk / confidence normalizers
# ---------------------------------------------------------------------------


def test_normalize_vision_risk_accepts_valid_values():
    assert _normalize_vision_risk("High-Risk") == "High-Risk"
    assert _normalize_vision_risk("Low-Risk") == "Low-Risk"
    assert _normalize_vision_risk("insufficient confidence") == "insufficient confidence"


def test_normalize_vision_risk_accepts_aliases():
    assert _normalize_vision_risk("high risk") == "High-Risk"
    assert _normalize_vision_risk("low-risk") == "Low-Risk"
    assert _normalize_vision_risk("uncertain") == "insufficient confidence"
    assert _normalize_vision_risk("INSUFFICIENT") == "insufficient confidence"


def test_normalize_vision_risk_rejects_invalid_value():
    with pytest.raises(LLMError):
        _normalize_vision_risk("critical")


def test_normalize_vision_confidence_valid():
    assert _normalize_vision_confidence(0.85) == 0.85
    assert _normalize_vision_confidence(0.0) == 0.0
    assert _normalize_vision_confidence(1.0) == 1.0
    assert _normalize_vision_confidence("0.5") == 0.5


def test_normalize_vision_confidence_none():
    assert _normalize_vision_confidence(None) is None


def test_normalize_vision_confidence_out_of_range():
    with pytest.raises(LLMError, match="between 0 and 1"):
        _normalize_vision_confidence(1.5)
    with pytest.raises(LLMError, match="between 0 and 1"):
        _normalize_vision_confidence(-0.1)


def test_normalize_vision_confidence_non_numeric():
    with pytest.raises(LLMError, match="invalid vision confidence"):
        _normalize_vision_confidence("high")


# ---------------------------------------------------------------------------
# vision_response integration (mocked Ollama)
# ---------------------------------------------------------------------------


def test_vision_response_parses_valid_json():
    fake_raw = '{"risk":"Low-Risk","confidence":0.87,"rationale":"No abnormal findings."}'

    with patch("app.llm._chat_with_ollama", return_value=fake_raw):
        result = vision_response(b"\x89PNG fake image bytes")

    assert isinstance(result, VisionResult)
    assert result.risk == "Low-Risk"
    assert result.confidence == 0.87
    assert result.rationale == "No abnormal findings."


def test_vision_response_includes_patient_context_in_prompt():
    """Ensures patient context is formatted into the user prompt."""
    fake_raw = '{"risk":"insufficient confidence","confidence":null,"rationale":"No usable image."}'
    from app.models import PatientContext

    with patch("app.llm._chat_with_ollama", return_value=fake_raw) as mock_chat:
        vision_response(
            b"fake",
            patient_context=PatientContext(age=45, sex="female"),
        )

    call_args = mock_chat.call_args
    messages = call_args.kwargs["messages"]
    user_content = messages[1]["content"]
    assert "age=45" in user_content
    assert "sex=female" in user_content


def test_vision_response_raises_llm_error_on_invalid_json():
    with patch("app.llm._chat_with_ollama", return_value="not json at all"):
        with pytest.raises(LLMError):
            vision_response(b"fake")
