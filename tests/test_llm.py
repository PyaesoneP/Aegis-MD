from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.llm import (
    LLMError,
    _build_retrieval_query,
    _build_user_prompt,
    _chat_completion,
    _extract_message_content,
    _format_comorbidities,
    _format_patient_context,
    _format_vitals,
    _normalize_ats_category,
    _normalize_confidence,
    _normalize_vision_confidence,
    _normalize_vision_risk,
    _parse_json_payload,
    _vitals_normality_note,
    rag_response,
    vision_response,
)
from app.models import (
    ComorbidityFlags,
    PatientContext,
    TriageInput,
    VisionResult,
    Vitals,
)


def test_extract_message_content_from_openai_shape():
    resp = {"choices": [{"message": {"content": "hello"}}]}
    assert _extract_message_content(resp) == "hello"


def test_extract_message_content_from_object_response():
    response = SimpleNamespace(message={"content": "world"})
    assert _extract_message_content(response) == "world"

    response = SimpleNamespace(message=SimpleNamespace(content="ok"))
    assert _extract_message_content(response) == "ok"


def test_extract_message_content_empty_choices():
    assert _extract_message_content({"choices": []}) == ""


def test_extract_message_content_no_choices_key():
    assert _extract_message_content({"message": {"content": "fallback"}}) == ""


# ---------------------------------------------------------------------------
# _chat_completion tests (mocked httpx.Client)
# ---------------------------------------------------------------------------


def _make_mock_response(json_data, status_code=200):
    """Build a mock response object with working raise_for_status and .json()."""
    import unittest.mock as m

    mock_resp = m.Mock()
    mock_resp.json.return_value = json_data
    mock_resp.status_code = status_code
    if status_code >= 400:
        import httpx
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="Server error",
            request=m.Mock(),
            response=mock_resp,
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


def _make_mock_client(resp_factory):
    """Build a mock httpx.Client whose .post() returns responses from resp_factory."""
    import unittest.mock as m

    mock_client = m.Mock()
    mock_client.post.return_value = resp_factory()
    mock_client.__enter__ = m.Mock(return_value=mock_client)
    mock_client.__exit__ = m.Mock(return_value=False)
    return mock_client


def test_chat_completion_success():
    resp_data = {
        "choices": [{"message": {"content": '{"ats_category":"ATS-3","rationale":"ok","confidence":"high"}'}}],
    }
    mock_client = _make_mock_client(lambda: _make_mock_response(resp_data, 200))
    with patch("app.llm.httpx.Client", return_value=mock_client):
        result = _chat_completion("test-model", [{"role": "user", "content": "hi"}])
    assert "ATS-3" in result


