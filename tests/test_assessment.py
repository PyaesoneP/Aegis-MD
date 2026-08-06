"""Tests for the guideline quality assessment pipeline.

Covers rubric scoring, status derivation, gate logic, and PDF structure
checks. Uses synthetic criterion dicts and generated PDF fixtures to
avoid depending on the live corpus.
"""

from __future__ import annotations

import json
from pathlib import Path

import pypdf
import pytest

from data.guidelines.assess import (
    compute_quality_score,
    compute_status,
    assess_structure,
    assess_document,
    resolve_assessment_spec,
    normalize_filename,
    DOCUMENT_ASSESSMENT,
)
from data.chroma.chunk import load_assessment, DOCUMENT_REGISTRY


# ── Helpers ────────────────────────────────────────────────────────────────

def _criteria(
    authority: float = 1.0,
    currency: float = 1.0,
    relevance: float = 1.0,
    structure: float = 1.0,
    license_: float = 1.0,
) -> dict:
    return {
        "authority": {"score": authority, "reason": "test"},
        "currency": {"score": currency, "reason": "test"},
        "relevance": {"score": relevance, "reason": "test"},
        "structure": {"score": structure, "reason": "test"},
        "license": {"score": license_, "reason": "test"},
    }


# ── Filename normalization ────────────────────────────────────────────────

class TestNormalizeFilename:
    def test_collapse_underscores(self) -> None:
        assert normalize_filename("foo_bar.pdf") == "foo bar.pdf"

    def test_collapse_hyphens(self) -> None:
        assert normalize_filename("foo-bar.pdf") == "foo bar.pdf"

    def test_mixed_separators(self) -> None:
        assert normalize_filename("foo_bar-baz.pdf") == "foo bar baz.pdf"

    def test_lowercases(self) -> None:
        assert normalize_filename("FooBar.pdf") == "foobar.pdf"


# ── Assessment spec lookup ────────────────────────────────────────────────

class TestResolveAssessmentSpec:
    def test_known_document(self) -> None:
        spec = resolve_assessment_spec("Emergency_Severity_Index_Handbook.pdf")
        assert spec is not None
        assert spec["authority_score"] == 1.0

    def test_unknown_document(self) -> None:
        spec = resolve_assessment_spec("totally_unknown_doc.pdf")
        assert spec is None


# ── Status derivation ─────────────────────────────────────────────────────

class TestComputeStatus:
    def test_approved_all_pass(self) -> None:
        assert compute_status(_criteria()) == "approved"

    def test_rejected_authority_zero(self) -> None:
        assert compute_status(_criteria(authority=0)) == "rejected"

    def test_rejected_relevance_zero(self) -> None:
        assert compute_status(_criteria(relevance=0)) == "rejected"

    def test_rejected_structure_zero(self) -> None:
        assert compute_status(_criteria(structure=0)) == "rejected"

    def test_rejected_license_zero(self) -> None:
        assert compute_status(_criteria(license_=0)) == "rejected"

    def test_conditional_currency_zero(self) -> None:
        assert compute_status(_criteria(currency=0)) == "conditional"

    def test_conditional_license_half(self) -> None:
        assert compute_status(_criteria(license_=0.5)) == "conditional"

    def test_conditional_authority_half(self) -> None:
        assert compute_status(_criteria(authority=0.5)) == "conditional"

    def test_rejected_takes_priority_over_conditional(self) -> None:
        assert (
            compute_status(_criteria(authority=0.5, license_=0))
            == "rejected"
        )


# ── Quality score computation ─────────────────────────────────────────────

class TestComputeQualityScore:
    def test_perfect_score(self) -> None:
        assert compute_quality_score(_criteria()) == 5

    def test_low_score(self) -> None:
        assert compute_quality_score(_criteria(authority=0.5, currency=0)) == 4

    def test_clamped_minimum(self) -> None:
        assert compute_quality_score(_criteria(authority=0, currency=0, relevance=0, structure=0, license_=0)) == 1

    def test_clamped_maximum(self) -> None:
        assert compute_quality_score(_criteria()) == 5


# ── PDF structure check ───────────────────────────────────────────────────

class TestAssessStructure:
    def test_blank_page_fails(self, tmp_path: Path) -> None:
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        pdf_path = tmp_path / "blank.pdf"
        with open(pdf_path, "wb") as f:
            writer.write(f)

        result = assess_structure(pdf_path)
        assert result["score"] == 0.0

    def test_text_content_passes(self, tmp_path: Path) -> None:
        pdf_path = tmp_path / "text.pdf"
        with open(pdf_path, "wb") as f:
            f.write(_build_text_pdf())

        result = assess_structure(pdf_path)
        assert result["score"] == 1.0

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = assess_structure(tmp_path / "no_such_file.pdf")
        assert result["score"] == 0.0


