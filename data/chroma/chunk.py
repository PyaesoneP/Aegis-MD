from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
import json

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ── Quality assessment gate ───────────────────────────────────────────

ASSESSMENT_PATH = Path("data/guidelines/assessment.json")


def load_assessment() -> tuple[dict[str, dict], dict[str, dict]]:
    """Load assessment results from a single file read.

    Returns (documents, approved) where ``documents`` is the full
    assessment record map and ``approved`` contains only records whose
    status is "approved".

    Raises FileNotFoundError if assessment.json does not exist, or
    ValueError if the file is not a valid assessment schema — both
    require re-running assess.py.
    """
    if not ASSESSMENT_PATH.exists():
        raise FileNotFoundError(
            f"{ASSESSMENT_PATH} not found. "
            f"Run 'python data/guidelines/assess.py' first to assess documents."
        )
    data = json.loads(ASSESSMENT_PATH.read_text())
    documents = data.get("documents") if isinstance(data, dict) else None
    if not isinstance(documents, dict):
        raise ValueError(
            f"{ASSESSMENT_PATH} is missing the 'documents' map. "
            f"Regenerate it with 'python data/guidelines/assess.py'."
        )
    approved = {
        fname: rec
        for fname, rec in documents.items()
        if isinstance(rec, dict) and rec.get("status") == "approved"
    }
    return documents, approved


# ── Document registry ─────────────────────────────────────────────────
# Maps a normalized filename substring to tier, citation, and retrieval-
# routing metadata.
# Filenames are normalized (lowercased, "_" and "-" collapsed to spaces)
# before matching, so a single space-form key covers every separator
# variant a source file may use. Keep one entry per document.

