# Guideline Sources

This directory is the local staging area for clinical guideline PDFs used by the retrieval pipeline.

PDF files in this directory are **not committed to GitHub**. Redistribution rights vary by publisher, so the repository tracks this README as an inventory and keeps the actual PDFs local.

## Corpus Overview

| Metric | Value |
|--------|-------|
| Total documents | 18 |
| Indexed (approved by quality gate) | 15 |
| Staged, pending review (conditional) | 3 |
| Tier 1 (triage-specific) | 4 |
| Tier 2 (specialty ED-relevant) | 6 |
| Tier 3 (supplementary) | 8 |
| Max file size | 50 MB per document |

**Indexed vs staged:** only documents that pass the [assessment pipeline](#assessment-pipeline)
with status `approved` are indexed into ChromaDB. The 3 `conditional` documents below
are staged locally but excluded from retrieval until manually reviewed and promoted.

## Full Inventory

### Tier 1 — Triage-Specific Frameworks (Highest Priority)

| Filename | Size | Source | Citation Label | License | Status |
|---|---:|---|---|---|---|
| `emergency_triage_education_kit_-_second_edition.pdf` | 5.9 MB | ACSQHC Australia, 2024 | ETEK 2nd Ed | CC BY 3.0 AU | Active |
| `Emergency Department Triage.pdf` | 320 KB | ACEP/ENA, 2025 | ACEP/ENA Triage Policy | ACEP/ENA Policy | Active |
| `97517282-Triage-in-the-Hospital.pdf` | — | Scribd (original publisher unknown) | Triage in the Hospital | Scribd terms | Gated (pending review) |
| `Emergency_Severity_Index_Handbook.pdf` | — | ENA, 2020 | ESI Handbook | ENA Policy | Active |

### Tier 2 — Specialty Guidelines (ED-Relevant)

| Filename | Size | Source | Citation Label | License | Status |
|---|---:|---|---|---|---|
| `WHO-ICRC-Basic-Emergency-Care.pdf` | 4.1 MB | WHO/ICRC, 2018 | WHO BEC | CC BY-NC-SA 3.0 IGO | Active |
| `iitt_adult.pdf` | 53 KB | WHO/ICRC/MSF, 2020 | WHO IITT | WHO Open Access | Active |
| `NICE-head-injury.pdf` | 320 KB | NICE (CG176, updated to NG232), 2023 | NICE Head Injury NG232 | OGL v3.0 | Active |
| `Six-to-Help-Fix-Acute-Medicine-Guidance-for-improving-in-hospital-flow-FINAL-V1-July-2023.pdf` | 630 KB | GIRFT/SAM, 2023 | Six to Help Acute Medicine | NHS/GIRFT open | Active |
| `Management_of_Acute_Pain_in_Adults_2024_v1.pdf` | 764 KB | RCEM, 2024 | RCEM Acute Pain | RCEM | Gated (pending review) |
| `Management-of-patients-with-Haemophilia-in-Emergency-Departments.pdf` | 409 KB | NF MASAC 257, 2019 | Haemophilia Emergency Management | NF open access | Active |

### Tier 3 — Supplementary Guidelines

| Filename | Size | Source | Citation Label | License | Status |
|---|---:|---|---|---|---|
| `RCEM_Best_Practice_Invasive_Procedures_in_the_Emergency_Department.pdf` | 404 KB | RCEM, 2024 | RCEM Invasive Procedures | RCEM | Gated (pending review) |
| `9789241548373_eng.pdf` | — | WHO SEARO, 2021 | WHO IMAI Hospital Care | CC BY-NC-SA 3.0 IGO | Active |
| `pocket_booklet_hospital_care_0.pdf` | 11 MB | WHO, 2nd Ed | WHO Hospital Care Children | CC BY-NC-SA | Active |
| `pediatrics.pdf` | — | ACEP, 2003 (Ann Emerg Med) | ACEP Pediatric Fever | ACEP Policy | Active |
| `5506cpg1.pdf` | 310 KB | Singapore MOH, 2017 | MOH CPG General | SG govt pub. | Active |
| `MOH-Clinical-Practice-Guidelines-Hypertension.pdf` | 714 KB | Singapore MOH/SMJ, 2017 | MOH Hypertension | SG govt pub. | Active |
| `STI-Guidelines-2021.pdf` | 4.3 MB | CDC, 2021 | STI Guidelines 2021 | Public Domain | Active |
| `EPR-3_Asthma_Full_Report_2007.pdf` | 3.7 MB | NHLBI, 2007 | NHLBI Asthma EPR-3 | Public Domain | Active |

## Source References

Full source URLs, license details, and download links are recorded in [`SOURCES.md`](./SOURCES.md).

## Git Policy

The actual PDFs should remain local-only and ignored by Git:

```gitignore
data/guidelines/*.pdf
```

Commit only lightweight metadata such as this file, `SOURCES.md`, extraction scripts, or checksums if needed.

## Retrieval Pipeline

The backend retrieval flow:

1. Reads local PDFs from this directory.
2. Extracts text into chunks with enriched metadata (source, page, citation label, document tier, plus the enrichment fields `year_published`, `ats_level`, `symptom_tags`, `document_type`).
3. Builds a local ChromaDB index from those chunks.
4. Stores generated vector data in a gitignored directory (`data/chroma/chroma_db/`).
5. Returns top-k guideline chunks to the triage orchestration layer.

### Enrichment Metadata Fields

`chunk.py` decorates each chunk with **four** built-from-the-registry fields that
support retrieval routing and explainability, in addition to the core `source`,
`page_number`, `source_url`, and `document_tier` metadata:

| Field | Type | Content |
|---|---|---|
| `year_published` | `int \| None` | Year the document was published (from `DOCUMENT_REGISTRY`). Omitted when unknown/`None` rather than stored as a Chroma-invalid null. |
| `ats_level` | `list[str]` | Subset of ATS categories (`ATS-1`…`ATS-5`) the document most informs. Omitted when empty. |
| `symptom_tags` | `list[str]` | Lowercase presentation keywords (`head_injury`, `paediatric`, `hypertension`, …). Omitted when empty. |
| `document_type` | `str` | Kind of source (`triage_framework`, `clinical_guideline`, `handbook`, …). Always present, even as `unknown` for the fallback. |

**Delimited-encoding caveat.** The two list fields (`ats_level`, `symptom_tags`)
are a potential delimited string rather than a JSON array once round-tripped
through Chroma, so consumers (and the migration script) must parse them back
into lists. Because `build_chunk_metadata` omits empty/None fields, a missing
key means "not enriched" — readers should map it to its neutral value
(`None` / `[]` / `unknown`), which is exactly what
`scripts/migrate_metadata.py`'s `reconstruct_file_metadata` does.

## Before Indexing

For each PDF, confirm:

- the official source URL (recorded in `SOURCES.md`);
- redistribution and non-commercial use terms;
- whether the document is appropriate for triage-only research use;
- the preferred citation label to expose in API responses;
- the document is not superseded by a newer edition.

Do not expose raw PDF contents directly through the API. The backend should return short citation labels and generated rationale, not large copied passages.

## Assessment Pipeline

Before chunking, run the quality assessment gate to evaluate each PDF:

```bash
python data/guidelines/assess.py
```

This evaluates every PDF against five criteria and writes `assessment.json` (gitignored).

### Scoring Rubric

Each document receives a quality score (1–5) and a status:

| Criterion | Pass (1.0) | Partial (0.5) | Fail (0.0) |
|---|---|---|---|
| **Authority** | Gov/academic/professional body | Recognized content, unknown publisher | Unknown origin |
| **Currency** | ≤10 yrs old or foundational | — | Older, not foundational |
| **Relevance** | Triage-specific or ED-relevant | — | Unrelated |
| **Structure** | Text extractable (avg ≥100 chars/page) | — | Image-only / unreadable |
| **License** | Non-commercial research confirmed | Terms need review | Incompatible |

### Statuses

- **Approved** — passes all criteria. Indexed automatically.
- **Conditional** — minor concerns (outdated, license to verify, unknown publisher). Requires manual review before indexing.
- **Rejected** — fails a hard gate (unrecognized authority, irrelevant, unreadable, incompatible license). Excluded from indexing.

### Promoting a Conditional Document

`assessment.json` is **generated** by `assess.py` and is gitignored — edits to it are overwritten on the next run and lost on a fresh clone. The durable way to promote a conditional document is to change its metadata in the `DOCUMENT_ASSESSMENT` registry in `assess.py`, then re-run `assess.py`:

- **Outdated but foundational** — set `"foundational": True` (e.g., ESI Handbook, NHLBI Asthma EPR-3, WHO Pocket Book, ACEP Pediatric Fever).
- **License verified** — set `"license_score": 1.0` once non-commercial research use is confirmed (e.g., the RCEM documents).
- **Publisher confirmed** — set `"authority_score": 1.0` when the original publisher is identified.

### Assessment Registry

The `DOCUMENT_ASSESSMENT` dict in `assess.py` holds per-document metadata (authority, year, foundational flag, relevance, license). Its normalized pattern keys must stay in sync with `DOCUMENT_REGISTRY` in `data/chroma/chunk.py` — `tests/test_assessment.py` enforces this. New PDFs added to the corpus without a registry entry default to `rejected` status: register the document in both registries before expecting it to be indexed.

## Chunking Pipeline

Run the chunking script to build or rebuild the ChromaDB collection:

```bash
python data/chroma/chunk.py
```

This script will:
- Load `assessment.json` from the assessment pipeline (run `assess.py` first)
- Index only `approved` documents; skip `conditional` and `rejected`
- Skip files larger than 50 MB
- Enrich chunk metadata with source URL, citation label, document tier, and the four routing fields `year_published`, `ats_level`, `symptom_tags`, `document_type` (see [Enrichment Metadata Fields](#enrichment-metadata-fields))
- Clear and rebuild the ChromaDB collection
- Print a summary of documents and chunks processed
