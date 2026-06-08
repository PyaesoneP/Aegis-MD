from fastapi.testclient import TestClient

import pytest

from app.config import Settings
from app.llm import LLMError, RagResponse, _vitals_normality_note
from app.main import create_app
from app.models import (
    ATSCard,
    ComorbidityFlags,
    TriageInput,
    TriageResult,
    VisionResult,
    Vitals,
)
from app.triage import (
    DISCLAIMER,
    _highest_ats,
    _rule_based_result,
    _select_ats,
    classify_text,
    classify_vision,
    merge_triage_results,
)


def test_classify_text_uses_rule_ats_when_higher(monkeypatch):
    monkeypatch.setattr(
        "app.triage.rag_response",
        lambda triage_input, rule_ats=None, vision_findings=None: RagResponse(
            ats_category="ATS-4",
            rationale="LLM says semi-urgent.",
            confidence="medium",
            sources=["source1"],
        ),
    )

    triage_input = TriageInput(
        chief_complaint="I have chest pain and shortness of breath.",
        age=40,
        sex="female",
        pain_score=8,
    )

    result = classify_text(triage_input)

    assert result.ats_category == "ATS-2"
    assert "Local triage safeguards raised the final ATS category" in result.rationale
    assert result.confidence == "medium"


def test_triage_endpoint_returns_503_when_llm_dependency_fails(tmp_path, monkeypatch):
    app = create_app(Settings(log_dir=str(tmp_path / "logs")))
    monkeypatch.setattr(
        "app.main.classify_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMError("dependency error")),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/triage",
            data={
                "chief_complaint": "I have a mild cough.",
                "age": "30",
                "sex": "female",
                "pain_score": "2",
            },
        )

    assert response.status_code == 503
    assert "RAG/LLM dependency" in response.json()["detail"]


# ===========================================================================
# _select_ats — keyword-based ATS classification
# ===========================================================================


class TestSelectAts:
    def test_ats1_cardiac_arrest(self):
        assert _select_ats("cardiac arrest patient unresponsive") == "ATS-1"

    def test_ats1_airway_obstruction(self):
        assert _select_ats("airway obstruction after choking") == "ATS-1"

    def test_ats1_unresponsive(self):
        assert _select_ats("patient found unresponsive at home") == "ATS-1"

    def test_ats1_major_trauma(self):
        assert _select_ats("major trauma from MVA") == "ATS-1"

    def test_ats1_anaphylactic_shock(self):
        assert _select_ats("anaphylactic shock after bee sting") == "ATS-1"

    def test_ats2_chest_pain(self):
        assert _select_ats("chest pain radiating to left arm") == "ATS-2"

    def test_ats2_stroke(self):
        assert _select_ats("sudden facial droop, possible stroke") == "ATS-2"

    def test_ats2_seizure(self):
        assert _select_ats("active seizure lasting 3 minutes") == "ATS-2"

    def test_ats2_anaphylaxis(self):
        assert _select_ats("anaphylaxis to peanuts") == "ATS-2"

    def test_ats2_suicidal(self):
        assert _select_ats("patient reports suicidal ideation") == "ATS-2"

    def test_ats2_shortness_of_breath(self):
        assert _select_ats("sudden shortness of breath") == "ATS-2"

    def test_ats4_sprain(self):
        assert _select_ats("ankle sprain after jogging") == "ATS-4"

    def test_ats4_laceration(self):
        assert _select_ats("small laceration on finger") == "ATS-4"

    def test_ats4_dysuria(self):
        assert _select_ats("dysuria for 3 days") == "ATS-4"

    def test_ats4_earache(self):
        assert _select_ats("ear pain for 2 days") == "ATS-4"

    def test_ats4_sore_throat(self):
        assert _select_ats("sore throat, no fever") == "ATS-4"

    def test_ats5_suture_removal(self):
        assert _select_ats("suture removal left hand") == "ATS-5"

    def test_ats5_medical_certificate(self):
        assert _select_ats("needs medical certificate for work") == "ATS-5"

    def test_ats5_medication_refill(self):
        assert _select_ats("medication refill request") == "ATS-5"

    def test_ats5_minor_rash(self):
        assert _select_ats("minor rash on forearm, no fever") == "ATS-5"

    def test_ats5_wound_check(self):
        assert _select_ats("wound check post-surgery") == "ATS-5"

    def test_default_ats3_for_undifferentiated(self):
        assert _select_ats("feeling generally unwell for a week") == "ATS-3"

    def test_default_ats3_for_vague_symptoms(self):
        assert _select_ats("abdominal discomfort no other symptoms") == "ATS-3"

    def test_ats1_takes_priority_over_ats2(self):
        # "unresponsive" is ATS-1, "chest pain" is ATS-2
        # ATS-1 terms checked first → returns ATS-1
        assert _select_ats("unresponsive patient with chest pain") == "ATS-1"

    def test_ats2_takes_priority_over_ats4_ats5(self):
        # "chest pain" is ATS-2, checked before ATS-4/5 terms
        assert _select_ats("chest pain and sprain") == "ATS-2"

    def test_ats5_takes_priority_over_ats4(self):
        # ATS-5 terms checked before ATS-4 terms
        # "suture removal" is ATS-5, "laceration" is ATS-4
        assert _select_ats("suture removal for laceration") == "ATS-5"