DOCUMENT_REGISTRY: dict[str, dict] = {
    # Each entry: tier, citation_label, source_url, year_published and the
    # retrieval-routing fields ats_level / symptom_tags / document_type.
    # ats_level is the subset of ATS categories (ATS-1..5) the document most
    # informs; symptom_tags are lowercase presentation keywords; document_type
    # describes the kind of source. These enrich chunk metadata so downstream
    # retrieval can filter by urgency band and presentation.
    # Tier 1 — Triage-specific frameworks
    "emergency triage education kit": {
        "tier": "tier_1",
        "citation_label": "ETEK 2nd Ed",
        "source_url": "https://www.safetyandquality.gov.au/resources/emergency-triage-education-kit-etek-second-edition",
        "year_published": 2024,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"],
        "symptom_tags": ["general_presentation", "vital_signs", "consciousness", "pain"],
        "document_type": "triage_framework",
    },
    "emergency department triage": {
        "tier": "tier_1",
        "citation_label": "ACEP/ENA Triage Policy",
        "source_url": "https://www.ena.org/sites/default/files/2025-08/Emergency%20Department%20Triage.pdf",
        "year_published": 2025,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"],
        "symptom_tags": ["triage_scale", "general_presentation"],
        "document_type": "position_statement",
    },
    "triage in the hospital": {
        "tier": "tier_1",
        "citation_label": "Triage in the Hospital",
        "source_url": "https://www.scribd.com/document/97517282/Triage-in-the-Hospital",
        "year_published": None,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"],
        "symptom_tags": ["general_presentation"],
        "document_type": "educational_reference",
    },
    "emergency severity index": {
        "tier": "tier_1",
        "citation_label": "ESI Handbook",
        "source_url": "https://media.emscimprovement.center/documents/Emergency_Severity_Index_Handbook.pdf",
        "year_published": 2020,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4", "ATS-5"],
        "symptom_tags": ["triage_scale", "resource_utilization", "general_presentation"],
        "document_type": "handbook",
    },
    # Tier 2 — Specialty care (ED-relevant)
    "basic emergency care": {
        "tier": "tier_2",
        "citation_label": "WHO BEC",
        "source_url": "https://hlh.who.int/docs/librariesprovider4/clinical-care/who-icrc-basic-emergency-care.pdf",
        "year_published": 2018,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3"],
        "symptom_tags": ["airway", "breathing", "circulation", "shock", "trauma", "seizure"],
        "document_type": "clinical_guideline",
    },
    "iitt": {
        "tier": "tier_2",
        "citation_label": "WHO IITT",
        "source_url": "https://cdn.who.int/media/docs/default-source/integrated-health-services-(ihs)/csy/iitt/iitt_adult.pdf",
        "year_published": 2020,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4"],
        "symptom_tags": ["vital_signs", "airway", "breathing", "circulation"],
        "document_type": "triage_tool",
    },
    "head injury": {
        "tier": "tier_2",
        "citation_label": "NICE Head Injury NG232",
        "source_url": "https://www.nice.org.uk/guidance/ng232",
        "year_published": 2023,
        "ats_level": ["ATS-2", "ATS-3"],
        "symptom_tags": ["head_injury", "trauma", "vomiting", "loss_of_consciousness", "anticoagulant"],
        "document_type": "clinical_guideline",
    },
    "acute medicine": {
        "tier": "tier_2",
        "citation_label": "Six to Help Acute Medicine",
        "source_url": "https://gettingitrightfirsttime.co.uk/wp-content/uploads/2023/07/Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf",
        "year_published": 2023,
        "ats_level": ["ATS-3", "ATS-4"],
        "symptom_tags": ["hospital_flow", "clinical_deterioration"],
        "document_type": "operational_guidance",
    },
    "acute pain": {
        "tier": "tier_2",
        "citation_label": "RCEM Acute Pain",
        "source_url": "https://www.rcem.ac.uk/Publications/",
        "year_published": 2024,
        "ats_level": ["ATS-3", "ATS-4"],
        "symptom_tags": ["pain", "analgesia"],
        "document_type": "clinical_guideline",
    },
    "haemophilia": {
        "tier": "tier_2",
        "citation_label": "Haemophilia Emergency Management",
        "source_url": "https://www.bleeding.org/healthcare-professionals/guidelines-on-care/masac-documents/masac-document-257-guidelines-for-emergency-department-management-of-individuals-with-hemophilia-and-other-bleeding-disorders",
        "year_published": 2019,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3"],
        "symptom_tags": ["bleeding", "anticoagulant", "haemophilia"],
        "document_type": "clinical_guideline",
    },
    # Tier 3 — Supplementary guidelines
    "hospital care": {
        "tier": "tier_3",
        "citation_label": "WHO Hospital Care Children",
        "source_url": "https://www.who.int/publications/i/item/9789241549902",
        "year_published": 2013,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3", "ATS-4"],
        "symptom_tags": ["paediatric", "fever", "emergency_signs"],
        "document_type": "clinical_guideline",
    },
    "9789241548373": {
        "tier": "tier_3",
        "citation_label": "WHO IMAI Hospital Care",
        "source_url": "https://iris.who.int/bitstream/handle/10665/350623/9789290228882-eng.pdf",
        "year_published": 2021,
        "ats_level": ["ATS-2", "ATS-3", "ATS-4"],
        "symptom_tags": ["severe_illness", "airway", "breathing", "circulation"],
        "document_type": "clinical_manual",
    },
    "invasive procedures": {
        "tier": "tier_3",
        "citation_label": "RCEM Invasive Procedures",
        "source_url": "https://www.rcem.ac.uk/Publications/",
        "year_published": 2024,
        "ats_level": ["ATS-3", "ATS-4", "ATS-5"],
        "symptom_tags": ["procedures", "analgesia", "sedation"],
        "document_type": "procedural_guideline",
    },
    "5506cpg1": {
        "tier": "tier_3",
        "citation_label": "MOH CPG General",
        "source_url": "https://www.moh.gov.sg/hpp/doctors/guidelines/cpg_medical",
        "year_published": 2017,
        "ats_level": ["ATS-4", "ATS-5"],
        "symptom_tags": ["general_practice"],
        "document_type": "clinical_guideline",
    },
    "hypertension": {
        "tier": "tier_3",
        "citation_label": "MOH Hypertension",
        "source_url": "http://www.smj.org.sg/sites/default/files/07_CPG-298122017_Hypertension.pdf",
        "year_published": 2017,
        "ats_level": ["ATS-2", "ATS-3", "ATS-4"],
        "symptom_tags": ["hypertension", "blood_pressure", "cardiac"],
        "document_type": "clinical_guideline",
    },
    "sti guidelines": {
        "tier": "tier_3",
        "citation_label": "STI Guidelines 2021",
        "source_url": "https://www.cdc.gov/std/treatment-guidelines/STI-Guidelines-2021.pdf",
        "year_published": 2021,
        "ats_level": ["ATS-4", "ATS-5"],
        "symptom_tags": ["sti", "sexual_health", "rash", "genital"],
        "document_type": "clinical_guideline",
    },
    "asthma": {
        "tier": "tier_3",
        "citation_label": "NHLBI Asthma EPR-3",
        "source_url": "https://www.nhlbi.nih.gov/guidelines/asthma",
        "year_published": 2007,
        "ats_level": ["ATS-1", "ATS-2", "ATS-3"],
        "symptom_tags": ["asthma", "wheeze", "breathlessness", "respiratory"],
        "document_type": "clinical_guideline",
    },
    "pediatrics": {
        "tier": "tier_3",
        "citation_label": "ACEP Pediatric Fever",
        "source_url": "https://www.acep.org/siteassets/uploads/uploaded-files/acep/clinical-and-practice-management/clinical-policies/pediatrics.pdf",
        "year_published": 2003,
        "ats_level": ["ATS-2", "ATS-3", "ATS-4"],
        "symptom_tags": ["paediatric", "fever", "infant"],
        "document_type": "clinical_policy",
    },
}


