"""Guideline quality assessment pipeline.

Evaluates each PDF in data/guidelines/ against five criteria, assigns a
quality score (1-5) and status (approved / conditional / rejected), and
writes results to assessment.json for the chunking pipeline to consume.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pypdf

CURRENT_YEAR = datetime.now(timezone.utc).year
ASSESSMENT_PATH = Path("data/guidelines/assessment.json")

# ── Document assessment registry ──────────────────────────────────────────
# Mirrors the normalize_filename / DOCUMENT_REGISTRY pattern in chunk.py.
# Keys are normalized filename substrings matched against lowercased,
# "_" / "-" collapsed filenames. One entry per document.

DOCUMENT_ASSESSMENT: dict[str, dict[str, Any]] = {
    # Tier 1 — Triage-specific frameworks
    "emergency triage education kit": {
        "authority": "Australian Commission on Safety and Quality in Health Care",
        "authority_score": 1.0,
        "publication_year": 2024,
        "foundational": False,
        "relevance": "triage_specific",
        "license": "CC BY 3.0 AU",
        "license_score": 1.0,
        "notes": "Current ETEK 2nd edition.",
    },
    "emergency department triage": {
        "authority": "ACEP / ENA",
        "authority_score": 1.0,
        "publication_year": 2025,
        "foundational": False,
        "relevance": "triage_specific",
        "license": "ACEP/ENA policy",
        "license_score": 1.0,
        "notes": "Joint ACEP/ENA triage policy statement.",
    },
    "triage in the hospital": {
        "authority": "Scribd (original publisher unknown)",
        "authority_score": 0.5,
        "publication_year": None,
        "foundational": False,
        "relevance": "triage_specific",
        "license": "Scribd terms (restricted)",
        "license_score": 0.5,
        "notes": "User-uploaded content; original publisher could not be identified.",
    },
    "emergency severity index": {
        "authority": "Emergency Nurses Association",
        "authority_score": 1.0,
        "publication_year": 2020,
        "foundational": True,
        "relevance": "triage_specific",
        "license": "ENA policy",
        "license_score": 1.0,
        "notes": "Definitive ESI algorithm reference.",
    },
    # Tier 2 — Specialty guidelines (ED-relevant)
    "basic emergency care": {
        "authority": "WHO / ICRC / IFEM",
        "authority_score": 1.0,
        "publication_year": 2018,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "CC BY-NC-SA 3.0 IGO",
        "license_score": 1.0,
        "notes": "WHO Basic Emergency Care guidelines.",
    },
    "iitt": {
        "authority": "WHO / ICRC / MSF",
        "authority_score": 1.0,
        "publication_year": 2020,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "WHO open access",
        "license_score": 1.0,
        "notes": "Interagency Integrated Triage Tool for adults.",
    },
    "head injury": {
        "authority": "NICE (UK)",
        "authority_score": 1.0,
        "publication_year": 2023,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "Open Government Licence v3.0",
        "license_score": 1.0,
        "notes": "NICE NG232 head injury triage criteria.",
    },
    "acute medicine": {
        "authority": "GIRFT / Society for Acute Medicine (NHS England)",
        "authority_score": 1.0,
        "publication_year": 2023,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "NHS/GIRFT open",
        "license_score": 1.0,
        "notes": "Six-step guidance for acute hospital flow.",
    },
    "acute pain": {
        "authority": "Royal College of Emergency Medicine",
        "authority_score": 1.0,
        "publication_year": 2024,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "RCEM (terms to verify)",
        "license_score": 0.5,
        "notes": "RCEM site requires account for some publications.",
    },
    "haemophilia": {
        "authority": "National Hemophilia Foundation (MASAC)",
        "authority_score": 1.0,
        "publication_year": 2019,
        "foundational": False,
        "relevance": "ed_relevant",
        "license": "NF open access",
        "license_score": 1.0,
        "notes": "MASAC Document 257, ED management of hemophilia.",
    },
    # Tier 3 — Supplementary guidelines
    "invasive procedures": {
        "authority": "Royal College of Emergency Medicine",
        "authority_score": 1.0,
        "publication_year": 2024,
        "foundational": False,
        "relevance": "supplementary",
        "license": "RCEM (terms to verify)",
        "license_score": 0.5,
        "notes": "RCEM site requires account for some publications.",
    },
    "9789241548373": {
        "authority": "WHO South-East Asia Regional Office",
        "authority_score": 1.0,
        "publication_year": 2021,
        "foundational": False,
        "relevance": "supplementary",
        "license": "WHO open access",
        "license_score": 1.0,
        "notes": "District clinician manual for adolescents and adults.",
    },
    "hospital care": {
        "authority": "WHO",
        "authority_score": 1.0,
        "publication_year": 2013,
        "foundational": False,
        "relevance": "supplementary",
        "license": "CC BY-NC-SA 3.0 IGO",
        "license_score": 1.0,
        "notes": "Pocket Book of Hospital Care for Children, 2nd ed.",
    },
    "5506cpg1": {
        "authority": "Ministry of Health, Singapore",
        "authority_score": 1.0,
        "publication_year": 2017,
        "foundational": False,
        "relevance": "supplementary",
        "license": "Singapore government publication",
        "license_score": 1.0,
        "notes": "General CPG framework document.",
    },
    "hypertension": {
        "authority": "Ministry of Health, Singapore",
        "authority_score": 1.0,
        "publication_year": 2017,
        "foundational": False,
        "relevance": "supplementary",
        "license": "Singapore government publication",
        "license_score": 1.0,
        "notes": "MOH hypertension CPG, 2nd ed.",
    },
    "sti guidelines": {
        "authority": "U.S. CDC",
        "authority_score": 1.0,
        "publication_year": 2021,
        "foundational": False,
        "relevance": "supplementary",
        "license": "Public domain (U.S. government)",
        "license_score": 1.0,
        "notes": "CDC STI treatment guidelines 2021.",
    },
    "asthma": {
        "authority": "U.S. NHLBI",
        "authority_score": 1.0,
        "publication_year": 2007,
        "foundational": True,
        "relevance": "supplementary",
        "license": "Public domain (U.S. government)",
        "license_score": 1.0,
        "notes": "NHLBI Asthma EPR-3, definitive respiratory guideline.",
    },
    "pediatrics": {
        "authority": "ACEP",
        "authority_score": 1.0,
        "publication_year": 2003,
        "foundational": False,
        "relevance": "supplementary",
        "license": "ACEP clinical policy",
        "license_score": 1.0,
        "notes": "ACEP clinical policy on fever in children.",
    },
}


def normalize_filename(filename: str) -> str:
    """Lowercase and collapse '_' / '-' to spaces for pattern matching."""
    return filename.lower().replace("_", " ").replace("-", " ")


def resolve_assessment_spec(filename: str) -> dict[str, Any] | None:
    """Look up assessment metadata by filename pattern.

    Returns the spec dict, or None if the document is not registered.
    """
    normalized = normalize_filename(filename)
    for pattern, spec in DOCUMENT_ASSESSMENT.items():
        if pattern in normalized:
            return spec
    return None


# ── Automated PDF structure check ─────────────────────────────────────────

MIN_CHARS_PER_PAGE = 100
MIN_NONEMPTY_RATIO = 0.8


def assess_structure(file_path: Path) -> dict[str, Any]:
    """Evaluate PDF text extractability.

    Returns {"score": 1.0|0.0, "reason": "..."} with page stats.
    """
    try:
        reader = pypdf.PdfReader(str(file_path))
    except Exception as exc:
        return {"score": 0.0, "reason": f"Cannot open PDF: {exc}"}

    pages = reader.pages
    if not pages:
        return {"score": 0.0, "reason": "PDF contains no pages"}

    char_counts = [len((page.extract_text() or "")) for page in pages]
    total_pages = len(char_counts)
    avg_chars = sum(char_counts) // total_pages
    nonempty = sum(1 for c in char_counts if c >= MIN_CHARS_PER_PAGE)
    ratio = nonempty / total_pages

    if avg_chars >= MIN_CHARS_PER_PAGE and ratio >= MIN_NONEMPTY_RATIO:
        return {
            "score": 1.0,
            "reason": (
                f"{total_pages} pages, avg {avg_chars} chars/page, "
                f"{nonempty}/{total_pages} pages with text"
            ),
        }
    return {
        "score": 0.0,
        "reason": (
            f"Insufficient extractable text: {total_pages} pages, "
            f"avg {avg_chars} chars/page, "
            f"{nonempty}/{total_pages} pages with text"
        ),
    }


# ── Scoring and status ────────────────────────────────────────────────────

RELEVANCE_PASS = {"triage_specific", "ed_relevant", "supplementary"}


def score_authority(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": spec["authority_score"],
        "reason": spec["authority"],
    }


def score_currency(spec: dict[str, Any]) -> dict[str, Any]:
    year = spec.get("publication_year")
    if year is None:
        return {"score": 0.0, "reason": "Publication year unknown"}
    age = CURRENT_YEAR - year
    if spec.get("foundational"):
        return {
            "score": 1.0,
            "reason": f"Published {year} ({age} yrs old, foundational exemption)",
        }
    if age <= 10:
        return {"score": 1.0, "reason": f"Published {year} ({age} yrs old)"}
    return {"score": 0.0, "reason": f"Published {year} ({age} yrs old, exceeds 10-yr threshold)"}


def score_relevance(spec: dict[str, Any]) -> dict[str, Any]:
    rel = spec.get("relevance", "unrelated")
    if rel in RELEVANCE_PASS:
        return {"score": 1.0, "reason": f"Relevance: {rel}"}
    return {"score": 0.0, "reason": f"Relevance: {rel} (not ED-triage relevant)"}


def score_license(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "score": spec["license_score"],
        "reason": spec["license"],
    }


def compute_status(criteria: dict[str, dict[str, Any]]) -> str:
    """Derive approved / conditional / rejected from criterion scores.

    Hard gates (reject): authority=0, relevance=0, structure=0, license=0.
    Conditional flags: currency=0, license=0.5, authority=0.5.
    """
    auth = criteria["authority"]["score"]
    curr = criteria["currency"]["score"]
    rel = criteria["relevance"]["score"]
    struct = criteria["structure"]["score"]
    lic = criteria["license"]["score"]

    if auth == 0 or rel == 0 or struct == 0 or lic == 0:
        return "rejected"
    if curr == 0 or lic == 0.5 or auth == 0.5:
        return "conditional"
    return "approved"


def compute_quality_score(criteria: dict[str, dict[str, Any]]) -> int:
    total = sum(c["score"] for c in criteria.values())
    return max(1, min(5, round(total)))


def assess_document(file_path: Path) -> dict[str, Any]:
    """Run full assessment on a single PDF.

    Returns a record dict suitable for assessment.json.
    """
    spec = resolve_assessment_spec(file_path.name)
    if spec is None:
        spec = {
            "authority": "Not in assessment registry",
            "authority_score": 0.5,
            "publication_year": None,
            "foundational": False,
            "relevance": "triage_specific",
            "license": "Unknown (not in registry)",
            "license_score": 0.5,
            "notes": "Document not found in DOCUMENT_ASSESSMENT registry.",
        }

    criteria = {
        "authority": score_authority(spec),
        "currency": score_currency(spec),
        "relevance": score_relevance(spec),
        "structure": assess_structure(file_path),
        "license": score_license(spec),
    }

    status = compute_status(criteria)
    quality_score = compute_quality_score(criteria)

    return {
        "quality_score": quality_score,
        "status": status,
        "criteria": criteria,
        "notes": spec.get("notes", ""),
    }


# ── CLI entry point ───────────────────────────────────────────────────────

def main() -> None:
    folder = Path("data/guidelines")
    pdf_files = sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        print("No PDF files found in data/guidelines/")
        return

    print(f"Assessing {len(pdf_files)} PDF file(s) in data/guidelines/")
    print()

    results: dict[str, dict[str, Any]] = {}
    for file_path in pdf_files:
        record = assess_document(file_path)
        results[file_path.name] = record

    # ── Write assessment.json ─────────────────────────────────────────
    counts = {
        "approved": sum(1 for r in results.values() if r["status"] == "approved"),
        "conditional": sum(
            1 for r in results.values() if r["status"] == "conditional"
        ),
        "rejected": sum(
            1 for r in results.values() if r["status"] == "rejected"
        ),
    }

    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "documents": results,
    }

    ASSESSMENT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Assessment written to {ASSESSMENT_PATH}")
    print()

    # ── Summary table ─────────────────────────────────────────────────
    header = f"{'Filename':<50} {'Score':>5} {'Status':<12}"
    print(header)
    print("-" * len(header))

    for fname, rec in results.items():
        status_display = rec["status"].upper()
        print(f"{fname:<50} {rec['quality_score']:>5} {status_display:<12}")

    print()
    print(f"Approved:    {counts['approved']}")
    print(f"Conditional: {counts['conditional']}")
    print(f"Rejected:    {counts['rejected']}")

    # ── Detail for non-approved docs ──────────────────────────────────
    for fname, rec in results.items():
        if rec["status"] == "rejected":
            print(f"\nREJECTED: {fname}")
            print(f"  Score: {rec['quality_score']}")
            for crit, val in rec["criteria"].items():
                print(f"  {crit}: {val['score']} — {val['reason']}")
            if rec["notes"]:
                print(f"  Notes: {rec['notes']}")
        elif rec["status"] == "conditional":
            print(f"\nCONDITIONAL: {fname}")
            print(f"  Score: {rec['quality_score']}")
            for crit, val in rec["criteria"].items():
                print(f"  {crit}: {val['score']} — {val['reason']}")
            if rec["notes"]:
                print(f"  Notes: {rec['notes']}")

    if counts["rejected"]:
        print(f"\n{counts['rejected']} document(s) rejected. "
              "These will be excluded from indexing.")


if __name__ == "__main__":
    main()
