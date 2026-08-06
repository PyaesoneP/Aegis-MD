import builtins

import pytest

from app.retriever import (
    RetrievalError,
    get_guideline_collection,
    retrieve_relevant_guidelines,
)


class DummyCollection:
    def __init__(self, result):
        self.result = result

    def query(self, query_texts, include, n_results):
        return self.result


def test_retrieve_relevant_guidelines_builds_guideline_objects():
    results = {
        "documents": [["Doc 1", "Doc 2"]],
        "metadatas": [
            [
                {"source": "source1.pdf", "page_number": 4},
                {"source": "source2.pdf", "page_number": None},
            ]
        ],
    }

    guidelines = retrieve_relevant_guidelines(
        query="any",
        collection=DummyCollection(results),
        top_k=2,
    )

    assert len(guidelines) == 2
    assert guidelines[0].content == "Doc 1"
    assert guidelines[0].citation == "source1.pdf p.4"
    assert guidelines[1].citation == "source2.pdf"


def test_retrieve_populates_enrichment_fields_from_metadata():
    results = {
        "documents": [["Doc 1"]],
        "metadatas": [
            [
                {
                    "source": "source1.pdf",
                    "page_number": 2,
                    "citation_label": "ETEK 2nd Ed",
                    "source_url": "https://example.test/etek.pdf",
                    "year_published": 2024,
                    "ats_level": ["ATS-1", "ATS-2"],
                    "symptom_tags": ["vital_signs", "pain"],
                    "document_type": "triage_framework",
                }
            ]
        ],
    }

    guidelines = retrieve_relevant_guidelines(
        query="any", collection=DummyCollection(results), top_k=1
    )

    guideline = guidelines[0]
    assert guideline.citation_label == "ETEK 2nd Ed"
    assert guideline.source_url == "https://example.test/etek.pdf"
    assert guideline.year_published == 2024
    assert guideline.ats_level == ["ATS-1", "ATS-2"]
    assert guideline.symptom_tags == ["vital_signs", "pain"]
    assert guideline.document_type == "triage_framework"


def test_retrieve_defaults_enrichment_fields_when_missing():
    # Chunks indexed before enrichment lack the four new metadata keys; the
    # resulting RetrievedGuideline must fall back to neutral (None) values.
    results = {
        "documents": [["Doc 1"]],
        "metadatas": [[{"source": "source1.pdf", "page_number": 1}]],
    }

    guidelines = retrieve_relevant_guidelines(
        query="any", collection=DummyCollection(results), top_k=1
    )

    guideline = guidelines[0]
    assert guideline.year_published is None
    assert guideline.ats_level is None
    assert guideline.symptom_tags is None
    assert guideline.document_type is None


def test_retrieve_relevant_guidelines_raises_when_no_results():
    results = {"documents": [[]], "metadatas": [[]]}

    with pytest.raises(RetrievalError):
        retrieve_relevant_guidelines(query="any", collection=DummyCollection(results))


def test_get_guideline_collection_raises_when_chromadb_import_fails(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "chromadb":
            raise ImportError("chromadb is unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RetrievalError):
        get_guideline_collection(chroma_path="unused", collection_name="unused")