def _build_text_pdf() -> bytes:
    """Return minimal valid PDF with a text-bearing page."""
    content = b"BT /F1 12 Tf 72 720 Td (Hello world this is a test of text extraction used for validating the pdf structure quality assessment pipeline in the aegis md project) Tj ET"
    header = b"%PDF-1.4\n"
    obj1 = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    obj2 = b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    obj3 = b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    obj4 = (
        f"4 0 obj << /Length {len(content)} >> stream\n"
        f"{content.decode()}\n"
        "endstream endobj\n"
    ).encode()
    obj5 = b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"

    parts = [header, obj1, obj2, obj3, obj4, obj5]
    offsets: list[int] = []
    offset = 0
    for i, part in enumerate(parts):
        if i > 0:
            offsets.append(offset)
        offset += len(part)

    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
    trailer += f"{offset}\n%%EOF".encode()

    return b"".join(parts) + xref + trailer


# ── End-to-end document assessment ────────────────────────────────────────

class TestAssessDocument:
    def test_approved_document(self, tmp_path: Path) -> None:
        pdf_path = tmp_path / "Emergency_Severity_Index_Handbook.pdf"
        with open(pdf_path, "wb") as f:
            f.write(_build_text_pdf())

        record = assess_document(pdf_path)
        assert record["status"] == "approved"
        assert record["quality_score"] == 5

    def test_unknown_document_is_rejected(self, tmp_path: Path) -> None:
        pdf_path = tmp_path / "mystery_doc.pdf"
        with open(pdf_path, "wb") as f:
            f.write(_build_text_pdf())

        record = assess_document(pdf_path)
        assert record["status"] == "rejected"
        assert "registry" in record["notes"]


# ── Assessment JSON schema ────────────────────────────────────────────────

class TestAssessmentJson:
    def test_schema_structure(self, tmp_path: Path) -> None:
        pdf_path = tmp_path / "Emergency_Severity_Index_Handbook.pdf"
        with open(pdf_path, "wb") as f:
            f.write(_build_text_pdf())

        record = assess_document(pdf_path)
        assert "quality_score" in record
        assert "status" in record
        assert "criteria" in record
        assert "notes" in record
        assert isinstance(record["quality_score"], int)
        assert record["status"] in {"approved", "conditional", "rejected"}
        assert "authority" in record["criteria"]
        assert "currency" in record["criteria"]
        assert "relevance" in record["criteria"]
        assert "structure" in record["criteria"]
        assert "license" in record["criteria"]


# ── Chunking gate (data/chroma/chunk.py) ───────────────────────────────────


class TestLoadAssessment:
    def test_missing_file_raises(self, monkeypatch, tmp_path: Path) -> None:
        missing = tmp_path / "assessment.json"
        monkeypatch.setattr("data.chroma.chunk.ASSESSMENT_PATH", missing)
        with pytest.raises(FileNotFoundError):
            load_assessment()

    def test_returns_full_and_approved(self, monkeypatch, tmp_path: Path) -> None:
        assessment = tmp_path / "assessment.json"
        assessment.write_text(
            json.dumps(
                {
                    "documents": {
                        "a.pdf": {"status": "approved"},
                        "b.pdf": {"status": "rejected"},
                        "c.pdf": {"status": "conditional"},
                        "d.pdf": {"status": "approved"},
                    }
                }
            )
        )
        monkeypatch.setattr("data.chroma.chunk.ASSESSMENT_PATH", assessment)

        documents, approved = load_assessment()

        assert set(documents) == {"a.pdf", "b.pdf", "c.pdf", "d.pdf"}
        assert set(approved) == {"a.pdf", "d.pdf"}

    def test_invalid_json_raises(self, monkeypatch, tmp_path: Path) -> None:
        assessment = tmp_path / "assessment.json"
        assessment.write_text("{ not valid json")
        monkeypatch.setattr("data.chroma.chunk.ASSESSMENT_PATH", assessment)
        with pytest.raises(json.JSONDecodeError):
            load_assessment()

    def test_missing_documents_key_raises(self, monkeypatch, tmp_path: Path) -> None:
        assessment = tmp_path / "assessment.json"
        assessment.write_text(json.dumps({"schema_version": 1}))
        monkeypatch.setattr("data.chroma.chunk.ASSESSMENT_PATH", assessment)
        with pytest.raises(ValueError, match="documents"):
            load_assessment()


# ── Registry sync between assess.py and chunk.py ───────────────────────────


class TestRegistrySync:
    def test_registry_keys_match(self) -> None:
        """Every pattern in DOCUMENT_ASSESSMENT must exist in DOCUMENT_REGISTRY."""
        assert set(DOCUMENT_ASSESSMENT) == set(DOCUMENT_REGISTRY)

    def test_publication_years_match(self) -> None:
        for pattern in DOCUMENT_ASSESSMENT:
            assert (
                DOCUMENT_ASSESSMENT[pattern].get("publication_year")
                == DOCUMENT_REGISTRY[pattern]["year_published"]
            ), f"publication_year mismatch for '{pattern}'"

    def test_every_registry_entry_resolves(self) -> None:
        """Each registry pattern must match a representative normalized filename."""
        for pattern in DOCUMENT_REGISTRY:
            probe = pattern.replace(" ", "-").replace("  ", "_")
            assert resolve_assessment_spec(f"{probe}.pdf") is not None
