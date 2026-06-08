from fastapi.testclient import TestClient

from app.config import Settings
from app.llm import LLMError, RagResponse
from app.main import create_app
from app.models import TriageInput
from app.triage import classify_text


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