# ===========================================================================
# _highest_ats — urgency comparison
# ===========================================================================


class TestHighestAts:
    def test_ats1_higher_than_ats2(self):
        assert _highest_ats("ATS-1", "ATS-2") == "ATS-1"

    def test_ats1_higher_than_ats5(self):
        assert _highest_ats("ATS-1", "ATS-5") == "ATS-1"

    def test_ats2_higher_than_ats3(self):
        assert _highest_ats("ATS-2", "ATS-3") == "ATS-2"

    def test_ats3_higher_than_ats4(self):
        assert _highest_ats("ATS-3", "ATS-4") == "ATS-3"

    def test_symmetric(self):
        assert _highest_ats("ATS-4", "ATS-2") == "ATS-2"

    def test_same_category(self):
        assert _highest_ats("ATS-3", "ATS-3") == "ATS-3"


# ===========================================================================
# merge_triage_results — text + vision fusion
# ===========================================================================


class TestMergeTriageResults:
    @pytest.fixture
    def text_result(self) -> TriageResult:
        return TriageResult(
            ats_category="ATS-3",
            ats_card=ATSCard.from_category("ATS-3"),
            rationale="Text-based assessment: moderate urgency.",
            confidence="medium",
            sources=["source1.pdf"],
            disclaimer=DISCLAIMER,
        )

    def test_high_risk_vision_elevates_to_ats2(self, text_result):
        vision = VisionResult(
            risk="High-Risk",
            confidence=0.90,
            rationale="Suspicious lesion with irregular borders.",
        )
        merged = merge_triage_results(text_result, vision)
        assert merged.ats_category == "ATS-2"
        assert "elevated" in merged.rationale.lower()

    def test_low_risk_vision_does_not_elevate(self, text_result):
        vision = VisionResult(
            risk="Low-Risk",
            confidence=0.85,
            rationale="Benign-appearing nevus.",
        )
        merged = merge_triage_results(text_result, vision)
        assert merged.ats_category == "ATS-3"

    def test_insufficient_confidence_does_not_modify(self, text_result):
        vision = VisionResult(
            risk="insufficient confidence",
            confidence=None,
            rationale="Unable to classify the image.",
        )
        merged = merge_triage_results(text_result, vision)
        assert merged.ats_category == "ATS-3"
        assert "inconclusive" in merged.rationale.lower()

    def test_rationale_includes_image_findings(self, text_result):
        vision = VisionResult(
            risk="High-Risk",
            confidence=0.75,
            rationale="Erythematous wound with purulent drainage.",
        )
        merged = merge_triage_results(text_result, vision)
        assert "Erythematous wound" in merged.rationale

    def test_confidence_str_formatted_in_rationale(self, text_result):
        vision = VisionResult(
            risk="Low-Risk",
            confidence=0.50,
            rationale="Minimal findings.",
        )
        merged = merge_triage_results(text_result, vision)
        # 0.50 → "50%"
        assert "50%" in merged.rationale

    def test_ats1_text_not_overridden_by_low_risk_vision(self):
        text = TriageResult(
            ats_category="ATS-1",
            ats_card=ATSCard.from_category("ATS-1"),
            rationale="Immediately life-threatening.",
            confidence="high",
            sources=[],
            disclaimer=DISCLAIMER,
        )
        vision = VisionResult(
            risk="Low-Risk",
            confidence=0.9,
            rationale="Clean wound.",
        )
        merged = merge_triage_results(text, vision)
        # ATS-1 should not be downgraded
        assert merged.ats_category == "ATS-1"


