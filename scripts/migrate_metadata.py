#!/usr/bin/env python3
"""
In-place metadata enrichment for the Chroma "guidelines" collection.

Reads the existing collection and, for every chunk, recovers the original
file stem from the chunk id (``{stem}_p{page}_c{index}``), resolves the
authoritative ``DOCUMENT_REGISTRY`` entry via
``resolve_document_metadata``, pulls the page number, and recomputes the
enriched metadata via ``build_chunk_metadata(file_metadata, page_number)``.
Only the fields that differ are written back with
``collection.update(ids=..., metadatas=...)`` — the stored documents and the
embeddings are left untouched.

Resolution deliberately avoids ``source_url``: it is not a unique registry
key (several RCEM publications share one landing page), so URL matching
silently resolved those documents to the first matching entry.

Usage:
  python scripts/migrate_metadata.py                  # enrich in place
  python scripts/migrate_metadata.py --dry-run        # preview only, no writes
  python scripts/migrate_metadata.py --reset          # force full recompute
  python scripts/migrate_metadata.py --dry-run --reset
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb  # noqa: E402

from data.chroma.chunk import (  # noqa: E402
    build_chunk_metadata,
    resolve_document_metadata,
)

CHROMA_PATH = "data/chroma/chroma_db"
COLLECTION_NAME = "guidelines"


_CHUNK_ID_RE = re.compile(r"^(?P<stem>.+)_p(-?\d+)_c(\d+)$")


def extract_file_stem(chunk_id: str) -> str | None:
    """Recover the original file stem embedded in a chunk id.

    Index builds name chunks ``{stem}_p{page}_c{index}``, so the stem is
    everything before the final ``_p{page}_c{index}`` suffix.  Greedy
    matching keeps this correct even when the stem itself contains a
    ``_p{n}_c{m}``-shaped substring.  Returns None when the id does not
    follow that convention.
    """
    match = _CHUNK_ID_RE.match(chunk_id)
    if match is None:
        return None
    return match.group("stem")


def reconstruct_file_metadata(current: dict, chunk_id: str = "") -> dict:
    """Reconstruct the original file_metadata dict for a stored chunk.

    Resolution key priority:
      1. the file stem embedded in the chunk id — invariant across index
         versions and unique per document;
      2. the stored ``source`` field — the original filename in pre-PR
         indexes, the citation label in post-PR indexes.

    Re-resolving from the registry is what pre-PR indexes need: their stored
    metadata predates the enrichment fields (``ats_level``, ``symptom_tags``,
    ``year_published``), so reading them back from the chunk itself would
    enrich nothing.  ``source_url`` is never used: it is not unique per
    document (several RCEM publications share one landing page), so URL
    matching resolved those documents to the first matching entry.
    """
    stem = extract_file_stem(chunk_id)
    if stem is None:
        stem = current.get("source") or ""
    return resolve_document_metadata(stem)


def enrichment_delta(existing: dict, enriched: dict, reset: bool) -> dict:
    """Compute the metadata diff to write back for one chunk.

    additive mode: only fields that are absent or differ from the stored
    value, so re-running on an already-migrated chunk yields an empty diff;
    reset mode: every enriched field is rewritten.
    """
    if reset:
        return dict(enriched)
    return {k: v for k, v in enriched.items() if existing.get(k) != v}


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
        file_metadata = reconstruct_file_metadata(existing, chunk_id)
        page_number = existing.get("page_number", -1)
        enriched = build_chunk_metadata(file_metadata, page_number)
        delta = enrichment_delta(existing, enriched, reset)

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