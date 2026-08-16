#!/usr/bin/env python3
"""
In-place metadata enrichment for the Chroma "guidelines" collection.

Reads the existing collection and, for every chunk, looks up the authoritative
``DOCUMENT_REGISTRY`` by ``source_url``, reconstructs the ``file_metadata``
dict from the registry entry, pulls the page number, and recomputes the
enriched metadata via ``build_chunk_metadata(file_metadata, page_number)``.
Only the fields produced by the enrichment are written back with
``collection.update(ids=..., metadatas=...)`` — the stored documents and the
embeddings are left untouched.

Usage:
  python scripts/migrate_metadata.py                  # enrich in place
  python scripts/migrate_metadata.py --dry-run        # preview only, no writes
  python scripts/migrate_metadata.py --reset          # force full recompute
  python scripts/migrate_metadata.py --dry-run --reset
"""

from __future__ import annotations

import sys

import chromadb

from data.chroma.chunk import (
    DOCUMENT_REGISTRY,
    build_chunk_metadata,
    resolve_document_metadata,
)

CHROMA_PATH = "data/chroma/chroma_db"
COLLECTION_NAME = "guidelines"


def reconstruct_file_metadata(current: dict) -> dict:
    """Reconstruct the original file_metadata dict from the DOCUMENT_REGISTRY.

    Reads the ``source_url`` from the chunk's stored metadata and uses it to
    look up the authoritative registry entry.  This is critical: reading from
    the chunk's own stored metadata (``current``) is useless for pre-PR
    indexes because the enrichment fields (``ats_level``, ``symptom_tags``,
    ``year_published``) do not yet exist there — they would all come back as
    neutral values (``[]``, ``None``) and the migration would enrich nothing.

    Falls back to ``resolve_document_metadata`` when ``source_url`` is not in
    the registry.
    """
    source_url = current.get("source_url", "")
    # Try to find the matching registry entry by source_url
    registry_entry = None
    for pattern, entry in DOCUMENT_REGISTRY.items():
        if entry["source_url"] == source_url:
            registry_entry = entry
            break

    if registry_entry is not None:
        # Authoritative lookup — this is what pre-PR indexes need
        return {
            "source_url": registry_entry["source_url"],
            "citation_label": registry_entry["citation_label"],
            "document_tier": registry_entry["tier"],
            "year_published": registry_entry.get("year_published"),
            "ats_level": registry_entry.get("ats_level", []),
            "symptom_tags": registry_entry.get("symptom_tags", []),
            "document_type": registry_entry.get("document_type", "unknown"),
        }

    # Fallback: use resolve_document_metadata by source_url stem
    # Extract filename from URL for pattern matching
    stem = source_url.rstrip("/").split("/")[-1]
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    return resolve_document_metadata(stem)


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