def normalize_filename(filename: str) -> str:
    """Lowercase and collapse "_"/"-" to spaces for pattern matching."""
    return filename.lower().replace("_", " ").replace("-", " ")


def resolve_document_metadata(filename: str) -> dict:
    """Return tier/citation/retrieval-routing metadata by filename pattern matching.

    Falls back to generic tier_3 metadata when no pattern matches.
    """
    normalized = normalize_filename(filename)
    for pattern, metadata in DOCUMENT_REGISTRY.items():
        if pattern in normalized:
            return {
                "source_url": metadata["source_url"],
                "citation_label": metadata["citation_label"],
                "document_tier": metadata["tier"],
                "year_published": metadata["year_published"],
                "ats_level": metadata["ats_level"],
                "symptom_tags": metadata["symptom_tags"],
                "document_type": metadata["document_type"],
            }
    # Default fallback for unregistered documents
    return {
        "source_url": "N/A",
        "citation_label": Path(filename).stem,
        "document_tier": "tier_3",
        "year_published": None,
        "ats_level": [],
        "symptom_tags": [],
        "document_type": "unknown",
    }


def build_chunk_metadata(
    file_metadata: dict, page_number: int
) -> dict:
    """Build a Chroma-compatible metadata dict for one chunk.

    All values are guaranteed to be non-None (Chroma rejects None).  Keys
    whose values are empty or None are omitted entirely so that old indexes
    without the new fields can still be queried — missing keys simply mean
    "not enriched yet".

    Parameters
    ----------
    file_metadata : dict
        Output of ``resolve_document_metadata()``.
    page_number : int
        Page number (already defaulted to -1 when None).

    Returns
    -------
    dict
        Metadata ready for Chroma ``add(metadatas=...)``.
    """
    meta: dict = {
        "source": file_metadata["citation_label"],
        "page_number": page_number,
        "source_url": file_metadata["source_url"],
        "citation_label": file_metadata["citation_label"],
        "document_tier": file_metadata["document_tier"],
    }
    # Optional fields — omit when empty/None (Chroma rejects None)
    if file_metadata.get("year_published") is not None:
        meta["year_published"] = file_metadata["year_published"]
    if file_metadata.get("ats_level"):
        meta["ats_level"] = file_metadata["ats_level"]
    if file_metadata.get("symptom_tags"):
        meta["symptom_tags"] = file_metadata["symptom_tags"]
    # document_type is always present (even "unknown" for fallback)
    if dt := file_metadata.get("document_type"):
        meta["document_type"] = dt
    return meta


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
    files_gate_skipped = 0
    files_rejected = 0
    files_conditional = 0
    total_chunks = 0

    pdf_files = sorted(
        f for f in folder_path.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        print("No PDF files found in data/guidelines/")
        return

    full_assessment, approved = load_assessment()
    print(f"Found {len(pdf_files)} PDF file(s) in data/guidelines/")
    print(f"Approved for indexing: {len(approved)}")
    print()

    for file_path in pdf_files:
        if file_path.name not in approved:
            files_gate_skipped += 1
            reason = "not in assessment"
            if file_path.name in full_assessment:
                rec = full_assessment[file_path.name]
                reason = f"status={rec['status']}"
                if rec["status"] == "rejected":
                    files_rejected += 1
                elif rec["status"] == "conditional":
                    files_conditional += 1
            print(f"  SKIP (assessment): {file_path.name} — {reason}")
            continue
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
            meta = build_chunk_metadata(file_metadata, page_number)
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
    print(f"  Files processed:     {files_processed}")
    print(f"  Files skipped:       {files_skipped}")
    print(f"  Files gate-skipped:  {files_gate_skipped}")
    print(f"    Rejected:          {files_rejected}")
    print(f"    Conditional:       {files_conditional}")
    print(f"  Total chunks:        {total_chunks}")
    print("  Collection:          guidelines")
    print("  Storage path:        data/chroma/chroma_db")
    print("=" * 60)


if __name__ == "__main__":
    main()
