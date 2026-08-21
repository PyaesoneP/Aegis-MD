"""Regression tests for scripts/migrate_metadata.py (PR #63 review).

Covers the registry resolution used by the in-place migration:

* ``source_url`` is NOT a unique registry key — "RCEM Acute Pain" (tier_2)
  and "RCEM Invasive Procedures" (tier_3) share
  https://www.rcem.ac.uk/Publications/, so URL matching resolved both to
  the first entry and corrupted tier/ATS/fields of the tier_3 document.
* Unregistered documents (``source_url == "N/A"``) must keep a sane
  ``citation_label`` derived from the filename, not the string ``"A"``
  produced by ``Path("N/A").stem``.
* Re-running the migration on an already-enriched chunk must yield an
  empty diff (idempotency).
"""

from __future__ import annotations

from data.chroma.chunk import build_chunk_metadata
from scripts.migrate_metadata import (
    enrichment_delta,
    extract_file_stem,
    reconstruct_file_metadata,
)

SHARED_RCEM_URL = "https://www.rcem.ac.uk/Publications/"

INVASIVE_STEM = (
    "RCEM_Best_Practice_Invasive_Procedures_in_the_Emergency_Department"
)
ACUTE_PAIN_STEM = "Management_of_Acute_Pain_in_Adults_2024_v1"


def _pre_pr_chunk(source: str, source_url: str, page_number: int = 2) -> dict:
    """Shape of a chunk stored by the pre-PR index build."""
    return {
        "source": source,
        "source_url": source_url,
        "document_tier": "tier_3",
        "page_number": page_number,
    }


# ── extract_file_stem ──────────────────────────────────────────────────


class TestExtractFileStem:
    def test_plain_chunk_id(self) -> None:
        assert extract_file_stem(
            "Management-of-patients-with-Haemophilia_p0_c3"
        ) == "Management-of-patients-with-Haemophilia"

    def test_negative_page_number(self) -> None:
        assert extract_file_stem("foo_p-1_c0") == "foo"

    def test_stem_containing_suffix_like_substring(self) -> None:
        # Greedy match must strip only the final _p{page}_c{index} suffix.
        assert extract_file_stem("report_p2_c3_p5_c7") == "report_p2_c3"

    def test_non_conforming_id_returns_none(self) -> None:
        assert extract_file_stem("legacy_chunk") is None
        assert extract_file_stem("") is None


# ── registry resolution: shared source_url must not collide ────────────


class TestReconstructWithSharedSourceUrl:
    """Bug regression: two registry entries share one source_url; the
    invasive-procedures document was being migrated as acute pain."""

    def test_invasive_procedures_resolves_to_tier_3_entry(self) -> None:
        current = _pre_pr_chunk(
            f"{INVASIVE_STEM}.pdf", SHARED_RCEM_URL
        )

        metadata = reconstruct_file_metadata(
            current, chunk_id=f"{INVASIVE_STEM}_p2_c1"
        )

        assert metadata["citation_label"] == "RCEM Invasive Procedures"
        assert metadata["document_tier"] == "tier_3"
        assert metadata["ats_level"] == ["ATS-3", "ATS-4", "ATS-5"]
        assert metadata["symptom_tags"] == [
            "procedures",
            "analgesia",
            "sedation",
        ]
        assert metadata["document_type"] == "procedural_guideline"

    def test_acute_pain_resolves_to_tier_2_entry_with_same_url(self) -> None:
        # The same source_url must still resolve to the other document
        # for its own chunks — disambiguation must work both ways.
        current = _pre_pr_chunk(f"{ACUTE_PAIN_STEM}.pdf", SHARED_RCEM_URL)

        metadata = reconstruct_file_metadata(
            current, chunk_id=f"{ACUTE_PAIN_STEM}_p0_c0"
        )

        assert metadata["citation_label"] == "RCEM Acute Pain"
        assert metadata["document_tier"] == "tier_2"
        assert metadata["ats_level"] == ["ATS-3", "ATS-4"]
        assert metadata["document_type"] == "clinical_guideline"

    def test_resolution_does_not_depend_on_stored_source_url(self) -> None:
        # Even if the stored source_url is missing or wrong, the chunk id
        # (or the stored filename) pins the correct registry entry.
        current = _pre_pr_chunk(f"{INVASIVE_STEM}.pdf", "")
        current.pop("source_url")

        metadata = reconstruct_file_metadata(
            current, chunk_id=f"{INVASIVE_STEM}_p2_c1"
        )

        assert metadata["citation_label"] == "RCEM Invasive Procedures"

    def test_falls_back_to_stored_source_field_without_chunk_id(self) -> None:
        current = _pre_pr_chunk(f"{INVASIVE_STEM}.pdf", SHARED_RCEM_URL)

        metadata = reconstruct_file_metadata(current, chunk_id="")

        assert metadata["citation_label"] == "RCEM Invasive Procedures"


