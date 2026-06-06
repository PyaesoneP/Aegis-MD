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