# ===========================================================================
# _rule_based_result — Tier 3 fallback
# ===========================================================================


class TestRuleBasedResult:
    def test_returns_correct_ats(self):
        triage_input = TriageInput(
            chief_complaint="chest pain radiating to arm",
            age=40, sex="male", pain_score=7,
        )
        result = _rule_based_result("ATS-2", triage_input)
        assert result.ats_category == "ATS-2"
        assert result.confidence == "low"
        assert "LLM unavailable" in result.rationale
        assert "rule-based fallback" in result.sources[0]

    def test_appends_age_note_for_elderly(self):
        triage_input = TriageInput(
            chief_complaint="mild cough",
            age=70, sex="male", pain_score=2,
        )
        result = _rule_based_result("ATS-3", triage_input)
        assert "Age over 65" in result.rationale

    def test_no_age_note_for_young_patient(self):
        triage_input = TriageInput(
            chief_complaint="mild cough",
            age=30, sex="female", pain_score=2,
        )
        result = _rule_based_result("ATS-3", triage_input)
        assert "Age over 65" not in result.rationale


# ===========================================================================
# classify_vision — all paths
# ===========================================================================


class TestClassifyVision:
    def test_returns_none_for_empty_bytes(self):
        result = classify_vision(b"")
        assert result is None

    def test_returns_placeholder_when_vision_disabled(self, monkeypatch):
        monkeypatch.setattr("app.triage.get_settings", lambda: Settings(vision_enabled=False))
        result = classify_vision(b"\x89PNG fake")
        assert result is not None
        assert result.risk == "insufficient confidence"
        assert "placeholder" in result.rationale.lower()

    def test_returns_graceful_degradation_on_llm_error(self, monkeypatch):
        from app.llm import LLMError

        def _raise(*args, **kwargs):
            raise LLMError("vision model crash")

        monkeypatch.setattr("app.triage.vision_response", _raise)
        result = classify_vision(b"\x89PNG fake")
        assert result is not None
        assert result.risk == "insufficient confidence"
        assert "failed" in result.rationale.lower()


# ===========================================================================
# classify_text — three-tier degradation and escalation notes
# ===========================================================================


