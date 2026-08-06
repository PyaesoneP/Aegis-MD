"""Unit tests for chunk metadata enrichment (issue #44).

Covers ``build_chunk_metadata`` (empty/None handling, delimited-encoding of the
list fields, and registry fallbacks) and ``resolve_document_metadata`` (every
registry entry exposes the four enrichment fields ``year_published``,
``ats_level``, ``symptom_tags`` and ``document_type``).
"""

from __future__ import annotations

from data.chroma.chunk import (
    build_chunk_metadata,
    resolve_document_metadata,
    DOCUMENT_REGISTRY,
)

ENRICHED_FIELDS = frozenset(
    {"year_published", "ats_level", "symptom_tags", "document_type"}
)


def _file_metadata(**overrides: object) -> dict:
    """Return a minimal ``resolve_document_metadata``-shaped dict.

    None values are the neutral state for the optional fields (the shape the
    fallback path in ``resolve_document_metadata`` returns); callers overlay
    concrete values via ``overrides``.
    """
    base: dict = {
        "source_url": "https://example.test/source.pdf",
        "citation_label": "Example Doc",
        "document_tier": "tier_2",
        "year_published": None,
        "ats_level": [],
        "symptom_tags": [],
        "document_type": "unknown",
    }
    base.update(overrides)
    return base


# ── build_chunk_metadata: core & empty/None handling ──────────────────────


class TestBuildChunkMetadata:
    def test_base_keys_always_present(self) -> None:
        meta = build_chunk_metadata(_file_metadata(), page_number=3)

        assert meta["source"] == "Example Doc"
        assert meta["page_number"] == 3
        assert meta["document_tier"] == "tier_2"

    def test_source_key_derived_from_citation_label(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(citation_label="NICE NG232"), page_number=1
        )

        assert meta["source"] == "NICE NG232"
        assert meta["source_url"] == "https://example.test/source.pdf"

    def test_omits_none_year_published(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(year_published=None), page_number=1
        )

        assert "year_published" not in meta

    def test_includes_year_published_when_set(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(year_published=2024), page_number=1
        )

        assert meta["year_published"] == 2024

    def test_omits_empty_ats_level(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(ats_level=[]), page_number=1
        )

        assert "ats_level" not in meta

    def test_omits_empty_symptom_tags(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(symptom_tags=[]), page_number=1
        )

        assert "symptom_tags" not in meta

    def test_omits_empty_document_type(self) -> None:
        # document_type is the one optional field that may legitimately be
        # absent from a caller-provided dict; it must be dropped, not stored
        # as None.
        meta = build_chunk_metadata(
            _file_metadata(document_type=""), page_number=1
        )

        assert "document_type" not in meta

    def test_all_optional_fields_emitted_when_populated(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(
                year_published=2020,
                ats_level=["ATS-3", "ATS-4"],
                symptom_tags=["head_injury", "trauma"],
                document_type="clinical_guideline",
            ),
            page_number=7,
        )

        assert meta["year_published"] == 2020
        assert meta["ats_level"] == ["ATS-3", "ATS-4"]
        assert meta["symptom_tags"] == ["head_injury", "trauma"]
        assert meta["document_type"] == "clinical_guideline"


# ── build_chunk_metadata: delimited-encoding caveat ────────────────────────


class TestBuildChunkMetadataDelimitedEncoding:
    """List fields are stored as lists by the builder; Chroma round-trip may
    later surface them as delimited strings, which is the consumer's concern.
    Here we pin the builder's onward contract: list values stay lists.
    """

    def test_ats_level_preserved_as_list(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(ats_level=["ATS-1", "ATS-5"]), page_number=1
        )

        assert isinstance(meta.get("ats_level"), list)
        assert meta["ats_level"] == ["ATS-1", "ATS-5"]

    def test_symptom_tags_preserved_as_list(self) -> None:
        meta = build_chunk_metadata(
            _file_metadata(
                symptom_tags=["paediatric", "fever", "emergency_signs"]
            ),
            page_number=1,
        )

        assert isinstance(meta.get("symptom_tags"), list)
        assert meta["symptom_tags"] == [
            "paediatric",
            "fever",
            "emergency_signs",
        ]

    def test_chroma_none_rejection_guard(self) -> None:
        # Chroma rejects None metadata values: no field in the emitted dict
        # may be None.
        meta = build_chunk_metadata(_file_metadata(), page_number=1)

        assert all(v is not None for v in meta.values())


# ── resolve_document_metadata: registry entries & fallbacks ────────────────


class TestResolveDocumentMetadata:
    def test_every_registry_entry_exposes_expected_layout(self) -> None:
        for pattern in DOCUMENT_REGISTRY:
            probe = pattern.replace(" ", "-").replace("  ", "_")
            metadata = resolve_document_metadata(f"{probe}.pdf")

            assert metadata["source_url"] == DOCUMENT_REGISTRY[pattern][
                "source_url"
            ]
            assert metadata["citation_label"] == DOCUMENT_REGISTRY[pattern][
                "citation_label"
            ]
            assert metadata["document_tier"] == DOCUMENT_REGISTRY[pattern][
                "tier"
            ]

    def test_every_registry_entry_has_the_four_enrichment_fields(
        self,
    ) -> None:
        for pattern in DOCUMENT_REGISTRY:
            probe = pattern.replace(" ", "-").replace("  ", "_")
            metadata = resolve_document_metadata(f"{probe}.pdf")

            for field in ENRICHED_FIELDS:
                assert field in metadata, (
                    f"registry entry '{pattern}' missing enrichment field "
                    f"'{field}'"
                )
            expected = DOCUMENT_REGISTRY[pattern]
            assert metadata["ats_level"] == expected["ats_level"]
            assert metadata["symptom_tags"] == expected["symptom_tags"]
            assert metadata["document_type"] == expected["document_type"]
            assert metadata["year_published"] == expected["year_published"]

    def test_year_published_passthrough(self) -> None:
        metadata = resolve_document_metadata("Emergency_Severity_Index.pdf")

        assert metadata["year_published"] == 2020

    def test_unknown_document_falls_back_to_tier_3(self) -> None:
        metadata = resolve_document_metadata("totally_unknown_doc.pdf")

        assert metadata == {
            "source_url": "N/A",
            "citation_label": "totally_unknown_doc",
            "document_tier": "tier_3",
            "year_published": None,
            "ats_level": [],
            "symptom_tags": [],
            "document_type": "unknown",
        }

    def test_fallback_builds_chroma_safe_metadata(self) -> None:
        file_metadata = resolve_document_metadata("unregistered_manual.pdf")
        meta = build_chunk_metadata(file_metadata, page_number=1)

        assert meta["document_tier"] == "tier_3"
        assert meta["document_type"] == "unknown"
        assert "year_published" not in meta
        assert "ats_level" not in meta
        assert "symptom_tags" not in meta