def test_chat_completion_empty_content_raises():
    resp_data = {"choices": [{"message": {"content": ""}}]}
    mock_client = _make_mock_client(lambda: _make_mock_response(resp_data, 200))
    with patch("app.llm.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError, match="empty response"):
            _chat_completion("test-model", [{"role": "user", "content": "hi"}])


def test_chat_completion_http_error_raises():
    mock_client = _make_mock_client(lambda: _make_mock_response(None, 500))
    with patch("app.llm.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError):
            _chat_completion("test-model", [{"role": "user", "content": "hi"}])


def test_chat_completion_timeout_raises():
    mock_client = _make_mock_client(lambda: _make_mock_response(None, 504))
    with patch("app.llm.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError):
            _chat_completion("test-model", [{"role": "user", "content": "hi"}])


def test_chat_completion_retry_then_success():
    import unittest.mock as m

    call_count = [0]

    def resp_factory():
        call_count[0] += 1
        if call_count[0] <= 1:
            return _make_mock_response(None, 500)
        return _make_mock_response({
            "choices": [{"message": {"content": '{"ats_category":"ATS-2","rationale":"ok","confidence":"medium"}'}}],
        }, 200)

    mock_client = m.Mock()
    mock_client.post = m.Mock(side_effect=lambda *a, **kw: resp_factory())
    mock_client.__enter__ = m.Mock(return_value=mock_client)
    mock_client.__exit__ = m.Mock(return_value=False)

    with patch("app.llm.httpx.Client", return_value=mock_client):
        result = _chat_completion("test-model", [{"role": "user", "content": "hi"}])
    assert "ATS-2" in result
    assert call_count[0] == 2


def test_chat_completion_exhaust_retries_raises():
    mock_client = _make_mock_client(lambda: _make_mock_response(None, 500))
    with patch("app.llm.httpx.Client", return_value=mock_client):
        with pytest.raises(LLMError, match="attempts"):
            _chat_completion("test-model", [{"role": "user", "content": "hi"}])
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
# vision_response — stub behavior (migration deferred)
# ---------------------------------------------------------------------------


def test_vision_response_returns_placeholder():
    result = vision_response(b"\x89PNG fake image bytes")

    assert isinstance(result, VisionResult)
    assert result.risk == "insufficient confidence"
    assert result.confidence is None
    assert "placeholder mode active" in result.rationale


def test_vision_response_ignores_patient_context():
    """Stub ignores patient_context argument gracefully."""
    result = vision_response(
        b"fake",
        patient_context=PatientContext(age=45, sex="female"),
    )
    assert result.risk == "insufficient confidence"
    assert "placeholder mode active" in result.rationale


def test_vision_response_does_not_call_llm():
    """Verify no LLM calls are made — vision is a stub."""
    with patch("app.llm._chat_completion", side_effect=AssertionError("should not be called")):
        result = vision_response(b"fake")
    assert result.risk == "insufficient confidence"


# ===========================================================================
# _build_retrieval_query
# ===========================================================================


class TestBuildRetrievalQuery:
    def test_includes_chief_complaint(self):
        triage_input = TriageInput(
            chief_complaint="chest pain radiating to arm",
            age=50, sex="male", pain_score=7,
        )
        query = _build_retrieval_query(triage_input)
        assert "chest pain radiating to arm" in query

    def test_includes_mechanism_when_present(self):
        triage_input = TriageInput(
            chief_complaint="head injury",
            age=30, sex="male", pain_score=5,
            mechanism="Fall",
        )
        query = _build_retrieval_query(triage_input)
        assert "mechanism: Fall" in query

    def test_no_mechanism_appended_when_none(self):
        triage_input = TriageInput(
            chief_complaint="fever",
            age=25, sex="female", pain_score=3,
            mechanism=None,
        )
        query = _build_retrieval_query(triage_input)
        assert "mechanism:" not in query


# ===========================================================================
# _format_vitals
# ===========================================================================


class TestFormatVitals:
    def test_all_vitals_recorded(self):
        vitals = Vitals(hr=72, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        result = _format_vitals(vitals, age=30)
        assert "HR: 72 bpm" in result
        assert "RR: 16 /min" in result
        assert "SpO2: 98 %" in result
        assert "Temp: 36.8 C" in result
        assert "Systolic BP: 120 mmHg" in result
        assert "Diastolic BP: 78 mmHg" in result

    def test_missing_vitals_show_not_recorded(self):
        vitals = Vitals(hr=72, temp=36.8)  # only 2 recorded
        result = _format_vitals(vitals, age=30)
        assert "not recorded" in result

    def test_pediatric_note_when_age_under_18(self):
        vitals = Vitals(hr=90, rr=24)
        result = _format_vitals(vitals, age=14)
        assert "pediatric" in result.lower()

    def test_no_pediatric_note_for_adult(self):
        vitals = Vitals(hr=72)
        result = _format_vitals(vitals, age=30)
        assert "pediatric" not in result.lower()


# ===========================================================================
# _format_comorbidities
# ===========================================================================


class TestFormatComorbidities:
    def test_all_active(self):
        coms = ComorbidityFlags(
            cardiac_disease=True, diabetes_mellitus=True,
            respiratory_disease=True, immunocompromised=True,
            anticoagulants=True, renal_disease=True,
        )
        result = _format_comorbidities(coms)
        assert len(result) == 6
        assert any("Cardiac disease" in r for r in result)
        assert any("Diabetes mellitus" in r for r in result)

    def test_none_active(self):
        coms = ComorbidityFlags()
        result = _format_comorbidities(coms)
        assert len(result) == 0

    def test_partial_active(self):
        coms = ComorbidityFlags(cardiac_disease=True, anticoagulants=True)
        result = _format_comorbidities(coms)
        assert len(result) == 2
        assert any("Cardiac disease" in r for r in result)
        assert any("Anticoagulants" in r for r in result)


# ===========================================================================
# _format_patient_context
# ===========================================================================


class TestFormatPatientContext:
    def test_both_age_and_sex(self):
        ctx = PatientContext(age=45, sex="female")
        result = _format_patient_context(ctx)
        assert "age=45" in result
        assert "sex=female" in result

    def test_age_only(self):
        ctx = PatientContext(age=60)
        result = _format_patient_context(ctx)
        assert "age=60" in result
        assert "sex" not in result

    def test_none_returns_not_provided(self):
        result = _format_patient_context(None)
        assert result == "Not provided"

    def test_empty_returns_not_provided(self):
        ctx = PatientContext()
        result = _format_patient_context(ctx)
        assert result == "Not provided"


# ===========================================================================
# _build_user_prompt
# ===========================================================================


class TestBuildUserPrompt:
    @pytest.fixture
    def basic_input(self) -> TriageInput:
        return TriageInput(
            chief_complaint="chest pain radiating to left arm",
            vitals=Vitals(hr=110, rr=22, spo2=94),
            age=65,
            sex="male",
            pain_score=8,
            onset="<1 hour",
            arrival_mode="Ambulance",
            consciousness="Alert",
            comorbidities=ComorbidityFlags(cardiac_disease=True),
            allergies="penicillin",
        )

    def test_includes_chief_complaint(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-2", guidelines=[],
        )
        assert "chest pain radiating to left arm" in prompt

    def test_includes_vitals_section(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-2", guidelines=[],
        )
        assert "Vitals:" in prompt
        assert "HR:" in prompt

    def test_includes_rule_ats_prior(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-2", guidelines=[],
        )
        assert "Rule-based ATS prior" in prompt
        assert "ATS-2" in prompt

    def test_includes_guidelines_when_present(self, basic_input):
        from app.retriever import RetrievedGuideline

        guidelines = [
            RetrievedGuideline(
                content="ACS guidelines for chest pain assessment.",
                source="acs_guidelines.pdf", page_number=3,
            ),
        ]
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-3", guidelines=guidelines,
        )
        assert "ACS guidelines" in prompt
        assert "acs_guidelines.pdf p.3" in prompt

    def test_no_guidelines_message_when_empty(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-3", guidelines=[],
        )
        assert "No relevant guideline chunks were retrieved" in prompt

    def test_includes_clinical_context(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-2", guidelines=[],
        )
        assert "Clinical context:" in prompt
        assert "Onset: <1 hour" in prompt
        assert "Arrival mode: Ambulance" in prompt

    def test_includes_risk_modifiers(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-2", guidelines=[],
        )
        assert "Risk modifiers:" in prompt
        assert "Cardiac disease" in prompt
        assert "penicillin" in prompt

    def test_appends_vision_findings_verbatim(self, basic_input):
        prompt = _build_user_prompt(
            triage_input=basic_input, rule_ats="ATS-3", guidelines=[],
            vision_findings="Risk: High-Risk\nFindings: Erythematous lesion.",
        )
        assert "Image analysis findings" in prompt
        assert "Erythematous lesion" in prompt

    def test_no_clinical_context_when_empty(self):
        triage_input = TriageInput(
            chief_complaint="rash",
            age=25, sex="female", pain_score=1,
        )
        prompt = _build_user_prompt(
            triage_input=triage_input, rule_ats="ATS-5", guidelines=[],
        )
        assert "Clinical context:" not in prompt


# ===========================================================================
# _vitals_normality_note (additional edge cases for llm.py version)
# ===========================================================================


class TestVitalsNormalityNoteLLM:
    def test_all_vitals_none_returns_none(self):
        vitals = Vitals()
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        # Fewer than 3 recorded → None
        assert note is None

    def test_exactly_three_normal_returns_note(self):
        vitals = Vitals(hr=72, rr=16, spo2=98)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is not None
        assert "VITALS NORMALITY" in note


# ===========================================================================
# rag_response — pipeline integration (mocked Ollama)
# ===========================================================================


class TestRagResponse:
    def test_parses_valid_ollama_response(self):
        fake_raw = (
            'Some prefix {"ats_category":"ATS-3",'
            '"rationale":"Moderate urgency based on clinical features.",'
            '"confidence":"medium"}'
        )

        triage_input = TriageInput(
            chief_complaint="fever and cough",
            age=30, sex="female", pain_score=4,
        )

        with patch("app.llm._chat_completion", return_value=fake_raw):
            with patch("app.llm.retrieve_relevant_guidelines", return_value=[]):
                result = rag_response(triage_input)

        assert result.ats_category == "ATS-3"
        assert result.confidence == "medium"
        assert "retrieval unavailable" in result.sources[0]

    def test_proceeds_without_retrieval(self):
        fake_raw = '{"ats_category":"ATS-4","rationale":"Minor complaint.","confidence":"high"}'

        triage_input = TriageInput(
            chief_complaint="ankle sprain",
            age=22, sex="male", pain_score=3,
        )

        with patch("app.llm._chat_completion", return_value=fake_raw):
            with patch(
                "app.llm.retrieve_relevant_guidelines",
                side_effect=Exception("Chroma unavailable"),
            ):
                result = rag_response(triage_input)

        assert result.ats_category == "ATS-4"
        assert "retrieval unavailable" in result.sources[0]

    def test_includes_guideline_sources_when_retrieved(self):
        from app.retriever import RetrievedGuideline

        fake_raw = '{"ats_category":"ATS-2","rationale":"Urgent assessment.","confidence":"high"}'
        guidelines = [
            RetrievedGuideline(
                content="Chest pain guideline text.",
                source="chest_pain.pdf", page_number=1,
            ),
        ]

        triage_input = TriageInput(
            chief_complaint="chest pain",
            age=65, sex="male", pain_score=8,
        )

        with patch("app.llm._chat_completion", return_value=fake_raw):
            with patch(
                "app.llm.retrieve_relevant_guidelines",
                return_value=guidelines,
            ):
                result = rag_response(triage_input)

        assert "chest_pain.pdf p.1" in result.sources
