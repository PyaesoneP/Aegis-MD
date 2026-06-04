# Guideline Sources

This directory is the local staging area for clinical guideline PDFs used by the future retrieval pipeline.

PDF files in this directory are **not committed to GitHub**. Redistribution rights vary by publisher, so the repository tracks this README as an inventory and keeps the actual PDFs local.

## Current Local Files

| Filename | Size | Source / Working Label | Intended Use |
|---|---:|---|---|
| `5506cpg1.pdf` | 310 KB | Singapore MOH clinical practice guideline | Candidate source for retrieval chunks |
| `MOH-Clinical-Practice-Guidelines-Hypertension.pdf` | 714 KB | Singapore MOH hypertension guideline | Candidate source for retrieval chunks |
| `STI-Guidelines-2021.pdf` | 4.3 MB | STI guideline document | Candidate source; confirm scope before indexing |
| `EPR-3_Asthma_Full_Report_2007.pdf` | 3.7 MB | NHLBI asthma full report | Candidate source for respiratory triage context |
| `pocket_booklet_hospital_care_0.pdf` | 11 MB | WHO pocket booklet / hospital care document | Candidate source for pediatric and general hospital-care context |
| `emergency_triage_education_kit_-_second_edition.pdf` | 5.9 MB | Emergency Triage Education Kit, second edition | Candidate source for triage urgency framing |
| `participant_manual.pdf` | 598 KB | Participant manual | Candidate source; confirm topic and license before indexing |

## Git Policy

The actual PDFs should remain local-only and ignored by Git:

```gitignore
data/guidelines/*.pdf
```

Commit only lightweight metadata such as this file, source notes, extraction scripts, or checksums if needed.

## Future Retrieval Pipeline

The planned backend retrieval flow should:

1. Read local PDFs from this directory.
2. Extract text into small chunks with source metadata.
3. Build a local ChromaDB index from those chunks.
4. Store generated vector data in a gitignored directory such as `data/chroma/`.
5. Return top-k guideline chunks to the triage orchestration layer.

## Before Indexing

For each PDF, confirm:

- the official source URL;
- redistribution and non-commercial use terms;
- whether the document is appropriate for triage-only research use;
- the preferred citation label to expose in API responses.

Do not expose raw PDF contents directly through the API. The backend should return short citation labels and generated rationale, not large copied passages.
