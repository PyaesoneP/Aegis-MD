from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ── Document registry ─────────────────────────────────────────────────
# Maps a normalized filename substring to tier and citation metadata.
# Filenames are normalized (lowercased, "_" and "-" collapsed to spaces)
# before matching, so a single space-form key covers every separator
# variant a source file may use. Keep one entry per document.

DOCUMENT_REGISTRY: dict[str, dict] = {
    # Tier 1 — Triage-specific frameworks
    "emergency triage education kit": {
        "tier": "tier_1",
        "citation_label": "ETEK 2nd Ed",
        "source_url": "https://www.safetyandquality.gov.au/resources/emergency-triage-education-kit-etek-second-edition",
        "publication_year": 2024,
    },
    "emergency department triage": {
        "tier": "tier_1",
        "citation_label": "ACEP/ENA Triage Policy",
        "source_url": "https://www.ena.org/sites/default/files/2025-08/Emergency%20Department%20Triage.pdf",
        "publication_year": 2025,
    },
    "triage in the hospital": {
        "tier": "tier_1",
        "citation_label": "Triage in the Hospital",
        "source_url": "https://www.scribd.com/document/97517282/Triage-in-the-Hospital",
        "publication_year": None,
    },
    "emergency severity index": {
        "tier": "tier_1",
        "citation_label": "ESI Handbook",
        "source_url": "https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf",
        "publication_year": 2020,
    },
    # Tier 2 — Specialty guidelines (ED-relevant)
    "basic emergency care": {
        "tier": "tier_2",
        "citation_label": "WHO BEC",
        "source_url": "https://hlh.who.int/docs/librariesprovider4/clinical-care/who-icrc-basic-emergency-care.pdf",
        "publication_year": 2018,
    },
    "iitt": {
        "tier": "tier_2",
        "citation_label": "WHO IITT",
        "source_url": "https://cdn.who.int/media/docs/default-source/integrated-health-services-(ihs)/csy/iitt/iitt_adult.pdf",
        "publication_year": 2020,
    },
    "head injury": {
        "tier": "tier_2",
        "citation_label": "NICE Head Injury NG232",
        "source_url": "https://www.nice.org.uk/guidance/ng232",
        "publication_year": 2023,
    },
    "acute medicine": {
        "tier": "tier_2",
        "citation_label": "Six to Help Acute Medicine",
        "source_url": "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2023/07/Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf",
        "publication_year": 2023,
    },
    "acute pain": {
        "tier": "tier_2",
        "citation_label": "RCEM Acute Pain",
        "source_url": "https://www.rcem.ac.uk/Publications/",
        "publication_year": 2024,
    },
    "haemophilia": {
        "tier": "tier_2",
        "citation_label": "Haemophilia Emergency Management",
        "source_url": "https://www.bleeding.org/healthcare-professionals/guidelines-on-care/masac-documents/masac-document-257-guidelines-for-emergency-department-management-of-individuals-with-hemophilia-and-other-bleeding-disorders",
        "publication_year": 2019,
    },
    # Tier 3 — Supplementary guidelines
    "hospital care": {
        "tier": "tier_3",
        "citation_label": "WHO Hospital Care Children",
        "source_url": "https://www.who.int/publications/i/item/9789241549902",
        "publication_year": 2013,
    },
    "9789241548373": {
        "tier": "tier_3",
        "citation_label": "WHO IMAI Hospital Care",
        "source_url": "https://iris.who.int/bitstream/handle/10665/350623/9789290228882-eng.pdf",
        "publication_year": 2021,
    },
    "invasive procedures": {
        "tier": "tier_3",
        "citation_label": "RCEM Invasive Procedures",
        "source_url": "https://www.rcem.ac.uk/Publications/",
        "publication_year": 2024,
    },
    "5506cpg1": {
        "tier": "tier_3",
        "citation_label": "MOH CPG General",
        "source_url": "https://www.moh.gov.sg/hpp/doctors/guidelines/cpg_medical",
        "publication_year": 2017,
    },
    "hypertension": {
        "tier": "tier_3",
        "citation_label": "MOH Hypertension",
        "source_url": "http://www.smj.org.sg/sites/default/files/07_CPG-298122017_Hypertension.pdf",
        "publication_year": 2017,
    },
    "sti guidelines": {
        "tier": "tier_3",
        "citation_label": "STI Guidelines 2021",
        "source_url": "https://www.cdc.gov/std/treatment-guidelines/STI-Guidelines-2021.pdf",
        "publication_year": 2021,
    },
    "asthma": {
        "tier": "tier_3",
        "citation_label": "NHLBI Asthma EPR-3",
        "source_url": "https://www.nhlbi.nih.gov/guidelines/asthma",
        "publication_year": 2007,
    },
    "pediatrics": {
        "tier": "tier_3",
        "citation_label": "Pediatrics Guidelines",
        "source_url": "https://www.acep.org/siteassets/uploads/uploaded-files/acep/clinical-and-practice-management/clinical-policies/pediatrics.pdf",
        "publication_year": 2003,
    },
}


