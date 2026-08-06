#!/usr/bin/env python3
"""
In-place metadata enrichment for the Chroma "guidelines" collection.

Reads the existing collection and, for every chunk, reconstructs the original
``file_metadata`` dict from the chunk's current Chroma metadata, pulls the
page number, and recomputes the enriched metadata via
``build_chunk_metadata(file_metadata, page_number)``. Only the fields produced
by the enrichment (e.g. the new ``source`` routing key) are written back with
``collection.update(ids=..., metadatas=...)`` — the stored documents and the
embeddings are left untouched.

Usage:
  python scripts/migrate_metadata.py                  # enrich in place
  python scripts/migrate_metadata.py --dry-run        # preview only, no writes
  python scripts/migrate_metadata.py --reset          # force full recompute
  python scripts/migrate_metadata.py --dry-run --reset
"""

from __future__ import annotations

import argparse
import sys

import chromadb

from data.chroma.chunk import build_chunk_metadata

CHROMA_PATH = "data/chroma/chroma_db"
COLLECTION_NAME = "guidelines"

# Non-None keys that build_chunk_metadata may output. Used to distinguish
# enrichment fields from arbitrary legacy keys we must not touch.
ENRICHED_FIELDS = frozenset(
    {
        "source",
        "page_number",
        "source_url",
        "citation_label",
        "document_tier",
        "year_published",
        "ats_level",
        "symptom_tags",
        "document_type",
    }
)

# Fields that build_chunk_metadata consumes to reconstruct file_metadata.
FILE_METADATA_KEYS = frozenset(
    {
        "source_url",
        "citation_label",
        "document_tier",
        "year_published",
        "ats_level",
        "symptom_tags",
        "document_type",
    }
)


def reconstruct_file_metadata(current: dict) -> dict:
    """Reconstruct the original file_metadata dict from chunk metadata.

    ``build_chunk_metadata`` omits empty fields (e.g. a document with no
    ``year_published``), so a missing key here must map back to its neutral
    value — most importantly ``None`` for ``year_published`` and ``[]`` for the
    list fields — rather than being dropped entirely. Otherwise the recomputed
    metadata would differ from the originally computed one.
    """
    return {
        "source_url": current["source_url"],
        "citation_label": current["citation_label"],
        "document_tier": current["document_tier"],
        "year_published": current.get("year_published"),
        "ats_level": current.get("ats_level", []),
        "symptom_tags": current.get("symptom_tags", []),
        "document_type": current.get("document_type", "unknown"),
    }


def parse_cli(argv: list[str]) -> tuple[bool, bool]:
    """Parse --dry-run / --reset flags with minimal, self-contained CLI."""
    dry_run = False
    reset = False
    for arg in argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--reset":
            reset = True
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            sys.exit(0)
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            sys.exit(2)
    return dry_run, reset


def main() -> None:
    dry_run, reset = parse_cli(sys.argv)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    stored = collection.get(include=["documents", "metadatas"])
    ids = stored["ids"]
    metadatas = stored["metadatas"] or []

    print(f"Collection: {COLLECTION_NAME}")
    print(f"Total chunks read: {len(ids)}")

    to_update_ids: list[str] = []
    to_update_metas: list[dict] = []
    skipped: int = 0

    for chunk_id, existing in zip(ids, metadatas):
        existing = dict(existing or {})
        file_metadata = reconstruct_file_metadata(existing)
        page_number = existing.get("page_number", -1)
        enriched = build_chunk_metadata(file_metadata, page_number)

        if reset:
            # Full recompute: overwrite all enriched fields.
            delta = {k: v for k, v in enriched.items()}
        else:
            # Idempotent add: only fields that are absent or differ.
            delta = {
                k: v
                for k, v in enriched.items()
                if existing.get(k) != v
            }

        if not delta:
            skipped += 1
            continue

        to_update_ids.append(chunk_id)
        to_update_metas.append(delta)

    print(f"Candidate chunks needing state change: {len(to_update_ids)}")
    if skipped:
        print(f"Chunks already in target state (skipped): {skipped}")

    if not to_update_ids:
        print("\nNothing to do. Collection already enriched.")
        return

    if dry_run:
        print("\n[DRY-RUN] Would update the following chunks "
              f"({len(to_update_ids)}):")
        for chunk_id, meta in zip(to_update_ids, to_update_metas):
            added = ", ".join(f"{k}=" + _preview(v) for k, v in meta.items())
            print(f"  {chunk_id}")
            print(f"    -> {added}")
        print("\nNo changes written.")
        return

    # Batch update in place — collection.update overwrites only the supplied
    # metadata keys and leaves documents/embeddings untouched.
    batch_size = 1000
    for i in range(0, len(to_update_ids), batch_size):
        batch_end = min(i + batch_size, len(to_update_ids))
        collection.update(
            ids=to_update_ids[i:batch_end],
            metadatas=to_update_metas[i:batch_end],
        )

    print("\nUpdated in place:")
    print(f"  Chunks updated:     {len(to_update_ids)}")
    print(f"  Chunks unchanged:   {skipped}")
    print(f"  Collection:         {collection.name}")
    print(f"  Storage path:       {CHROMA_PATH}")
    print(f"  Mode:               {'reset' if reset else 'additive'}")
    print("=" * 60)


def _preview(value) -> str:
    """Render a metadata value for the dry-run audit, truncating lists."""
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)


if __name__ == "__main__":
    main()