# ── registry resolution: unregistered documents ────────────────────────


class TestReconstructUnregisteredDocument:
    """Bug regression: Path("N/A").stem is "A", so unregistered documents
    used to be rewritten with source/citation_label == "A"."""

    def test_source_url_unchanged_and_label_from_filename(self) -> None:
        current = _pre_pr_chunk("my_new_guideline.pdf", "N/A")

        metadata = reconstruct_file_metadata(
            current, chunk_id="my_new_guideline_p0_c0"
        )

        assert metadata["citation_label"] == "my_new_guideline"
        assert metadata["source_url"] == "N/A"
        assert metadata["document_tier"] == "tier_3"
        assert metadata["ats_level"] == []
        assert metadata["symptom_tags"] == []
        assert metadata["document_type"] == "unknown"

    def test_enriched_metadata_is_chroma_safe(self) -> None:
        current = _pre_pr_chunk("my_new_guideline.pdf", "N/A")
        metadata = reconstruct_file_metadata(
            current, chunk_id="my_new_guideline_p0_c0"
        )
        meta = build_chunk_metadata(metadata, page_number=0)

        assert meta["source"] == "my_new_guideline"
        assert meta["citation_label"] != "A"
        assert all(v is not None for v in meta.values())
        assert "ats_level" not in meta
        assert "symptom_tags" not in meta


# ── enrichment_delta ───────────────────────────────────────────────────


class TestEnrichmentDelta:
    def test_additive_adds_missing_fields(self) -> None:
        enriched = {"document_tier": "tier_3", "ats_level": ["ATS-5"]}

        assert enrichment_delta({}, enriched, reset=False) == enriched

    def test_additive_is_noop_when_already_target_state(self) -> None:
        existing = {"document_tier": "tier_3", "ats_level": ["ATS-5"]}

        assert enrichment_delta(existing, existing, reset=False) == {}

    def test_additive_keeps_only_differing_fields(self) -> None:
        existing = {"document_tier": "tier_3", "ats_level": ["ATS-3"]}
        enriched = {"document_tier": "tier_3", "ats_level": ["ATS-3", "ATS-5"]}

        assert enrichment_delta(existing, enriched, reset=False) == {
            "ats_level": ["ATS-3", "ATS-5"]
        }

    def test_reset_always_rewrites_all_enriched_fields(self) -> None:
        existing = {"document_tier": "tier_3", "ats_level": ["ATS-5"]}
        enriched = {"document_tier": "tier_3", "ats_level": ["ATS-5"]}

        assert enrichment_delta(existing, enriched, reset=True) == enriched


# ── idempotency: re-running on an enriched index is a no-op ────────────


class TestReRunOnEnrichedIndex:
    def test_enriched_invasive_chunk_yields_empty_delta(self) -> None:
        # What a post-PR index build stored for this chunk.
        existing = build_chunk_metadata(
            reconstruct_file_metadata(
                _pre_pr_chunk(f"{INVASIVE_STEM}.pdf", SHARED_RCEM_URL),
                chunk_id=f"{INVASIVE_STEM}_p2_c1",
            ),
            page_number=2,
        )

        delta = enrichment_delta(
            existing,
            build_chunk_metadata(
                reconstruct_file_metadata(existing, f"{INVASIVE_STEM}_p2_c1"),
                page_number=2,
            ),
            reset=False,
        )

        assert delta == {}

    def test_enriched_chunk_second_run_preserves_citation_label(self) -> None:
        # Under the old source_url matching, a second run rewrote the
        # invasive-procedures chunk's citation to "RCEM Acute Pain".
        existing = build_chunk_metadata(
            reconstruct_file_metadata(
                _pre_pr_chunk(f"{INVASIVE_STEM}.pdf", SHARED_RCEM_URL),
                chunk_id=f"{INVASIVE_STEM}_p2_c1",
            ),
            page_number=2,
        )
        assert existing["citation_label"] == "RCEM Invasive Procedures"

        rerun = reconstruct_file_metadata(existing, f"{INVASIVE_STEM}_p2_c1")

        assert rerun["citation_label"] == "RCEM Invasive Procedures"
        assert rerun["document_tier"] == "tier_3"
