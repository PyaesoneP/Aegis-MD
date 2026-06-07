from fastapi.testclient import TestClient

from app.config import Settings
from app.llm import LLMError, RagResponse
from app.main import create_app
from app.models import PatientContext
from app.triage import classify_text


def test_classify_text_uses_rule_urgency_when_higher(monkeypatch):
    monkeypatch.setattr(
        "app.triage.rag_response",
        lambda symptoms, patient_context, rule_urgency, vision_findings=None: RagResponse(
            urgency="Routine",
            rationale="LLM says routine.",
            confidence="medium",
            sources=["source1"],
        ),
    )

    result = classify_text(
        "I have chest pain and shortness of breath.",
        PatientContext(age=40, sex="female"),
    )

    assert result.urgency == "Emergency"
    assert "Local triage safeguards raised the final urgency" in result.rationale
    assert result.confidence == "medium"


def test_triage_endpoint_returns_503_when_llm_dependency_fails(tmp_path, monkeypatch):
    app = create_app(Settings(log_dir=str(tmp_path / "logs")))
    monkeypatch.setattr(
        "app.main.classify_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(LLMError("dependency error")),
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/triage", data={"symptoms": "I have a mild cough."})

    assert response.status_code == 503
    assert "RAG/LLM dependency" in response.json()["detail"]