class TestClassifyTextTiers:
    def test_tier3_fallback_when_llm_fails(self, monkeypatch):
        def _raise(*args, **kwargs):
            raise LLMError("simulated failure")

        monkeypatch.setattr("app.triage.rag_response", _raise)

        triage_input = TriageInput(
            chief_complaint="chest pain",
            age=40, sex="male", pain_score=7,
        )
        result = classify_text(triage_input)
        # Falls back to rule-based
        assert result.confidence == "low"
        assert "LLM unavailable" in result.rationale

    def test_ats5_rule_not_overridden_by_llm_downgrade(self, monkeypatch):
        """ATS-5 from rules cannot be overridden — security lock."""
        monkeypatch.setattr(
            "app.triage.rag_response",
            lambda triage_input, rule_ats=None, vision_findings=None: RagResponse(
                ats_category="ATS-2",  # LLM wants higher urgency
                rationale="LLM assessment.",
                confidence="medium",
                sources=[],
            ),
        )

        triage_input = TriageInput(
            chief_complaint="suture removal",
            age=30, sex="male", pain_score=0,
        )
        result = classify_text(triage_input)
        # ATS-5 from rules, LLM says ATS-2 — rules should still take effect
        # Because rule_ats="ATS-5" and the code says: if rule_ats != "ATS-5": ats = _highest_ats(...)
        # So when rule_ats IS ATS-5, ats stays ATS-5 (safety lock)
        assert result.ats_category == "ATS-5"

    def test_escalation_note_for_age(self, monkeypatch):
        monkeypatch.setattr(
            "app.triage.rag_response",
            lambda triage_input, rule_ats=None, vision_findings=None: RagResponse(
                ats_category="ATS-3",
                rationale="Moderate urgency.",
                confidence="medium",
                sources=[],
            ),
        )

        triage_input = TriageInput(
            chief_complaint="fever",
            age=70, sex="female", pain_score=3,
        )
        result = classify_text(triage_input)
        assert "Age over 65" in result.rationale

    def test_escalation_note_for_anticoagulants(self, monkeypatch):
        monkeypatch.setattr(
            "app.triage.rag_response",
            lambda triage_input, rule_ats=None, vision_findings=None: RagResponse(
                ats_category="ATS-3",
                rationale="Moderate urgency.",
                confidence="medium",
                sources=[],
            ),
        )

        triage_input = TriageInput(
            chief_complaint="head injury",
            age=40, sex="male", pain_score=2,
            comorbidities=ComorbidityFlags(anticoagulants=True),
        )
        result = classify_text(triage_input)
        assert "Anticoagulant" in result.rationale

    def test_escalation_note_for_pregnancy(self, monkeypatch):
        monkeypatch.setattr(
            "app.triage.rag_response",
            lambda triage_input, rule_ats=None, vision_findings=None: RagResponse(
                ats_category="ATS-3",
                rationale="Moderate urgency.",
                confidence="medium",
                sources=[],
            ),
        )

        triage_input = TriageInput(
            chief_complaint="abdominal pain",
            age=28, sex="female", pain_score=6,
            pregnancy="Yes",
        )
        result = classify_text(triage_input)
        assert "Pregnancy" in result.rationale


# ===========================================================================
# _vitals_normality_note
# ===========================================================================


class TestVitalsNormalityNote:
    def test_all_normal_vitals_returns_note(self):
        vitals = Vitals(hr=72, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is not None
        assert "VITALS NORMALITY" in note
        assert "ATS-4" in note

    def test_any_abnormal_vital_returns_none(self):
        vitals = Vitals(hr=130, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is None

    def test_fewer_than_three_recorded_returns_none(self):
        vitals = Vitals(hr=72, temp=36.8)  # only 2 recorded
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is None

    def test_elderly_with_comorbidities_suppressed(self):
        vitals = Vitals(hr=72, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=70, has_comorbidities=True)
        assert note is None

    def test_elderly_without_comorbidities_not_suppressed(self):
        vitals = Vitals(hr=72, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=70, has_comorbidities=False)
        assert note is not None

    def test_borderline_vital_triggers_none(self):
        # HR at the boundary of normal
        vitals = Vitals(hr=101, rr=16, spo2=98, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is None

    def test_low_spo2_returns_none(self):
        vitals = Vitals(hr=72, rr=16, spo2=91, temp=36.8, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is None

    def test_high_temp_returns_none(self):
        vitals = Vitals(hr=72, rr=16, spo2=98, temp=39.5, bp_systolic=120, bp_diastolic=78)
        note = _vitals_normality_note(vitals, age=30, has_comorbidities=False)
        assert note is None
