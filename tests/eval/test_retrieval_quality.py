"""Minimal retrieval quality check.

For each synthetic triage case, query the ChromaDB collection with the chief
complaint and verify that at least one returned chunk comes from a tier_1 or
tier_2 document.  This is not a full RAG eval (no MRR/nDCG, no human labels) —
just a sanity gate that the index surfaces triage-relevant content for known
clinical presentations.
"""

from __future__ import annotations

import pytest

from scripts.synthetic_triage_cases import CASES


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_collection():
    """Load the persisted ChromaDB collection, or skip if unavailable."""
    try:
        import chromadb  # noqa: F401
    except ImportError:
        pytest.skip("chromadb not installed")

    try:
        client = chromadb.PersistentClient(path="data/chroma/chroma_db")
        return client.get_collection(name="guidelines")
    except Exception:
        pytest.skip("guidelines collection not found — run chunk.py first")


def _query(collection, text: str, top_k: int = 3) -> list[dict]:
    """Return list of {doc, metadata} dicts for *top_k* results."""
    result = collection.query(
        query_texts=[text],
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return [
        {"content": doc, "meta": meta}
        for doc, meta in zip(result["documents"][0], result["metadatas"][0])
    ]


# ── Tests ──────────────────────────────────────────────────────────────────

def test_retrieval_coverage():
    """At least 80% of synthetic cases should retrieve tier_1 or tier_2 content.

    Low-acuity presentations (UTI, minor rash) may not match triage-specific docs —
    that's a corpus gap, not a retrieval bug. The threshold accounts for this.
    """
    collection = _get_collection()
    total = len(CASES)
    passed = 0
    failures = []

    for case in CASES:
        hits = _query(collection, case.chief_complaint)
        tiers_hit = {h["meta"].get("document_tier") for h in hits}
        if {"tier_1", "tier_2"} & tiers_hit:
            passed += 1
        else:
            failures.append(case.name)

    pct = passed / total * 100 if total else 0
    print(f"\nRetrieval tier coverage: {passed}/{total} cases ({pct:.0f}%)")
    if failures:
        print(f"  Only tier_3 hits for: {', '.join(failures)}")

    assert pct >= 80, (
        f"Retrieval tier coverage is {pct:.0f}% ({passed}/{total}). "
        f"Expected >= 80%. Cases without tier_1/tier_2 hits: {failures}"
    )