def normalize_filename(filename: str) -> str:
    """Lowercase and collapse "_"/"-" to spaces for pattern matching."""
    return filename.lower().replace("_", " ").replace("-", " ")


def resolve_document_metadata(filename: str) -> dict:
    """Return tier/citation metadata based on filename pattern matching.

    Falls back to generic tier_3 metadata when no pattern matches.
    """
    normalized = normalize_filename(filename)
    for pattern, metadata in DOCUMENT_REGISTRY.items():
        if pattern in normalized:
            return {
                "source_url": metadata["source_url"],
                "citation_label": metadata["citation_label"],
                "document_tier": metadata["tier"],
                "publication_year": metadata["publication_year"],
            }
    # Default fallback for unregistered documents
    return {
        "source_url": "N/A",
        "citation_label": Path(filename).stem,
        "document_tier": "tier_3",
        "publication_year": None,
    }


def process_pdf(file_path: Path) -> tuple[list, dict] | None:
    """Load and chunk a single PDF file.

    Returns (documents, file_metadata) on success, or None on failure.
    """
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        print(f"  SKIP: {file_path.name} exceeds 50 MB limit ({file_size / (1024*1024):.1f} MB)")
        return None

    try:
        loader = PyPDFLoader(str(file_path))
        docs = loader.load()
        if not docs:
            print(f"  SKIP: {file_path.name} yielded no pages")
            return None

        file_metadata = resolve_document_metadata(file_path.name)
        return docs, file_metadata
    except Exception as exc:
        print(f"  ERROR: {file_path.name} — {exc}")
        return None


def main():
    folder_path = Path("data/guidelines")
    all_ids: list[str] = []
    all_docs: list = []
    all_metadatas: list[dict] = []
    files_processed = 0
    files_skipped = 0
    total_chunks = 0

    pdf_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        print("No PDF files found in data/guidelines/")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in data/guidelines/")
    print()

    for file_path in pdf_files:
        print(f"Processing: {file_path.name}")
        result = process_pdf(file_path)
        if result is None:
            files_skipped += 1
            continue

        docs, file_metadata = result
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, chunk_overlap=150
        )
        splits = text_splitter.split_documents(docs)

        for i, split in enumerate(splits):
            # Chroma metadata values must not be None; default missing pages to -1.
            page = split.metadata.get("page")
            page_number = page if page is not None else -1
            chunk_id = f"{file_path.stem}_p{page_number}_c{i}"
            meta = {
                "source": file_path.name,
                "page_number": page_number,
                "source_url": file_metadata["source_url"],
                "citation_label": file_metadata["citation_label"],
                "document_tier": file_metadata["document_tier"],
            }
            if file_metadata["publication_year"] is not None:
                meta["publication_year"] = file_metadata["publication_year"]
            all_ids.append(chunk_id)
            all_docs.append(split.page_content)
            all_metadatas.append(meta)

        total_chunks += len(splits)
        files_processed += 1
        print(f"  -> {len(splits)} chunks (tier: {file_metadata['document_tier']})")

    # ── Clear and rebuild collection ──────────────────────────────────
    client = chromadb.PersistentClient(path="data/chroma/chroma_db")

    # Remove existing collection if it exists
    existing = client.list_collections()
    for coll_name in [c.name for c in existing]:
        try:
            client.get_collection(name=coll_name)
            client.delete_collection(name=coll_name)
            print(f"\nCleared existing collection: {coll_name}")
        except Exception:
            pass

    collection = client.create_collection(
        name="guidelines",
        metadata={"hnsw:space": "cosine"},
    )

    # Batch add to avoid overwhelming the client
    batch_size = 500
    for i in range(0, len(all_docs), batch_size):
        batch_end = min(i + batch_size, len(all_docs))
        collection.add(
            documents=all_docs[i:batch_end],
            ids=all_ids[i:batch_end],
            metadatas=all_metadatas[i:batch_end],
        )

    print()
    print("=" * 60)
    print("Indexing complete:")
    print(f"  Files processed: {files_processed}")
    print(f"  Files skipped:   {files_skipped}")
    print(f"  Total chunks:    {total_chunks}")
    print("  Collection:      guidelines")
    print("  Storage path:    data/chroma/chroma_db")
    print("=" * 60)


if __name__ == "__main__":
    main()
